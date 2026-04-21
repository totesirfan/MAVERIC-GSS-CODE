"""Persistent EPS HK snapshot store.

Single-snapshot equivalent of `telemetry/gnc_registers/store.py`. Holds
the latest decoded `eps_hk` packet and replays it on fresh `/ws/rx`
connections via the mission adapter's `on_client_connect` hook.

Survives `MAV_WEB.py` restart. The on-disk file lives at
`<general.log_dir>/.eps_snapshot.json` — same trust boundary as the
platform's pending-queue sidecar, not a separately user-editable knob.

Copy to `mav_gss_lib/missions/maveric/telemetry/eps_store.py`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path


class EpsStore:
    """Latest decoded `eps_hk` snapshot, persisted to disk.

    Shape of the held dict:
        {"received_at_ms": int, "pkt_num": int, "fields": {<name>: <float>}}

    Writes atomically on every update so an interrupted write cannot
    corrupt the file.
    """

    def __init__(self, path: str | Path = ".eps_snapshot.json"):
        self.path = Path(path)
        self.snapshot: dict | None = None
        self._load()

    def _load(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            if isinstance(data, dict) and "fields" in data:
                self.snapshot = data
        except (OSError, json.JSONDecodeError) as e:
            logging.warning("EPS store: failed to load %s (%s)", self.path, e)

    def _save(self) -> None:
        if self.snapshot is None:
            return
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self.snapshot))
            tmp.replace(self.path)
        except OSError as e:
            logging.warning("EPS store: failed to save %s (%s)", self.path, e)

    def update(self, snapshot: dict) -> None:
        if not snapshot or "fields" not in snapshot:
            return
        self.snapshot = snapshot
        self._save()

    def get(self) -> dict | None:
        return dict(self.snapshot) if self.snapshot else None

    def clear(self) -> None:
        self.snapshot = None
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
