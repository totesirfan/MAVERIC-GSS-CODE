"""Guardrail: every cmd_id referenced by FILE_KIND_CAPS in the frontend
registry exists in mission.yml's meta_commands and routes to the same
allowed nodes as the registry's fallbackNodes.

Skips when mission.yml is absent (gitignored on developer machines that
don't have the mission file)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
CAPS_TS = REPO / "mav_gss_lib/web/src/plugins/maveric/shared/fileKinds.ts"
MISSION_YML = REPO / "mav_gss_lib/missions/maveric/mission.yml"


def _extract_cmd_ids(src: str) -> set[str]:
    referenced: set[str] = set()
    referenced.update(re.findall(r"(?:cntCmd|getCmd|deleteCmd|captureCmd):\s*'([a-z_]+)'", src))
    for block in re.findall(r"extraCmds:\s*\[([^\]]+)\]", src):
        referenced.update(re.findall(r"'([a-z_]+)'", block))
    return referenced


class FrontendFileKindsCapsTests(unittest.TestCase):
    def setUp(self) -> None:
        if not CAPS_TS.exists():
            self.skipTest(f"{CAPS_TS} not present")
        if not MISSION_YML.exists():
            self.skipTest(f"{MISSION_YML} not present (gitignored)")

    def test_all_caps_cmd_ids_exist_in_mission(self) -> None:
        referenced = _extract_cmd_ids(CAPS_TS.read_text())
        mission = yaml.safe_load(MISSION_YML.read_text()) or {}
        meta_commands = set((mission.get("meta_commands") or {}).keys())
        missing = referenced - meta_commands
        self.assertFalse(
            missing,
            f"FILE_KIND_CAPS references cmd_ids absent from mission.yml meta_commands: {sorted(missing)}",
        )

    def test_caps_cmd_ids_route_to_caps_fallback_nodes(self) -> None:
        """cnt/get/delete cmd_ids must allow exactly the registry's fallback nodes."""
        referenced = _extract_cmd_ids(CAPS_TS.read_text())
        mission = yaml.safe_load(MISSION_YML.read_text()) or {}
        meta_commands = mission.get("meta_commands") or {}

        registry_nodes = {"HLNV", "ASTR"}
        for cmd_id in sorted(referenced):
            if cmd_id not in meta_commands:
                continue
            allowed = (meta_commands[cmd_id].get("allowed_packet") or {}).get("dest") or []
            self.assertEqual(
                set(allowed),
                registry_nodes,
                f"{cmd_id}: allowed_packet.dest={allowed}, registry expects {sorted(registry_nodes)}",
            )


if __name__ == "__main__":
    unittest.main()
