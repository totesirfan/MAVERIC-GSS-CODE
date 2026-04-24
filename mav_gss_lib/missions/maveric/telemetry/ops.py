"""MAVERIC TelemetryOps implementation.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.missions.maveric.rx.packet import MavericRxPacket
from mav_gss_lib.missions.maveric.telemetry import TELEMETRY_MANIFEST
from mav_gss_lib.missions.maveric.telemetry.extractors import EXTRACTORS
from mav_gss_lib.platform import PacketEnvelope, TelemetryDomainSpec, TelemetryOps
from mav_gss_lib.platform.telemetry import TelemetryFragment


@dataclass(frozen=True, slots=True)
class MavericTelemetryExtractor:
    nodes: NodeTable

    def extract(self, packet: PacketEnvelope) -> Iterable[TelemetryFragment]:
        pkt = MavericRxPacket.from_envelope(packet)
        fragments: list[TelemetryFragment] = []
        for extract in EXTRACTORS:
            fragments.extend(extract(pkt, self.nodes, packet.received_at_ms))
        _derive_sat_time(packet, fragments)
        return fragments


def _derive_sat_time(packet: PacketEnvelope, fragments: list[TelemetryFragment]) -> None:
    """Back-fill `ts_result` on the mission payload from a beacon time fragment.

    Command-wire packets carry `sat_time` in `cmd["sat_time"]` already; beacons
    carry the satellite clock only as an extracted fragment. Rendering / log
    formatting both read `mission_data["ts_result"]`, so this hook writes it
    once here rather than teaching each renderer to inspect fragments for a
    clock value.
    """
    if not isinstance(packet.mission_payload, dict):
        return
    if packet.mission_payload.get("ts_result") is not None:
        return
    for fragment in fragments:
        if fragment.domain != "spacecraft" or fragment.key != "time":
            continue
        unix_ms = fragment.value.get("unix_ms") if isinstance(fragment.value, dict) else None
        if unix_ms is None:
            return
        try:
            dt_utc = datetime.fromtimestamp(unix_ms / 1000.0, tz=timezone.utc)
            dt_local = dt_utc.astimezone()
        except (OSError, OverflowError, ValueError):
            return
        packet.mission_payload["ts_result"] = (dt_utc, dt_local, unix_ms)
        return


def build_telemetry_ops(nodes: NodeTable) -> TelemetryOps:
    domains = {
        name: TelemetryDomainSpec(
            merge=spec.get("merge", TelemetryDomainSpec().merge),
            load_entries=spec.get("load_entries"),
            catalog=spec.get("catalog"),
        )
        for name, spec in TELEMETRY_MANIFEST.items()
    }
    return TelemetryOps(
        domains=domains,
        extractors=[MavericTelemetryExtractor(nodes)],
    )
