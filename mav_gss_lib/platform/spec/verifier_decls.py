"""Declarative verifier types for XTCE-lite VerifierSet authoring.

A `VerifierSpecDecl` is the YAML-declared analogue of XTCE's verifier
elements (TransferredToRangeVerifier, AcceptedVerifier, CompleteVerifier,
FailedVerifier, ...). Each spec carries an opaque mission-assigned id
plus the display + window metadata the platform consumes to drive the
verifier state machine and the per-command UI tick strip.

`VerifierRules.by_dest` maps a destination node name to the ordered list
of verifier_ids expected for commands sent to that destination — the
declarative analogue of XTCE's `<BaseMetaCommand>` inheritance pattern,
where the rule table is the "base" and per-command overrides specialize.

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
    by_dest: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


__all__ = ["VerifierSpecDecl", "VerifierRules", "VerifierStage", "VerifierTone"]
