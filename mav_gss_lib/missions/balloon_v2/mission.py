"""Non-space fixture mission for platform v2.

Balloon proves the platform can support a mission with no nodes, ptypes,
spacecraft routing, CSP, AX.25, or command schema.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

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
    TelemetryDomainSpec,
    TelemetryOps,
)
from mav_gss_lib.web_runtime.telemetry import TelemetryFragment


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


@dataclass(frozen=True, slots=True)
class BalloonTelemetryExtractor:
    def extract(self, packet: PacketEnvelope) -> Iterable[TelemetryFragment]:
        payload = packet.mission_payload if isinstance(packet.mission_payload, dict) else {}
        if payload.get("type") != "beacon":
            return []
        out: list[TelemetryFragment] = []
        if "alt_m" in payload:
            out.append(TelemetryFragment("environment", "altitude_m", payload["alt_m"], packet.received_at_ms, unit="m"))
        if "temp_c" in payload:
            out.append(TelemetryFragment("environment", "temperature_c", payload["temp_c"], packet.received_at_ms, unit="C"))
        if "lat" in payload and "lon" in payload:
            out.append(
                TelemetryFragment(
                    "position",
                    "gps",
                    {"lat": payload["lat"], "lon": payload["lon"]},
                    packet.received_at_ms,
                )
            )
        return out


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
        return []

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


def _environment_catalog() -> list[dict[str, str]]:
    return [
        {"name": "altitude_m", "type": "float", "unit": "m"},
        {"name": "temperature_c", "type": "float", "unit": "C"},
    ]


def _position_catalog() -> list[dict[str, str]]:
    return [{"name": "gps", "type": "object", "unit": ""}]


def build(ctx: MissionContext) -> MissionSpec:
    return MissionSpec(
        id="balloon_v2",
        name="Balloon V2",
        packets=BalloonPacketOps(),
        ui=BalloonUiOps(),
        telemetry=TelemetryOps(
            domains={
                "environment": TelemetryDomainSpec(catalog=_environment_catalog),
                "position": TelemetryDomainSpec(catalog=_position_catalog),
            },
            extractors=[BalloonTelemetryExtractor()],
        ),
        config=MissionConfigSpec(),
    )
