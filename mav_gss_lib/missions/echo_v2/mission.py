"""Minimal non-MAVERIC fixture mission.

Echo proves a mission can run without nodes, ptypes, routing, CSP/AX.25,
telemetry domains, custom routers, or mission-specific frontend pages —
commands are free-form ASCII lines.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mav_gss_lib.platform import (
    CommandDraft,
    CommandOps,
    EncodedCommand,
    FramedCommand,
    MissionConfigSpec,
    MissionContext,
    MissionPacket,
    MissionSpec,
    NormalizedPacket,
    PacketFlags,
    PacketOps,
    ValidationIssue,
)


@dataclass(frozen=True, slots=True)
class EchoPacketOps(PacketOps):
    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket:
        return NormalizedPacket(raw=raw, payload=raw, frame_type="RAW")

    def parse(self, normalized: NormalizedPacket) -> MissionPacket:
        return MissionPacket(payload={"hex": normalized.payload.hex()})

    def classify(self, packet: MissionPacket) -> PacketFlags:
        return PacketFlags(is_unknown=False)

    def match_verifiers(self, packet, open_instances, *, now_ms, rx_event_id=""):
        return []


@dataclass(frozen=True, slots=True)
class EchoCommandOps(CommandOps):
    def parse_input(self, value: str | dict[str, Any]) -> CommandDraft:
        if isinstance(value, dict):
            line = str(value.get("line", ""))
        else:
            line = value
        line = line.strip()
        if not line:
            raise ValueError("empty command input")
        return CommandDraft({"line": line})

    def validate(self, draft: CommandDraft) -> list[ValidationIssue]:
        return []

    def encode(self, draft: CommandDraft) -> EncodedCommand:
        line = str(draft.payload["line"])
        cmd_id = line.split()[0] if line else "echo"
        return EncodedCommand(
            raw=line.encode("ascii"),
            cmd_id=cmd_id,
            mission_facts={"header": {"cmd_id": cmd_id, "line": line}},
        )

    def frame(self, encoded: EncodedCommand) -> FramedCommand:
        return FramedCommand(wire=encoded.raw, frame_label="RAW")

    def correlation_key(self, encoded):
        return ()  # empty tuple — no verification possible without a cmd_id

    def schema(self) -> dict[str, Any]:
        return {}


def build(ctx: MissionContext) -> MissionSpec:
    return MissionSpec(
        id="echo_v2",
        name="Echo V2",
        packets=EchoPacketOps(),
        commands=EchoCommandOps(),
        config=MissionConfigSpec(),
    )
