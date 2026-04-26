"""Wire-format serializers for AlarmEvent / AlarmChange.

Pure: no FastAPI / WebSocket / I/O dependencies. Both the WS handler
(server side) and any future audit-export tool can use these.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

from typing import Any

from mav_gss_lib.platform.alarms.contract import AlarmChange, AlarmEvent
from mav_gss_lib.platform.alarms.registry import AlarmRegistry


def serialize_event(ev: AlarmEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "source": str(ev.source),
        "label": ev.label,
        "detail": ev.detail,
        "severity": ev.severity.name.lower(),
        "state": str(ev.state),
        "first_seen_ms": ev.first_seen_ms,
        "last_eval_ms": ev.last_eval_ms,
        "last_transition_ms": ev.last_transition_ms,
        "context": ev.context,
    }


def serialize_change(ch: AlarmChange) -> dict[str, Any]:
    return {
        "type": "alarm_change",
        "event": serialize_event(ch.event),
        "prev_state": str(ch.prev_state) if ch.prev_state is not None else None,
        "prev_severity": (
            ch.prev_severity.name.lower() if ch.prev_severity is not None else None
        ),
        "removed": ch.removed,
        "operator": ch.operator,
    }


def snapshot_message(registry: AlarmRegistry) -> dict[str, Any]:
    return {
        "type": "alarm_snapshot",
        "alarms": [serialize_event(e) for e in registry.snapshot()],
    }


__all__ = ["serialize_change", "serialize_event", "snapshot_message"]
