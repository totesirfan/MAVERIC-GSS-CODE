"""MissionSpec loader scaffolding for platform v2.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .mission_api import MissionContext, MissionSpec


def load_mission_spec_from_split(
    platform_cfg: dict[str, Any],
    mission_id: str,
    mission_cfg: dict[str, Any],
    *,
    data_dir: str | Path = "logs",
) -> MissionSpec:
    """Load the active mission's MissionSpec from split state directly."""

    if not mission_id:
        raise ValueError("missing required mission id")

    module = importlib.import_module(f"mav_gss_lib.missions.{mission_id}.mission")
    build = getattr(module, "build", None)
    if build is None:
        raise ValueError(f"mission '{mission_id}' has no build(ctx) function")

    ctx = MissionContext(
        platform_config=platform_cfg,
        mission_config=mission_cfg,
        data_dir=Path(data_dir),
    )
    spec = build(ctx)
    validate_mission_spec(spec)
    return spec


def load_mission_spec(cfg: dict[str, Any], *, data_dir: str | Path = "logs") -> MissionSpec:
    """Test-only convenience: accept a native `{platform, mission}` dict and
    delegate to `load_mission_spec_from_split`.

    Production code paths (`PlatformRuntimeV2.from_split`, `WebRuntime`) call
    `load_mission_spec_from_split` directly with the split tuple. This wrapper
    keeps test ergonomics ergonomic without smuggling the flat legacy shape
    back into the loader surface.
    """

    mission_section = cfg.get("mission") or {}
    mission_id = mission_section.get("id")
    if not mission_id:
        raise ValueError("missing required config key: mission.id")

    return load_mission_spec_from_split(
        cfg.get("platform") or {},
        mission_id,
        mission_section.get("config") or {},
        data_dir=data_dir,
    )


def validate_mission_spec(spec: MissionSpec) -> None:
    """Validate required MissionSpec shape without assuming mission vocabulary."""

    if not isinstance(spec.id, str) or not spec.id:
        raise ValueError("MissionSpec.id must be a non-empty string")
    if not isinstance(spec.name, str) or not spec.name:
        raise ValueError("MissionSpec.name must be a non-empty string")
    for attr in ("packets", "ui", "config"):
        if getattr(spec, attr, None) is None:
            raise ValueError(f"MissionSpec.{attr} is required")
