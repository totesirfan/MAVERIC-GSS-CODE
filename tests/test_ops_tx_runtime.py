"""Operations-focused TX runtime tests for MAVERIC GSS."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import mav_gss_lib.web_runtime.services as services
from mav_gss_lib.missions.maveric.wire_format import resolve_ptype
from mav_gss_lib.web_runtime.runtime import make_cmd, sanitize_queue_items, validate_cmd_item
from mav_gss_lib.web_runtime.state import create_runtime


class TestTxRuntime(unittest.TestCase):
    """Covers TX validation plus send/guard/delay/abort lifecycle behavior."""

    def setUp(self):
        self.runtime = create_runtime()
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime.cfg.setdefault("general", {})["log_dir"] = self.tmp.name
        self.runtime.cfg.setdefault("tx", {})["delay_ms"] = 0
        self.runtime.tx.queue.clear()
        self.runtime.tx.history.clear()
        self.runtime.tx.zmq_sock = object()
        self.sent_payloads = []
        self.messages = []
        self.queue_updates = []

        async def _capture(msg):
            self.messages.append(msg)

        async def _capture_queue_update():
            # Capture snapshots instead of broadcasting over websockets.
            self.queue_updates.append(self.runtime.tx.sending.copy())

        self.runtime.tx.broadcast = _capture
        self.runtime.tx.send_queue_update = _capture_queue_update
        self.runtime.tx.log = None
        self._orig_send_pdu = services.send_pdu
        services.send_pdu = self._fake_send_pdu

    def tearDown(self):
        services.send_pdu = self._orig_send_pdu
        self.tmp.cleanup()

    def _fake_send_pdu(self, _sock, payload):
        """Record sent payloads while reporting success to the TX service."""
        self.sent_payloads.append(payload)
        return True

    def test_unknown_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not in schema"):
            validate_cmd_item(6, 2, 0, resolve_ptype("REQ"), "definitely_not_real", "REQ", runtime=self.runtime)

    def test_rx_only_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "receive-only"):
            validate_cmd_item(6, 2, 0, resolve_ptype("REQ"), "tlm_beacon", "1 1767230528021 0 0", runtime=self.runtime)

    def test_missing_required_args_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_cmd_item(6, 2, 0, resolve_ptype("REQ"), "set_voltage", "", runtime=self.runtime)

    def test_asm_golay_size_limit_is_enforced(self):
        with self.runtime.cfg_lock:
            old_mode = self.runtime.cfg.get("tx", {}).get("uplink_mode", "AX.25")
            self.runtime.cfg["tx"]["uplink_mode"] = "ASM+Golay"
        try:
            with self.assertRaisesRegex(ValueError, "too large for ASM\\+Golay"):
                validate_cmd_item(6, 2, 0, resolve_ptype("REQ"), "ping", "A" * 220, runtime=self.runtime)
        finally:
            with self.runtime.cfg_lock:
                self.runtime.cfg["tx"]["uplink_mode"] = old_mode

    def test_queue_restore_sanitizes_invalid_entries(self):
        valid = validate_cmd_item(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", runtime=self.runtime)
        invalid = {
            "type": "cmd",
            "src": 6,
            "dest": 2,
            "echo": 0,
            "ptype": resolve_ptype("REQ"),
            "cmd": "not_real",
            "args": "REQ",
            "guard": False,
        }
        items, skipped = sanitize_queue_items([valid, {"type": "delay", "delay_ms": 250}, invalid], runtime=self.runtime)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["cmd"], "ping")
        self.assertEqual(items[1]["type"], "delay")

    def test_run_send_processes_delay_then_command(self):
        self.runtime.tx.queue = [
            {"type": "delay", "delay_ms": 100},
            make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", runtime=self.runtime),
        ]
        self.runtime.tx.renumber_queue()
        self.runtime.tx.sending.update(active=True, idx=-1, total=len(self.runtime.tx.queue), guarding=False, sent_at=0, waiting=False)

        asyncio.run(self.runtime.tx.run_send())

        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.runtime.tx.queue, [])
        self.assertEqual(len(self.runtime.tx.history), 1)
        self.assertEqual(self.runtime.tx.history[0]["cmd"], "ping")
        self.assertTrue(any(msg.get("type") == "send_complete" for msg in self.messages if isinstance(msg, dict)))

    def test_run_send_waits_for_guard_confirmation(self):
        self.runtime.tx.queue = [
            make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", guard=True, runtime=self.runtime),
        ]
        self.runtime.tx.renumber_queue()
        self.runtime.tx.sending.update(active=True, idx=-1, total=1, guarding=False, sent_at=0, waiting=False)

        async def _run():
            task = asyncio.create_task(self.runtime.tx.run_send())
            for _ in range(20):
                if self.runtime.tx.sending["guarding"]:
                    break
                await asyncio.sleep(0.02)
            self.assertTrue(self.runtime.tx.sending["guarding"])
            self.runtime.tx.guard_ok.set()
            await task

        asyncio.run(_run())

        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.runtime.tx.queue, [])
        self.assertTrue(any(msg.get("type") == "guard_confirm" for msg in self.messages if isinstance(msg, dict)))

    def test_run_send_abort_during_guard_keeps_queue_item(self):
        self.runtime.tx.queue = [
            make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", guard=True, runtime=self.runtime),
        ]
        self.runtime.tx.renumber_queue()
        self.runtime.tx.sending.update(active=True, idx=-1, total=1, guarding=False, sent_at=0, waiting=False)

        async def _run():
            task = asyncio.create_task(self.runtime.tx.run_send())
            for _ in range(20):
                if self.runtime.tx.sending["guarding"]:
                    break
                await asyncio.sleep(0.02)
            self.assertTrue(self.runtime.tx.sending["guarding"])
            self.runtime.tx.abort.set()
            await task

        asyncio.run(_run())

        self.assertEqual(len(self.sent_payloads), 0)
        self.assertEqual(len(self.runtime.tx.queue), 1)
        self.assertTrue(any(msg.get("type") == "send_aborted" for msg in self.messages if isinstance(msg, dict)))

    def test_run_send_abort_during_delay_keeps_following_items(self):
        self.runtime.tx.queue = [
            {"type": "delay", "delay_ms": 500},
            make_cmd(6, 2, 0, resolve_ptype("REQ"), "ping", "REQ", runtime=self.runtime),
        ]
        self.runtime.tx.renumber_queue()
        self.runtime.tx.sending.update(active=True, idx=-1, total=2, guarding=False, sent_at=0, waiting=False)

        async def _run():
            task = asyncio.create_task(self.runtime.tx.run_send())
            for _ in range(20):
                if self.runtime.tx.sending["waiting"]:
                    break
                await asyncio.sleep(0.02)
            self.assertTrue(self.runtime.tx.sending["waiting"])
            self.runtime.tx.abort.set()
            await task

        asyncio.run(_run())

        self.assertEqual(len(self.sent_payloads), 0)
        self.assertEqual(len(self.runtime.tx.queue), 2)
        self.assertTrue(any(msg.get("type") == "send_aborted" for msg in self.messages if isinstance(msg, dict)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
