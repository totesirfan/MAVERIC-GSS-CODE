"""CI-stable coverage of schema inlining, validation, and to_end semantics
that does NOT depend on the gitignored mav_gss_lib/missions/maveric/mission.yml.

Uses a public fixture mission with named ArgumentTypes that exercise
every path the year=2026 fix relies on.
"""

import unittest
from pathlib import Path

from mav_gss_lib.platform.spec.command_codec import DeclarativeCommandOpsAdapter
from mav_gss_lib.platform.spec.runtime import DeclarativeWalker
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml


_FIXTURE = Path("tests/fixtures/spec/argument_types_fixture_mission.yml")


class _StubCodec:
    def complete_header(self, h): return h
    def wrap(self, h, b): return b


class _StubFramer: pass


def _ops(mission):
    return DeclarativeCommandOpsAdapter(
        mission=mission,
        walker=DeclarativeWalker(mission, plugins={}),
        packet_codec=_StubCodec(),
        framer=_StubFramer(),
    )


class TestPublicFixtureSchemaAndValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mission = parse_yaml(_FIXTURE, plugins={})
        cls.ops = _ops(cls.mission)

    def test_year_2digit_t_present_in_argument_types(self):
        self.assertIn("year_2digit_t", self.mission.argument_types)
        t = self.mission.argument_types["year_2digit_t"]
        self.assertEqual(t.valid_range, (0.0, 99.0))

    def test_validate_rejects_out_of_range_year(self):
        from mav_gss_lib.platform.contract.commands import CommandDraft
        draft = CommandDraft(payload={"cmd_id": "set_year",
                                       "args": {"year": "2026"},
                                       "packet": {}})
        issues = self.ops.validate(draft)
        self.assertTrue(any("outside" in i.message.lower() for i in issues))

    def test_validate_accepts_in_range_year(self):
        from mav_gss_lib.platform.contract.commands import CommandDraft
        draft = CommandDraft(payload={"cmd_id": "set_year",
                                       "args": {"year": "26"},
                                       "packet": {}})
        self.assertEqual(self.ops.validate(draft), [])

    def test_validate_enforces_valid_values_set(self):
        from mav_gss_lib.platform.contract.commands import CommandDraft
        draft_ok = CommandDraft(payload={"cmd_id": "set_ops",
                                          "args": {"stage": "1"},
                                          "packet": {}})
        self.assertEqual(self.ops.validate(draft_ok), [])
        draft_bad = CommandDraft(payload={"cmd_id": "set_ops",
                                           "args": {"stage": "3"},
                                           "packet": {}})
        issues = self.ops.validate(draft_bad)
        self.assertTrue(any("not in" in i.message.lower() for i in issues))

    def test_to_end_string_arg_in_cli_captures_full_remainder(self):
        # The platform adapter is now `to_end`-aware (Task 5 Step 5):
        # when the meta's last arg is encoding=to_end, parse_input(str)
        # uses split(maxsplit=n) so the trailing element is the verbatim
        # remainder — including any internal whitespace.
        #
        # This is the platform contract: every mission that ships a
        # to_end ArgumentType inherits this grammar without writing a
        # wrapper. MAVERIC's wrapper still adds routing-prefix support
        # on top, but the *bare* CLI form is fully handled here.
        draft = self.ops.parse_input("log_text hello world how are you")
        self.assertEqual(draft.payload["cmd_id"], "log_text")
        self.assertEqual(draft.payload["args"], {"msg": "hello world how are you"})

    def test_to_end_string_arg_preserves_internal_whitespace(self):
        # Double-spaces inside the to_end remainder must survive — this
        # is exactly why split(maxsplit=n) is required (plain split()
        # would collapse the run, then a " ".join() reconstitution
        # would lose fidelity).
        draft = self.ops.parse_input("log_text hello  world\twith\ttabs")
        self.assertEqual(draft.payload["args"], {"msg": "hello  world\twith\ttabs"})

    def test_to_end_must_be_last_arg_at_parse_time(self):
        # Verified at YAML-parse time by Task 2 Step 5a; if a future
        # author tries to put TextBlob mid-list, parse_yaml would raise.
        # This fixture is well-formed (TextBlob is the only arg), so the
        # mission parses cleanly.
        self.assertIn("log_text", self.mission.meta_commands)


class TestPublicFixtureSchemaInlining(unittest.TestCase):
    """Exercises the platform schema-inlining helper directly against
    the public fixture mission, so CI proves /api/schema-shaped output
    inlines ArgumentType metadata correctly without depending on the
    gitignored MAVERIC mission.yml.
    """

    @classmethod
    def setUpClass(cls):
        cls.mission = parse_yaml(_FIXTURE, plugins={})

    def test_inline_argument_metadata_year_carries_valid_range_and_description(self):
        from mav_gss_lib.platform.spec.schema_helpers import inline_argument_metadata
        meta = self.mission.meta_commands["set_year"]
        inlined = inline_argument_metadata(self.mission, meta)
        self.assertEqual(len(inlined), 1)
        year_arg = inlined[0]
        self.assertEqual(year_arg["name"], "year")
        self.assertEqual(year_arg["valid_range"], [0, 99])
        self.assertIn("2-digit", year_arg["description"])
        self.assertIsNone(year_arg["valid_values"])

    def test_inline_argument_metadata_ops_carries_valid_values(self):
        from mav_gss_lib.platform.spec.schema_helpers import inline_argument_metadata
        meta = self.mission.meta_commands["set_ops"]
        inlined = inline_argument_metadata(self.mission, meta)
        stage_arg = inlined[0]
        self.assertEqual(stage_arg["valid_values"], [0, 1, 2])
        self.assertIsNone(stage_arg["valid_range"])

    def test_inline_argument_metadata_text_blob_no_constraints(self):
        from mav_gss_lib.platform.spec.schema_helpers import inline_argument_metadata
        meta = self.mission.meta_commands["log_text"]
        inlined = inline_argument_metadata(self.mission, meta)
        msg_arg = inlined[0]
        self.assertIsNone(msg_arg["valid_range"])
        self.assertIsNone(msg_arg["valid_values"])
        self.assertIn("trailing", msg_arg["description"].lower())


class TestPlatformAdapterSchemaShape(unittest.TestCase):
    """The platform DeclarativeCommandOpsAdapter.schema() must emit
    {cmd_id: CommandSchemaItem} with `tx_args` (no legacy "commands"
    wrapper, no MAVERIC-extension keys). This is the contract Task 8b
    later codifies as a TypedDict.
    """

    @classmethod
    def setUpClass(cls):
        cls.mission = parse_yaml(_FIXTURE, plugins={})
        cls.ops = _ops(cls.mission)
        cls.schema = cls.ops.schema()

    def test_schema_is_unwrapped(self):
        # Old shape was {"commands": {...}}; new shape lifts cmd_ids to top.
        self.assertNotIn("commands", self.schema)
        self.assertIn("set_year", self.schema)

    def test_every_command_has_tx_args(self):
        for cmd_id, item in self.schema.items():
            self.assertIn("tx_args", item, f"{cmd_id} missing tx_args")
            self.assertIsInstance(item["tx_args"], list)

    def test_year_arg_carries_inlined_valid_range(self):
        year_arg = next(
            a for a in self.schema["set_year"]["tx_args"] if a["name"] == "year"
        )
        self.assertEqual(year_arg["valid_range"], [0, 99])
        self.assertIn("2-digit", year_arg["description"])

    def test_no_routing_extension_fields_on_platform_adapter(self):
        # Platform adapter is mission-agnostic — must NOT emit dest/echo/
        # ptype/nodes (those live on MAVERIC's MavericCommandSchemaItem).
        forbidden = {"dest", "echo", "ptype", "nodes"}
        for cmd_id, item in self.schema.items():
            extras = forbidden & set(item.keys())
            self.assertFalse(
                extras,
                f"{cmd_id}: platform adapter must not emit {extras}",
            )


if __name__ == "__main__":
    unittest.main()
