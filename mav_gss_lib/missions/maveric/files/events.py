"""MAVERIC file-chunk events source.

Single ``EventOps`` source that watches inbound packets, dispatches by
``cmd_id`` to the correct ``FileKindAdapter``, drives the
``ChunkFileStore``, and persists adapter on-complete metadata via
``store.set_extras`` so status views read cached values rather than
re-parsing files.

Replaces the legacy ``MavericImagingEvents`` — which only handled
imaging — with one watcher that handles all file kinds via the
adapter registry.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from mav_gss_lib.missions.maveric.files.adapters import (
    FileKindAdapter,
    args_by_key,
    packet_source,
    slice_chunk_data,
)
from mav_gss_lib.missions.maveric.files.store import ChunkFeedResult, ChunkFileStore, FileRef


@dataclass(slots=True)
class MavericFileChunkEvents:
    """``EventOps`` source that drives ``ChunkFileStore`` from packets."""

    store: ChunkFileStore
    adapters: list[FileKindAdapter]

    _by_cnt: dict[str, FileKindAdapter] = field(init=False, default_factory=dict)
    _by_get: dict[str, FileKindAdapter] = field(init=False, default_factory=dict)
    _by_capture: dict[str, FileKindAdapter] = field(init=False, default_factory=dict)
    _by_kind: dict[str, FileKindAdapter] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        for a in self.adapters:
            self._by_cnt[a.cnt_cmd] = a
            self._by_get[a.get_cmd] = a
            self._by_kind[a.kind] = a
            if a.capture_cmd:
                self._by_capture[a.capture_cmd] = a

    def adapter_for_kind(self, kind: str) -> FileKindAdapter:
        return self._by_kind[kind]

    # ── EventOps surface ──────────────────────────────────────────

    def on_packet(self, packet: Any) -> Iterable[dict[str, Any]]:
        payload = getattr(packet, "mission_payload", None)
        if payload is None:
            return []
        header = getattr(payload, "header", None)
        if not isinstance(header, dict):
            return []
        cmd_id = header.get("cmd_id")
        ptype = header.get("ptype")
        if not isinstance(cmd_id, str) or not isinstance(ptype, str):
            return []

        if ptype == "RES" and cmd_id in self._by_cnt:
            return self._handle_seed(self._by_cnt[cmd_id], packet, header, source="cnt")
        if ptype == "RES" and cmd_id in self._by_capture:
            return self._handle_seed(self._by_capture[cmd_id], packet, header, source="capture")
        if ptype == "FILE" and cmd_id in self._by_get:
            return self._handle_get(self._by_get[cmd_id], packet, header)
        return []

    def on_client_connect(self) -> Iterable[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for ref in self.store.known_files():
            adapter = self._by_kind.get(ref.kind)
            if adapter is None:
                continue
            out.append(self._progress_msg(adapter, ref))
        return out

    # ── Handlers ──────────────────────────────────────────────────

    def _handle_seed(
        self,
        adapter: FileKindAdapter,
        packet: Any,
        header: dict[str, Any],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        args = args_by_key(packet)
        if not args:
            return []
        node = packet_source(header)
        seeder = adapter.seed_from_capture if source == "capture" else adapter.seed_from_cnt
        msgs: list[dict[str, Any]] = []
        for filename, total in seeder(args):
            ref = FileRef(kind=adapter.kind, source=node, filename=filename)
            try:
                self.store.set_total(ref, total)
            except (ValueError, TypeError):
                continue
            msgs.append(self._progress_msg(adapter, ref))
        return msgs

    def _handle_get(
        self,
        adapter: FileKindAdapter,
        packet: Any,
        header: dict[str, Any],
    ) -> list[dict[str, Any]]:
        args = args_by_key(packet)
        filename = str(args.get("filename", ""))
        if not filename:
            return []
        try:
            chunk_idx = int(args.get("chunk_idx", ""))
        except (ValueError, TypeError):
            return []
        try:
            chunk_len = int(args.get("chunk_len", ""))
        except (ValueError, TypeError):
            chunk_len = 0
        payload = packet.mission_payload
        data = slice_chunk_data(payload.args_raw, chunk_len)
        node = packet_source(header)
        ref = FileRef(kind=adapter.kind, source=node, filename=filename)
        try:
            result = self.store.feed_chunk(ref, chunk_idx, data, chunk_size=chunk_len)
        except (ValueError, TypeError):
            return []
        adapter.partial_repair(result.path)
        extras: dict[str, Any] = {}
        if result.complete:
            extras = adapter.on_complete(result.path) or {}
            if extras:
                self.store.set_extras(ref, **extras)
        return [self._progress_msg(adapter, ref, result=result, extras=extras)]

    # ── Message builder ───────────────────────────────────────────

    def _progress_msg(
        self,
        adapter: FileKindAdapter,
        ref: FileRef,
        *,
        result: ChunkFeedResult | None = None,
        extras: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if result is not None:
            received, total, complete = result.received, result.total, result.complete
        else:
            received, total = self.store.progress(ref)
            complete = self.store.is_complete(ref)
        msg: dict[str, Any] = {
            "type": "file_progress",
            "kind": ref.kind,
            "source": ref.source,
            "id": ref.id,
            "filename": ref.filename,
            "received": received,
            "total": total,
            "complete": complete,
        }
        if extras:
            msg.update(extras)
        return msg
