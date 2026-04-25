"""Platform verifier types.

Shapes the verifier state machine consumes; no behavior. The registry that
applies behavior lives in the same module (added in a later task) and pairs
with `CheckWindow` timers and persistence.

Stage is derived from the full verifier outcome map, not a linear chain.
See docs/superpowers/specs/2026-04-24-command-verification-design.md §4.4
for the derivation rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


VerifierStage = Literal["received", "accepted", "complete", "failed"]
VerifierState = Literal["pending", "passed", "failed", "window_expired"]
InstanceStage = Literal[
    "released", "received", "accepted", "complete", "failed", "timed_out",
]


@dataclass(frozen=True, slots=True)
class CheckWindow:
    start_ms: int
    stop_ms: int


@dataclass(frozen=True, slots=True)
class VerifierSpec:
    verifier_id: str          # opaque mission-assigned
    stage: VerifierStage
    check_window: CheckWindow
    display_label: str        # e.g. "UPPM" — mission-provided
    display_tone: str         # 'info' | 'success' | 'warning' | 'danger'


@dataclass(frozen=True, slots=True)
class VerifierSet:
    verifiers: tuple[VerifierSpec, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for v in self.verifiers:
            if v.verifier_id in seen:
                raise ValueError(f"duplicate verifier_id in VerifierSet: {v.verifier_id}")
            seen.add(v.verifier_id)


@dataclass(frozen=True, slots=True)
class VerifierOutcome:
    state: VerifierState
    matched_at_ms: int | None = None
    match_event_id: str | None = None

    @classmethod
    def pending(cls) -> "VerifierOutcome":
        return cls(state="pending")

    @classmethod
    def passed(cls, *, matched_at_ms: int, match_event_id: str) -> "VerifierOutcome":
        return cls(state="passed", matched_at_ms=matched_at_ms, match_event_id=match_event_id)

    @classmethod
    def failed(cls, *, matched_at_ms: int, match_event_id: str) -> "VerifierOutcome":
        return cls(state="failed", matched_at_ms=matched_at_ms, match_event_id=match_event_id)

    @classmethod
    def window_expired(cls) -> "VerifierOutcome":
        return cls(state="window_expired")


@dataclass(slots=True)
class CommandInstance:
    instance_id: str
    correlation_key: tuple
    t0_ms: int
    cmd_event_id: str
    verifier_set: VerifierSet
    outcomes: dict[str, VerifierOutcome] = field(default_factory=dict)
    stage: InstanceStage = "released"


# ─── Registry ─────────────────────────────────────────────────────────


def _derive_stage(inst: CommandInstance) -> InstanceStage:
    """Compute an instance's stage from its verifier outcomes.

    Rules (spec §4.4):
      0. Empty VerifierSet ("verification disabled" — e.g. FTDI dest or
         fixture missions): terminal as Complete. There's nothing to wait
         for; keeping it non-terminal would block the admission gate
         indefinitely.
      1. Any FailedVerifier passed → Failed (NACK wins, even after Complete).
      2. Else CompleteVerifier passed → Complete.
      3. Else all verifier windows closed → TimedOut.
      4. Else transient: Accepted | Received | Released.
    """
    if not inst.verifier_set.verifiers:
        return "complete"

    received_specs  = [v for v in inst.verifier_set.verifiers if v.stage == "received"]
    failed_specs    = [v for v in inst.verifier_set.verifiers if v.stage == "failed"]
    complete_specs  = [v for v in inst.verifier_set.verifiers if v.stage == "complete"]

    # 1. Failed — any NACK passed.
    for spec in failed_specs:
        if inst.outcomes.get(spec.verifier_id, VerifierOutcome.pending()).state == "passed":
            return "failed"

    # 2. Complete — any CompleteVerifier passed.
    for spec in complete_specs:
        if inst.outcomes.get(spec.verifier_id, VerifierOutcome.pending()).state == "passed":
            return "complete"

    # 3. TimedOut — every window closed (passed or window_expired, not pending).
    all_closed = all(
        inst.outcomes.get(v.verifier_id, VerifierOutcome.pending()).state != "pending"
        for v in inst.verifier_set.verifiers
    )
    if all_closed:
        return "timed_out"

    # 4. Transient.
    received_passed = sum(
        1 for v in received_specs
        if inst.outcomes.get(v.verifier_id, VerifierOutcome.pending()).state == "passed"
    )
    if received_specs and received_passed == len(received_specs):
        return "accepted"
    if received_passed > 0:
        return "received"
    return "released"


_TERMINAL: tuple[InstanceStage, ...] = ("complete", "failed", "timed_out")


class VerifierRegistry:
    """In-memory registry of open command instances.

    Platform-owned, mission-agnostic. All mutation sites run on the asyncio
    event loop:
      - TxService.register(instance) on publish
      - RxService.broadcast_loop after match_verifiers (NOT the ZMQ SUB
        thread — that thread only hands raw frames off via queue.Queue)
      - Sweeper task for window_expired transitions
      - Admission gate via lookup_open(correlation_key)

    Concurrency: mutations are currently asyncio-serialized. A `threading.Lock`
    is held on every access anyway — belt-and-suspenders against future
    refactors that might introduce true cross-thread access. The lock adds
    negligible overhead (microseconds) and makes the code robust to callers
    that forget the architectural invariant.

    Terminal instances remain in `open_instances()` until `finalize_terminals()`
    is called — lets the UI observe the final state before the row becomes a
    pure history entry. The sweeper calls finalize at end of its pass.
    """

    def __init__(self) -> None:
        import threading
        self._lock = threading.Lock()
        self._by_id: dict[str, CommandInstance] = {}

    def register(self, instance: CommandInstance) -> None:
        with self._lock:
            self._by_id[instance.instance_id] = instance

    def apply(self, instance_id: str, verifier_id: str, outcome: VerifierOutcome) -> None:
        with self._lock:
            inst = self._by_id.get(instance_id)
            if inst is None:
                return
            inst.outcomes[verifier_id] = outcome
            inst.stage = _derive_stage(inst)

    def open_instances(self) -> list[CommandInstance]:
        with self._lock:
            return list(self._by_id.values())

    def lookup_open(self, correlation_key: tuple) -> CommandInstance | None:
        with self._lock:
            for inst in self._by_id.values():
                if inst.correlation_key == correlation_key and inst.stage not in _TERMINAL:
                    return inst
            return None

    def finalize_terminals(self) -> list[CommandInstance]:
        """Drop and return terminal instances. Caller logs them."""
        with self._lock:
            terminal_ids = [i.instance_id for i in self._by_id.values() if i.stage in _TERMINAL]
            return [self._by_id.pop(i) for i in terminal_ids]
