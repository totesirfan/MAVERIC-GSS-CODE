"""
mav_gss_lib.server.api.schema -- Schema / Column Routes

Endpoints: api_schema, api_tx_capabilities, api_tx_columns, api_rx_columns

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from ..state import get_runtime

router = APIRouter()


@router.get("/api/schema")
async def api_schema(request: Request) -> dict[str, Any]:
    runtime = get_runtime(request)
    return runtime.mission.commands.schema() if runtime.mission.commands is not None else {}


@router.get("/api/tx/capabilities")
async def api_tx_capabilities(request: Request) -> dict[str, Any]:
    """Return TX capabilities for the loaded mission."""
    runtime = get_runtime(request)
    return {"mission_commands": runtime.mission.commands is not None}


@router.get("/api/tx-columns")
async def api_tx_columns(request: Request) -> list[dict[str, Any]]:
    """Return declarative TX column definitions from mission.yml."""
    runtime = get_runtime(request)
    spec_root = getattr(runtime.mission, "spec_root", None)
    ui = getattr(spec_root, "ui", None) if spec_root is not None else None
    if ui is None:
        return []
    return [column.to_json() for column in ui.tx_columns]


@router.get("/api/rx-columns")
async def api_rx_columns(request: Request) -> list[dict[str, Any]]:
    """Return declarative RX column definitions from mission.yml.

    Each entry is `{id, label, path, width?, align?, flex?, toggle?, badge?}`.
    Empty list when the mission omits the ``ui.rx_columns`` block — the
    frontend falls through to platform-shell columns only.
    """
    runtime = get_runtime(request)
    spec_root = getattr(runtime.mission, "spec_root", None)
    ui = getattr(spec_root, "ui", None) if spec_root is not None else None
    if ui is None:
        return []
    return [column.to_json() for column in ui.rx_columns]
