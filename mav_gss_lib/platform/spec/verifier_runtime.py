"""derive_verifier_set — XTCE-lite verifier resolution.

Resolves a VerifierSet from a Mission's declarative verifier_rules table
and per-MetaCommand overrides for a given command id + mission facts.

Resolution order:
  1. Resolve verifier_rules.selector against mission_facts, then look up
     verifier_rules.by_key[selected.upper()] — ordered base verifier ids.
  2. If meta_commands[cmd_id].verifier_override is non-empty, REPLACE all
     verifiers whose stage matches an override key with the override's
     listed ids (in order). An empty list for a stage drops that stage.
     A keyed override resolves against its own selector, or the base
     verifier_rules.selector when omitted.
  3. For no_response commands with no explicit complete override, drop
     inherited CompleteVerifier ids.
  4. Resolve each remaining id to a VerifierSpec via mission.verifier_specs.

Author: Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any, Mapping

from mav_gss_lib.platform.tx.verifiers import (
    CheckWindow,
    VerifierSet,
    VerifierSpec,
)

from .mission import Mission
from .verifier_decls import VerifierOverrideByKey


def derive_verifier_set(
    mission: Mission,
    *,
    cmd_id: str,
    mission_facts: Mapping[str, Any],
) -> VerifierSet:
    """Resolve a VerifierSet from the mission's verifier_rules + per-command
    overrides. Returns an empty VerifierSet if no rules are declared.

    Resolution order (XTCE-lite):
    1. Resolve verifier_rules.selector against mission_facts, then look up
       verifier_rules.by_key[selected.upper()] → ordered base verifier_ids.
    2. If meta_commands[cmd_id].verifier_override is non-empty, REPLACE all
       verifiers whose stage matches an override key with the override's
       listed ids (in order). Keyed overrides resolve against their own
       selector, or verifier_rules.selector when omitted.
    3. For no_response commands with no explicit complete override, drop
       inherited CompleteVerifier ids.
    4. Resolve each id to a VerifierSpec via mission.verifier_specs[id].
    """
    rules = mission.verifier_rules
    if rules is None or not rules.by_key:
        return VerifierSet(verifiers=())

    key = _lookup_fact_path(mission_facts, rules.selector)
    if key in (None, ""):
        return VerifierSet(verifiers=())

    base_ids: list[str] = list(rules.by_key.get(str(key).upper(), ()))

    meta = mission.meta_commands.get(cmd_id)
    overrides = dict(meta.verifier_override) if meta else {}
    if meta is not None and meta.no_response and "complete" not in overrides:
        overrides["complete"] = ()
    if overrides:
        replaced_stages = set(overrides.keys())
        kept: list[str] = []
        for sid in base_ids:
            decl = mission.verifier_specs.get(sid)
            if decl is not None and decl.stage not in replaced_stages:
                kept.append(sid)
        for override in overrides.values():
            kept.extend(_resolve_override_ids(
                override,
                mission_facts=mission_facts,
                default_selector=rules.selector,
            ))
        base_ids = kept

    verifiers: list[VerifierSpec] = []
    for sid in base_ids:
        decl = mission.verifier_specs.get(sid)
        if decl is None:
            # Already validated at parse time, but be defensive.
            continue
        verifiers.append(VerifierSpec(
            verifier_id=decl.verifier_id,
            stage=decl.stage,
            check_window=CheckWindow(start_ms=decl.start_ms, stop_ms=decl.stop_ms),
            display_label=decl.display_label,
            display_tone=decl.display_tone,
        ))
    return VerifierSet(verifiers=tuple(verifiers))


def _lookup_fact_path(facts: Mapping[str, Any], path: str) -> Any:
    cur: Any = facts
    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def _resolve_override_ids(
    override: tuple[str, ...] | VerifierOverrideByKey,
    *,
    mission_facts: Mapping[str, Any],
    default_selector: str,
) -> tuple[str, ...]:
    if not isinstance(override, VerifierOverrideByKey):
        return override

    selector = override.selector or default_selector
    key = _lookup_fact_path(mission_facts, selector)
    if key in (None, ""):
        return ()
    return override.by_key.get(str(key).upper(), ())


__all__ = ["derive_verifier_set"]
