import textwrap
import unittest
from dataclasses import dataclass
from pathlib import Path

from mav_gss_lib.platform.spec.containers import ParameterRefEntry
from mav_gss_lib.platform.spec.errors import MissingPluginError, ParseError
from mav_gss_lib.platform.spec.runtime import DeclarativeWalker
from mav_gss_lib.platform.spec.yaml_parse import (
    parse_yaml,
    parse_yaml_for_tooling,
)


@dataclass(frozen=True, slots=True)
class _Pkt:
    args_raw: bytes
    header: dict


FIXTURE = Path(__file__).parent / "fixtures" / "spec" / "minimal_mission.yml"


class TestYamlParser(unittest.TestCase):
    def test_parse_yaml_returns_mission_with_built_ins_plus_declared(self):
        m = parse_yaml(FIXTURE, plugins={})
        self.assertEqual(m.id, "testmission")
        self.assertEqual(m.name, "Test Mission")
        # Built-in u8 visible
        self.assertIn("u8", m.parameter_types)
        # Declared types visible
        self.assertIn("V_volts", m.parameter_types)
        self.assertIn("GncMode", m.parameter_types)
        # Containers + meta-commands present
        self.assertIn("eps_hk", m.sequence_containers)
        self.assertIn("gnc_get_mode", m.meta_commands)

    def test_parse_yaml_extract_path_emits_fragment(self):
        m = parse_yaml(FIXTURE, plugins={})
        walker = DeclarativeWalker(m, plugins={})
        pkt = _Pkt(args_raw=b"1", header={"cmd_id": "gnc_get_mode", "ptype": "RES"})
        updates = list(walker.extract(pkt, now_ms=42))
        self.assertEqual(len(updates), 1)
        # Walker emits qualified ParamUpdate.name = "<group>.<key>".
        self.assertTrue(updates[0].name.endswith(".GNC_MODE") or updates[0].name == "GNC_MODE")
        self.assertEqual(updates[0].value, 1)

    def test_parse_yaml_for_tooling_skips_plugin_check(self):
        # The minimal fixture has no python: refs, but the entry-point
        # difference is the plugins kwarg; tooling form must not require it.
        m = parse_yaml_for_tooling(FIXTURE)
        self.assertEqual(m.id, "testmission")

    def test_missing_plugin_rejected(self):
        # Inject a plugin reference into a copy of the fixture
        bad = FIXTURE.parent / "_with_missing_plugin.yml"
        text = FIXTURE.read_text()
        text = text.replace(
            "calibrator: {polynomial: [0, 0.001]}",
            "calibrator: {python: 'eps.compute_pwr'}",
        )
        bad.write_text(text)
        try:
            with self.assertRaises(MissingPluginError):
                parse_yaml(bad, plugins={})
        finally:
            bad.unlink(missing_ok=True)


def _write_tmp_yaml(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body))
    return p


class TestEntryListPureParameterRef(unittest.TestCase):
    """XTCE 1.3 alignment — container entries are pure parameter references.

    `ParameterRefEntry` carries only `parameterRef` per CCSDS 660.1-B-2 /
    OMG XTCE 1.3 (`ExpandedNameReferenceWithPathType`). Per-entry type
    overrides are no longer permitted; type comes from the parameter
    declaration, and any redundant `type:` field must match.
    """

    def _container_yaml(self, entry_yaml: str) -> str:
        return textwrap.dedent(
            """\
            schema_version: 1
            id: testmission
            name: "Test Mission"
            header:
              version: "1.0.0"
              date: "2026-04-25"
              description: "Smoke test"

            extensions:
              nodes:  {NONE: 0, GS: 1, NODE_A: 2}
              ptypes: {CMD: 1, RES: 2, TLM: 5}

            parameter_types:
              V_volts:
                kind: int
                size_bits: 16
                signed: true
                calibrator: {polynomial: [0, 0.001]}
                unit: V
              GncMode:
                kind: enum
                size_bits: 8
                values: {0: Safe, 1: Auto}

            parameters:
              V_BUS: {type: V_volts, description: "Bus voltage"}
              GNC_MODE: {type: GncMode, description: "Planner mode"}

            meta_commands:
              gnc_get_mode:
                packet: {dest: NODE_A, echo: NONE, ptype: CMD}

            sequence_containers:
              eps_hk:
                domain: eps
                layout: binary
                restriction_criteria: {packet: {cmd_id: eps_hk, ptype: TLM}}
                entry_list:
                  - __ENTRY__
            """
        ).replace("__ENTRY__", entry_yaml)

    def test_entry_without_type_resolves_from_parameter_declaration(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            yaml_text = self._container_yaml("{name: V_BUS}")
            p = _write_tmp_yaml(tmp, "m.yml", yaml_text)
            m = parse_yaml(p, plugins={})
            container = m.sequence_containers["eps_hk"]
            entry = container.entry_list[0]
            self.assertIsInstance(entry, ParameterRefEntry)
            self.assertEqual(entry.name, "V_BUS")
            # Type resolved from parameter declaration
            self.assertEqual(entry.type_ref, "V_volts")
            self.assertEqual(entry.parameter_ref, "V_BUS")

    def test_entry_with_matching_type_parses(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # type matches the parameter declaration's type — redundant but legal
            yaml_text = self._container_yaml("{name: V_BUS, type: V_volts}")
            p = _write_tmp_yaml(tmp, "m.yml", yaml_text)
            m = parse_yaml(p, plugins={})
            entry = m.sequence_containers["eps_hk"].entry_list[0]
            self.assertEqual(entry.type_ref, "V_volts")

    def test_entry_with_mismatching_type_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # V_BUS declared as V_volts; entry asserts GncMode — must error
            yaml_text = self._container_yaml("{name: V_BUS, type: GncMode}")
            p = _write_tmp_yaml(tmp, "m.yml", yaml_text)
            with self.assertRaises(ParseError) as cm:
                parse_yaml(p, plugins={})
            msg = str(cm.exception)
            # Message names entry, parameter declared type, and entry-asserted type
            self.assertIn("V_BUS", msg)
            self.assertIn("V_volts", msg)
            self.assertIn("GncMode", msg)


class TestWireBackedAggregateValidation(unittest.TestCase):
    """Wire-backed aggregate parameter types must declare a coherent set of
    fields. Incoherent combinations are parse-time errors so the walker
    doesn't have to guess later."""

    def _agg_yaml(self, agg_block: str) -> str:
        # Minimal mission with a custom aggregate type
        return textwrap.dedent(f"""
        schema_version: 1
        id: m
        name: m
        header:
          version: "1.0.0"
          date: "2026-04-30"
          description: "test"
        parameter_types:
          MyAgg:
{textwrap.indent(agg_block, '            ')}
        parameters:
          P: {{ type: MyAgg, domain: gnc }}
        sequence_containers:
          c:
            domain: gnc
            layout: ascii_tokens
            restriction_criteria:
              packet:
                cmd_id: foo
                ptype: RES
            entry_list:
              - {{ name: P }}
        meta_commands: {{}}
        """).lstrip()

    def test_size_bits_without_byte_order_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            block = textwrap.dedent("""
                kind: aggregate
                size_bits: 32
                wire_format: u8_tokens
                calibrator:
                  python: "stub"
                member_list:
                  - { name: x, type: u8 }
            """).strip()
            p = _write_tmp_yaml(tmp, "m.yml", self._agg_yaml(block))
            with self.assertRaisesRegex(ParseError, r"byte_order"):
                parse_yaml(p, plugins={"stub": lambda r: ({"x": 0}, "")})

    def test_size_bits_without_calibrator_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            block = textwrap.dedent("""
                kind: aggregate
                size_bits: 32
                byte_order: little
                wire_format: u8_tokens
                member_list:
                  - { name: x, type: u8 }
            """).strip()
            p = _write_tmp_yaml(tmp, "m.yml", self._agg_yaml(block))
            with self.assertRaisesRegex(ParseError, r"calibrator"):
                parse_yaml(p, plugins={})

    def test_i16_tokens_with_size_bits_8_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            block = textwrap.dedent("""
                kind: aggregate
                size_bits: 8
                byte_order: little
                wire_format: i16_tokens
                calibrator:
                  python: "stub"
                member_list:
                  - { name: x, type: u8 }
            """).strip()
            p = _write_tmp_yaml(tmp, "m.yml", self._agg_yaml(block))
            with self.assertRaisesRegex(ParseError, r"i16_tokens.*size_bits"):
                parse_yaml(p, plugins={"stub": lambda r: ({"x": 0}, "")})

    def test_in_place_aggregate_with_calibrator_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            block = textwrap.dedent("""
                kind: aggregate
                calibrator:
                  python: "stub"
                member_list:
                  - { name: x, type: u8 }
            """).strip()
            p = _write_tmp_yaml(tmp, "m.yml", self._agg_yaml(block))
            with self.assertRaisesRegex(ParseError, r"calibrator.*size_bits"):
                parse_yaml(p, plugins={"stub": lambda r: ({"x": 0}, "")})


class TestNestedTypeRefChecks(unittest.TestCase):
    """Cross-reference checks must catch unknown type refs in aggregate
    member lists, array element refs, and bitfield enum refs."""

    _HEADER = textwrap.dedent("""
        schema_version: 1
        id: m
        name: m
        header:
          version: "1.0.0"
          date: "2026-04-30"
          description: "test"
    """).lstrip()

    def test_aggregate_member_unknown_type_ref_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            yaml_text = self._HEADER + textwrap.dedent("""
            parameter_types:
              Bad:
                kind: aggregate
                member_list:
                  - { name: x, type: NoSuchType }
            parameters:
              P: { type: Bad }
            sequence_containers: {}
            meta_commands: {}
            """)
            p = _write_tmp_yaml(tmp, "m.yml", yaml_text)
            with self.assertRaisesRegex(Exception, r"NoSuchType"):
                parse_yaml(p, plugins={})

    def test_bitfield_enum_ref_unknown_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            yaml_text = self._HEADER + textwrap.dedent("""
            parameter_types: {}
            bitfield_types:
              MyReg:
                size_bits: 32
                byte_order: little
                entry_list:
                  - { name: MODE, bits: [0, 6], kind: enum, enum_ref: NoSuchEnum }
            parameters:
              S: { type: MyReg }
            sequence_containers: {}
            meta_commands: {}
            """)
            p = _write_tmp_yaml(tmp, "m.yml", yaml_text)
            with self.assertRaisesRegex(Exception, r"NoSuchEnum"):
                parse_yaml(p, plugins={})


if __name__ == "__main__":
    unittest.main()
