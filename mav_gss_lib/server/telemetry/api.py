"""
mav_gss_lib.server.telemetry.api -- Telemetry REST Router (transitional)

Mission-opaque endpoints over the live ``ParameterCache``:

  DELETE /api/telemetry/{domain}/snapshot  -- clear all params under that group prefix
  GET    /api/telemetry/{domain}/catalog   -- return mission-owned catalog (declarative)

Catalog projection is read off ``MissionSpec.spec_root`` when a declarative
mission is loaded; non-declarative missions return 404 for the catalog.
Task 6 will retire this router in favor of explicit /api/parameters surface.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from mav_gss_lib.server.state import get_runtime


def get_telemetry_router() -> APIRouter:
    """Build the telemetry router. Called once by ``server/app.py`` at startup."""
    router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

    @router.delete("/{domain}/snapshot")
    async def clear_snapshot(domain: str, request: Request) -> JSONResponse:
        runtime = get_runtime(request)
        spec_root = getattr(runtime.mission, "spec_root", None)
        known_domains = _declared_domains(spec_root)
        if known_domains and domain not in known_domains:
            raise HTTPException(status_code=404, detail=f"unknown domain: {domain}")
        cleared = runtime.parameter_cache.clear_group(domain)
        msg = {"type": "parameters", "cleared_group": domain, "count": cleared}
        await runtime.rx.broadcast(msg)
        return JSONResponse({"ok": True})

    @router.get("/{domain}/catalog")
    async def get_domain_catalog(domain: str, request: Request) -> JSONResponse:
        runtime = get_runtime(request)
        spec_root = getattr(runtime.mission, "spec_root", None)
        known_domains = _declared_domains(spec_root)
        if not known_domains:
            raise HTTPException(status_code=404, detail=f"no catalog for domain: {domain}")
        if domain not in known_domains:
            raise HTTPException(status_code=404, detail=f"unknown domain: {domain}")
        catalog = _build_catalog_for_domain(spec_root, domain)
        return JSONResponse(catalog)

    return router


def _declared_domains(spec_root) -> set[str]:
    if spec_root is None:
        return set()
    return {c.domain for c in spec_root.sequence_containers.values() if c.domain}


def _build_catalog_for_domain(spec_root, domain: str) -> list[dict]:
    """Return a flat catalog of parameters whose container or parameter
    domain matches *domain*. Each entry projects ``{name, type, unit,
    description}`` from the declarative spec."""
    out: list[dict] = []
    seen: set[str] = set()
    for container in spec_root.sequence_containers.values():
        if container.domain != domain:
            continue
        for entry in container.entry_list:
            name = getattr(entry, "name", None)
            if not name or name in seen:
                continue
            seen.add(name)
            param = spec_root.parameters.get(name)
            type_ref = getattr(entry, "type_ref", "") or ""
            type_obj = spec_root.parameter_types.get(type_ref)
            unit = getattr(type_obj, "unit", "") or ""
            description = (param.description if param else "") or ""
            out.append({
                "name": name,
                "type": type_ref,
                "unit": unit,
                "description": description,
            })
    return out
