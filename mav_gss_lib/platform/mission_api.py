"""Top-level mission spec for the platform v2 architecture.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from fastapi import APIRouter

from .commands import CommandOps
from .events import EventOps
from .packets import PacketOps
from .rendering import ColumnDef, PacketRendering
from .telemetry import TelemetryOps


# Typed loosely as `Iterable[Any]` to avoid a platform → preflight import
# cycle; concrete objects are `mav_gss_lib.preflight.CheckResult`.
MissionPreflightFn = Callable[[], Iterable[Any]]


@dataclass(frozen=True, slots=True)
class MissionConfigSpec:
    schema: dict[str, Any] = field(default_factory=dict)
    editable_paths: set[str] = field(default_factory=set)
    protected_paths: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class MissionContext:
    platform_config: dict[str, Any]
    mission_config: dict[str, Any]
    data_dir: Path


@dataclass(frozen=True, slots=True)
class HttpOps:
    routers: list[APIRouter] = field(default_factory=list)


class UiOps(Protocol):
    def packet_columns(self) -> list[ColumnDef]: ...

    def tx_columns(self) -> list[ColumnDef]: ...

    def render_packet(self, packet) -> PacketRendering: ...

    def render_log_data(self, packet) -> dict[str, Any]: ...

    def format_text_log(self, packet) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class MissionSpec:
    id: str
    name: str
    packets: PacketOps
    ui: UiOps
    config: MissionConfigSpec
    commands: CommandOps | None = None
    telemetry: TelemetryOps | None = None
    events: EventOps | None = None
    http: HttpOps | None = None
    preflight: MissionPreflightFn | None = None
