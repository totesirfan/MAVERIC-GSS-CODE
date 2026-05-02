"""End-to-end coverage for type-driven argument validation in
DeclarativeCommandOpsAdapter.validate. Constraints come from
mission.argument_types; values from operator dict input are
coerced + checked.
"""

import unittest
from typing import Any

from mav_gss_lib.platform.contract.commands import CommandDraft
from mav_gss_lib.platform.spec.argument_types import (
    BUILT_IN_ARGUMENT_TYPES,
    IntegerArgumentType,
)
from mav_gss_lib.platform.spec.command_codec import DeclarativeCommandOpsAdapter
from mav_gss_lib.platform.spec.commands import Argument, MetaCommand
from mav_gss_lib.platform.spec.mission import Mission, MissionHeader
from mav_gss_lib.platform.spec.parameter_types import BUILT_IN_PARAMETER_TYPES
from mav_gss_lib.platform.spec.runtime import DeclarativeWalker


class _StubCodec:
    def complete_header(self, h):
        return h
    def wrap(self, h, b):
        return b


class _StubFramer:
    pass


def _build_ops(arg_types_extra: dict, *metas: MetaCommand) -> DeclarativeCommandOpsAdapter:
    """Build a minimal DeclarativeCommandOpsAdapter for validate-path tests.

    Accepts one or more MetaCommands so tests can register multiple
    commands against the same mission (used by string-validation tests
    that need both `ascii_token` and `to_end` commands in the registry).
    """
    arg_types = dict(BUILT_IN_ARGUMENT_TYPES)
    arg_types.update(arg_types_extra)
    mission = Mission(
        id="t", name="t",
        header=MissionHeader(version="0", date="2026-01-01"),
        parameter_types=dict(BUILT_IN_PARAMETER_TYPES),
        argument_types=arg_types,
        parameters={}, bitfield_types={}, sequence_containers={},
        meta_commands={m.id: m for m in metas},
    )
    walker = DeclarativeWalker(mission, plugins={})
    return DeclarativeCommandOpsAdapter(
        mission=mission, walker=walker,
        packet_codec=_StubCodec(), framer=_StubFramer(),
    )


def _draft(cmd_id: str, args: dict[str, Any]) -> CommandDraft:
    return CommandDraft(payload={"cmd_id": cmd_id, "args": args, "packet": {}})


class TestTypeDrivenValidRange(unittest.TestCase):
    def setUp(self):
        year_t = IntegerArgumentType(name="year_2digit_t", size_bits=8, valid_range=(0.0, 99.0))
        meta = MetaCommand(
            id="set_year",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="year", type_ref="year_2digit_t"),),
        )
        self.ops = _build_ops({"year_2digit_t": year_t}, meta)

    def test_dict_string_in_range_passes(self):
        self.assertEqual(self.ops.validate(_draft("set_year", {"year": "26"})), [])

    def test_dict_string_out_of_range_returns_issue(self):
        issues = self.ops.validate(_draft("set_year", {"year": "2026"}))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].field, "year")
        self.assertIn("outside", issues[0].message.lower())

    def test_dict_int_in_range_passes(self):
        self.assertEqual(self.ops.validate(_draft("set_year", {"year": 26})), [])

    def test_dict_int_out_of_range_returns_issue(self):
        issues = self.ops.validate(_draft("set_year", {"year": 2026}))
        self.assertEqual(len(issues), 1)

    def test_dict_float_with_fraction_for_int_arg_rejected(self):
        # 26.5 is numeric but not integer; must NOT silently truncate.
        issues = self.ops.validate(_draft("set_year", {"year": 26.5}))
        self.assertEqual(len(issues), 1)
        self.assertIn("integer", issues[0].message.lower())

    def test_dict_float_with_zero_fraction_for_int_arg_accepted(self):
        # 26.0 == 26 — accept (common when JSON gives all numbers as floats).
        self.assertEqual(self.ops.validate(_draft("set_year", {"year": 26.0})), [])

    def test_dict_garbage_string_for_int_arg(self):
        issues = self.ops.validate(_draft("set_year", {"year": "abc"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("integer", issues[0].message.lower())

    def test_dict_bool_for_int_arg_rejected(self):
        # bool is subclass of int in Python — guard against True validating as 1.
        issues = self.ops.validate(_draft("set_year", {"year": True}))
        self.assertEqual(len(issues), 1)

    def test_cli_string_input_regression(self):
        draft = self.ops.parse_input("set_year 26")
        self.assertEqual(self.ops.validate(draft), [])


class TestTypeDrivenValidValues(unittest.TestCase):
    def setUp(self):
        ops_stage_t = IntegerArgumentType(name="ops_stage_t", size_bits=8, valid_values=(0, 1, 2))
        meta = MetaCommand(
            id="set_ops",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="ops_stage", type_ref="ops_stage_t"),),
        )
        self.ops = _build_ops({"ops_stage_t": ops_stage_t}, meta)

    def test_value_in_set_passes(self):
        self.assertEqual(self.ops.validate(_draft("set_ops", {"ops_stage": "1"})), [])

    def test_value_outside_set_returns_issue(self):
        issues = self.ops.validate(_draft("set_ops", {"ops_stage": "3"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("not in", issues[0].message.lower())


class TestImplicitSizeBitsRangeForIntegers(unittest.TestCase):
    """When an IntegerArgumentType has no explicit valid_range, validate
    derives one from size_bits/signed. Operators expect u8 to reject
    999 — without this, validate would accept it and the encoder would
    silently emit an out-of-range token (or fail unhelpfully).
    """

    def setUp(self):
        u8_t = IntegerArgumentType(name="u8_arg_t", size_bits=8)
        i8_t = IntegerArgumentType(name="i8_arg_t", size_bits=8, signed=True)
        meta_u8 = MetaCommand(
            id="set_u8",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="x", type_ref="u8_arg_t"),),
        )
        meta_i8 = MetaCommand(
            id="set_i8",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="x", type_ref="i8_arg_t"),),
        )
        self.ops_u8 = _build_ops({"u8_arg_t": u8_t}, meta_u8)
        self.ops_i8 = _build_ops({"i8_arg_t": i8_t}, meta_i8)

    def test_u8_rejects_negative(self):
        issues = self.ops_u8.validate(_draft("set_u8", {"x": "-1"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("size_bits", issues[0].message)

    def test_u8_rejects_above_255(self):
        issues = self.ops_u8.validate(_draft("set_u8", {"x": "999"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("[0, 255]", issues[0].message)

    def test_u8_accepts_boundary_values(self):
        self.assertEqual(self.ops_u8.validate(_draft("set_u8", {"x": "0"})), [])
        self.assertEqual(self.ops_u8.validate(_draft("set_u8", {"x": "255"})), [])

    def test_i8_accepts_negative_within_range(self):
        self.assertEqual(self.ops_i8.validate(_draft("set_i8", {"x": "-128"})), [])
        self.assertEqual(self.ops_i8.validate(_draft("set_i8", {"x": "127"})), [])

    def test_i8_rejects_outside_signed_range(self):
        issues = self.ops_i8.validate(_draft("set_i8", {"x": "128"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("[-128, 127]", issues[0].message)

    def test_explicit_valid_range_wins_over_size_bits(self):
        # year_2digit_t is u8 (size_bits=8) BUT valid_range=[0,99];
        # explicit must override the implicit [0,255].
        year_t = IntegerArgumentType(name="year_2digit_t", size_bits=8, valid_range=(0.0, 99.0))
        meta = MetaCommand(
            id="set_year",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="year", type_ref="year_2digit_t"),),
        )
        ops = _build_ops({"year_2digit_t": year_t}, meta)
        # 200 is within size_bits range [0,255] but outside explicit [0,99]
        issues = ops.validate(_draft("set_year", {"year": "200"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("[0, 99]", issues[0].message)
        self.assertIn("valid_range", issues[0].message)


class TestReservedSlotsViaTighterRange(unittest.TestCase):
    """Reserved schedule slots 0–15 are excluded by tightening valid_range
    to [16, 31] — no `invalid_values` field needed (XTCE has no equivalent).
    """

    def setUp(self):
        sched_id_user_t = IntegerArgumentType(
            name="sched_id_user_t", size_bits=8, valid_range=(16.0, 31.0),
        )
        meta = MetaCommand(
            id="set_sched",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="sched_id", type_ref="sched_id_user_t"),),
        )
        self.ops = _build_ops({"sched_id_user_t": sched_id_user_t}, meta)

    def test_unreserved_id_passes(self):
        self.assertEqual(self.ops.validate(_draft("set_sched", {"sched_id": "16"})), [])

    def test_reserved_id_returns_outside_range_issue(self):
        issues = self.ops.validate(_draft("set_sched", {"sched_id": "3"}))
        self.assertEqual(len(issues), 1)
        self.assertIn("outside", issues[0].message.lower())


class TestMissingArgsStillRejected(unittest.TestCase):
    def setUp(self):
        year_t = IntegerArgumentType(name="year_2digit_t", size_bits=8, valid_range=(0.0, 99.0))
        meta = MetaCommand(
            id="set_year",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="year", type_ref="year_2digit_t"),),
        )
        self.ops = _build_ops({"year_2digit_t": year_t}, meta)

    def test_empty_value_flagged_as_missing(self):
        issues = self.ops.validate(_draft("set_year", {"year": ""}))
        self.assertEqual(len(issues), 1)
        self.assertIn("missing", issues[0].message.lower())

    def test_unknown_arg_flagged(self):
        issues = self.ops.validate(_draft("set_year", {"year": 26, "bogus": 1}))
        self.assertTrue(any(i.field == "bogus" for i in issues))


class TestAsciiTokenStringRejectsWhitespace(unittest.TestCase):
    """`ascii_token` strings are SINGLE whitespace-delimited tokens on
    the wire. Dict/API input must be rejected if it contains whitespace,
    otherwise `AsciiArgumentEncoder.encode_ascii()` (str(value)) would
    emit two wire tokens and break the framer's positional decoding.
    """

    def setUp(self):
        from mav_gss_lib.platform.spec.argument_types import StringArgumentType
        token_t = StringArgumentType(name="callsign_t", encoding="ascii_token")
        free_t = StringArgumentType(name="msg_t", encoding="to_end")
        meta_token = MetaCommand(
            id="set_callsign",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="cs", type_ref="callsign_t"),),
        )
        meta_free = MetaCommand(
            id="log_msg",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="text", type_ref="msg_t"),),
        )
        self.ops = _build_ops(
            {"callsign_t": token_t, "msg_t": free_t},
            meta_token, meta_free,
        )

    def test_ascii_token_with_space_rejected(self):
        issues = self.ops.validate(_draft("set_callsign", {"cs": "foo bar"}))
        self.assertTrue(
            any("whitespace" in i.message.lower() and i.field == "cs" for i in issues),
            f"expected whitespace rejection, got {issues}",
        )

    def test_ascii_token_with_tab_rejected(self):
        issues = self.ops.validate(_draft("set_callsign", {"cs": "foo\tbar"}))
        self.assertTrue(any(i.field == "cs" for i in issues))

    def test_ascii_token_with_newline_rejected(self):
        issues = self.ops.validate(_draft("set_callsign", {"cs": "foo\nbar"}))
        self.assertTrue(any(i.field == "cs" for i in issues))

    def test_ascii_token_single_token_accepted(self):
        self.assertEqual(self.ops.validate(_draft("set_callsign", {"cs": "MAV-GSS"})), [])

    def test_to_end_string_with_whitespace_accepted(self):
        # to_end is whitespace-preserving by design — must NOT be rejected.
        self.assertEqual(
            self.ops.validate(_draft("log_msg", {"text": "all systems nominal"})),
            [],
        )


class TestIsToEndArgumentHelper(unittest.TestCase):
    """Public helper is the single source of truth for `to_end` lookup.
    Both platform parser and MAVERIC wrapper consume it; private
    method on the adapter would be a Protocol-boundary leak.
    """

    def setUp(self):
        from mav_gss_lib.platform.spec.argument_types import (
            BUILT_IN_ARGUMENT_TYPES, StringArgumentType,
        )
        from mav_gss_lib.platform.spec.parameter_types import BUILT_IN_PARAMETER_TYPES
        arg_types = dict(BUILT_IN_ARGUMENT_TYPES)
        arg_types["free_t"] = StringArgumentType(name="free_t", encoding="to_end")
        self.mission = Mission(
            id="t", name="t",
            header=MissionHeader(version="0", date="2026-01-01"),
            parameter_types=dict(BUILT_IN_PARAMETER_TYPES),
            argument_types=arg_types,
            parameters={}, bitfield_types={}, sequence_containers={},
            meta_commands={},
        )

    def test_to_end_string_returns_true(self):
        from mav_gss_lib.platform.spec.argument_types import is_to_end_argument
        self.assertTrue(is_to_end_argument(self.mission.argument_types, "free_t"))

    def test_ascii_token_string_returns_false(self):
        from mav_gss_lib.platform.spec.argument_types import is_to_end_argument
        self.assertFalse(is_to_end_argument(self.mission.argument_types, "ascii_token"))

    def test_integer_returns_false(self):
        from mav_gss_lib.platform.spec.argument_types import is_to_end_argument
        self.assertFalse(is_to_end_argument(self.mission.argument_types, "u8"))

    def test_unknown_type_ref_returns_false(self):
        # No KeyError — unknown refs are not to_end (they'll fail later
        # in validate() with a clearer message).
        from mav_gss_lib.platform.spec.argument_types import is_to_end_argument
        self.assertFalse(is_to_end_argument(self.mission.argument_types, "no_such_type"))


class TestPlatformParseInputToEnd(unittest.TestCase):
    """Platform-layer to_end grammar: the bare-CLI form (no routing
    prefix) must capture the whitespace-preserving remainder for a
    final to_end string arg, BEFORE any MAVERIC wrapper gets involved.
    """

    def setUp(self):
        from mav_gss_lib.platform.spec.argument_types import (
            BUILT_IN_ARGUMENT_TYPES, StringArgumentType,
        )
        free_t = StringArgumentType(name="free_t", encoding="to_end")
        meta = MetaCommand(
            id="log",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="text", type_ref="free_t"),),
        )
        self.ops = _build_ops({"free_t": free_t}, meta)

    def test_cli_to_end_captures_full_remainder(self):
        draft = self.ops.parse_input("log all systems nominal")
        self.assertEqual(draft.payload["args"], {"text": "all systems nominal"})

    def test_cli_to_end_preserves_internal_whitespace(self):
        # Double-spaces and tabs in the remainder must survive; the
        # platform parser uses split(maxsplit=n) for exactly this reason.
        draft = self.ops.parse_input("log foo  bar\tbaz")
        self.assertEqual(draft.payload["args"], {"text": "foo  bar\tbaz"})

    def test_cli_no_args_after_cmd_yields_empty_args(self):
        draft = self.ops.parse_input("log")
        self.assertEqual(draft.payload["args"], {})

    def test_cli_unknown_command_returns_empty_args(self):
        # parse_input doesn't know cmd_id; validate() reports unknowns.
        draft = self.ops.parse_input("does_not_exist hello world")
        self.assertEqual(draft.payload["cmd_id"], "does_not_exist")
        self.assertEqual(draft.payload["args"], {})


class TestPlatformParseInputAsciiToken(unittest.TestCase):
    """When the last arg is NOT to_end, the platform parser must use
    plain split() — i.e. the existing zip-by-token behavior — so a CLI
    line with extra trailing tokens does NOT silently merge them.
    """

    def setUp(self):
        from mav_gss_lib.platform.spec.argument_types import (
            BUILT_IN_ARGUMENT_TYPES, StringArgumentType,
        )
        token_t = StringArgumentType(name="token_t", encoding="ascii_token")
        meta = MetaCommand(
            id="set_callsign",
            packet={"echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="cs", type_ref="token_t"),),
        )
        self.ops = _build_ops({"token_t": token_t}, meta)

    def test_cli_ascii_token_takes_first_token_only(self):
        # Extra trailing tokens are dropped (no place to put them given
        # only one arg in the meta). This matches the pre-existing
        # zip-by-token semantics for non-to_end last args.
        draft = self.ops.parse_input("set_callsign MAV-GSS extra junk")
        self.assertEqual(draft.payload["args"], {"cs": "MAV-GSS"})


if __name__ == "__main__":
    unittest.main()
