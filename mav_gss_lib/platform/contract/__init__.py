"""Platform/mission contract — the protocols and types missions implement.

This subpackage holds the mission/platform boundary:

    commands.py    — CommandOps + draft/encoded/framed types
    events.py      — EventOps + PacketEventSource
    http.py        — HttpOps
    mission.py     — MissionSpec + MissionContext + MissionConfigSpec + MissionPreflightFn
    packets.py     — PacketOps + envelope + normalized + flags
    parameters.py  — ParamUpdate (walker emit type, sole live-state input)
Naming convention used across `platform/`:

    contract/X.py    — defines the protocol/dataclass surface (e.g. PacketOps, CommandOps)
    rx/X.py / tx/X.py — implements the platform-side machinery for that surface

Same basename, different role. Always import explicitly:
    from mav_gss_lib.platform.contract.packets import PacketOps
    from mav_gss_lib.platform.rx.packet_pipeline import PacketPipeline

Core nouns are re-exported here for ergonomic mid-level imports:
    from mav_gss_lib.platform.contract import MissionSpec, PacketOps, CommandOps

Author:  Irfan Annuar - USC ISI SERC
"""

from .commands import (
    CommandDraft,
    CommandOps,
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
from .parameters import ParamUpdate

__all__ = [
    "CommandDraft",
    "CommandOps",
    "EncodedCommand",
    "EventOps",
    "FramedCommand",
    "HttpOps",
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
    "ParamUpdate",
    "ValidationIssue",
]
