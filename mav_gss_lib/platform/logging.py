"""Platform v2 logging envelope helpers.

This intentionally does not clean up the full historical JSON log schema.
It defines the minimum stable v2 envelope so mission/platform cutover does
not spread mission-specific fields through platform logging.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any

from .mission_api import MissionSpec
from .packets import PacketEnvelope
from .render_pipeline import format_text_log_safe, render_log_data_safe, render_packet_safe


def build_rx_log_record(
    mission: MissionSpec,
    packet: PacketEnvelope,
    version: str,
    *,
    operator: str = "",
    station: str = "",
) -> dict[str, Any]:
    """Build a platform-owned RX JSONL envelope for v2 packets."""

    rendering = packet.rendering or render_packet_safe(mission, packet)
    record: dict[str, Any] = {
        "v": version,
        "mission": mission.id,
        "mission_name": mission.name,
        "pkt": packet.seq,
        "gs_ts": packet.received_at_text,
        "operator": operator,
        "station": station,
        "frame_type": packet.frame_type,
        "tx_meta": str(packet.transport_meta.get("transmitter", "")),
        "raw_hex": packet.raw.hex(),
        "payload_hex": packet.payload.hex(),
        "raw_len": len(packet.raw),
        "payload_len": len(packet.payload),
        "duplicate": packet.flags.is_duplicate,
        "uplink_echo": packet.flags.is_uplink_echo,
        "unknown": packet.flags.is_unknown,
        "warnings": list(packet.warnings),
        "telemetry": [fragment.to_dict() for fragment in packet.telemetry],
        "_rendering": rendering.to_json(),
    }
    mission_log = render_log_data_safe(mission, packet)
    if mission_log:
        record["mission_log"] = mission_log
    return record


def format_rx_text_lines(mission: MissionSpec, packet: PacketEnvelope) -> list[str]:
    """Return mission text-log lines for a v2 packet with failure isolation."""

    return format_text_log_safe(mission, packet)
