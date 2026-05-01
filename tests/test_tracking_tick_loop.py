import asyncio
import threading
import unittest
from unittest.mock import MagicMock

from mav_gss_lib.server.tracking._tick import DopplerBroadcaster, doppler_tick_loop


class _Runtime:
    def __init__(self) -> None:
        self.platform_cfg = {"tracking": {"control": {
            "rx_zmq_addr": "tcp://127.0.0.1:0",
            "tx_zmq_addr": "tcp://127.0.0.1:0",
            "tick_period_s": 0.05,
        }}}
        self.cfg_lock = threading.Lock()
        self.tracking = MagicMock()
        self.tracking.doppler_mode = "connected"
        self.tracking.doppler.return_value = {"mode": "connected", "rx_tune_hz": 1.0}
        self.tracking.last_error = ""


class DopplerTickLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_loop_invokes_doppler_each_tick(self) -> None:
        runtime = _Runtime()
        broadcaster = DopplerBroadcaster()
        task = asyncio.create_task(
            doppler_tick_loop(runtime, broadcaster, period_s_override=0.05)
        )
        await asyncio.sleep(0.18)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self.assertGreaterEqual(runtime.tracking.doppler.call_count, 2)

    async def test_loop_swallows_errors_and_keeps_running(self) -> None:
        runtime = _Runtime()
        runtime.tracking.doppler.side_effect = [
            RuntimeError("boom"),
            {"mode": "connected"},
            {"mode": "connected"},
        ]
        broadcaster = DopplerBroadcaster()
        task = asyncio.create_task(
            doppler_tick_loop(runtime, broadcaster, period_s_override=0.05)
        )
        await asyncio.sleep(0.18)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self.assertGreaterEqual(runtime.tracking.doppler.call_count, 2)

    async def test_loop_broadcasts_doppler_messages(self) -> None:
        runtime = _Runtime()
        broadcaster = DopplerBroadcaster()
        received: list[dict] = []

        async def consumer() -> None:
            async for msg in broadcaster.subscribe():
                received.append(msg)
                if any(m.get("type") == "doppler" for m in received):
                    return

        consumer_task = asyncio.create_task(consumer())
        loop_task = asyncio.create_task(
            doppler_tick_loop(runtime, broadcaster, period_s_override=0.05)
        )
        try:
            await asyncio.wait_for(consumer_task, timeout=1.0)
        finally:
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        self.assertTrue(any(m.get("type") == "doppler" for m in received))


if __name__ == "__main__":
    unittest.main()
