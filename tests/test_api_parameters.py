"""Structural tests for /api/parameters and /api/parameters/group/{group}.

Asserts envelope shape only — does not assume mission.yml content,
so passes in any environment.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from mav_gss_lib.platform.contract.parameters import ParamUpdate
from mav_gss_lib.server.app import create_app


class ApiParametersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.runtime = self.app.state.runtime
        self.token = self.runtime.session_token

    def test_get_parameters_envelope(self) -> None:
        body = self.client.get("/api/parameters").json()
        self.assertIn("parameters", body)
        self.assertIsInstance(body["parameters"], list)
        for p in body["parameters"]:
            for field in ("name", "group", "key", "type", "unit", "description", "enum", "tags"):
                self.assertIn(field, p, f"missing field: {field}")
            self.assertIsInstance(p["tags"], dict)

    def test_clear_group_isolation(self) -> None:
        # Use unique non-mission prefixes so a stale on-disk parameters.json
        # cannot contaminate. Test isolation via prefix uniqueness.
        self.runtime.parameter_cache.apply([
            ParamUpdate(name="_test_alpha.X", value=1, ts_ms=1000),
            ParamUpdate(name="_test_beta.Y", value=2, ts_ms=1000),
        ])
        r = self.client.delete(
            "/api/parameters/group/_test_alpha",
            headers={"x-gss-token": self.token},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"cleared": 1})
        names = {p["name"] for p in self.runtime.parameter_cache.replay()}
        self.assertNotIn("_test_alpha.X", names)
        self.assertIn("_test_beta.Y", names)
        # Cleanup so the next test run starts clean.
        self.runtime.parameter_cache.clear_group("_test_beta")

    def test_clear_group_requires_token(self) -> None:
        r = self.client.delete("/api/parameters/group/_test_alpha")
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
