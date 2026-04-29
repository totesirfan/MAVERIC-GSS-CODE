"""Packet contract — normalized/mission/envelope types plus mission PacketOps.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Hashable, Protocol

from .parameters import ParamUpdate

if TYPE_CHECKING:
    from mav_gss_lib.platform.tx.verifiers import CommandInstance, VerifierOutcome


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
    # Opaque, mission-owned structured facts safe to forward to clients/logs.
    # Generic platform code may read only ``mission["id"]``; everything under
    # ``facts`` is mission-specific and must stay out of platform contracts.
    mission: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PacketFlags:
    duplicate_key: Hashable | None = None
    is_duplicate: bool = False
    is_unknown: bool = False
    is_uplink_echo: bool = False
    # None = not checked / not applicable; True = CRC pass; False = CRC fail.
    integrity_ok: bool | None = None


@dataclass(slots=True)
class PacketEnvelope:
    seq: int
    received_at_ms: int
    raw: bytes
    payload: bytes
    frame_type: str
    transport_meta: dict[str, Any]
    warnings: list[str]
    mission_payload: Any
    flags: PacketFlags
    mission: dict[str, Any] = field(default_factory=dict)
    parameters: tuple[ParamUpdate, ...] = ()
    event_id: str = ""
    received_mono_ns: int = 0


class PacketOps(Protocol):
    """Mission packet capability.

    Missions own protocol/frame semantics. The platform owns sequencing,
    timestamps, duplicate-window state, rates, logging envelope, and fallback
    behavior.
    """

    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket: ...

    def parse(self, normalized: NormalizedPacket) -> MissionPacket: ...

    def classify(self, packet: MissionPacket) -> PacketFlags: ...

    def match_verifiers(
        self,
        envelope: "PacketEnvelope",
        open_instances: list["CommandInstance"],
        *,
        now_ms: int,
        rx_event_id: str = "",
    ) -> list[tuple[str, str, "VerifierOutcome"]]: ...
    """Match this inbound packet envelope against open instances.

    Takes the full PacketEnvelope because:
      - `envelope.mission_payload` holds mission-private parse output.
      - `rx_event_id` (passed in by the server before log write) goes
        onto `VerifierOutcome.match_event_id` so verifier outcomes can
        back-point to the matched rx_packet log entry.

    Returns a list of (instance_id, verifier_id, outcome) transitions to apply.
    Empty list when the packet doesn't match any open verifier. Mission-private
    logic handles newest-instance-wins, response routing, and
    pass/fail discrimination.
    """
