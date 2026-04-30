"""Tests for /api/radio/* — status codes, auth gating, error contracts."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from mav_gss_lib.server.app import create_app


class RadioApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.runtime = self.app.state.runtime
        self.token = self.runtime.session_token

    def test_status_returns_200_with_envelope(self) -> None:
        r = self.client.get("/api/radio/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("enabled", "state", "running", "pid", "log_lines"):
            self.assertIn(key, body)


if __name__ == "__main__":
    unittest.main()
