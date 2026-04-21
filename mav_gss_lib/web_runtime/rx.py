"""RX runtime and websocket handling."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .state import WebRuntime, get_runtime
from .shutdown import schedule_shutdown_check
from .security import authorize_websocket

router = APIRouter()

@router.websocket("/ws/rx")
async def ws_rx(websocket: WebSocket):
    runtime = get_runtime(websocket)
    if not await authorize_websocket(websocket):
        return
    await websocket.accept()
    runtime.had_clients = True
    # Send column definitions before any packet data
    columns = runtime.adapter.packet_list_columns()
    await websocket.send_text(json.dumps({"type": "columns", "data": columns}))
    for pkt_json in list(runtime.rx.packets):
        try:
            await websocket.send_text(json.dumps({"type": "packet", "data": pkt_json}))
        except Exception:
            return

    # Plugin hook — let the adapter replay its current snapshots as
    # synthetic WS messages before the client enters its live loop.
    # This removes the need for a REST seed step on the frontend:
    # the first WS frames a plugin consumer sees are the current state.
    connect_hook = getattr(runtime.adapter, "on_client_connect", None)
    if connect_hook is not None:
        try:
            for msg in connect_hook() or []:
                await websocket.send_text(json.dumps(msg))
        except Exception:
            import logging
            logging.warning("on_client_connect hook failed", exc_info=True)

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
