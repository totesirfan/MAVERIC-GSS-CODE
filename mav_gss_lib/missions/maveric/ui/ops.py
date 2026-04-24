"""MAVERIC UiOps implementation for platform v2.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mav_gss_lib.missions.maveric.ui import log_format, rendering
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.missions.maveric.rx.packet import MavericRxPacket
from mav_gss_lib.platform import Cell, ColumnDef, DetailBlock, IntegrityBlock, PacketEnvelope, PacketRendering


def _detail(block: dict) -> DetailBlock:
    return DetailBlock(
        kind=str(block.get("kind", "")),
        label=str(block.get("label", "")),
        fields=list(block.get("fields", [])),
    )


@dataclass(frozen=True, slots=True)
class MavericUiOps:
    nodes: NodeTable

    def packet_columns(self) -> list[ColumnDef]:
        return [ColumnDef.from_dict(col) for col in rendering.packet_list_columns()]

    def tx_columns(self) -> list[ColumnDef]:
        return [ColumnDef.from_dict(col) for col in rendering.tx_queue_columns()]

    def render_packet(self, packet: PacketEnvelope) -> PacketRendering:
        pkt = MavericRxPacket.from_envelope(packet)
        row = rendering.packet_list_row(pkt, self.nodes)
        values = row.get("values", {})
        cells = {
            key: Cell(
                value=value,
                badge=(key == "ptype"),
                monospace=(key in {"time", "frame"}),
            )
            for key, value in values.items()
        }
        return PacketRendering(
            columns=self.packet_columns(),
            row=cells,
            detail_blocks=[_detail(block) for block in rendering.packet_detail_blocks(pkt, self.nodes)],
            protocol_blocks=[_detail(asdict(block)) for block in rendering.protocol_blocks(pkt)],
            integrity_blocks=[
                IntegrityBlock(**asdict(block))
                for block in rendering.integrity_blocks(pkt)
            ],
        )

    def render_log_data(self, packet: PacketEnvelope) -> dict[str, Any]:
        return log_format.build_log_mission_data(MavericRxPacket.from_envelope(packet))

    def format_text_log(self, packet: PacketEnvelope) -> list[str]:
        return log_format.format_log_lines(MavericRxPacket.from_envelope(packet), self.nodes)
