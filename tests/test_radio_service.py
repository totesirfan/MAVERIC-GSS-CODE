"""Unit tests for RadioService — the optional GNU Radio supervisor."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mav_gss_lib.server.radio.service import RadioService


def _fake_runtime(radio_cfg=None):
    radio_cfg = radio_cfg or {"enabled": True, "script": "gnuradio/MAV_DUO.py"}
    return SimpleNamespace(
        platform_cfg={"radio": radio_cfg},
        mission_id="maveric",
        rx=SimpleNamespace(log=None),
        tx=SimpleNamespace(log=None),
    )


class RadioServiceConfigTests(unittest.TestCase):
    def test_log_capacity_clamped(self):
        rt = _fake_runtime({"log_lines": 50})
        svc = RadioService(rt)
        self.assertEqual(svc.log_capacity(), 100)  # clamps to floor

    def test_disabled_start_returns_status_with_error(self):
        rt = _fake_runtime({"enabled": False})
        svc = RadioService(rt)
        result = svc.start()
        self.assertEqual(result["state"], "stopped")
        self.assertIn("disabled", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
