"""Tests for mission config seeding and startup diagnostics.

Verifies:
  1. MAVERIC build(ctx) seeds mission_cfg and platform_cfg.tx with defaults
  2. Operator-supplied values in gss.yml win over mission defaults
  3. Platform _DEFAULTS stay mission-free
  4. MAVERIC settings helpers and init_nodes accept the native mission-config shape
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib.config import _DEFAULTS, load_split_config
from mav_gss_lib.missions.maveric.defaults import seed_mission_cfg
from mav_gss_lib.missions.maveric.nodes import init_nodes
from mav_gss_lib.missions.maveric.config_access import command_defs_name, gs_node_name
from mav_gss_lib.platform.loader import load_mission_spec_from_split


class TestMissionDefaultsSeeding(unittest.TestCase):
    """Verify MAVERIC defaults seeding into split state."""

    def test_seed_mission_cfg_fills_missing_keys(self):
        platform_cfg = {"tx": {}}
        mission_cfg: dict = {}
        seed_mission_cfg(mission_cfg, platform_cfg)
        self.assertIn("nodes", mission_cfg)
        self.assertIn("ptypes", mission_cfg)
        self.assertEqual(mission_cfg["mission_name"], "MAVERIC")
        self.assertEqual(mission_cfg["gs_node"], "GS")
        self.assertEqual(mission_cfg["command_defs"], "commands.yml")
        self.assertIn("frequency", platform_cfg["tx"])
        self.assertEqual(platform_cfg["tx"]["uplink_mode"], "ASM+Golay")

    def test_seed_mission_cfg_respects_operator_values(self):
        """Operator-set mission_cfg values win over mission defaults."""
        mission_cfg = {
            "mission_name": "OPERATOR_NAME",
            "nodes": {0: "ZERO", 99: "CUSTOM"},
            "ax25": {"src_call": "REAL"},
        }
        seed_mission_cfg(mission_cfg, {"tx": {"frequency": "437.6 MHz"}})
        self.assertEqual(mission_cfg["mission_name"], "OPERATOR_NAME")
        self.assertEqual(mission_cfg["nodes"][0], "ZERO")
        self.assertEqual(mission_cfg["nodes"][99], "CUSTOM")
        # MAVERIC default for node 1 fills the gap.
        self.assertEqual(mission_cfg["nodes"][1], "LPPM")
        # One-deep merge on ax25: operator src_call wins, default dest_call fills.
        self.assertEqual(mission_cfg["ax25"]["src_call"], "REAL")
        self.assertEqual(mission_cfg["ax25"]["dest_call"], "NOCALL")

    def test_build_maveric_from_empty_split_seeds_mission_cfg(self):
        """Loading the MAVERIC spec with an empty mission_cfg still yields
        a populated spec via build(ctx)."""
        mission_cfg: dict = {}
        spec = load_mission_spec_from_split({}, "maveric", mission_cfg)
        self.assertEqual(spec.name, "MAVERIC")
        self.assertIn("nodes", mission_cfg)
        self.assertIn("ptypes", mission_cfg)
        self.assertIn("ax25", mission_cfg)
        self.assertIn("csp", mission_cfg)

    def test_maveric_settings_helpers_accept_native_mission_shape(self):
        mission_cfg = {
            "nodes": {0: "NONE", 1: "CPU"},
            "ptypes": {1: "CMD"},
            "gs_node": "CPU",
            "command_defs": "native-commands.yml",
        }
        self.assertEqual(gs_node_name(mission_cfg), "CPU")
        self.assertEqual(command_defs_name(mission_cfg), "native-commands.yml")

    def test_init_nodes_accepts_native_mission_shape(self):
        mission_cfg = {
            "nodes": {0: "NONE", 1: "CPU"},
            "ptypes": {1: "CMD"},
            "gs_node": "CPU",
        }
        nodes = init_nodes(mission_cfg)
        self.assertEqual(nodes.gs_node, 1)


class TestConfigDefaults(unittest.TestCase):
    def test_platform_defaults_have_no_mission_keys(self):
        """Platform _DEFAULTS must not carry mission-owned placeholders."""
        for key in ("nodes", "ptypes", "node_descriptions", "ax25", "csp"):
            self.assertNotIn(key, _DEFAULTS,
                f"'{key}' should not be in platform _DEFAULTS")

    def test_load_split_config_returns_mission_free_platform_cfg(self):
        """load_split_config returns platform_cfg without mission keys."""
        platform_cfg, _, _ = load_split_config()
        self.assertIn("tx", platform_cfg)
        self.assertIn("rx", platform_cfg)
        self.assertIn("general", platform_cfg)
        for key in ("nodes", "ptypes", "ax25", "csp"):
            self.assertNotIn(key, platform_cfg)

    def test_build_populates_mission_cfg_from_real_gss_yml(self):
        """Loading MAVERIC against the real operator split state yields a
        fully populated mission_cfg."""
        platform_cfg, mission_id, mission_cfg = load_split_config()
        load_mission_spec_from_split(platform_cfg, mission_id, mission_cfg)
        self.assertIn("nodes", mission_cfg)
        self.assertIn("ptypes", mission_cfg)
        self.assertIn("ax25", mission_cfg)
        self.assertIn("csp", mission_cfg)
        self.assertTrue(len(mission_cfg["nodes"]) > 0)


if __name__ == "__main__":
    unittest.main()
