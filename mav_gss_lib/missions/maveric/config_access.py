"""Mission-config read helpers.

Each function reads a single mission-general value out of a mission_cfg
dict. The `general`-subdict fallback accepts legacy flat gss.yml files
still on disk (those land under `general.*` during canonicalization).

Seeding of mission_cfg (identity constants, placeholder AX.25/CSP, TX
defaults) lives in `defaults.py`; this module is read-only.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any


def _section(cfg: dict[str, Any], key: str) -> dict[str, Any]:
    value = cfg.get(key)
    return value if isinstance(value, dict) else {}


def mission_name(cfg: dict[str, Any]) -> str:
    general = _section(cfg, "general")
    return str(cfg.get("mission_name") or general.get("mission_name") or "MAVERIC")


def command_defs_name(cfg: dict[str, Any]) -> str:
    general = _section(cfg, "general")
    return str(cfg.get("command_defs") or general.get("command_defs") or "commands.yml")


def gs_node_name(cfg: dict[str, Any]) -> str:
    general = _section(cfg, "general")
    return str(cfg.get("gs_node") or general.get("gs_node") or "GS")


def image_dir(cfg: dict[str, Any]) -> str:
    imaging = _section(cfg, "imaging")
    general = _section(cfg, "general")
    return str(imaging.get("dir") or cfg.get("image_dir") or general.get("image_dir") or "images")
