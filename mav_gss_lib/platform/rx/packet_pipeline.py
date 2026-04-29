"""PacketPipeline — stateful RX packet processor.

Drives mission `PacketOps.normalize / parse / classify` and layers platform
state on top: sequencing, timestamps, duplicate-window, rate counters.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from typing import Any

from ..contract.mission import MissionSpec
from ..contract.packets import PacketEnvelope, PacketFlags

DUP_WINDOW = 1.0


class PacketPipeline:
    """Stateful platform packet pipeline for MissionSpec.packets.

    The mission owns frame/payload semantics. The platform owns sequencing,
    timestamps, duplicate-window state, and aggregate counters.
    """

    def __init__(self, mission: MissionSpec, *, max_seen_fps: int = 10_000) -> None:
        self.mission = mission
        self.max_seen_fps = max_seen_fps
        self.seen_fps: OrderedDict[Any, float] = OrderedDict()
        self.pkt_times = deque(maxlen=3600)
        self.total_count = 0
        self.packet_count = 0
        self.unknown_count = 0
        self.uplink_echo_count = 0
        self.last_arrival: float | None = None

    def reset_counts(self) -> None:
        self.total_count = 0
        self.packet_count = 0
        self.unknown_count = 0
        self.uplink_echo_count = 0
        self.seen_fps.clear()
        self.pkt_times.clear()
        self.last_arrival = None

    def process(self, meta: dict[str, Any], raw: bytes) -> PacketEnvelope:
        now = time.time()
        now_ms = int(now * 1000)

        normalized = self.mission.packets.normalize(meta, raw)
        assert isinstance(normalized.raw, (bytes, bytearray)), \
            f"normalize must return bytes, got {type(normalized.raw).__name__}"

        mission_packet = self.mission.packets.parse(normalized)
        flags = self.mission.packets.classify(mission_packet)
        assert isinstance(flags, PacketFlags), \
            f"classify returned {type(flags).__name__}, expected PacketFlags"

        is_dup = self._check_duplicate(flags.duplicate_key, now)
        is_unknown = flags.is_unknown
        is_uplink_echo = flags.is_uplink_echo

        self.total_count += 1
        if is_unknown:
            self.unknown_count += 1
        else:
            self.packet_count += 1
        if is_uplink_echo:
            self.uplink_echo_count += 1
        self._update_rate(now, is_uplink_echo, is_unknown)
        self.last_arrival = now

        warnings = list(normalized.warnings) + list(mission_packet.warnings)
        mission = dict(mission_packet.mission or {})

        return PacketEnvelope(
            seq=self.total_count,
            received_at_ms=now_ms,
            raw=normalized.raw,
            payload=normalized.payload,
            frame_type=normalized.frame_type,
            transport_meta=dict(meta),
            warnings=warnings,
            mission_payload=mission_packet.payload,
            mission=mission,
            flags=PacketFlags(
                duplicate_key=flags.duplicate_key,
                is_duplicate=is_dup,
                is_unknown=is_unknown,
                is_uplink_echo=is_uplink_echo,
                integrity_ok=flags.integrity_ok,
            ),
        )

    def _check_duplicate(self, duplicate_key: Any, now: float) -> bool:
        if duplicate_key is None:
            return False
        prev = self.seen_fps.get(duplicate_key)
        is_dup = prev is not None and (now - prev) < DUP_WINDOW
        self.seen_fps[duplicate_key] = now
        self.seen_fps.move_to_end(duplicate_key)
        if len(self.seen_fps) > self.max_seen_fps:
            for _ in range(max(1, self.max_seen_fps // 5)):
                self.seen_fps.popitem(last=False)
        return is_dup

    def _update_rate(self, now: float, is_uplink_echo: bool, is_unknown: bool) -> None:
        if not is_uplink_echo and not is_unknown:
            self.pkt_times.append(now)
        while self.pkt_times and self.pkt_times[0] <= now - 60.0:
            self.pkt_times.popleft()
