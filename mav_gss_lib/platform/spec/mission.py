"""Mission root dataclass — the parser's output.

`parse_warnings` carries non-fatal authoring warnings (container shadow,
enum-slice truncation, etc.). Fatal issues raise `ParseError` instead.
The platform loader logs each warning and forwards them to the
`/ws/preflight` payload so operators see them at startup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .bitfield import BitfieldType
from .commands import MetaCommand
from .containers import SequenceContainer
from .parameters import Parameter
from .parameter_types import ParameterType


@dataclass(frozen=True, slots=True)
class MissionHeader:
    version: str
    date: str
    description: str = ""


# ---- Parse warnings (non-fatal; fatal issues raise ParseError) ----


class ParseWarning:
    """Base class for non-fatal mission-author warnings."""


@dataclass(frozen=True, slots=True)
class ContainerShadow(ParseWarning):
    broader: str
    specific: str

    def __str__(self) -> str:
        return (
            f"container {self.broader!r} (broader equality signature) precedes "
            f"{self.specific!r} (more specific) in YAML order; "
            f"{self.specific!r} will never match — reorder if intended"
        )


@dataclass(frozen=True, slots=True)
class EnumSliceTruncation(ParseWarning):
    bitfield: str
    slice_name: str
    slice_width: int
    enum_max_raw: int

    def __str__(self) -> str:
        return (
            f"bitfield {self.bitfield!r} slice {self.slice_name!r} is "
            f"{self.slice_width} bit(s) but referenced enum has max raw value "
            f"{self.enum_max_raw} — truncation hazard"
        )


@dataclass(frozen=True, slots=True)
class Mission:
    id: str
    name: str
    header: MissionHeader

    parameter_types: Mapping[str, ParameterType]
    parameters: Mapping[str, Parameter]
    bitfield_types: Mapping[str, BitfieldType]
    sequence_containers: Mapping[str, SequenceContainer]
    meta_commands: Mapping[str, MetaCommand]

    node_id_map: Mapping[str, int] = field(default_factory=dict)
    ptype_id_map: Mapping[str, int] = field(default_factory=dict)
    node_description_map: Mapping[str, str] = field(default_factory=dict)
    parse_warnings: tuple[ParseWarning, ...] = ()

    def declared_domains(self) -> frozenset[str]:
        return frozenset(
            c.domain for c in self.sequence_containers.values() if c.domain
        )


__all__ = [
    "MissionHeader",
    "Mission",
    "ParseWarning",
    "ContainerShadow",
    "EnumSliceTruncation",
]
