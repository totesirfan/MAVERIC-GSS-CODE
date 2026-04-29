"""Non-space fixture mission.

Balloon proves the platform can support a mission with no nodes, ptypes,
spacecraft routing, CSP, AX.25, or command schema.

Telemetry is intentionally absent until ported to mission.yml — the
declarative walker is the only emit path post-Task 4. balloon_v2 is silent
on the parameter stream; PacketOps surfaces inbound JSON for downstream
consumers.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mav_gss_lib.platform import (
    MissionConfigSpec,
    MissionContext,
    MissionPacket,
    MissionSpec,
    NormalizedPacket,
    PacketFlags,
    PacketOps,
)


@dataclass(frozen=True, slots=True)
class BalloonPacketOps(PacketOps):
    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket:
        return NormalizedPacket(raw=raw, payload=raw, frame_type="JSON")

    def parse(self, normalized: NormalizedPacket) -> MissionPacket:
        try:
            payload = json.loads(normalized.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return MissionPacket(payload={"type": "unknown", "error": str(exc)}, warnings=[str(exc)])
        if not isinstance(payload, dict):
            return MissionPacket(payload={"type": "unknown", "value": payload}, warnings=["JSON payload was not an object"])
        return MissionPacket(payload=payload)

    def classify(self, packet: MissionPacket) -> PacketFlags:
        payload = packet.payload if isinstance(packet.payload, dict) else {}
        return PacketFlags(is_unknown=payload.get("type") != "beacon")

    def match_verifiers(self, packet, open_instances, *, now_ms, rx_event_id=""):
        return []


def build(ctx: MissionContext) -> MissionSpec:
    return MissionSpec(
        id="balloon_v2",
        name="Balloon V2",
        packets=BalloonPacketOps(),
        config=MissionConfigSpec(),
    )
