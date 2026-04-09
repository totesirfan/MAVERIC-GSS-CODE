"""
mav_gss_lib.web_runtime.api.schema -- Schema / Column Routes

Endpoints: api_schema, api_columns, api_tx_capabilities, api_tx_columns

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..state import get_runtime

router = APIRouter()


@router.get("/api/schema")
async def api_schema(request: Request):
    return get_runtime(request).cmd_defs


@router.get("/api/columns")
async def api_columns(request: Request):
    """Return adapter-provided column definitions for packet list rendering.

    Minimal enabler: same data as sent over /ws/rx on connect, exposed via
    REST so the log viewer can render rows from _rendering.row.
    """
    runtime = get_runtime(request)
    return runtime.adapter.packet_list_columns()


@router.get("/api/tx/capabilities")
async def api_tx_capabilities(request: Request):
    """Return TX capabilities for the loaded mission adapter."""
    from mav_gss_lib.mission_adapter import get_tx_capabilities
    runtime = get_runtime(request)
    return get_tx_capabilities(runtime.adapter)


@router.get("/api/tx-columns")
async def api_tx_columns(request: Request):
    """Return adapter-provided column definitions for TX queue/history rendering."""
    runtime = get_runtime(request)
    return runtime.adapter.tx_queue_columns()
