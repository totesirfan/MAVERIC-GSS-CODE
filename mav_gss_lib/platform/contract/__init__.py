"""Platform/mission contract — the protocols and types missions implement.

This subpackage holds the mission/platform boundary:

    commands.py   — CommandOps + draft/encoded/framed types
    events.py     — EventOps + PacketEventSource
    http.py       — HttpOps
    mission.py    — MissionSpec + MissionContext + MissionConfigSpec + MissionPreflightFn
    packets.py    — PacketOps + envelope + normalized + flags
    rendering.py  — Cell + ColumnDef + PacketRendering + DetailBlock + IntegrityBlock
    telemetry.py  — TelemetryOps + TelemetryExtractor + TelemetryDomainSpec
    ui.py         — UiOps

Core nouns are re-exported here for ergonomic mid-level imports:
    from mav_gss_lib.platform.contract import MissionSpec, PacketOps, CommandOps

Author:  Irfan Annuar - USC ISI SERC
"""

from .commands import (
    CommandDraft,
    CommandOps,
    CommandRendering,
    EncodedCommand,
    FramedCommand,
    ValidationIssue,
)
from .events import EventOps, PacketEventSource
from .http import HttpOps
from .mission import MissionConfigSpec, MissionContext, MissionPreflightFn, MissionSpec
from .packets import (
    MissionPacket,
    NormalizedPacket,
    PacketEnvelope,
    PacketFlags,
    PacketOps,
)
from .rendering import Cell, ColumnDef, DetailBlock, IntegrityBlock, PacketRendering
from .telemetry import (
    CatalogProvider,
    TelemetryDomainSpec,
    TelemetryExtractor,
    TelemetryOps,
)
from .ui import UiOps

__all__ = [
    "CatalogProvider",
    "Cell",
    "ColumnDef",
    "CommandDraft",
    "CommandOps",
    "CommandRendering",
    "DetailBlock",
    "EncodedCommand",
    "EventOps",
    "FramedCommand",
    "HttpOps",
    "IntegrityBlock",
    "MissionConfigSpec",
    "MissionContext",
    "MissionPacket",
    "MissionPreflightFn",
    "MissionSpec",
    "NormalizedPacket",
    "PacketEnvelope",
    "PacketEventSource",
    "PacketFlags",
    "PacketOps",
    "PacketRendering",
    "TelemetryDomainSpec",
    "TelemetryExtractor",
    "TelemetryOps",
    "UiOps",
    "ValidationIssue",
]
