"""
Mission Template — Copy this package to start a new mission.

Rename the directory to your mission name, update mission.example.yml,
and implement the adapter. Set general.mission in gss.yml to activate.

Mission packages are discovered by convention — no platform registration needed.

Mission package contract:
  - ADAPTER_API_VERSION: int (only 1 supported)
  - ADAPTER_CLASS: type satisfying MissionAdapter protocol
  - init_mission(cfg): called after metadata merge, returns cmd_defs
"""

ADAPTER_API_VERSION = 1

from mav_gss_lib.missions.template.adapter import TemplateMissionAdapter as ADAPTER_CLASS  # noqa: F401


def init_mission(cfg: dict) -> dict:
    """Initialize mission resources after metadata merge.

    This is where you load command schema, populate lookup tables,
    or do any one-time setup your adapter needs.

    Returns:
        {"cmd_defs": dict, "cmd_warn": str | None}
    """
    return {"cmd_defs": {}, "cmd_warn": None}
