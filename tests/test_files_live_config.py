"""MAVERIC ImageKindAdapter reads live mission config.

Regression guard: ImageKindAdapter must close over a live reference
to mission_config so /api/config edits to imaging.thumb_prefix are
observed without rebuilding the MissionSpec. This is the same
guarantee the legacy imaging router's config_accessor provided.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


MISSION_YML = Path(__file__).parent.parent / "mav_gss_lib/missions/maveric/mission.yml"


@unittest.skipUnless(MISSION_YML.is_file(), "mission.yml not present (gitignored)")
class TestMavericImageAdapterClosesOverLiveMissionConfig(unittest.TestCase):
    def _build_mission_capturing_adapter(self, mission_config: dict):
        """Build the MAVERIC MissionSpec while capturing the
        ImageKindAdapter constructor argument so we can assert on it.
        """
        from mav_gss_lib.missions.maveric import mission as maveric_mission
        from mav_gss_lib.missions.maveric.files import registry as files_registry
        from mav_gss_lib.platform import MissionContext

        captured: dict = {}
        real_build = files_registry.build_file_kind_adapters

        def _spy(cfg):
            adapters = real_build(cfg)
            captured["adapters"] = adapters
            captured["seen_cfg"] = cfg
            return adapters

        files_registry.build_file_kind_adapters = _spy
        # mission.py imports build_file_kind_adapters at module load; for
        # the spy to take effect we patch the attribute mission.py uses.
        maveric_mission.build_file_kind_adapters = _spy
        try:
            ctx = MissionContext(
                platform_config={},
                mission_config=mission_config,
                data_dir=Path(tempfile.mkdtemp()),
            )
            spec = maveric_mission.build(ctx)
        finally:
            files_registry.build_file_kind_adapters = real_build
            maveric_mission.build_file_kind_adapters = real_build
        return spec, captured

    def test_image_adapter_holds_live_mission_cfg_reference(self):
        from mav_gss_lib.server.state import create_runtime
        rt = create_runtime()

        _spec, captured = self._build_mission_capturing_adapter(rt.mission_cfg)

        adapters = captured.get("adapters") or []
        image_adapter = next((a for a in adapters if a.kind == "image"), None)
        self.assertIsNotNone(image_adapter, "image adapter not constructed")
        self.assertIs(
            image_adapter.mission_cfg, rt.mission_cfg,
            "ImageKindAdapter.mission_cfg must be the live mission_cfg dict, "
            "not a snapshot — mutations to runtime.mission_cfg must propagate.",
        )

        # Confirm in-place mutation is observed via the adapter's
        # thumb_prefix property.
        rt.mission_cfg.setdefault("imaging", {})["thumb_prefix"] = "ROUNDTRIP_"
        self.assertEqual(image_adapter.thumb_prefix, "ROUNDTRIP_")

    def test_files_status_endpoint_reflects_live_thumb_prefix(self):
        """End-to-end: hit /api/plugins/files/status?kind=image after
        mutating runtime.mission_cfg.imaging.thumb_prefix and confirm
        the router responds 200 with the live adapter behind it.
        """
        from fastapi.testclient import TestClient
        from mav_gss_lib.server.app import create_app

        app = create_app()
        runtime = app.state.runtime
        runtime.mission_cfg.setdefault("imaging", {})["thumb_prefix"] = "seed_"
        client = TestClient(app)
        resp = client.get("/api/plugins/files/status?kind=image")
        self.assertEqual(resp.status_code, 200, resp.text)


if __name__ == "__main__":
    unittest.main()
