"""Confirms /api/schema-shaped output inlines argument-type metadata
into tx_args, so the TxBuilder UI can render description / range chip
without needing to follow type_refs.
"""

import unittest
from pathlib import Path

from mav_gss_lib.missions.maveric.declarative import build_declarative_capabilities


_MISSION_YML = Path("mav_gss_lib/missions/maveric/mission.yml")


@unittest.skipUnless(_MISSION_YML.exists(), "mission.yml is local-only; skip if absent")
class TestSchemaInlinesArgumentTypeMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        caps = build_declarative_capabilities(
            mission_yml_path=str(_MISSION_YML),
            mission_cfg={"csp": {"prio": 2, "src": 0, "dest": 8, "dport": 24, "sport": 0, "flags": 0}},
        )
        cls.schema = caps.command_ops.schema()

    def test_year_arg_carries_type_description_and_valid_range(self):
        year_arg = next(a for a in self.schema["ppm_set_time"]["tx_args"] if a["name"] == "year")
        self.assertEqual(year_arg["valid_range"], [0, 99])
        self.assertIn("2-digit", year_arg["description"])

    def test_start_delay_ms_arg_renamed_and_typed(self):
        names = [a["name"] for a in self.schema["ppm_sched_cmd"]["tx_args"]]
        self.assertIn("start_delay_ms", names)
        self.assertNotIn("start_delay", names)
        arg = next(a for a in self.schema["ppm_sched_cmd"]["tx_args"] if a["name"] == "start_delay_ms")
        self.assertIn("milliseconds", arg["description"].lower())

    def test_sched_id_user_t_range_excludes_reserved(self):
        arg = next(a for a in self.schema["ppm_sched_cmd"]["tx_args"] if a["name"] == "sched_id")
        self.assertEqual(arg["valid_range"], [16, 31])

    def test_arg_without_constraints_keeps_nulls(self):
        arg = next(a for a in self.schema["ppm_sched_cmd"]["tx_args"] if a["name"] == "cmd_args")
        self.assertIsNone(arg.get("valid_range"))
        self.assertIsNone(arg.get("valid_values"))


if __name__ == "__main__":
    unittest.main()
