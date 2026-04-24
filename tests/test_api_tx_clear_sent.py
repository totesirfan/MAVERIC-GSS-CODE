"""Regression test for POST /api/tx/clear-sent.

Today: unconditional clear of history. Future: gated on open verifier
CheckWindows.
"""
import tempfile
import unittest
from fastapi.testclient import TestClient

from mav_gss_lib.server.app import create_app


class ClearSentEndpoint(unittest.TestCase):
    """Auth-gated clear of in-memory TX history."""

    def _build_app(self, tmp: str):
        """Build an app with log_dir redirected to a temp directory so
        lifespan startup doesn't write session log files into cwd."""
        app = create_app()
        app.state.runtime.platform_cfg.setdefault("general", {})["log_dir"] = tmp
        token = app.state.runtime.session_token
        return app, token

    def test_clear_sent_empty_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, token = self._build_app(tmp)
            with TestClient(app) as client:
                r = client.post("/api/tx/clear-sent",
                                headers={"x-gss-token": token})
                self.assertEqual(r.status_code, 200)
                body = r.json()
                self.assertTrue(body["ok"])
                self.assertEqual(body["cleared"], 0)

    def test_clear_sent_with_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, token = self._build_app(tmp)
            runtime = app.state.runtime
            runtime.tx.history.extend([{"n": 1}, {"n": 2}, {"n": 3}])
            with TestClient(app) as client:
                r = client.post("/api/tx/clear-sent",
                                headers={"x-gss-token": token})
                self.assertEqual(r.status_code, 200)
                body = r.json()
                self.assertTrue(body["ok"])
                self.assertEqual(body["cleared"], 3)
                self.assertEqual(runtime.tx.history, [])

    def test_clear_sent_requires_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, _token = self._build_app(tmp)
            with TestClient(app) as client:
                # No x-gss-token header → 403.
                r = client.post("/api/tx/clear-sent")
                self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
