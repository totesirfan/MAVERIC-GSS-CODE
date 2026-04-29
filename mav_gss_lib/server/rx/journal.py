"""Accepted RX ingest journal.

The journal is intentionally below decode: once a PDU passes session/noise
gates, it is queued here before mission parsing, cache updates, logging, or UI
fanout. The file is a compact length-prefixed binary stream:

    b"RXJ1" once, then repeated ``meta_len:uint32 raw_len:uint32 meta_json raw``.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import struct
import threading
from pathlib import Path

from mav_gss_lib.platform.rx.records import RxIngestRecord

_MAGIC = b"RXJ1"
_SENTINEL = object()
_log = logging.getLogger(__name__)


class RxIngestJournal:
    _FLUSH_EVERY_N = 64
    _FLUSH_EVERY_S = 0.5
    _DEFAULT_MAX_QUEUE = 100_000

    def __init__(self, path: str | Path, *, max_queue: int = _DEFAULT_MAX_QUEUE) -> None:
        if max_queue <= 0:
            raise ValueError("max_queue must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_queue = max_queue
        self.dropped_records = 0
        self._q: queue.Queue[RxIngestRecord | object] = queue.Queue(maxsize=max_queue)
        self._closed = False
        self._lock = threading.Lock()
        self._writer = threading.Thread(target=self._writer_loop, name="rx-journal-writer", daemon=True)
        self._writer.start()

    def append(self, record: RxIngestRecord) -> None:
        with self._lock:
            if self._closed or not self._writer.is_alive():
                return
            try:
                self._q.put_nowait(record)
            except queue.Full:
                self.dropped_records += 1

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._q.put(_SENTINEL)
        self._writer.join(timeout=5.0)

    def rename(self, path: str | Path) -> None:
        """Move the active journal file and keep appending to the new path."""

        new_path = Path(path)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path = self.path
        self.close()
        if self._writer.is_alive():
            raise RuntimeError("RX journal writer did not stop within timeout")
        if old_path != new_path:
            if old_path.exists():
                os.rename(old_path, new_path)
            elif not new_path.exists():
                new_path.write_bytes(_MAGIC)
        self.path = new_path
        self._q = queue.Queue(maxsize=self.max_queue)
        self._closed = False
        self._writer = threading.Thread(target=self._writer_loop, name="rx-journal-writer", daemon=True)
        self._writer.start()

    def _writer_loop(self) -> None:
        try:
            with open(self.path, "ab") as handle:
                if handle.tell() == 0:
                    handle.write(_MAGIC)
                unflushed = 0
                while True:
                    try:
                        item = self._q.get(timeout=self._FLUSH_EVERY_S)
                    except queue.Empty:
                        if unflushed:
                            handle.flush()
                            unflushed = 0
                        continue
                    if item is _SENTINEL:
                        while not self._q.empty():
                            pending = self._q.get_nowait()
                            if pending is not _SENTINEL:
                                try:
                                    self._write_record(handle, pending)  # type: ignore[arg-type]
                                except Exception as exc:
                                    _log.warning("RX journal write failed: %s", exc)
                        handle.flush()
                        return
                    try:
                        self._write_record(handle, item)  # type: ignore[arg-type]
                    except Exception as exc:
                        _log.warning("RX journal write failed: %s", exc)
                        continue
                    unflushed += 1
                    if unflushed >= self._FLUSH_EVERY_N:
                        handle.flush()
                        unflushed = 0
        except Exception as exc:
            _log.warning("RX journal open failed for %s: %s", self.path, exc)

    @staticmethod
    def _write_record(handle, record: RxIngestRecord) -> None:
        meta = json.dumps(
            {
                "session_generation": record.session_generation,
                "event_id": record.event_id,
                "received_at_ms": record.received_at_ms,
                "received_mono_ns": record.received_mono_ns,
                "transport_meta": record.transport_meta,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        raw = record.raw
        handle.write(struct.pack("<II", len(meta), len(raw)))
        handle.write(meta)
        handle.write(raw)


__all__ = ["RxIngestJournal"]
