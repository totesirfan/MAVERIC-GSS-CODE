"""Side-effect bundle for AlarmRegistry transitions.

Holds two pluggable sinks (audit + broadcast) and the asyncio loop the
broadcast schedules onto. Lives in the platform package so it has no
FastAPI / WS / I/O imports — sinks and the loop are injected.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from mav_gss_lib.platform.alarms.contract import AlarmChange
from mav_gss_lib.platform.alarms.serialization import serialize_change


class AuditSink(Protocol):
    def write_alarm(self, change: AlarmChange, ts_ms: int) -> None: ...


class BroadcastTarget(Protocol):
    """Anything that knows how to async-broadcast a JSON string.

    The server adapter is ``WebRuntime.alarm_clients`` paired with
    ``broadcast_safe``; tests can pass a no-op.
    """
    def broadcast_text(self, text: str) -> Awaitable[None]: ...


@dataclass(frozen=True, slots=True)
class AlarmDispatch:
    audit_sink: AuditSink
    broadcast_target: BroadcastTarget
    loop: asyncio.AbstractEventLoop | None  # None disables broadcast (test mode)

    def emit(self, change: AlarmChange | None, now_ms: int) -> None:
        if change is None:
            return
        self.audit_sink.write_alarm(change, now_ms)
        if self.loop is None:
            return
        text = json.dumps(serialize_change(change))
        self.loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self.broadcast_target.broadcast_text(text),
        )


def make_dispatch(
    audit_sink: AuditSink,
    broadcast_target: BroadcastTarget,
    loop: asyncio.AbstractEventLoop | None,
) -> AlarmDispatch:
    return AlarmDispatch(audit_sink=audit_sink,
                         broadcast_target=broadcast_target, loop=loop)


__all__ = ["AlarmDispatch", "AuditSink", "BroadcastTarget", "make_dispatch"]
