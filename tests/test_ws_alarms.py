"""WS /ws/alarms — wire serialization (imported from platform serialization)."""
from __future__ import annotations

import json
import unittest

from mav_gss_lib.platform.alarms.contract import (
    AlarmChange, AlarmEvent, AlarmSource, AlarmState, Severity,
)
from mav_gss_lib.platform.alarms.registry import AlarmRegistry, Verdict
from mav_gss_lib.platform.alarms.serialization import (
    serialize_change, serialize_event, snapshot_message,
)


class TestSerialization(unittest.TestCase):
    def test_event_severity_lowercased(self):
        ev = AlarmEvent(
            id="p.x", source=AlarmSource.PARAMETER, label="X", detail="hot",
            severity=Severity.CRITICAL, state=AlarmState.UNACKED_ACTIVE,
            first_seen_ms=1, last_eval_ms=1, last_transition_ms=1,
        )
        msg = serialize_event(ev)
        self.assertEqual(msg["severity"], "critical")
        self.assertEqual(msg["state"], "unacked_active")
        self.assertEqual(msg["source"], "parameter")

    def test_change_carries_removed_flag(self):
        ev = AlarmEvent(
            id="p.x", source=AlarmSource.PARAMETER, label="X", detail="",
            severity=Severity.WARNING, state=AlarmState.ACKED_ACTIVE,
            first_seen_ms=1, last_eval_ms=1, last_transition_ms=1,
        )
        ch = AlarmChange(event=ev, prev_state=AlarmState.UNACKED_ACTIVE,
                         prev_severity=Severity.WARNING, removed=True,
                         operator="op")
        msg = serialize_change(ch)
        self.assertEqual(msg["type"], "alarm_change")
        self.assertTrue(msg["removed"])
        self.assertEqual(msg["operator"], "op")

    def test_snapshot_envelope(self):
        r = AlarmRegistry()
        r.observe(Verdict(id="p.x", source=AlarmSource.PARAMETER, label="X",
                          severity=Severity.WARNING, detail=""), now_ms=1000)
        msg = snapshot_message(r)
        self.assertEqual(msg["type"], "alarm_snapshot")
        self.assertEqual(len(msg["alarms"]), 1)


if __name__ == "__main__":
    unittest.main()
