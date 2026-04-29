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


def _facts(dest: str):
    return {"header": {"dest": dest}}


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
      res_hlnv:   { stage: complete, label: "RES",  tone: success, window: { stop_ms: 30000 } }
      res_astr:   { stage: complete, label: "RES",  tone: success, window: { stop_ms: 30000 } }
      file_hlnv:  { stage: complete, label: "FILE", tone: success, window: { stop_ms: 30000 } }
      file_astr:  { stage: complete, label: "FILE", tone: success, window: { stop_ms: 30000 } }
      nack_uppm:  { stage: failed,   label: "NACK", tone: danger,  window: { stop_ms: 30000 } }
      tlm_eps_hk: { stage: complete, label: "TLM",  tone: success, window: { stop_ms: 30000 } }
    verifier_rules:
      selector: header.dest
      by_key:
        EPS:  [uppm_ack, res_eps, nack_uppm]
        HLNV: [uppm_ack, res_hlnv, nack_uppm]
        ASTR: [uppm_ack, res_astr, nack_uppm]
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
      rpi_shutdown:
        packet: { dest: HLNV, echo: NONE, ptype: CMD }
        no_response: true
        argument_list: []
      img_get_chunks:
        packet: { echo: NONE, ptype: CMD }
        allowed_packet: { dest: [HLNV, ASTR] }
        argument_list: []
        verifier_override:
          complete:
            by_key:
              HLNV: [file_hlnv]
              ASTR: [file_astr]
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
      selector: header.dest
      by_key:
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
      selector: header.dest
      by_key:
        EPS: [uppm_ack]
    meta_commands:
      ping:
        packet: { dest: EPS, echo: NONE, ptype: CMD }
        argument_list: []
        verifier_override:
          complete: [ghost_verifier]
""").strip()

YAML_UNKNOWN_VERIFIER_IN_KEYED_OVERRIDE = textwrap.dedent("""
    schema_version: 1
    id: test_bad3
    name: bad3
    header: { version: "0.0.1", date: "2026-04-25" }
    extensions: {}
    parameter_types: {}
    parameters: {}
    bitfield_types: {}
    sequence_containers: {}
    verifier_specs:
      uppm_ack: { stage: received, label: "UPPM", tone: info }
    verifier_rules:
      selector: header.dest
      by_key:
        HLNV: [uppm_ack]
    meta_commands:
      img_get_chunks:
        packet: { dest: HLNV, echo: NONE, ptype: CMD }
        argument_list: []
        verifier_override:
          complete:
            by_key:
              HLNV: [ghost_file]
""").strip()


class TestDeriveVerifierSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = _load_yaml(YAML_FULL)

    def test_base_rule_no_override(self):
        """com_ping with dest EPS → 3 verifiers in rule order."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("EPS"))
        self.assertEqual(len(vs.verifiers), 3)
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertEqual(ids, ["uppm_ack", "res_eps", "nack_uppm"])

    def test_override_replaces_stage(self):
        """eps_hk: complete stage replaced by tlm_eps_hk → uppm_ack, nack_uppm, tlm_eps_hk."""
        vs = derive_verifier_set(self.mission, cmd_id="eps_hk", mission_facts=_facts("EPS"))
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertIn("uppm_ack", ids)
        self.assertIn("nack_uppm", ids)
        self.assertIn("tlm_eps_hk", ids)
        self.assertNotIn("res_eps", ids)
        self.assertEqual(len(vs.verifiers), 3)

    def test_override_empty_drops_stage(self):
        """eps_cut: complete stage override=[] → res_eps dropped, 2 verifiers remain."""
        vs = derive_verifier_set(self.mission, cmd_id="eps_cut", mission_facts=_facts("EPS"))
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertIn("uppm_ack", ids)
        self.assertIn("nack_uppm", ids)
        self.assertNotIn("res_eps", ids)
        self.assertEqual(len(vs.verifiers), 2)

    def test_no_response_drops_default_complete_stage(self):
        """no_response commands inherit ACK/NACK checks but do not wait for RES."""
        vs = derive_verifier_set(self.mission, cmd_id="rpi_shutdown", mission_facts=_facts("HLNV"))
        ids = [v.verifier_id for v in vs.verifiers]
        self.assertEqual(ids, ["uppm_ack", "nack_uppm"])
        self.assertNotIn("res_hlnv", ids)

    def test_override_by_key_selects_one_complete_verifier(self):
        """img_get_chunks picks the FILE verifier for the selected destination only."""
        hlnv = derive_verifier_set(self.mission, cmd_id="img_get_chunks", mission_facts=_facts("HLNV"))
        astr = derive_verifier_set(self.mission, cmd_id="img_get_chunks", mission_facts=_facts("ASTR"))
        self.assertEqual(
            [v.verifier_id for v in hlnv.verifiers],
            ["uppm_ack", "nack_uppm", "file_hlnv"],
        )
        self.assertEqual(
            [v.verifier_id for v in astr.verifiers],
            ["uppm_ack", "nack_uppm", "file_astr"],
        )

    def test_ftdi_dest_empty(self):
        """FTDI has an empty list in by_key → empty VerifierSet."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("FTDI"))
        self.assertEqual(len(vs.verifiers), 0)

    def test_unknown_dest_gives_empty(self):
        """A key not in by_key → empty VerifierSet (not an error)."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("UNKNOWN_NODE"))
        self.assertEqual(len(vs.verifiers), 0)

    def test_dest_case_insensitive(self):
        """dest lookup is upper-cased — 'eps' and 'EPS' resolve the same."""
        vs_lower = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("eps"))
        vs_upper = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("EPS"))
        self.assertEqual(
            [v.verifier_id for v in vs_lower.verifiers],
            [v.verifier_id for v in vs_upper.verifiers],
        )

    def test_verifier_spec_fields_populated(self):
        """Check that CheckWindow fields propagate correctly."""
        vs = derive_verifier_set(self.mission, cmd_id="com_ping", mission_facts=_facts("EPS"))
        uppm = next(v for v in vs.verifiers if v.verifier_id == "uppm_ack")
        self.assertEqual(uppm.stage, "received")
        self.assertEqual(uppm.display_label, "UPPM")
        self.assertEqual(uppm.display_tone, "info")
        self.assertEqual(uppm.check_window.stop_ms, 15000)
        self.assertEqual(uppm.check_window.start_ms, 0)


class TestNoVerifierRules(unittest.TestCase):
    def test_mission_without_verifier_rules_returns_empty(self):
        mission = _load_yaml(YAML_NO_VERIFIER_RULES)
        vs = derive_verifier_set(mission, cmd_id="ping", mission_facts=_facts("GS"))
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

    def test_unknown_verifier_id_in_keyed_override_raises(self):
        with self.assertRaises(UnknownVerifierId) as ctx:
            _load_yaml(YAML_UNKNOWN_VERIFIER_IN_KEYED_OVERRIDE)
        self.assertIn("ghost_file", str(ctx.exception))

    def test_by_key_requires_selector(self):
        with self.assertRaises(ValueError):
            _load_yaml(textwrap.dedent("""
                schema_version: 1
                id: test_bad_selector
                name: bad
                header: { version: "0.0.1", date: "2026-04-25" }
                extensions: {}
                parameter_types: {}
                parameters: {}
                bitfield_types: {}
                sequence_containers: {}
                verifier_specs:
                  ack: { stage: received, label: "ACK", tone: info }
                verifier_rules:
                  by_key:
                    NODE: [ack]
                meta_commands: {}
            """).strip())


if __name__ == "__main__":
    unittest.main()
