"""MAVERIC PacketOps implementation.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mav_gss_lib.missions.maveric.rx import parser as rx_ops
from mav_gss_lib.missions.maveric.ui import log_format
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.platform import MissionPacket, NormalizedPacket, PacketFlags, PacketOps


@dataclass(frozen=True, slots=True)
class MavericPacketOps(PacketOps):
    cmd_defs: dict
    nodes: NodeTable

    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket:
        frame_type = rx_ops.detect(meta)
        payload, stripped_hdr, warnings = rx_ops.normalize(frame_type, raw)
        return NormalizedPacket(
            raw=raw,
            payload=payload,
            frame_type=frame_type,
            stripped_header=stripped_hdr,
            warnings=list(warnings),
        )

    def parse(self, normalized: NormalizedPacket) -> MissionPacket:
        parsed = rx_ops.parse_packet(normalized.payload, self.cmd_defs, list(normalized.warnings))
        mission_data = dict(parsed.mission_data)
        mission_data["stripped_hdr"] = normalized.stripped_header
        return MissionPacket(payload=mission_data, warnings=list(parsed.warnings))

    def classify(self, packet: MissionPacket) -> PacketFlags:
        mission_data = packet.payload if isinstance(packet.payload, dict) else {}
        return PacketFlags(
            duplicate_key=rx_ops.duplicate_fingerprint(mission_data),
            is_unknown=log_format.is_unknown_packet(mission_data),
            is_uplink_echo=rx_ops.is_uplink_echo(mission_data, self.nodes.gs_node),
        )
