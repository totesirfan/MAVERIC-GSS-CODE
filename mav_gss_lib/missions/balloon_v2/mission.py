"""Non-space fixture mission.

Balloon proves the platform can support a mission with no nodes, ptypes,
spacecraft routing, CSP, AX.25, or command schema.

Telemetry is intentionally absent until ported to mission.yml — the
declarative walker is the only emit path post-Task 4. balloon_v2 is silent
on the parameter stream; PacketOps + UiOps still surface inbound JSON.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mav_gss_lib.platform import (
    Cell,
    ColumnDef,
    DetailBlock,
    MissionConfigSpec,
    MissionContext,
    MissionPacket,
    MissionSpec,
    NormalizedPacket,
    PacketEnvelope,
    PacketFlags,
    PacketOps,
    PacketRendering,
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


@dataclass(frozen=True, slots=True)
class BalloonUiOps:
    def packet_columns(self) -> list[ColumnDef]:
        return [
            ColumnDef("num", "#", width="w-10", align="right"),
            ColumnDef("time", "time", width="w-[72px]"),
            ColumnDef("kind", "kind", width="w-20"),
            ColumnDef("alt", "alt", width="w-20", align="right"),
            ColumnDef("temp", "temp", width="w-20", align="right"),
            ColumnDef("gps", "gps", flex=True),
        ]

    def tx_columns(self) -> list[ColumnDef]:
        # Balloon has no CommandOps today, so /api/tx-columns returns
        # [] for this mission regardless. The verifier stub is
        # forward-compat — if Balloon grows a CommandOps later, the
        # slot is already declared here.
        return [
            ColumnDef("verifiers", "verify", width="w-[60px]", align="right", hide_if_all=[""]),
        ]

    def render_packet(self, packet: PacketEnvelope) -> PacketRendering:
        payload = packet.mission_payload if isinstance(packet.mission_payload, dict) else {}
        gps = ""
        if "lat" in payload and "lon" in payload:
            gps = f"{payload['lat']}, {payload['lon']}"
        return PacketRendering(
            columns=self.packet_columns(),
            row={
                "num": Cell(packet.seq),
                "time": Cell(packet.received_at_short, monospace=True),
                "kind": Cell(payload.get("type", "unknown"), badge=packet.flags.is_unknown),
                "alt": Cell(payload.get("alt_m"), tooltip="meters above mean sea level"),
                "temp": Cell(payload.get("temp_c"), tooltip="degrees Celsius"),
                "gps": Cell(gps),
            },
            detail_blocks=[
                DetailBlock(
                    kind="json",
                    label="Balloon Packet",
                    fields=[{"name": k, "value": str(v)} for k, v in sorted(payload.items())],
                )
            ],
        )

    def render_log_data(self, packet: PacketEnvelope) -> dict[str, Any]:
        return dict(packet.mission_payload) if isinstance(packet.mission_payload, dict) else {}

    def format_text_log(self, packet: PacketEnvelope) -> list[str]:
        payload = packet.mission_payload if isinstance(packet.mission_payload, dict) else {}
        return [f"  BALLOON     {json.dumps(payload, sort_keys=True)}"]


def build(ctx: MissionContext) -> MissionSpec:
    return MissionSpec(
        id="balloon_v2",
        name="Balloon V2",
        packets=BalloonPacketOps(),
        ui=BalloonUiOps(),
        config=MissionConfigSpec(),
    )
