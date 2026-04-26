"""derive_verifier_set — XTCE-lite verifier resolution.

Resolves a VerifierSet from a Mission's declarative verifier_rules table
and per-MetaCommand overrides for a given (cmd_id, dest) pair.

Resolution order:
  1. Look up verifier_rules.by_dest[dest.upper()] — ordered base verifier ids.
  2. If meta_commands[cmd_id].verifier_override is non-empty, REPLACE all
     verifiers whose stage matches an override key with the override's
     listed ids (in order). An empty list for a stage drops that stage.
  3. Resolve each remaining id to a VerifierSpec via mission.verifier_specs.

Author: Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from mav_gss_lib.platform.tx.verifiers import (
    CheckWindow,
    VerifierSet,
    VerifierSpec,
)

from .mission import Mission


def derive_verifier_set(
    mission: Mission,
    *,
    cmd_id: str,
    dest: str,
) -> VerifierSet:
    """Resolve a VerifierSet from the mission's verifier_rules + per-command
    overrides. Returns an empty VerifierSet if no rules are declared.

    Resolution order (XTCE-lite):
    1. Look up verifier_rules.by_dest[dest.upper()] → ordered base verifier_ids.
    2. If meta_commands[cmd_id].verifier_override is non-empty, REPLACE all
       verifiers whose stage matches an override key with the override's
       listed ids (in order).
    3. Resolve each id to a VerifierSpec via mission.verifier_specs[id].
    """
    rules = mission.verifier_rules
    if rules is None or not rules.by_dest:
        return VerifierSet(verifiers=())

    base_ids: list[str] = list(rules.by_dest.get(dest.upper(), ()))

    meta = mission.meta_commands.get(cmd_id)
    overrides = meta.verifier_override if meta else {}
    if overrides:
        replaced_stages = set(overrides.keys())
        kept: list[str] = []
        for sid in base_ids:
            decl = mission.verifier_specs.get(sid)
            if decl is not None and decl.stage not in replaced_stages:
                kept.append(sid)
        for stage in overrides:
            kept.extend(overrides[stage])
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


__all__ = ["derive_verifier_set"]
