"""Platform-spec tests for declarative verifier rules + per-command overrides.

Covers:
  - Empty mission (no verifier_rules) → VerifierSet(verifiers=())
  - Rule-only (no overrides) → resolves base ids in order
  - Override REPLACES base verifiers of the matching stage
  - Override with empty list DROPS verifiers of that stage
  - Multiple destinations resolve independently
  - Unknown verifier_id at parse time raises UnknownVerifierId
  - Mission with no verifier_rules → empty VerifierSet from derive
"""

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mav_gss_lib.platform.spec import (
    UnknownVerifierId,
    derive_verifier_set,
    parse_yaml_for_tooling,
)


def _load_yaml(yaml_str: str):
    with TemporaryDirectory() as td:
        p = Path(td) / "m.yml"
        p.write_text(yaml_str)
        return parse_yaml_for_tooling(p)


YAML_FULL = textwrap.dedent("""
    schema_version: 1
    id: test
    name: test
    header: { version: "0.0.1", date: "2026-04-25" }
    extensions: {}
    parameter_types: {}
    parameters: {}
    bitfield_types: {}
    sequence_containers: {}
    verifier_specs:
      uppm_ack:   { stage: received, label: "UPPM", tone: info,    window: { stop_ms: 15000 } }
      res_eps:    { stage: complete, label: "RES",  tone: success, window: { stop_ms: 30000 } }
      nack_uppm:  { stage: failed,   label: "NACK", tone: danger,  window: { stop_ms: 30000 } }
      tlm_eps_hk: { stage: complete, label: "TLM",  tone: success, window: { stop_ms: 30000 } }
    verifier_rules:
      by_dest:
        EPS:  [uppm_ack, res_eps, nack_uppm]
        FTDI: []
    meta_commands:
      com_ping:
        packet: { dest: EPS, echo: NONE, ptype: CMD }
        argument_list: []
      eps_hk:
        packet: { dest: EPS, echo: NONE, ptype: CMD }
        argument_list: []
        verifier_override:
          complete: [tlm_eps_hk]
      eps_cut:
        packet: { dest: EPS, echo: NONE, ptype: CMD }
        argument_list: []
        verifier_override:
          complete: []
""").strip()

YAML_NO_VERIFIER_RULES = textwrap.dedent("""
    schema_version: 1
    id: test_bare
    name: bare
    header: { version: "0.0.1", date: "2026-04-25" }
    extensions: {}
    parameter_types: {}
    parameters: {}
    bitfield_types: {}
    sequence_containers: {}
    meta_commands:
      ping:
        packet: { dest: GS, echo: NONE, ptype: CMD }
        argument_list: []
""").strip()

YAML_UNKNOWN_VERIFIER_IN_RULES = textwrap.dedent("""
    schema_version: 1
    id: test_bad
    name: bad
    header: { version: "0.0.1", date: "2026-04-25" }
    extensions: {}
    parameter_types: {}
    parameters: {}
    bitfield_types: {}
    sequence_containers: {}
    verifier_specs:
      uppm_ack: { stage: received, label: "UPPM", tone: info }
    verifier_rules:
      by_dest:
        EPS: [uppm_ack, nonexistent_id]
    meta_commands: {}
""").strip()

YAML_UNKNOWN_VERIFIER_IN_OVERRIDE = textwrap.dedent("""
    schema_version: 1
    id: test_bad2
    name: bad2
    header: { version: "0.0.1", date: "2026-04-25" }
    extensions: {}
    parameter_types: {}
    parameters: {}
    bitfield_types: {}
    sequence_containers: {}
    verifier_specs:
      uppm_ack: { stage: received, label: "UPPM", tone: info }
    verifier_rules:
      by_dest:
        EPS: [uppm_ack]
    meta_commands:
      ping:
        packet: { dest: EPS, echo: NONE, ptype: CMD }
        argument_list: []
        verifier_override:
          complete: [ghost_verifier]
""").strip()


class TestDeriveVerifierSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = _load_yaml(YAML_FULL)

    def test_base_rule_no_override(self):
        """com_ping with dest EPS → 3 verifiers in rule order."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", dest="EPS")
        self.assertEqual(len(vs.verifiers), 3)
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertEqual(ids, ["uppm_ack", "res_eps", "nack_uppm"])

    def test_override_replaces_stage(self):
        """eps_hk: complete stage replaced by tlm_eps_hk → uppm_ack, nack_uppm, tlm_eps_hk."""
        vs = derive_verifier_set(self.mission, cmd_id="eps_hk", dest="EPS")
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertIn("uppm_ack", ids)
        self.assertIn("nack_uppm", ids)
        self.assertIn("tlm_eps_hk", ids)
        self.assertNotIn("res_eps", ids)
        self.assertEqual(len(vs.verifiers), 3)

    def test_override_empty_drops_stage(self):
        """eps_cut: complete stage override=[] → res_eps dropped, 2 verifiers remain."""
        vs = derive_verifier_set(self.mission, cmd_id="eps_cut", dest="EPS")
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertIn("uppm_ack", ids)
        self.assertIn("nack_uppm", ids)
        self.assertNotIn("res_eps", ids)
        self.assertEqual(len(vs.verifiers), 2)

    def test_ftdi_dest_empty(self):
        """FTDI has an empty list in by_dest → empty VerifierSet."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", dest="FTDI")
        self.assertEqual(len(vs.verifiers), 0)

    def test_unknown_dest_gives_empty(self):
        """A destination not in by_dest → empty VerifierSet (not an error)."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", dest="UNKNOWN_NODE")
        self.assertEqual(len(vs.verifiers), 0)

    def test_dest_case_insensitive(self):
        """dest lookup is upper-cased — 'eps' and 'EPS' resolve the same."""
        vs_lower = derive_verifier_set(self.mission, cmd_id="com_ping", dest="eps")
        vs_upper = derive_verifier_set(self.mission, cmd_id="com_ping", dest="EPS")
        self.assertEqual(
            [v.verifier_id for v in vs_lower.verifiers],
            [v.verifier_id for v in vs_upper.verifiers],
        )

    def test_verifier_spec_fields_populated(self):
        """Check that CheckWindow fields propagate correctly."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", dest="EPS")
        uppm = next(v for v in vs.verifiers if v.verifier_id == "uppm_ack")
        self.assertEqual(uppm.stage, "received")
        self.assertEqual(uppm.display_label, "UPPM")
        self.assertEqual(uppm.display_tone, "info")
        self.assertEqual(uppm.check_window.stop_ms, 15000)
        self.assertEqual(uppm.check_window.start_ms, 0)


class TestNoVerifierRules(unittest.TestCase):
    def test_mission_without_verifier_rules_returns_empty(self):
        mission = _load_yaml(YAML_NO_VERIFIER_RULES)
        vs = derive_verifier_set(mission, cmd_id="ping", dest="GS")
        self.assertEqual(vs.verifiers, ())

    def test_mission_without_verifier_rules_has_none(self):
        mission = _load_yaml(YAML_NO_VERIFIER_RULES)
        self.assertIsNone(mission.verifier_rules)


class TestParseTimeValidation(unittest.TestCase):
    def test_unknown_verifier_id_in_rules_raises(self):
        with self.assertRaises(UnknownVerifierId) as ctx:
            _load_yaml(YAML_UNKNOWN_VERIFIER_IN_RULES)
        self.assertIn("nonexistent_id", str(ctx.exception))

    def test_unknown_verifier_id_in_override_raises(self):
        with self.assertRaises(UnknownVerifierId) as ctx:
            _load_yaml(YAML_UNKNOWN_VERIFIER_IN_OVERRIDE)
        self.assertIn("ghost_verifier", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
