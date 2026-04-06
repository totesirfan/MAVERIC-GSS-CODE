"""Operations-focused web runtime and config workflow tests for MAVERIC GSS."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mav_gss_lib.config import (
    get_command_defs_path,
    get_decoder_yml_path,
    get_generated_commands_dir,
    load_gss_config,
)
from mav_gss_lib.protocol import resolve_ptype
from mav_gss_lib.web_runtime.api import (
    export_queue,
    import_file,
    list_import_files,
    parse_import_file,
    preview_import,
)
from mav_gss_lib.web_runtime.runtime import make_cmd, make_delay
from mav_gss_lib.web_runtime.state import create_runtime


def _request_for(runtime, *, token=True):
    """Build the minimal request shape expected by the API helpers."""
    headers = {}
    if token:
        headers["x-maveric-token"] = runtime.session_token
    app = SimpleNamespace(state=SimpleNamespace(runtime=runtime))
    return SimpleNamespace(app=app, headers=headers)


class TestWebRuntimeWorkflows(unittest.TestCase):
    """Covers config-path and import/export workflows exposed to operators."""

    def setUp(self):
        self.cfg = load_gss_config()
        self.runtime = create_runtime()
        self.tmp = tempfile.TemporaryDirectory()
        self.generated_dir = Path(self.tmp.name) / "imports"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.runtime.cfg.setdefault("general", {})["generated_commands_dir"] = str(self.generated_dir)
        self.runtime.tx.queue.clear()

        async def _noop(_msg=None):
            # API helpers await this during import/export flows.
            return None

        self.runtime.tx.send_queue_update = _noop

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_paths_resolve_expected_locations(self):
        command_defs = Path(get_command_defs_path(self.cfg))
        decoder_yml = Path(get_decoder_yml_path(self.cfg))
        generated_dir = get_generated_commands_dir(self.cfg)
        self.assertTrue(command_defs.is_absolute())
        self.assertTrue(command_defs.exists())
        self.assertTrue(decoder_yml.is_absolute())
        self.assertEqual(generated_dir.name, "generated_commands")

    def test_config_paths_preserve_absolute_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self.cfg["general"]["command_defs"] = str(tmp_path / "cmds.yml")
            self.cfg["general"]["decoder_yml"] = str(tmp_path / "decoder.yml")
            self.cfg["general"]["generated_commands_dir"] = str(tmp_path / "exports")
            self.assertEqual(Path(get_command_defs_path(self.cfg)), tmp_path / "cmds.yml")
            self.assertEqual(Path(get_decoder_yml_path(self.cfg)), tmp_path / "decoder.yml")
            self.assertEqual(get_generated_commands_dir(self.cfg), tmp_path / "exports")

    def test_parse_import_file_supports_hybrid_array_and_sanitizes_comments(self):
        payload = """
        // comment
        ["GS", "EPS", "NONE", "REQ", "ping", "REQ", "guard": true] // trailing
        {"type": "delay", "delay_ms": 250}
        """.strip()
        path = self.generated_dir / "sample.jsonl"
        path.write_text(payload + "\n")
        items, skipped = parse_import_file(path, runtime=self.runtime)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["guard"])
        self.assertEqual(items[0]["cmd"], "ping")
        self.assertEqual(items[1]["type"], "delay")

    def test_list_import_files_uses_configured_directory(self):
        (self.generated_dir / "a.jsonl").write_text("{}\n")
        (self.generated_dir / "b.jsonl").write_text("{}\n")
        result = asyncio.run(list_import_files(_request_for(self.runtime)))
        names = [item["name"] for item in result]
        self.assertEqual(set(names), {"a.jsonl", "b.jsonl"})

    def test_preview_and_import_use_sanitized_runtime_queue_items(self):
        path = self.generated_dir / "queue.jsonl"
        path.write_text('["GS", "EPS", "NONE", "REQ", "ping", "REQ"]\n')
        preview = asyncio.run(preview_import("queue.jsonl", _request_for(self.runtime)))
        self.assertEqual(preview["skipped"], 0)
        self.assertEqual(preview["items"][0]["cmd"], "ping")
        self.assertEqual(preview["items"][0]["dest"], "EPS")

        result = asyncio.run(import_file("queue.jsonl", _request_for(self.runtime)))
        self.assertEqual(result["loaded"], 1)
        self.assertEqual(self.runtime.tx.queue[0]["cmd"], "ping")

    def test_export_queue_writes_to_configured_directory(self):
        self.runtime.tx.queue.extend(
            [
                make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", runtime=self.runtime),
                make_delay(500),
            ]
        )
        result = asyncio.run(export_queue({"name": "ops smoke"}, _request_for(self.runtime)))
        self.assertTrue(result["ok"])
        export_path = self.generated_dir / "ops_smoke.jsonl"
        self.assertTrue(export_path.exists())
        contents = export_path.read_text()
        self.assertIn('"cmd": "ping"', contents)
        self.assertIn('"type": "delay"', contents)

    def test_export_queue_requires_session_token(self):
        self.runtime.tx.queue.append(
            make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", runtime=self.runtime)
        )
        response = asyncio.run(export_queue({"name": "blocked"}, _request_for(self.runtime, token=False)))
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
