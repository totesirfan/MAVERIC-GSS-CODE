"""RX runtime and websocket handling."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .state import WebRuntime, get_runtime
from .runtime import schedule_shutdown_check
from .security import authorize_websocket

router = APIRouter()

@router.websocket("/ws/rx")
async def ws_rx(websocket: WebSocket):
    runtime = get_runtime(websocket)
    if not await authorize_websocket(websocket):
        return
    await websocket.accept()
    runtime.had_clients = True
    for pkt_json in list(runtime.rx.packets):
        try:
            await websocket.send_text(json.dumps({"type": "packet", "data": pkt_json}))
        except Exception:
            return
    with runtime.rx.lock:
        runtime.rx.clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with runtime.rx.lock:
            if websocket in runtime.rx.clients:
                runtime.rx.clients.remove(websocket)
        schedule_shutdown_check(runtime)
