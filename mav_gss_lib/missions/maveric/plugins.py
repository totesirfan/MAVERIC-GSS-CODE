"""Calibrator-plugin registry for MAVERIC's declarative mission.yml.

Plugin signature (per spec §3.5):
    (raw: int | float) -> tuple[Any, str]

Where ``Any`` is JSON-serializable. The returned ``unit`` string overrides
the type's declared unit at fragment emission and catalog projection.

Plugins are referenced from mission.yml via ``calibrator: {python: <key>}``
and resolved by ``parse_yaml(path, plugins=PLUGINS)``.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any, Callable

PluginCallable = Callable[..., tuple[Any, str]]


PLUGINS: dict[str, PluginCallable] = {}
"""Public registry. Phases 6 and later populate this."""
