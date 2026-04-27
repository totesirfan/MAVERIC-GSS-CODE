"""Flat parameter cache keyed by fully-qualified name (``"<group>.<key>"``).

Single live-state surface for all decoded parameters: one JSON file on
disk; one shared lock. LWW by ts_ms. Mission metadata (unit, type,
description, enum/bitfield, tags) lives in mission.yml — not here.

Author: Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterable

from mav_gss_lib.platform.contract.parameters import ParamUpdate

ApplyCallback = Callable[[list], None]


def _json_safe(obj: Any) -> Any:
    """Replace NaN / +Inf / -Inf with None recursively. Browsers reject
    `NaN`/`Infinity` literals from `json.dumps`, so we lose the entire WS
    frame to a silent JSON.parse SyntaxError. Mapping to None keeps the
    cache file standards-compliant and the WS frames parseable."""
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, tuple):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    return obj


class ParameterCache:
    def __init__(self, path: str | Path, *,
                 on_apply: ApplyCallback | None = None) -> None:
        self._path = Path(path)
        self._lock = RLock()
        self._state: dict[str, dict[str, Any]] = {}
        self._on_apply = on_apply
        self._load()

    def apply(self, updates: Iterable[ParamUpdate]) -> list[dict]:
        changes: list[dict] = []
        captured: list[ParamUpdate] = []
        with self._lock:
            dirty = False
            for u in updates:
                captured.append(u)
                value = _json_safe(u.value)
                if u.display_only:
                    changes.append({"name": u.name, "v": value, "t": u.ts_ms,
                                    "display_only": True})
                    continue
                prev = self._state.get(u.name)
                if prev is not None and u.ts_ms < prev["t"]:
                    continue
                self._state[u.name] = {"v": value, "t": u.ts_ms}
                changes.append({"name": u.name, "v": value, "t": u.ts_ms})
                dirty = True
            if dirty:
                self._persist_locked()
        if self._on_apply is not None and captured:
            try:
                self._on_apply(captured)
            except Exception:
                logging.exception("ParameterCache on_apply raised")
        return changes

    def replay(self) -> list[dict]:
        with self._lock:
            return [{"name": n, "v": _json_safe(e["v"]), "t": e["t"]}
                    for n, e in self._state.items()]

    def clear_group(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._state if k.startswith(prefix + ".")]
            for k in keys:
                del self._state[k]
            if keys:
                self._persist_locked()
        return len(keys)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            logging.warning("ParameterCache: ignoring malformed %s (%s)", self._path, e)
            return
        if not isinstance(data, dict):
            return
        self._state = {
            k: {"v": _json_safe(v["v"]), "t": v["t"]}
            for k, v in data.items()
            if isinstance(v, dict) and "v" in v and "t" in v
        }

    def _persist_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._state, separators=(",", ":")))
        tmp.replace(self._path)


__all__ = ["ParameterCache"]
