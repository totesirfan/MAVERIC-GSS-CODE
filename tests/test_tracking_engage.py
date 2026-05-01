import threading
import unittest
from unittest.mock import MagicMock

from mav_gss_lib.platform.tracking.models import DopplerCorrection
from mav_gss_lib.server.tracking.service import (
    NullDopplerSink,
    TrackingService,
)


class _FakeRuntime:
    def __init__(self, control: dict | None = None) -> None:
        self.platform_cfg = {
            "tracking": {
                "selected_station_id": "usc",
                "stations": [
                    {"id": "usc", "name": "USC", "lat_deg": 34.02,
                     "lon_deg": -118.28, "alt_m": 70.0, "min_elevation_deg": 5.0}
                ],
                "tle": {
                    "source": "test",
                    "name": "MAVERIC",
                    "line1": "1 99999U 26001A   26182.53800926  .00000000  00000-0  15000-3 0  9999",
                    "line2": "2 99999  97.8250 154.7171 0058009 348.1000 351.9980 14.91466332000019",
                },
                "frequencies": {"rx_hz": 437_500_000.0, "tx_hz": 437_600_000.0},
                "display": {"day_night_map": True},
                "control": control or {
                    "rx_zmq_addr": "tcp://127.0.0.1:0",
                    "tx_zmq_addr": "tcp://127.0.0.1:0",
                    "tick_period_s": 1.0,
                },
            }
        }
        self.cfg_lock = threading.Lock()


class TrackingEngageTests(unittest.TestCase):
    def test_engage_swaps_in_active_sink_and_sets_mode(self) -> None:
        runtime = _FakeRuntime()
        active_sink = MagicMock()
        service = TrackingService(runtime, sink_factory=lambda **_: active_sink)

        mode = service.engage()

        self.assertEqual(mode, "connected")
        self.assertIs(service._sink, active_sink)
        self.assertEqual(service.doppler_mode, "connected")

    def test_disengage_restores_null_sink_and_closes_previous(self) -> None:
        runtime = _FakeRuntime()
        active_sink = MagicMock()
        service = TrackingService(runtime, sink_factory=lambda **_: active_sink)
        service.engage()

        mode = service.disengage()

        self.assertEqual(mode, "disconnected")
        self.assertIsInstance(service._sink, NullDopplerSink)
        active_sink.close.assert_called_once()

    def test_engage_failure_keeps_null_sink(self) -> None:
        runtime = _FakeRuntime()

        def boom(**_: object):
            raise RuntimeError("zmq bind failed")

        service = TrackingService(runtime, sink_factory=boom)

        with self.assertRaises(RuntimeError):
            service.engage()
        self.assertIsInstance(service._sink, NullDopplerSink)
        self.assertEqual(service.doppler_mode, "disconnected")

    def test_engage_is_idempotent(self) -> None:
        runtime = _FakeRuntime()
        calls: list[int] = []

        def factory(**_: object):
            calls.append(1)
            return MagicMock()

        service = TrackingService(runtime, sink_factory=factory)
        service.engage()
        service.engage()  # must not rebind
        self.assertEqual(len(calls), 1)
        self.assertEqual(service.doppler_mode, "connected")

    def test_disengage_when_already_disconnected_is_noop(self) -> None:
        runtime = _FakeRuntime()
        service = TrackingService(runtime)
        self.assertEqual(service.disengage(), "disconnected")

    def test_doppler_publishes_when_connected(self) -> None:
        runtime = _FakeRuntime()
        active_sink = MagicMock()
        service = TrackingService(runtime, sink_factory=lambda **_: active_sink)
        service.engage()

        result = service.doppler(time_ms=1_700_000_000_000)

        self.assertEqual(result["mode"], "connected")
        active_sink.publish.assert_called_once()
        published: DopplerCorrection = active_sink.publish.call_args.args[0]
        self.assertEqual(published.station_id, "usc")


if __name__ == "__main__":
    unittest.main()
