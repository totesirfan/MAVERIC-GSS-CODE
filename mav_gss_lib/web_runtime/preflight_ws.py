"""Preflight WebSocket endpoint — streams startup check results.

Sends check results as they execute. Late-joining clients receive
the full backlog of already-completed checks. Supports rerun with
single-run guard to prevent concurrent executions.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mav_gss_lib.preflight import CheckResult, run_preflight, summarize
from .state import get_runtime
from .security import authorize_websocket

router = APIRouter()


async def _broadcast(runtime, event: dict) -> None:
    """Append event to backlog and send to all current clients."""
    with runtime.preflight_lock:
        runtime.preflight_results.append(event)
        clients = list(runtime.preflight_clients)
    msg = json.dumps(event)
    for ws in clients:
        try:
            await ws.send_text(msg)
        except Exception:
            pass


async def run_preflight_and_broadcast(runtime, emit_reset: bool = False) -> None:
    """Run preflight checks and broadcast each result to connected clients.

    Guarded by runtime.preflight_running — concurrent calls are ignored.
    Always emits a summary event, even if the check generator raises,
    so the UI reaches a terminal state and rerun stays unblocked.

    When emit_reset=True, clears backlog and broadcasts a {type:"reset"}
    event to all current clients atomically before streaming new results.
    This folds the rerun reset into the broadcast function itself, so a
    late joiner cannot snapshot stale backlog between reset and clear.
    """
    if runtime.preflight_running:
        return
    runtime.preflight_running = True
    try:
        # Atomically clear backlog + snapshot clients for reset broadcast.
        # New clients connecting after this lock release will see an empty
        # backlog, so they cannot receive stale results from the prior run.
        with runtime.preflight_lock:
            runtime.preflight_results.clear()
            runtime.preflight_done = False
            reset_clients = list(runtime.preflight_clients) if emit_reset else []

        if emit_reset:
            reset_msg = json.dumps({"type": "reset"})
            for ws in reset_clients:
                try:
                    await ws.send_text(reset_msg)
                except Exception:
                    pass

        cfg = runtime.cfg
        results: list[CheckResult] = []

        try:
            for check in run_preflight(cfg=cfg):
                event = {
                    "type": "check",
                    "group": check.group,
                    "label": check.label,
                    "status": check.status,
                    "fix": check.fix,
                    "detail": check.detail,
                }
                await _broadcast(runtime, event)
                results.append(check)
                # Yield to event loop so WS frames flush and clients can connect
                await asyncio.sleep(0)
        except Exception as exc:
            # Generator raised. Emit a synthetic fail event so the UI sees
            # a concrete error line, then fall through to the summary.
            err = CheckResult(
                group="internal",
                label="Preflight generator error",
                status="fail",
                detail=str(exc),
            )
            await _broadcast(runtime, {
                "type": "check",
                "group": err.group,
                "label": err.label,
                "status": err.status,
                "fix": err.fix,
                "detail": err.detail,
            })
            results.append(err)

        summary = summarize(results)
        summary_event = {
            "type": "summary",
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "warnings": summary.warnings,
            "ready": summary.ready,
        }
        await _broadcast(runtime, summary_event)
        with runtime.preflight_lock:
            runtime.preflight_done = True
    finally:
        runtime.preflight_running = False


@router.websocket("/ws/preflight")
async def ws_preflight(websocket: WebSocket):
    runtime = get_runtime(websocket)
    if not await authorize_websocket(websocket):
        return
    await websocket.accept()

    # Snapshot backlog and register as a live client (under lock)
    with runtime.preflight_lock:
        backlog = list(runtime.preflight_results)
        runtime.preflight_clients.append(websocket)

    try:
        # Replay backlog for late joiners
        for event in backlog:
            await websocket.send_text(json.dumps(event))

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("action") == "rerun" and not runtime.preflight_running:
                # run_preflight_and_broadcast atomically clears backlog
                # and broadcasts the reset event to all current clients.
                await run_preflight_and_broadcast(runtime, emit_reset=True)
    except WebSocketDisconnect:
        pass
    finally:
        with runtime.preflight_lock:
            if websocket in runtime.preflight_clients:
                runtime.preflight_clients.remove(websocket)
