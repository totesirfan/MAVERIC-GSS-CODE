"""Packet contracts for the platform v2 mission boundary.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable, Protocol

from .rendering import PacketRendering
from .telemetry import TelemetryFragment


@dataclass(frozen=True, slots=True)
class NormalizedPacket:
    raw: bytes
    payload: bytes
    frame_type: str
    stripped_header: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MissionPacket:
    payload: Any
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PacketFlags:
    duplicate_key: Hashable | None = None
    is_duplicate: bool = False
    is_unknown: bool = False
    is_uplink_echo: bool = False


@dataclass(slots=True)
class PacketEnvelope:
    seq: int
    received_at_ms: int
    received_at_text: str
    received_at_short: str
    raw: bytes
    payload: bytes
    frame_type: str
    transport_meta: dict[str, Any]
    warnings: list[str]
    mission_payload: Any
    flags: PacketFlags
    telemetry: list[TelemetryFragment] = field(default_factory=list)
    rendering: PacketRendering | None = None


class PacketOps(Protocol):
    """Mission packet capability.

    Missions own protocol/frame semantics. The platform owns sequencing,
    timestamps, duplicate-window state, rates, logging envelope, and fallback
    behavior.
    """

    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket: ...

    def parse(self, normalized: NormalizedPacket) -> MissionPacket: ...

    def classify(self, packet: MissionPacket) -> PacketFlags: ...
