"""Radio process control REST endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request

from ..security import require_api_token
from ..state import get_runtime

router = APIRouter()


@router.get("/api/radio/status")
async def api_radio_status(request: Request) -> dict[str, Any]:
    runtime = get_runtime(request)
    return runtime.radio.status()


@router.get("/api/radio/logs")
async def api_radio_logs(request: Request) -> dict[str, Any]:
    runtime = get_runtime(request)
    return {"lines": runtime.radio.log_snapshot()}


@router.post("/api/radio/start")
async def api_radio_start(request: Request) -> dict[str, Any] | Any:
    denied = require_api_token(request)
    if denied:
        return denied
    runtime = get_runtime(request)
    return await asyncio.to_thread(runtime.radio.start)


@router.post("/api/radio/stop")
async def api_radio_stop(request: Request) -> dict[str, Any] | Any:
    denied = require_api_token(request)
    if denied:
        return denied
    runtime = get_runtime(request)
    return await asyncio.to_thread(runtime.radio.stop)


@router.post("/api/radio/restart")
async def api_radio_restart(request: Request) -> dict[str, Any] | Any:
    denied = require_api_token(request)
    if denied:
        return denied
    runtime = get_runtime(request)
    return await asyncio.to_thread(runtime.radio.restart)
