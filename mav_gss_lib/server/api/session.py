"""
mav_gss_lib.server.api.session -- Session Lifecycle Routes

Endpoints: api_session_get, api_session_new, api_session_rename
Helpers:   _session_info

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..state import Session, get_runtime
from ..security import require_api_token
from .._broadcast import broadcast_safe

if TYPE_CHECKING:
    from ..state import WebRuntime

router = APIRouter()


def _active_logs(runtime: "WebRuntime") -> list[Any]:
    """Return unique active log writer objects for session lifecycle actions."""
    logs = []
    for log in (runtime.rx.log, runtime.tx.log):
        if log is not None and not any(log is existing for existing in logs):
            logs.append(log)
    return logs


def _session_info(runtime: "WebRuntime") -> dict[str, Any]:
    """Build session info dict from runtime state."""
    s = runtime.session
    return {
        "session_id": s.session_id,
        "session_tag": s.session_tag,
        "started_at": s.started_at,
        "session_generation": s.session_generation,
        "operator": s.operator,
        "host": s.host,
        "station": s.station,
    }


@router.get("/api/session")
async def api_session_get(request: Request) -> dict[str, Any]:
    """Return current session info and traffic status."""
    runtime = get_runtime(request)
    info = _session_info(runtime)
    traffic_active = (
        runtime.rx.last_rx_at > 0
        and (time.time() - runtime.rx.last_rx_at) < 10.0
    )
    info["traffic_active"] = traffic_active
    return info


@router.post("/api/session/new", response_model=None)
async def api_session_new(body: dict[str, Any], request: Request) -> dict[str, Any] | JSONResponse:
    """Create a new session with two-phase atomic log rotation."""
    runtime = get_runtime(request)
    denied = require_api_token(request)
    if denied:
        return denied

    session_tag = body.get("session_tag") or body.get("tag") or "untitled"
    logs = _active_logs(runtime)
    if not logs:
        return JSONResponse(status_code=400, content={"error": "No active session"})

    old_gen = runtime.session.session_generation
    new_session = Session(
        session_id=uuid.uuid4().hex,
        session_tag=session_tag,
        started_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        session_generation=old_gen + 1,
        operator=runtime.operator,
        host=runtime.host,
        station=runtime.station,
    )

    # -- Prepare phase: open new files without closing old ones --
    prepared_logs: list[tuple[Any, dict[str, Any]]] = []
    try:
        for log in logs:
            prepared_logs.append((log, log.prepare_new_session(session_tag)))
    except Exception as exc:
        # Cleanup any prepared files on failure
        for _, prepared in prepared_logs:
            if prepared is not None:
                try:
                    prepared["jsonl_f"].close()
                except Exception:
                    pass
                try:
                    if os.path.isfile(prepared["jsonl_path"]):
                        os.remove(prepared["jsonl_path"])
                except OSError:
                    pass
        logging.error("Session prepare failed: %s", exc)
        return JSONResponse(status_code=500, content={"error": f"prepare failed: {exc}"})

    # -- Commit phase: commit each unique active log writer --
    # RX and TX normally share one SessionLog; identity de-duplication keeps
    # this safe if a test runtime wires the same object through both services.
    commit_errors = []
    for log, prepared in prepared_logs:
        try:
            log.commit_new_session(prepared)
        except Exception as exc:
            logging.error("Session log commit failed: %s", exc)
            commit_errors.append(f"session: {exc}")
    # Always update session — even partial rotation is better than stale state
    runtime.session = new_session

    # Mirror the frontend's session_new clears so a hard refresh can't
    # rehydrate stale state from the WS bootstrap path (rx.py:25, tx.py:35).
    runtime.rx.packets.clear()
    runtime.tx.history.clear()

    # Broadcast session_new to all channels
    event = {
        "type": "session_new",
        "session_id": new_session.session_id,
        "session_tag": new_session.session_tag,
        "session_generation": new_session.session_generation,
        "started_at": new_session.started_at,
        "operator": new_session.operator,
        "host": new_session.host,
        "station": new_session.station,
    }
    await runtime.rx.broadcast(event)
    await runtime.tx.broadcast(event)
    event_text = json.dumps(event)
    await broadcast_safe(runtime.session_clients, runtime.session_lock, event_text)

    info = _session_info(runtime)
    if commit_errors:
        info["ok"] = False
        info["partial"] = True
        info["error"] = "; ".join(commit_errors)
        return JSONResponse(status_code=207, content=info)
    info["ok"] = True
    return info


@router.patch("/api/session", response_model=None)
async def api_session_rename(body: dict[str, Any], request: Request) -> dict[str, Any] | JSONResponse:
    """Rename the current session tag and log files.

    Rollback is supported on POSIX (synchronous rename). On Windows,
    rename is queued to the writer thread so rollback is not reliable.
    """
    runtime = get_runtime(request)
    denied = require_api_token(request)
    if denied:
        return denied

    session_tag = (body.get("session_tag") or body.get("tag") or "").strip() or "untitled"

    # Preflight: check both log rename targets
    try:
        for log in _active_logs(runtime):
            log.rename_preflight(session_tag)
    except (FileExistsError, ValueError) as exc:
        return JSONResponse(status_code=409, content={"error": str(exc)})

    # Save original path for rollback
    logs = _active_logs(runtime)
    old_paths = [(log, log.jsonl_path) for log in logs]

    # Rename active session logs
    try:
        for log in logs:
            log.rename(session_tag)
    except Exception as exc:
        logging.error("Session rename failed: %s, rolling back", exc)
        for log, old_jsonl in old_paths:
            try:
                if log.jsonl_path != old_jsonl and os.path.exists(log.jsonl_path):
                    os.rename(log.jsonl_path, old_jsonl)
                log.jsonl_path = old_jsonl
            except Exception as rb_exc:
                logging.error("Session rollback also failed: %s", rb_exc)
        return JSONResponse(status_code=500, content={"error": f"session rename failed: {exc}"})

    # Update session tag
    runtime.session.session_tag = session_tag

    # Broadcast session_renamed
    event = {
        "type": "session_renamed",
        "session_id": runtime.session.session_id,
        "session_tag": session_tag,
        "operator": runtime.session.operator,
        "host": runtime.session.host,
        "station": runtime.session.station,
    }
    await runtime.rx.broadcast(event)
    await runtime.tx.broadcast(event)
    event_text = json.dumps(event)
    await broadcast_safe(runtime.session_clients, runtime.session_lock, event_text)

    info = _session_info(runtime)
    info["ok"] = True
    return info
