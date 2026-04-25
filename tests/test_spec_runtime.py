import unittest
from dataclasses import dataclass

from mav_gss_lib.platform.spec.commands import Argument, MetaCommand
from mav_gss_lib.platform.spec.containers import (
    Comparison,
    ParameterRefEntry,
    RestrictionCriteria,
    SequenceContainer,
)
from mav_gss_lib.platform.spec.mission import Mission, MissionHeader
from mav_gss_lib.platform.spec.parameters import Parameter
from mav_gss_lib.platform.spec.parameter_types import (
    BUILT_IN_PARAMETER_TYPES,
    EnumeratedParameterType,
    EnumValue,
    IntegerParameterType,
)
from mav_gss_lib.platform.spec.runtime import DeclarativeWalker


@dataclass(frozen=True, slots=True)
class _Pkt:
    args_raw: bytes
    header: dict


def _mission(**overrides):
    types = dict(BUILT_IN_PARAMETER_TYPES)
    types["GncMode"] = EnumeratedParameterType(
        name="GncMode", size_bits=8,
        values=(EnumValue(raw=0, label="Safe"), EnumValue(raw=1, label="Auto")),
    )
    types["V_volts"] = IntegerParameterType(name="V_volts", size_bits=16, signed=True, unit="V")
    params = {
        "GNC_MODE": Parameter(name="GNC_MODE", type_ref="GncMode"),
        "V_BUS": Parameter(name="V_BUS", type_ref="V_volts"),
    }
    containers = {
        "gnc_get_mode_res": SequenceContainer(
            name="gnc_get_mode_res",
            entry_list=(ParameterRefEntry(name="GNC_MODE", type_ref="GncMode", parameter_ref="GNC_MODE"),),
            restriction_criteria=RestrictionCriteria(
                packet=(Comparison("cmd_id", "gnc_get_mode"), Comparison("ptype", "RES")),
            ),
            domain="gnc",
        ),
    }
    cmds = {
        "gnc_get_mode": MetaCommand(
            id="gnc_get_mode",
            packet={"dest": "LPPM", "echo": "NONE", "ptype": "CMD"},
        ),
        "set_v": MetaCommand(
            id="set_v",
            packet={"dest": "EPS", "echo": "NONE", "ptype": "CMD"},
            argument_list=(Argument(name="v", type_ref="u32"),),
        ),
    }
    return Mission(
        id="testmission", name="Test", header=MissionHeader(version="1.0.0", date="2026-04-25"),
        parameter_types=types, parameters=params, bitfield_types={},
        sequence_containers=containers, meta_commands=cmds,
    )


class TestDeclarativeWalker(unittest.TestCase):
    def test_extract_emits_fragment_for_matching_packet(self):
        m = _mission()
        walker = DeclarativeWalker(m, plugins={})
        pkt = _Pkt(args_raw=b"1", header={"cmd_id": "gnc_get_mode", "ptype": "RES"})
        fragments = list(walker.extract(pkt, now_ms=42))
        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0].key, "GNC_MODE")
        self.assertEqual(fragments[0].domain, "gnc")
        self.assertEqual(fragments[0].value, 1)

    def test_extract_no_match_yields_nothing(self):
        m = _mission()
        walker = DeclarativeWalker(m, plugins={})
        pkt = _Pkt(args_raw=b"", header={"cmd_id": "missing", "ptype": "RES"})
        self.assertEqual(list(walker.extract(pkt, now_ms=0)), [])

    def test_encode_args_ascii_int(self):
        m = _mission()
        walker = DeclarativeWalker(m, plugins={})
        out = walker.encode_args("set_v", {"v": 42})
        self.assertEqual(out, b"42")

    def test_encode_args_no_arguments_returns_empty(self):
        m = _mission()
        walker = DeclarativeWalker(m, plugins={})
        out = walker.encode_args("gnc_get_mode", {})
        self.assertEqual(out, b"")

    def test_arg_run_size_returns_none_when_dynamic(self):
        m = _mission()
        walker = DeclarativeWalker(m, plugins={})
        # u32 ASCII width is dynamic — return None
        self.assertIsNone(walker.arg_run_size("set_v"))


if __name__ == "__main__":
    unittest.main()
