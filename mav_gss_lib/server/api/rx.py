"""RX packet detail REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mav_gss_lib.server.state import get_runtime

router = APIRouter()


@router.get("/api/rx/packets/{event_id}", response_model=None)
async def api_rx_packet_detail(event_id: str, request: Request) -> dict | JSONResponse:
    runtime = get_runtime(request)
    event = runtime.rx.detail_store.get(event_id)
    if event is None:
        return JSONResponse(status_code=404, content={"error": "packet not found"})
    return event


__all__ = ["router"]
