"""Regression tests for Session 1 safety-net changes."""

from __future__ import annotations

import asyncio
import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib.web_runtime._task_utils import log_task_exception


class TestLogTaskException(unittest.TestCase):
    def test_logs_exception_when_task_raises(self):
        async def _run():
            async def boom():
                raise RuntimeError("boom")

            task = asyncio.create_task(boom())
            task.add_done_callback(log_task_exception("test-task"))
            try:
                await task
            except RuntimeError:
                pass

        with self.assertLogs(level=logging.ERROR) as captured:
            asyncio.run(_run())
        self.assertTrue(any("test-task" in line and "boom" in line for line in captured.output))

    def test_does_not_log_on_successful_task(self):
        async def _run():
            async def ok():
                return 42

            task = asyncio.create_task(ok())
            task.add_done_callback(log_task_exception("test-task"))
            await task

        with self.assertNoLogs(level=logging.ERROR):
            asyncio.run(_run())

    def test_does_not_log_on_cancelled_task(self):
        async def _run():
            async def never():
                await asyncio.sleep(10)

            task = asyncio.create_task(never())
            task.add_done_callback(log_task_exception("test-task"))
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        with self.assertNoLogs(level=logging.ERROR):
            asyncio.run(_run())


class TestTaskCallbacksWired(unittest.TestCase):
    """Verify every asyncio.create_task in the web runtime has a done-callback.

    This is a structural test: reading each call site's 6-line window and
    checking for the presence of both `add_done_callback` and
    `log_task_exception`. Comment-only lines are stripped before the check
    so `# TODO wire add_done_callback(...)` cannot fool the test into
    thinking the wiring is present.
    """

    def _assert_callback_wired(self, file_relpath: str, create_task_line_substr: str):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        src = (root / file_relpath).read_text().splitlines()
        idx = next(i for i, line in enumerate(src) if create_task_line_substr in line)
        # Strip comment-only lines to avoid false positives from commented-out wiring.
        window_lines = [ln for ln in src[idx:idx + 6] if not ln.lstrip().startswith("#")]
        window = "\n".join(window_lines)
        self.assertIn("add_done_callback", window, f"missing add_done_callback near {file_relpath}:{idx + 1}")
        self.assertIn("log_task_exception", window, f"missing log_task_exception near {file_relpath}:{idx + 1}")

    def test_rx_broadcast_task_has_callback(self):
        self._assert_callback_wired(
            "mav_gss_lib/web_runtime/app.py",
            "runtime.rx.broadcast_task = asyncio.create_task(runtime.rx.broadcast_loop())",
        )

    def test_preflight_task_has_callback(self):
        self._assert_callback_wired(
            "mav_gss_lib/web_runtime/app.py",
            "runtime.preflight_task = asyncio.create_task(run_preflight_and_broadcast(runtime))",
        )

    def test_tx_send_task_has_callback(self):
        self._assert_callback_wired(
            "mav_gss_lib/web_runtime/tx_actions.py",
            "runtime.tx.send_task = asyncio.create_task(runtime.tx.run_send())",
        )

    def test_shutdown_task_has_callback(self):
        # runtime.py uses the older `asyncio.get_event_loop().create_task(...)`
        # form, so the substring we hunt for is the full assignment line.
        self._assert_callback_wired(
            "mav_gss_lib/web_runtime/runtime.py",
            "runtime.shutdown_task = asyncio.get_event_loop().create_task(check_shutdown(runtime))",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
