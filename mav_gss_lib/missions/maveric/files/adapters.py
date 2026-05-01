"""Per-kind file adapters.

Each adapter encapsulates everything format-specific about a file kind:
which packets seed totals, whether to repair partial files, MIME type,
status-view shape, optional on-complete validation, optional thumb
pairing.

Adapters are constructed once at ``mission.py::build(ctx)`` from
``FILE_TRANSPORTS`` rows (see ``registry.py``) and registered with the
events watcher and the HTTP router.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


# ── Shared helpers ─────────────────────────────────────────────────


def slice_chunk_data(args_raw: bytes, chunk_len: int) -> bytes:
    """Extract the trailing chunk_data bytes from a ``*_get_chunks_file``
    args_raw blob.

    Layout: ``<filename> <chunk_idx> <chunk_len> <bytes…>`` — the first
    three tokens are ASCII separated by single spaces. We walk past
    three spaces to land at the first byte of chunk_data, then take
    ``chunk_len`` bytes.

    Identical wire layout for ``img_get_chunks_file``,
    ``aii_get_chunks_file``, and ``mag_get_chunks_file`` in
    ``mission.yml`` — a single helper covers all three kinds.
    """
    if not args_raw or chunk_len <= 0:
        return b""
    pos = 0
    for _ in range(3):
        sp = args_raw.find(b" ", pos)
        if sp < 0:
            return b""
        pos = sp + 1
    return bytes(args_raw[pos:pos + chunk_len])


def args_by_key(packet: Any) -> dict[str, Any]:
    """Build a flat ``{key: value}`` map from a packet's parameter updates."""
    out: dict[str, Any] = {}
    for u in packet.parameters:
        if u.display_only:
            continue
        key = u.name.split(".", 1)[1] if "." in u.name else u.name
        out[key] = u.value
    return out


def packet_source(header: dict[str, Any]) -> str | None:
    src = header.get("src")
    if src is None:
        return None
    text = str(src).strip()
    return text or None


# ── Adapter Protocol ───────────────────────────────────────────────


class FileKindAdapter(Protocol):
    """Per-kind hooks the events watcher and router call into."""

    kind: str
    cnt_cmd: str
    get_cmd: str
    capture_cmd: str | None
    media_type: str

    def seed_from_cnt(self, args: dict[str, Any]) -> Iterable[tuple[str, int]]: ...

    def seed_from_capture(self, args: dict[str, Any]) -> Iterable[tuple[str, int]]: ...

    def partial_repair(self, path: str) -> None: ...

    def on_complete(self, path: str) -> dict[str, Any]: ...

    def status_view(self, store: ChunkFileStore) -> dict[str, Any]: ...
