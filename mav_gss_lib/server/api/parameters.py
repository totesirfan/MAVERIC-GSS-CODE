"""
mav_gss_lib.server.api.parameters -- Parameter Spec + Cache REST Routes

GET    /api/parameters                 -- static spec dump (cache forever)
DELETE /api/parameters/group/{group}   -- clear all parameters with prefix

The spec is derived from MissionSpec.spec_root (parsed mission.yml).
Missions without a spec return {"parameters": []}.

Author: Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mav_gss_lib.platform.spec.parameter_types import (
    AggregateParameterType,
    EnumeratedParameterType,
)
from mav_gss_lib.server.security import require_api_token
from mav_gss_lib.server.state import get_runtime

router = APIRouter()


def _unit_for(parameter_type: Any) -> str:
    return getattr(parameter_type, "unit", "") or ""


def _enum_table(parameter_type: Any) -> dict[str, int] | None:
    if isinstance(parameter_type, EnumeratedParameterType):
        return {ev.label: ev.raw for ev in parameter_type.values}
    return None


def _aggregate_members(parameter_type: Any) -> list[dict[str, str]] | None:
    """Surface AggregateParameterType.member_list so frontends can dispatch
    on declared shape (codegen, type-driven rendering, alarm authoring on
    individual members) without duck-typing the runtime dict."""
    if not isinstance(parameter_type, AggregateParameterType):
        return None
    return [{"name": m.name, "type": m.type_ref, "unit": m.unit} for m in parameter_type.member_list]


def _resolve_group(spec_root, parameter) -> str | None:
    if parameter.domain:
        return parameter.domain
    for c in spec_root.sequence_containers.values():
        for entry in c.entry_list:
            if getattr(entry, "name", None) == parameter.name:
                return c.domain
    return None


def _build_spec_payload(spec_root) -> dict[str, Any]:
    if spec_root is None:
        return {"parameters": []}
    out: list[dict[str, Any]] = []
    for p in spec_root.parameters.values():
        ptype = spec_root.parameter_types.get(p.type_ref)
        group = _resolve_group(spec_root, p)
        out.append({
            "name": f"{group}.{p.name}" if group else p.name,
            "group": group,
            "key": p.name,
            "type": p.type_ref,
            "unit": _unit_for(ptype) if ptype else "",
            "description": p.description or (getattr(ptype, "description", "") if ptype else ""),
            "enum": _enum_table(ptype) if ptype else None,
            "members": _aggregate_members(ptype) if ptype else None,
            "tags": dict(p.tags),
        })
    return {"parameters": out}


def _build_freshness_payload(spec_root, last_arrival_ms: dict) -> dict[str, Any]:
    if spec_root is None:
        return {}
    out: dict[str, Any] = {}
    for cid, c in spec_root.sequence_containers.items():
        last = int(last_arrival_ms.get(cid, 0))
        out[cid] = {
            "last_ms": last if last > 0 else None,
            "expected_period_ms": (
                int(getattr(c, "expected_period_ms", 0)) or None
            ),
        }
    return out


@router.get("/api/parameters")
async def get_parameters(request: Request) -> JSONResponse:
    runtime = get_runtime(request)
    cached = getattr(runtime, "_parameters_spec_cache", None)
    if cached is None:
        cached = _build_spec_payload(runtime.mission.spec_root)
        runtime._parameters_spec_cache = cached  # type: ignore[attr-defined]
    body = dict(cached)
    body["freshness"] = _build_freshness_payload(
        runtime.mission.spec_root, runtime.rx.last_arrival_ms,
    )
    return JSONResponse(body)


@router.delete("/api/parameters/group/{group}")
async def clear_parameter_group(group: str, request: Request) -> JSONResponse:
    runtime = get_runtime(request)
    if denied := require_api_token(request):
        return denied
    cleared = runtime.parameter_cache.clear_group(group)
    if cleared:
        await runtime.rx.broadcast({"type": "parameters_cleared", "group": group})
    return JSONResponse({"cleared": cleared})
