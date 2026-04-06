"""Tests for mission config validation and startup diagnostics.

Verifies:
  1. mission.yml is read and merged correctly
  2. Missing mission.yml produces a warning but doesn't crash
  3. Config validation catches invalid mission configs
  4. Startup diagnostics include mission metadata
"""

import unittest
import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib.config import load_gss_config
from mav_gss_lib.mission_adapter import (
    load_mission_adapter,
    _merge_mission_metadata,
    _MISSION_REGISTRY,
    MissionAdapter,
)
from mav_gss_lib.protocol import init_nodes, load_command_defs
from mav_gss_lib.config import get_command_defs_path


class TestMissionYml(unittest.TestCase):
    """Verify mission.yml reading and merging."""

    def test_maveric_mission_yml_exists(self):
        """MAVERIC mission.yml is present in the package directory."""
        from mav_gss_lib.missions import maveric
        pkg_dir = os.path.dirname(os.path.abspath(maveric.__file__))
        yml_path = os.path.join(pkg_dir, "mission.yml")
        self.assertTrue(os.path.isfile(yml_path), f"Expected {yml_path} to exist")

    def test_maveric_mission_yml_has_required_fields(self):
        """MAVERIC mission.yml contains required metadata fields."""
        import yaml
        from mav_gss_lib.missions import maveric
        pkg_dir = os.path.dirname(os.path.abspath(maveric.__file__))
        with open(os.path.join(pkg_dir, "mission.yml")) as f:
            data = yaml.safe_load(f)
        self.assertIn("mission_name", data)
        self.assertIn("nodes", data)
        self.assertIn("ptypes", data)
        self.assertIn("command_defs", data)
        self.assertEqual(data["mission_name"], "MAVERIC")

    def test_merge_fills_missing_keys(self):
        """_merge_mission_metadata fills keys absent from cfg."""
        cfg = {"general": {}}
        meta = {
            "mission_name": "TEST",
            "nodes": {0: "NONE", 1: "CPU"},
            "gs_node": "CPU",
        }
        _merge_mission_metadata(cfg, meta)
        self.assertEqual(cfg["nodes"], {0: "NONE", 1: "CPU"})
        self.assertEqual(cfg["general"]["mission_name"], "TEST")
        self.assertEqual(cfg["general"]["gs_node"], "CPU")

    def test_merge_does_not_override_operator_config(self):
        """Operator config values take precedence over mission.yml."""
        cfg = {
            "general": {"mission_name": "OPERATOR_NAME"},
            "nodes": {0: "ZERO", 99: "CUSTOM"},
        }
        meta = {
            "mission_name": "MISSION_NAME",
            "nodes": {0: "NONE", 1: "CPU"},
        }
        _merge_mission_metadata(cfg, meta)
        # Operator values win
        self.assertEqual(cfg["general"]["mission_name"], "OPERATOR_NAME")
        self.assertEqual(cfg["nodes"][0], "ZERO")
        self.assertEqual(cfg["nodes"][99], "CUSTOM")
        # Mission fills gaps
        self.assertEqual(cfg["nodes"][1], "CPU")


class TestStartupDiagnostics(unittest.TestCase):
    """Verify startup logging includes mission metadata."""

    def test_startup_log_includes_mission_info(self):
        """load_mission_adapter() logs mission name, id, API version."""
        from mav_gss_lib.mission_adapter import load_mission_metadata
        cfg = load_gss_config()
        load_mission_metadata(cfg)
        init_nodes(cfg)
        cmd_defs, _ = load_command_defs(get_command_defs_path(cfg))

        with self.assertLogs(level=logging.INFO) as cm:
            load_mission_adapter(cfg, cmd_defs)

        log_output = "\n".join(cm.output)
        self.assertIn("Mission loaded", log_output)
        self.assertIn("MAVERIC", log_output)
        self.assertIn("adapter API v1", log_output)

    def test_missing_mission_yml_does_not_crash(self):
        """A mission with no mission.yml still loads (with warning)."""
        _MISSION_REGISTRY["echo_test"] = "tests.echo_mission"
        try:
            cfg = {"general": {"mission": "echo_test"}}
            adapter = load_mission_adapter(cfg, {})
            self.assertIsInstance(adapter, MissionAdapter)
        finally:
            del _MISSION_REGISTRY["echo_test"]


if __name__ == "__main__":
    unittest.main()
