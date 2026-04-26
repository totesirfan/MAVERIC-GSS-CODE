"""GET /api/parameters includes a freshness map keyed by container id."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from mav_gss_lib.server.api.parameters import _build_freshness_payload


class TestFreshnessPayload(unittest.TestCase):
    def test_built_from_spec_and_last_arrival(self):
        spec = MagicMock()
        c1 = MagicMock(); c1.expected_period_ms = 60000
        c2 = MagicMock(); c2.expected_period_ms = 30000
        spec.sequence_containers = {"tlm_beacon": c1, "eps_hk": c2}
        last_arrival = {"tlm_beacon": 1714233900000}  # eps_hk never seen
        out = _build_freshness_payload(spec, last_arrival)
        self.assertEqual(out["tlm_beacon"]["last_ms"], 1714233900000)
        self.assertEqual(out["tlm_beacon"]["expected_period_ms"], 60000)
        self.assertIsNone(out["eps_hk"]["last_ms"])

    def test_no_spec_returns_empty(self):
        self.assertEqual(_build_freshness_payload(None, {}), {})


if __name__ == "__main__":
    unittest.main()
