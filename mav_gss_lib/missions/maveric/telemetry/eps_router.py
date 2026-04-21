"""FastAPI router for the EPS HK snapshot store.

Mounted automatically by `mav_gss_lib.missions.maveric.get_plugin_routers`
when the adapter carries an `eps_store`.

Only a DELETE route is exposed. The initial seed is delivered over
`/ws/rx` via the adapter's `on_client_connect` hook (synthetic
`eps_hk_update` message), so the frontend never has to reconcile a
REST GET response against a live WS update that may have arrived in
between. A GET endpoint is intentionally omitted to avoid dual code
paths — if you need one for scripting/debug, add it and route test
fixtures through it rather than through the hook.

Copy to `mav_gss_lib/missions/maveric/telemetry/eps_router.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mav_gss_lib.missions.maveric.telemetry.eps_store import EpsStore


def get_eps_router(store: "EpsStore"):
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse

    from mav_gss_lib.web_runtime.state import get_runtime

    router = APIRouter(prefix="/api/plugins/eps", tags=["eps"])

    @router.delete("/snapshot")
    async def clear_eps_snapshot(request: Request):
        """Operator action: wipe the persisted snapshot.

        Broadcasts `eps_snapshot_cleared` on /ws/rx so all live tabs
        reset their in-memory state. Broadcasting after the disk clear
        also eliminates the race where a live `eps_hk_update` arriving
        between the DELETE and the client setState would be silently
        overwritten by the clear.
        """
        store.clear()
        runtime = get_runtime(request)
        await runtime.rx.broadcast({"type": "eps_snapshot_cleared"})
        return JSONResponse({"ok": True})

    return router
