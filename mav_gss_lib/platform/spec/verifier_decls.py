"""Declarative verifier types for XTCE-lite VerifierSet authoring.

A `VerifierSpecDecl` is the YAML-declared analogue of XTCE's verifier
elements (TransferredToRangeVerifier, AcceptedVerifier, CompleteVerifier,
FailedVerifier, ...). Each spec carries an opaque mission-assigned id
plus the display + window metadata the platform consumes to drive the
verifier state machine and the per-command UI tick strip.

`VerifierRules` maps a mission-selected key to the ordered list of verifier
ids expected for matching commands — the declarative analogue of XTCE's
`<BaseMetaCommand>` inheritance pattern, where the rule table is the "base"
and per-command overrides specialize. `selector` is a mission-facts path
resolved by the mission command adapter, not by the platform send loop.

`VerifierOverrideByKey` gives a command-stage override the same keyed
selection behavior, for commands whose response source depends on the
encoded packet header.

Author: Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping


VerifierStage = Literal["received", "accepted", "complete", "failed"]
VerifierTone = Literal["info", "success", "warning", "danger"]


@dataclass(frozen=True, slots=True)
class VerifierSpecDecl:
    verifier_id: str
    stage: VerifierStage
    display_label: str
    display_tone: VerifierTone
    start_ms: int = 0
    stop_ms: int = 30_000


@dataclass(frozen=True, slots=True)
class VerifierRules:
    selector: str = ""
    by_key: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerifierOverrideByKey:
    selector: str = ""
    by_key: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


__all__ = [
    "VerifierOverrideByKey",
    "VerifierSpecDecl",
    "VerifierRules",
    "VerifierStage",
    "VerifierTone",
]
