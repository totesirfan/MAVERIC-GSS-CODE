"""Command contracts for the mission boundary.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .parameters import ParamUpdate


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    message: str
    field: str | None = None
    severity: str = "error"


@dataclass(frozen=True, slots=True)
class CommandDraft:
    payload: Any


@dataclass(frozen=True, slots=True)
class EncodedCommand:
    """Fully encoded mission command + display payload.

    `raw` is the mission-built inner PDU. `cmd_id` is an optional opaque
    command label for operator-facing logs/UI. `mission_facts` is the
    opaque display dict consumed by declarative TX columns and the detail
    panel — mirrors the RX `MissionFacts.facts` shape (`{header, protocol,
    ...}`). `parameters` carries typed arguments for the detail panel,
    paralleling RX `parameters`.
    """

    raw: bytes
    cmd_id: str = ""
    src: str = ""
    guard: bool = False
    mission_facts: dict[str, Any] = field(default_factory=dict)
    parameters: tuple[ParamUpdate, ...] = ()


@dataclass(frozen=True, slots=True)
class FramedCommand:
    """Fully framed TX bytes plus mission-provided log hooks.

    The platform publishes `wire` on ZMQ exactly as returned — it does not
    add, strip, or inspect framing. `frame_label` is a short display tag
    (e.g. "AX.25", "ASM+Golay", "RAW") the platform may surface in the TX
    log envelope; platform logic does not branch on it.

    `max_payload`, when set, is the mission's admission cap for how large
    `EncodedCommand.raw` may be AFTER any mission-owned inner wrapping
    (CSP, framing headers, FEC), expressed as the size ceiling for `wire`.
    The platform enforces this on queue admission.

    `log_fields` are JSONL-safe key/value pairs the TX log merges into the
    per-command record. `log_text` is a list of pre-formatted human-readable
    lines (one per line, no trailing newline) the TX log writes alongside
    the hex dump of `wire`. Both are opaque to the platform.
    """

    wire: bytes
    frame_label: str = ""
    max_payload: int | None = None
    log_fields: dict[str, Any] = field(default_factory=dict)
    log_text: list[str] = field(default_factory=list)


class CommandOps(Protocol):
    """Optional mission command capability.

    The platform owns queue persistence, ordering, guard confirmation, delays,
    transport send state, TX logging envelope, verifier derivation from
    declarative spec rules, and column definitions (read from
    `mission.yml::ui.tx_columns`). Missions own command grammar, validation
    semantics, byte encoding, wire framing (including any mission-specific
    header/FEC/modulation-prep steps), correlation-key shape, and MTU
    admission. Display fields populate `EncodedCommand.mission_facts` /
    `parameters` for declarative rendering.
    """

    def parse_input(self, value: str | dict[str, Any]) -> CommandDraft: ...

    def validate(self, draft: CommandDraft) -> list[ValidationIssue]: ...

    def encode(self, draft: CommandDraft) -> EncodedCommand: ...

    def frame(self, encoded: EncodedCommand) -> FramedCommand: ...

    def correlation_key(self, encoded: EncodedCommand) -> tuple: ...
    """Return an opaque, hashable correlation key for this command.

    Used by the admission gate and by match_verifiers to associate inbound
    packets with open command instances. The key is mission-defined; arguments
    are commonly excluded so admission can block at per-target granularity.
    """

    def schema(self) -> dict[str, Any]: ...
