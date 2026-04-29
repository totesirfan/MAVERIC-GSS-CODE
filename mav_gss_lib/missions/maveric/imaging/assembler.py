"""Image chunk reassembly for the MAVERIC imaging plugin.

Collects image chunks from img_get_chunks packets and reassembles them
into complete image files. Auto-saves to disk on every chunk so the
operator can view partial images at any time.

Individual chunks are persisted to a .chunks/ directory so non-contiguous
transfers survive server restarts. A .meta.json sidecar tracks progress.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import PurePosixPath
import shutil
from typing import Any


def derive_thumb_filename(full_filename: str, prefix: str | None) -> str | None:
    """Given a full image filename, return the thumb counterpart.

    Returns None if the prefix is empty or None (pairing disabled).
    """
    if not prefix:
        return None
    return f"{prefix}{full_filename}"


def derive_full_filename(thumb_filename: str, prefix: str | None) -> str | None:
    """Given a thumb image filename, return the full counterpart.

    Returns None if the prefix is empty, None, or the thumb filename
    doesn't start with the prefix (i.e. it isn't actually a thumb).
    """
    if not prefix:
        return None
    if not thumb_filename.startswith(prefix):
        return None
    return thumb_filename[len(prefix):]


@dataclass(frozen=True, order=True, slots=True)
class ImageFileRef:
    """Stable identity for an imaging product.

    The spacecraft filename alone is not globally unique: HoloNav and
    Astroboard can both emit ``capture.jpg``. Keep source as a first-class
    key so storage, progress, previews, and deletes all address the same
    logical product.
    """

    source: str | None
    filename: str

    @property
    def id(self) -> str:
        return image_file_id(self.source, self.filename)


def image_file_id(source: str | None, filename: str) -> str:
    """Return the client-facing stable id for a namespaced image file."""
    clean_source = _normalise_source(source)
    return f"{clean_source}/{filename}" if clean_source else filename


def _normalise_source(source: str | None) -> str | None:
    if source is None:
        return None
    text = str(source).strip()
    return text or None


def _source_segment(source: str) -> str:
    """Filesystem-safe path segment for a source node name."""
    segment = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in source)
    return segment or "_"


def _safe_relative_path(filename: str) -> str:
    name = str(filename).strip().replace("\\", "/")
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError(f"unsafe image filename: {filename!r}")
    return os.path.join(*path.parts)


def _safe_join(root: str, relative_path: str) -> str:
    root_abs = os.path.abspath(root)
    path = os.path.abspath(os.path.join(root_abs, relative_path))
    if os.path.commonpath([root_abs, path]) != root_abs:
        raise ValueError(f"unsafe image path: {relative_path!r}")
    return path


class ImageAssembler:
    """Collects image chunks and reassembles them into files.

    Each chunk is saved individually to:
        <output_dir>/.chunks/<source>/<filename>/<chunk_num>.bin

    The assembled image is written to:
        <output_dir>/<source>/<filename>

    Progress metadata is tracked in:
        <output_dir>/<source>/<filename>.meta.json
    """

    def __init__(self, output_dir: str = "images") -> None:
        self.output_dir = output_dir
        self.totals: dict[ImageFileRef, int] = {}
        self.received: dict[ImageFileRef, set[int]] = {}
        self.chunk_sizes: dict[ImageFileRef, int] = {}
        self.completed: dict[ImageFileRef, int] = {}
        os.makedirs(output_dir, exist_ok=True)
        self._restore_state()

    def _ref(self, filename: str, source: str | None = None) -> ImageFileRef:
        filename = str(filename).strip()
        _safe_relative_path(filename)
        return ImageFileRef(source=_normalise_source(source), filename=filename)

    def _image_root(self, ref: ImageFileRef) -> str:
        if ref.source:
            return os.path.join(self.output_dir, _source_segment(ref.source))
        return self.output_dir

    def _image_path(self, ref: ImageFileRef) -> str:
        return _safe_join(self._image_root(ref), _safe_relative_path(ref.filename))

    def file_path(self, filename: str, source: str | None = None) -> str:
        """Return the assembled image path for a client-supplied ref."""
        return self._image_path(self._ref(filename, source))

    def _chunks_dir_for(self, ref: ImageFileRef) -> str:
        """Directory for individual chunk files."""
        root = os.path.join(self.output_dir, ".chunks")
        if ref.source:
            root = os.path.join(root, _source_segment(ref.source))
        return _safe_join(root, _safe_relative_path(ref.filename))

    def _meta_path(self, ref: ImageFileRef) -> str:
        return _safe_join(
            self._image_root(ref),
            _safe_relative_path(ref.filename + ".meta.json"),
        )

    def _save_meta(self, ref: ImageFileRef) -> None:
        meta = {
            "source": ref.source,
            "filename": ref.filename,
            "total": self.totals.get(ref),
            "chunks": sorted(self.received.get(ref, set())),
            "complete": ref in self.completed,
        }
        if ref in self.chunk_sizes:
            meta["chunk_size"] = self.chunk_sizes[ref]
        try:
            path = self._meta_path(ref)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(meta, f)
        except Exception:
            pass

    def _save_chunk(self, ref: ImageFileRef, chunk_num: int, data: bytes) -> None:
        """Write one chunk to its individual file."""
        chunk_dir = self._chunks_dir_for(ref)
        os.makedirs(chunk_dir, exist_ok=True)
        with open(os.path.join(chunk_dir, f"{chunk_num}.bin"), "wb") as f:
            f.write(data)

    def _read_chunk(self, ref: ImageFileRef, chunk_num: int) -> bytes | None:
        """Read one chunk from disk. Returns bytes or None."""
        path = os.path.join(self._chunks_dir_for(ref), f"{chunk_num}.bin")
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def _restore_state(self) -> None:
        """Scan output directory for .meta.json sidecars and restore state."""
        if not os.path.isdir(self.output_dir):
            return
        for current, dirnames, filenames in os.walk(self.output_dir):
            if ".chunks" in dirnames:
                dirnames.remove(".chunks")
            for name in filenames:
                if not name.endswith(".meta.json"):
                    continue
                meta_path = os.path.join(current, name)
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                except Exception:
                    continue

                rel = os.path.relpath(meta_path, self.output_dir)
                parts = rel.split(os.sep)
                if len(parts) == 1:
                    source = None
                    filename = name[:-len(".meta.json")]
                else:
                    source = parts[0]
                    filename = os.path.join(*parts[1:])[:-len(".meta.json")]
                if isinstance(meta, dict):
                    source = meta.get("source", source)
                    filename = meta.get("filename", filename)
                try:
                    ref = self._ref(str(filename).replace(os.sep, "/"), source)
                except ValueError:
                    continue

                total = meta.get("total") if isinstance(meta, dict) else None
                if total is not None:
                    try:
                        self.totals[ref] = int(total)
                    except (ValueError, TypeError):
                        pass
                if isinstance(meta, dict) and meta.get("chunk_size"):
                    try:
                        self.chunk_sizes[ref] = int(meta["chunk_size"])
                    except (ValueError, TypeError):
                        pass
                if isinstance(meta, dict) and meta.get("complete"):
                    total_for_complete = self.totals.get(ref)
                    if total_for_complete is not None:
                        self.completed[ref] = total_for_complete
                else:
                    # Verify which chunks actually exist on disk.
                    chunk_dir = self._chunks_dir_for(ref)
                    real_chunks = set()
                    if os.path.isdir(chunk_dir):
                        for cf in os.listdir(chunk_dir):
                            if cf.endswith(".bin"):
                                try:
                                    real_chunks.add(int(cf[:-4]))
                                except ValueError:
                                    pass
                    self.received[ref] = real_chunks

    def set_total(self, filename: str, total: int, source: str | None = None) -> None:
        """Register the expected chunk count for a file (from img_cnt_chunks).

        Only resets state if the total changes (new transfer for same file).
        """
        ref = self._ref(filename, source)
        total = int(total)
        existing_total = self.totals.get(ref)
        if existing_total == total and (ref in self.received or ref in self.completed):
            return
        self.totals[ref] = total
        self.completed.pop(ref, None)
        self.received.pop(ref, None)
        # Clean old chunk files for a fresh transfer
        chunk_dir = self._chunks_dir_for(ref)
        if os.path.isdir(chunk_dir):
            shutil.rmtree(chunk_dir, ignore_errors=True)
        # Create placeholder so file appears in images/
        path = self._image_path(ref)
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                pass
        self._save_meta(ref)

    def feed_chunk(
        self,
        filename: str,
        chunk_num: int,
        data: bytes,
        chunk_size: int | None = None,
        source: str | None = None,
    ) -> tuple[int, int | None, bool]:
        """Store a chunk and auto-save the current image state to disk.

        Returns (received, total_or_None, complete).
        """
        ref = self._ref(filename, source)
        if ref not in self.received:
            self.received[ref] = set()
        key = int(chunk_num)
        if key in self.received[ref]:
            return self.progress(ref.filename, source=ref.source) + (False,)
        # Save chunk to its own file
        self._save_chunk(ref, key, data)
        self.received[ref].add(key)
        if chunk_size is not None and ref not in self.chunk_sizes:
            try:
                self.chunk_sizes[ref] = int(chunk_size)
            except (ValueError, TypeError):
                pass
        # Reassemble contiguous image from chunk files
        self._assemble(ref)
        self._save_meta(ref)
        complete = self._is_complete(ref)
        if complete:
            total = self.totals.get(ref)
            if total is not None:
                self.completed[ref] = total
            self.received.pop(ref, None)
            # Clean up chunk files — image is complete on disk
            chunk_dir = self._chunks_dir_for(ref)
            if os.path.isdir(chunk_dir):
                shutil.rmtree(chunk_dir, ignore_errors=True)
            self._save_meta(ref)
        return self.progress(ref.filename, source=ref.source) + (complete,)

    def _is_complete(self, ref: ImageFileRef) -> bool:
        """True if total is known and all chunks have been received."""
        total = self.totals.get(ref)
        if total is None:
            return False
        received = self.received.get(ref, set())
        return len(received) >= total

    def is_complete(self, filename: str, source: str | None = None) -> bool:
        return self._ref(filename, source) in self.completed

    def known_filenames(self) -> list[str]:
        """Every bare filename the assembler has state for (legacy API)."""
        return sorted({ref.filename for ref in self.known_files()})

    def known_files(self) -> list[ImageFileRef]:
        """Every source-qualified file the assembler has state for."""
        refs = set(self.totals) | set(self.received) | set(self.completed)
        return sorted(refs, key=lambda r: (r.source or "", r.filename))

    def _meta_mtime_ms(self, ref: ImageFileRef) -> int | None:
        """Wall-clock millis of the last state change for a file, or None.

        The meta sidecar is rewritten on every set_total / feed_chunk call,
        so its mtime is the most accurate 'last activity' signal we have.
        """
        path = self._meta_path(ref)
        if not os.path.isfile(path):
            return None
        try:
            return int(os.path.getmtime(path) * 1000)
        except OSError:
            return None

    def progress(self, filename: str, source: str | None = None) -> tuple[int, int | None]:
        """Returns (received_count, total_or_None)."""
        ref = self._ref(filename, source)
        if ref in self.completed:
            total = self.completed[ref]
            return total, total
        received = len(self.received.get(ref, set()))
        return received, self.totals.get(ref)

    def status(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for ref in self.known_files():
            received, total = self.progress(ref.filename, source=ref.source)
            files.append({
                "id": ref.id,
                "source": ref.source,
                "filename": ref.filename,
                "received": received,
                "total": total,
                "complete": self.is_complete(ref.filename, source=ref.source),
            })
        return {"files": files}

    def paired_status(self, prefix: str | None) -> dict[str, Any]:
        """Return file list grouped into (full, thumb) pairs via prefix.

        When ``prefix`` is empty/None, every file appears as its own
        unpaired entry with ``thumb`` = None.

        When ``prefix`` is set, every pair always has BOTH sides populated.
        If the assembler has only seen one side (the common case for
        scheduled captures where the GSS missed the cam_capture RX),
        the other side is a placeholder leaf with ``total: None,
        received: 0, complete: False`` and a filename derived from the
        prefix. This lets the operator recover a paired view by running
        ``img_cnt_chunks`` against either the real or derived filename.

        Each leaf dict has: ``filename``, ``received``, ``total``,
        ``complete``, ``chunk_size``. The outer dict has: ``stem``,
        ``full``, ``thumb``.
        """
        all_refs = set(self.totals) | set(self.received) | set(self.completed)

        def chunk_size_for(ref: ImageFileRef) -> int | None:
            if ref in self.chunk_sizes:
                return self.chunk_sizes[ref]
            legacy_sizes: dict[Any, int] = self.chunk_sizes
            legacy = legacy_sizes.get(ref.filename)
            return legacy if isinstance(legacy, int) else None

        def real_leaf(ref: ImageFileRef) -> dict[str, Any]:
            received, total = self.progress(ref.filename, source=ref.source)
            return {
                "id": ref.id,
                "source": ref.source,
                "filename": ref.filename,
                "received": received,
                "total": total,
                "complete": self.is_complete(ref.filename, source=ref.source),
                "chunk_size": chunk_size_for(ref),
            }

        def placeholder_leaf(ref: ImageFileRef) -> dict[str, Any]:
            return {
                "id": ref.id,
                "source": ref.source,
                "filename": ref.filename,
                "received": 0,
                "total": None,
                "complete": False,
                "chunk_size": None,
            }

        def pair_mtime(*refs: ImageFileRef) -> int:
            """Max mtime across the real sides of a pair, or 0 if none."""
            best = 0
            for ref in refs:
                if ref not in all_refs:
                    continue
                m = self._meta_mtime_ms(ref)
                if m and m > best:
                    best = m
            return best

        if not prefix:
            unpaired = [
                {
                    "id": ref.id,
                    "source": ref.source,
                    "stem": ref.filename,
                    "full": real_leaf(ref),
                    "thumb": None,
                    "last_activity_ms": self._meta_mtime_ms(ref),
                }
                for ref in all_refs
            ]
            unpaired.sort(
                key=lambda p: (
                    -(p["last_activity_ms"] or 0),
                    p["source"] or "",
                    p["stem"],
                )
            )
            return {"files": unpaired}

        # First pass — collect the stems present in assembler state,
        # scoped by source node so equal filenames from HLNV/ASTR never
        # collapse into the same pair.
        stems_by_source: dict[str | None, set[str]] = {}
        for ref in all_refs:
            stem = ref.filename[len(prefix):] if ref.filename.startswith(prefix) else ref.filename
            stems_by_source.setdefault(ref.source, set()).add(stem)

        # Second pass — build each pair with real or placeholder leaves.
        pairs = []
        for source, stems in stems_by_source.items():
            for stem in stems:
                full_ref = ImageFileRef(source, stem)
                thumb_ref = ImageFileRef(source, f"{prefix}{stem}")
                full = real_leaf(full_ref) if full_ref in all_refs else placeholder_leaf(full_ref)
                thumb = real_leaf(thumb_ref) if thumb_ref in all_refs else placeholder_leaf(thumb_ref)
                mtime = pair_mtime(full_ref, thumb_ref)
                pairs.append({
                    "id": image_file_id(source, stem),
                    "source": source,
                    "stem": stem,
                    "full": full,
                    "thumb": thumb,
                    "last_activity_ms": mtime or None,
                })

        # Newest-first — files touched most recently (set_total or new
        # chunk) float to the top of the operator's picker. Falls back to
        # source/stem for stable ordering within the same-mtime bucket.
        pairs.sort(
            key=lambda p: (
                -(p["last_activity_ms"] or 0),
                p["source"] or "",
                p["stem"],
            )
        )
        return {"files": pairs}

    def get_chunks(self, filename: str, source: str | None = None) -> list[int]:
        """Return sorted list of received chunk indices."""
        ref = self._ref(filename, source)
        if ref in self.completed:
            return list(range(self.completed[ref]))
        return sorted(self.received.get(ref, set()))

    def list_files(self) -> list[str]:
        if not os.path.isdir(self.output_dir):
            return []
        refs: set[ImageFileRef] = set(self.known_files())
        for current, dirnames, filenames in os.walk(self.output_dir):
            if ".chunks" in dirnames:
                dirnames.remove(".chunks")
            for name in filenames:
                if name.startswith(".") or name.endswith(".meta.json"):
                    continue
                path = os.path.join(current, name)
                if not os.path.isfile(path):
                    continue
                rel = os.path.relpath(path, self.output_dir)
                parts = rel.split(os.sep)
                try:
                    if len(parts) == 1:
                        refs.add(self._ref(parts[0]))
                    else:
                        refs.add(self._ref(os.path.join(*parts[1:]).replace(os.sep, "/"), parts[0]))
                except ValueError:
                    continue
        return sorted(ref.id for ref in refs)

    def delete_file(self, filename: str, source: str | None = None) -> None:
        """Remove all state for a file: image, meta, chunk dir, in-memory state."""
        ref = self._ref(filename, source)
        for path in (
            self._image_path(ref),
            self._meta_path(ref),
        ):
            if os.path.isfile(path):
                os.remove(path)
        chunk_dir = self._chunks_dir_for(ref)
        if os.path.isdir(chunk_dir):
            shutil.rmtree(chunk_dir, ignore_errors=True)
        self.totals.pop(ref, None)
        self.received.pop(ref, None)
        self.chunk_sizes.pop(ref, None)
        self.completed.pop(ref, None)

    def _assemble(self, ref: ImageFileRef) -> None:
        """Reassemble contiguous chunks from disk into the image file.

        Reads chunk files 0, 1, 2, ... until a gap. Appends JPEG EOI
        marker if the data starts with a JPEG SOI and doesn't already
        end with one (truncated/in-progress transfers get the safety EOI;
        complete transfers where the OBC already wrote EOI stay intact).
        """
        chunk_dir = self._chunks_dir_for(ref)
        if not os.path.isdir(chunk_dir):
            return
        # Check chunk 0 exists
        chunk0_path = os.path.join(chunk_dir, "0.bin")
        if not os.path.isfile(chunk0_path):
            return
        path = self._image_path(ref)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            i = 0
            first_bytes = None
            last_bytes = b""
            while True:
                cp = os.path.join(chunk_dir, f"{i}.bin")
                if not os.path.isfile(cp):
                    break
                with open(cp, "rb") as cf:
                    data = cf.read()
                if i == 0:
                    first_bytes = data[:2]
                if data:
                    last_bytes = (last_bytes + data)[-2:]
                out.write(data)
                i += 1
            # Append JPEG EOI so partial transfers are still viewable,
            # unless the OBC already terminated the stream with one.
            if first_bytes == b"\xff\xd8" and last_bytes != b"\xff\xd9":
                out.write(b"\xff\xd9")
