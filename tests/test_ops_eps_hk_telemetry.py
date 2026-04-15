"""Tests for MAVERIC EPS HK telemetry decoder + framework integration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib.missions.maveric.telemetry.types import TelemetryField


class TestTelemetryField(unittest.TestCase):

    def test_field_construction(self):
        f = TelemetryField(name="V_BUS", value=9192, unit="", raw=9192)
        self.assertEqual(f.name, "V_BUS")
        self.assertEqual(f.value, 9192)
        self.assertEqual(f.unit, "")
        self.assertEqual(f.raw, 9192)

    def test_to_dict_omits_raw(self):
        f = TelemetryField(name="V_BUS", value=9192, unit="", raw=9192)
        d = f.to_dict()
        self.assertEqual(d, {"name": "V_BUS", "value": 9192, "unit": ""})
        self.assertNotIn("raw", d)

    def test_field_is_frozen(self):
        f = TelemetryField(name="X", value=1, unit="", raw=1)
        with self.assertRaises(Exception):  # FrozenInstanceError
            f.value = 2  # type: ignore


if __name__ == "__main__":
    unittest.main()
