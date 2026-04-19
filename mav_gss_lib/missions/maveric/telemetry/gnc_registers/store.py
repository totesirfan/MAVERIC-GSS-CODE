"""Persistent GNC register snapshot store.

Latest-value snapshot per register, persisted to disk. Survives
`MAV_WEB.py` restart and seeds new dashboard mounts via the
`/api/plugins/gnc/snapshot` endpoint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path


class GncRegisterStore:
    """Latest-value snapshot per register, persisted to disk.

    Survives `MAV_WEB.py` restart and seeds new dashboard mounts via
    the `/api/plugins/gnc/snapshot` endpoint. Writes atomically on every
    update so an interrupted write cannot corrupt the file.

    Each snapshot dict holds the decoded register plus server-side
    timestamps (`gs_ts`, `pkt_num`, `received_at_ms`) so the frontend
    can compute age off a server clock anchor rather than the moment
    the WS message happened to arrive.
    """

    def __init__(self, path: str | Path = ".gnc_snapshot.json"):
        self.path = Path(path)
        self.snapshots: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        # Clean up any leftover .tmp from a previous interrupted save.
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            if isinstance(data, dict):
                self.snapshots = data
        except (OSError, json.JSONDecodeError) as e:
            logging.warning("GNC store: failed to load %s (%s)", self.path, e)

    def _save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self.snapshots))
            tmp.replace(self.path)
        except OSError as e:
            logging.warning("GNC store: failed to save %s (%s)", self.path, e)

    def update_many(self, updates: dict[str, dict]) -> None:
        if not updates:
            return
        for name, snap in updates.items():
            self.snapshots[name] = snap
        self._save()

    def get_all(self) -> dict[str, dict]:
        return dict(self.snapshots)

    def clear(self) -> None:
        self.snapshots = {}
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
