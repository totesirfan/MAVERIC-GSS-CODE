"""Platform evaluator: pure dispatch over (silence_s, zmq_state, crc_window, dup_window)."""
from __future__ import annotations

import unittest

from mav_gss_lib.platform.alarms import Severity
from mav_gss_lib.platform.alarms.evaluators.platform import (
    CRC_CRITICAL_THRESHOLD, CRC_WARNING_THRESHOLD,
    DUP_WARNING_THRESHOLD, PlatformAlarmInputs,
    SILENCE_CRITICAL_S, SILENCE_WARNING_S, evaluate_platform,
)


def _by_id(verdicts):
    return {v.id: v for v in verdicts}


class TestPlatformEvaluator(unittest.TestCase):
    def test_silence_clear(self):
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=10.0, zmq_state="OK"), now_ms=0))
        self.assertIsNone(v["platform.silence"].severity)
        self.assertIsNone(v["platform.zmq"].severity)
        self.assertIsNone(v["platform.crc"].severity)
        self.assertIsNone(v["platform.dup"].severity)

    def test_silence_warning(self):
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=SILENCE_WARNING_S, zmq_state="OK"), now_ms=0))
        self.assertEqual(v["platform.silence"].severity, Severity.WARNING)

    def test_silence_critical(self):
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=SILENCE_CRITICAL_S, zmq_state="OK"), now_ms=0))
        self.assertEqual(v["platform.silence"].severity, Severity.CRITICAL)

    def test_zmq_down_critical(self):
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0.0, zmq_state="DOWN"), now_ms=0))
        self.assertEqual(v["platform.zmq"].severity, Severity.CRITICAL)

    def test_zmq_retry_warning(self):
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0.0, zmq_state="RETRY"), now_ms=0))
        self.assertEqual(v["platform.zmq"].severity, Severity.WARNING)

    def test_crc_warning_band(self):
        now = 1_000_000
        events = tuple(now - i * 1000 for i in range(CRC_WARNING_THRESHOLD))
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0, zmq_state="OK", crc_event_ms=events),
            now_ms=now))
        self.assertEqual(v["platform.crc"].severity, Severity.WARNING)

    def test_crc_critical_band(self):
        now = 1_000_000
        events = tuple(now - i * 1000 for i in range(CRC_CRITICAL_THRESHOLD))
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0, zmq_state="OK", crc_event_ms=events),
            now_ms=now))
        self.assertEqual(v["platform.crc"].severity, Severity.CRITICAL)

    def test_old_events_outside_window_ignored(self):
        now = 1_000_000
        events = tuple(now - 70_000 - i * 1000 for i in range(20))
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0, zmq_state="OK", crc_event_ms=events),
            now_ms=now))
        self.assertIsNone(v["platform.crc"].severity)

    def test_dup_below_threshold(self):
        now = 1_000_000
        events = tuple(now - i * 1000 for i in range(DUP_WARNING_THRESHOLD - 1))
        v = _by_id(evaluate_platform(
            PlatformAlarmInputs(silence_s=0, zmq_state="OK", dup_event_ms=events),
            now_ms=now))
        self.assertIsNone(v["platform.dup"].severity)


if __name__ == "__main__":
    unittest.main()
