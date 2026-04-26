"""/ws/alarms — FastAPI WebSocket endpoint for the unified alarm bus.

Inbound:
  {"type": "ack",     "id": "<alarm_id>", "operator": "<op>"}
  {"type": "ack_all", "operator": "<op>"}

Outbound:
  {"type": "alarm_snapshot", "alarms": [...]}
  {"type": "alarm_change",   ...}  (built by serialize_change)

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mav_gss_lib.platform.alarms.serialization import snapshot_message
from mav_gss_lib.server._broadcast import broadcast_safe
from mav_gss_lib.server.state import get_runtime

router = APIRouter()


class WebRuntimeBroadcastTarget:
    """Adapter — implements the dispatch's BroadcastTarget protocol."""

    def __init__(self, runtime) -> None:
        self._runtime = runtime

    async def broadcast_text(self, text: str) -> None:
        await broadcast_safe(
            self._runtime.alarm_clients,
            self._runtime.alarm_clients_lock,
            text,
        )


@router.websocket("/ws/alarms")
async def alarms_ws(ws: WebSocket) -> None:
    runtime = get_runtime(ws)
    await ws.accept()
    with runtime.alarm_clients_lock:
        runtime.alarm_clients.append(ws)
    try:
        await ws.send_text(json.dumps(snapshot_message(runtime.alarm_registry)))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            now_ms = int(time.time() * 1000)
            kind = msg.get("type")
            operator = str(msg.get("operator", ""))
            dispatch = runtime._alarm_dispatch
            if dispatch is None:
                continue  # pre-bind / shutdown — silently drop
            if kind == "ack":
                ch = runtime.alarm_registry.acknowledge(
                    str(msg.get("id", "")), now_ms, operator=operator,
                )
                dispatch.emit(ch, now_ms)
            elif kind == "ack_all":
                for ch in runtime.alarm_registry.acknowledge_all(now_ms, operator=operator):
                    dispatch.emit(ch, now_ms)
    except WebSocketDisconnect:
        pass
    except Exception:
        logging.exception("alarms_ws handler")
    finally:
        with runtime.alarm_clients_lock:
            try:
                runtime.alarm_clients.remove(ws)
            except ValueError:
                pass


__all__ = ["WebRuntimeBroadcastTarget", "router"]
