"""Preflight WebSocket endpoint — streams startup check results.

Sends check results as they execute. Late-joining clients receive
the full backlog of already-completed checks. Supports rerun with
single-run guard to prevent concurrent executions.

Also hosts the updater integration: schedule_update_check kicks off
check_for_updates on a worker thread at lifespan start; an additional
synthetic "updates" check is yielded after the mission checks finish;
and an {action: "apply_update"} message drives apply_update with phase
progress broadcast back over the same WS channel.

schedule_update_check lives here (rather than app.py) so all updater-
coupled WS concerns — scheduling, result resolution, apply handling —
stay co-located with the broadcast/lock primitives they share.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mav_gss_lib.preflight import CheckResult, run_preflight, summarize
from mav_gss_lib.updater import (
    DirtyTreeError,
    PipBlockedError,
    UpdateStatus,
    VenvUnavailableError,
    apply_update,
    check_for_updates,
)
from .state import get_runtime
from .security import authorize_websocket

router = APIRouter()


# =============================================================================
#  UPDATE CHECK SCHEDULING
# =============================================================================

def schedule_update_check(runtime) -> None:
    """Schedule check_for_updates() on the default thread-pool executor.

    Stores the asyncio.Future on runtime.update_status_future, replacing
    any previous value. Must be called from within the event loop.
    """
    loop = asyncio.get_running_loop()
    runtime.update_status_future = loop.run_in_executor(
        None,
        check_for_updates,
        10.0,
    )


# =============================================================================
#  BROADCAST HELPERS
# =============================================================================

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


# =============================================================================
#  UPDATES CHECK EVENT BUILDER
# =============================================================================

async def _build_updates_event(runtime) -> dict:
    """Resolve the update-status future and build the WS event dict.

    Async because runtime.update_status_future is an asyncio.Future that
    must be awaited, not .result()-polled from inside the event loop.
    """
    fut = runtime.update_status_future
    if fut is None:
        return {
            "type": "check",
            "group": "updates",
            "label": "Update check not run",
            "status": "skip",
            "fix": "",
            "detail": "",
            "meta": None,
        }
    try:
        status: UpdateStatus = await asyncio.wait_for(fut, timeout=2.0)
    except asyncio.TimeoutError:
        return {
            "type": "check",
            "group": "updates",
            "label": "Update check still running",
            "status": "skip",
            "fix": "",
            "detail": "",
            "meta": None,
        }
    except Exception as exc:
        return {
            "type": "check",
            "group": "updates",
            "label": "Update check failed",
            "status": "skip",
            "fix": "",
            "detail": str(exc),
            "meta": None,
        }

    runtime.update_status = status

    meta = {
        "branch": status.branch,
        "current_sha": status.current_sha,
        "behind_count": status.behind_count,
        "commits": [asdict(c) for c in status.commits],
        "missing_pip_deps": list(status.missing_pip_deps),
        "requirements_changed": status.requirements_changed,
        "requirements_out_of_sync": status.requirements_out_of_sync,
        "dirty": status.working_tree_dirty,
        "button": None,
        "button_disabled": False,
        "button_reason": None,
    }

    nothing_to_do = (
        status.behind_count == 0
        and not status.missing_pip_deps
        and not status.requirements_changed
        and not status.requirements_out_of_sync
    )

    if status.update_applied_sha:
        label = f"Updated to {status.update_applied_sha[:7]}"
        result_status, result_label = ("ok", label)
    elif status.fetch_failed:
        meta["fetch_error"] = status.fetch_error
        result_status, result_label = ("skip", "Update check skipped · could not reach origin")
    elif nothing_to_do:
        result_status, result_label = ("ok", f"Up to date ({status.current_sha[:7]})")
    else:
        meta["button"] = "apply"
        if status.working_tree_dirty:
            meta["button_disabled"] = True
            meta["button_reason"] = "commit or stash local changes to enable"

        parts: list[str] = []
        if status.behind_count:
            parts.append(f"{status.behind_count} commits behind")
        if status.missing_pip_deps:
            parts.append(f"installing {len(status.missing_pip_deps)} new Python packages")
        elif status.requirements_changed:
            parts.append("refreshing Python dependencies")
        elif status.requirements_out_of_sync:
            parts.append("retrying previously failed dependency install")
        result_status, result_label = ("warn", "Update available · " + " · ".join(parts))

    return {
        "type": "check",
        "group": "updates",
        "label": result_label,
        "status": result_status,
        "fix": "",
        "detail": "",
        "meta": meta,
    }


# =============================================================================
#  PREFLIGHT DRIVER
# =============================================================================

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

        # After mission checks stream, resolve update status and broadcast
        # as a final check row.
        try:
            update_event = await _build_updates_event(runtime)
            await _broadcast(runtime, update_event)
            results.append(CheckResult(
                group="updates",
                label=update_event["label"],
                status=update_event["status"],
            ))
        except Exception as exc:
            fail_event = {
                "type": "check",
                "group": "updates",
                "label": "Update check failed",
                "status": "skip",
                "fix": "",
                "detail": str(exc),
                "meta": None,
            }
            await _broadcast(runtime, fail_event)
            results.append(CheckResult(
                group="updates",
                label=fail_event["label"],
                status=fail_event["status"],
            ))

        summary = summarize(results)
        # summarize() in preflight.py does not track 'skip' — compute it here
        # so the UI can distinguish a true "all passed" run from one that
        # silently skipped the updates check (e.g., offline fetch).
        skipped = sum(1 for r in results if r.status == "skip")
        summary_event = {
            "type": "summary",
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "warnings": summary.warnings,
            "skipped": skipped,
            "ready": summary.ready,
        }
        await _broadcast(runtime, summary_event)
        with runtime.preflight_lock:
            runtime.preflight_done = True
    finally:
        runtime.preflight_running = False


# =============================================================================
#  WS ENDPOINT
# =============================================================================

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

            action = msg.get("action")

            if action == "rerun" and not runtime.preflight_running:
                # Refresh the update future so the rerun picks up a fresh fetch
                # rather than replaying the stale cached result.
                schedule_update_check(runtime)
                # run_preflight_and_broadcast atomically clears backlog
                # and broadcasts the reset event to all current clients.
                await run_preflight_and_broadcast(runtime, emit_reset=True)
                continue

            if action == "launched":
                with runtime.update_lock:
                    runtime.launched = True
                continue

            if action == "apply_update":
                await _handle_apply_update(runtime, websocket)
                continue
    except WebSocketDisconnect:
        pass
    finally:
        with runtime.preflight_lock:
            if websocket in runtime.preflight_clients:
                runtime.preflight_clients.remove(websocket)


# =============================================================================
#  APPLY UPDATE HANDLER
# =============================================================================

async def _handle_apply_update(runtime, websocket: WebSocket) -> None:
    """Handle an {action: "apply_update"} message.

    Never holds runtime.update_lock across any await — we flip the in-progress
    flag inside the lock, release, then dispatch to the worker thread.
    """
    # Phase 1: validate state and flip the in-progress flag atomically.
    fail_reason: "str | None" = None
    should_apply: bool = False
    status: "UpdateStatus | None" = None

    with runtime.update_lock:
        if runtime.launched:
            fail_reason = "updates disabled after launch"
        elif runtime.update_in_progress:
            fail_reason = "update already in progress"
        else:
            status = runtime.update_status
            if status is None:
                fail_reason = "update status unavailable (re-launch to refresh)"
            elif (
                status.behind_count == 0
                and not status.missing_pip_deps
                and not status.requirements_changed
                and not status.requirements_out_of_sync
            ):
                fail_reason = "nothing to update"
            elif status.working_tree_dirty:
                fail_reason = "local changes detected — commit or stash"
            else:
                runtime.update_in_progress = True
                should_apply = True
    # update_lock released here, BEFORE any awaits

    if fail_reason is not None:
        try:
            await websocket.send_text(json.dumps({
                "type": "update_phase",
                "phase": "pip_install",
                "status": "fail",
                "detail": fail_reason,
            }))
        except Exception:
            pass
        return

    if not should_apply:
        return  # defensive

    # Phase 2: schedule apply_update on a worker thread with a thread->loop bridge.
    loop = asyncio.get_running_loop()

    def broadcast_dict(event: dict) -> None:
        """Called from worker thread; schedule onto the event loop.
        For the final 'restart' phase, block on flush before returning so
        the WS frame is sent before os.execv replaces the process."""
        fut = asyncio.run_coroutine_threadsafe(_broadcast(runtime, event), loop)
        if event.get("phase") == "restart" and event.get("status") == "running":
            try:
                fut.result(timeout=1.0)
            except Exception:
                pass

    # Phase 3: run apply_update, catch exceptions, always clear the flag.
    try:
        await loop.run_in_executor(None, apply_update, broadcast_dict, status)
    except DirtyTreeError:
        try:
            await websocket.send_text(json.dumps({
                "type": "update_phase",
                "phase": "git_pull",
                "status": "fail",
                "detail": "local changes detected at apply time",
            }))
        except Exception:
            pass
    except VenvUnavailableError:
        # _run_pip_install already broadcast the specific python3-venv fail phase.
        pass
    except PipBlockedError:
        try:
            await websocket.send_text(json.dumps({
                "type": "update_phase",
                "phase": "pip_install",
                "status": "fail",
                "detail": "pip blocked and venv fallback failed",
            }))
        except Exception:
            pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({
                "type": "update_phase",
                "phase": "pip_install",
                "status": "fail",
                "detail": f"{type(exc).__name__}: {exc}",
            }))
        except Exception:
            pass
    finally:
        with runtime.update_lock:
            runtime.update_in_progress = False
