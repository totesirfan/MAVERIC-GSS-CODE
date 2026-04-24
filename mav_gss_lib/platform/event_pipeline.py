"""Packet event helper for platform v2.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import logging

from .mission_api import MissionSpec
from .packets import PacketEnvelope


def collect_packet_events(mission: MissionSpec, packet: PacketEnvelope) -> list[dict]:
    """Collect mission plugin events with platform-owned error isolation."""

    if mission.events is None:
        return []

    messages: list[dict] = []
    for source in mission.events.sources:
        try:
            messages.extend(list(source.on_packet(packet) or []))
        except Exception as exc:
            logging.warning("Packet event source failed for mission %s: %s", mission.id, exc)
    return messages


def collect_connect_events(mission: MissionSpec) -> list[dict]:
    """Collect mission plugin replay events for a newly connected client."""

    if mission.events is None:
        return []

    messages: list[dict] = []
    for source in mission.events.sources:
        try:
            messages.extend(list(source.on_client_connect() or []))
        except Exception as exc:
            logging.warning("Connect event source failed for mission %s: %s", mission.id, exc)
    return messages
