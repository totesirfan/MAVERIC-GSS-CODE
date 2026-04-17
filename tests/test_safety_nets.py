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


if __name__ == "__main__":
    unittest.main(verbosity=2)
