"""RX rendering helpers — safe wrappers around mission UI renderers.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import logging
from typing import Any

from ..contract.mission import MissionSpec
from ..contract.packets import PacketEnvelope
from ..contract.rendering import Cell, ColumnDef, DetailBlock, PacketRendering


def render_packet(mission: MissionSpec, packet: PacketEnvelope) -> PacketRendering:
    """Render a packet, falling back to raw data if mission rendering fails."""

    try:
        rendering = mission.ui.render_packet(packet)
    except Exception as exc:
        logging.warning("Packet renderer failed for mission %s: %s", mission.id, exc)
        rendering = fallback_packet_rendering(packet)
    packet.rendering = rendering
    return rendering


def fallback_packet_rendering(packet: PacketEnvelope) -> PacketRendering:
    """Mission-neutral rendering used when mission UI code fails."""

    return PacketRendering(
        columns=[
            ColumnDef("num", "#", width="w-10", align="right"),
            ColumnDef("time", "time", width="w-[72px]"),
            ColumnDef("frame", "frame", width="w-20"),
            ColumnDef("size", "size", width="w-12", align="right"),
            ColumnDef("hex", "hex", flex=True),
        ],
        row={
            "num": Cell(packet.seq),
            "time": Cell(packet.received_at_short, monospace=True),
            "frame": Cell(packet.frame_type),
            "size": Cell(len(packet.raw)),
            "hex": Cell(packet.raw.hex(), monospace=True),
        },
        detail_blocks=[
            DetailBlock(
                kind="raw",
                label="Raw Packet",
                fields=[
                    {"name": "Frame", "value": packet.frame_type},
                    {"name": "Size", "value": str(len(packet.raw))},
                    {"name": "Hex", "value": packet.raw.hex()},
                ],
            )
        ],
    )


def render_log_data_safe(mission: MissionSpec, packet: PacketEnvelope) -> dict[str, Any]:
    """Render mission JSON log data, isolating mission failures."""

    try:
        data = mission.ui.render_log_data(packet)
    except Exception as exc:
        logging.warning("Log data renderer failed for mission %s: %s", mission.id, exc)
        return {}
    return data if isinstance(data, dict) else {}


def format_text_log_safe(mission: MissionSpec, packet: PacketEnvelope) -> list[str]:
    """Render mission text log lines, isolating mission failures."""

    try:
        lines = mission.ui.format_text_log(packet)
    except Exception as exc:
        logging.warning("Text log renderer failed for mission %s: %s", mission.id, exc)
        return []
    return [line for line in lines if isinstance(line, str)]
