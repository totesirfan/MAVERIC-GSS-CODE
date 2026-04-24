"""Telemetry extraction/ingest helpers for platform v2.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import logging

from mav_gss_lib.web_runtime.telemetry import TelemetryFragment
from mav_gss_lib.web_runtime.telemetry.router import TelemetryRouter

from .mission_api import MissionSpec
from .packets import PacketEnvelope


def extract_telemetry_fragments(mission: MissionSpec, packet: PacketEnvelope) -> list[TelemetryFragment]:
    """Run mission telemetry extractors with platform-owned error isolation."""

    if mission.telemetry is None:
        packet.telemetry = []
        return []

    fragments: list[TelemetryFragment] = []
    for extractor in mission.telemetry.extractors:
        try:
            fragments.extend(list(extractor.extract(packet) or []))
        except Exception as exc:
            logging.warning(
                "Telemetry extractor failed for mission %s: %s",
                mission.id,
                exc,
            )
    packet.telemetry = fragments
    return fragments


def ingest_packet_telemetry(router: TelemetryRouter, packet: PacketEnvelope) -> list[dict]:
    """Ingest packet telemetry into the platform router and return WS messages."""

    return router.ingest(packet.telemetry)
