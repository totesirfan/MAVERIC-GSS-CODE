"""Platform config boundary — spec + update appliers.

    spec.py    — PlatformConfigSpec + DEFAULT_PLATFORM_CONFIG_SPEC
    updates.py — apply_platform_config_update, apply_mission_config_update,
                 persist_mission_config

Author:  Irfan Annuar - USC ISI SERC
"""

from .spec import DEFAULT_PLATFORM_CONFIG_SPEC, PlatformConfigSpec
from .updates import (
    apply_mission_config_update,
    apply_platform_config_update,
    persist_mission_config,
)

__all__ = [
    "DEFAULT_PLATFORM_CONFIG_SPEC",
    "PlatformConfigSpec",
    "apply_mission_config_update",
    "apply_platform_config_update",
    "persist_mission_config",
]
