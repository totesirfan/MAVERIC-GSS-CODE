"""Radio WebSocket endpoint — /ws/radio log and status fan-out."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..security import authorize_websocket
from ..shutdown import schedule_shutdown_check
from ..state import get_runtime

router = APIRouter()


@router.websocket("/ws/radio")
async def ws_radio(websocket: WebSocket) -> None:
    runtime = get_runtime(websocket)
    if not await authorize_websocket(websocket):
        return
    await websocket.accept()
    runtime.had_clients = True

    try:
        await websocket.send_text(json.dumps({
            "type": "status",
            "status": runtime.radio.status(),
        }))
        await websocket.send_text(json.dumps({
            "type": "logs",
            "lines": runtime.radio.log_snapshot(),
        }))
    except Exception:
        return

    with runtime.radio.lock:
        runtime.radio.clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with runtime.radio.lock:
            if websocket in runtime.radio.clients:
                runtime.radio.clients.remove(websocket)
        schedule_shutdown_check(runtime)
