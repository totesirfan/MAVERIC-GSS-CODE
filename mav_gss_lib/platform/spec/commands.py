"""MetaCommand + Argument dataclasses.

`packet` and `allowed_packet` model the wire-envelope header in a
codec-agnostic way. The §3.6 encode pipeline composes
`meta_cmd.packet` defaults with operator overrides, allowlist-checks
against `meta_cmd.allowed_packet`, then the codec's
`complete_header` injects codec-side defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .verifier_decls import VerifierOverrideByKey, VerifierStage
from .types import HeaderValue


VerifierOverrideValue = tuple[str, ...] | VerifierOverrideByKey


@dataclass(frozen=True, slots=True)
class Argument:
    name: str
    type_ref: str
    description: str = ""
    important: bool = False


@dataclass(frozen=True, slots=True)
class MetaCommand:
    id: str
    packet: Mapping[str, HeaderValue] = field(default_factory=dict)
    allowed_packet: Mapping[str, tuple[HeaderValue, ...]] = field(default_factory=dict)
    guard: bool = False
    no_response: bool = False
    rx_only: bool = False
    deprecated: bool = False
    argument_list: tuple[Argument, ...] = ()
    description: str = ""
    verifier_override: Mapping[VerifierStage, VerifierOverrideValue] = field(default_factory=dict)


__all__ = ["Argument", "MetaCommand", "VerifierOverrideValue"]
