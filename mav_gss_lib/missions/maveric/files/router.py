"""FastAPI router for /api/plugins/files.

One router serves all kinds. ``?kind=image|aii|mag`` selects the
adapter; the adapter decides the status-view shape and the response
media type for previews.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from mav_gss_lib.missions.maveric.files.adapters import FileKindAdapter
from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


def get_files_router(store: ChunkFileStore, adapters: list[FileKindAdapter]) -> APIRouter:
    by_kind: dict[str, FileKindAdapter] = {a.kind: a for a in adapters}
    router = APIRouter(prefix="/api/plugins/files", tags=["files"])

    def _adapter_or_400(kind: str) -> FileKindAdapter | JSONResponse:
        a = by_kind.get(kind)
        if a is None:
            return JSONResponse({"error": f"unknown kind: {kind!r}"}, status_code=400)
        return a

    @router.get("/status")
    async def files_status(kind: str) -> JSONResponse:
        a = _adapter_or_400(kind)
        if isinstance(a, JSONResponse):
            return a
        return JSONResponse(a.status_view(store))

    @router.get("/files")
    async def files_list(kind: str) -> JSONResponse:
        a = _adapter_or_400(kind)
        if isinstance(a, JSONResponse):
            return a
        return JSONResponse({"files": [r.id for r in store.known_files(kind=kind)]})

    @router.get("/chunks/{filename:path}")
    async def files_chunks(filename: str, kind: str, source: str | None = None) -> JSONResponse:
        a = _adapter_or_400(kind)
        if isinstance(a, JSONResponse):
            return a
        try:
            chunks = store.get_chunks(FileRef(kind=kind, source=source, filename=filename))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"kind": kind, "source": source or None, "filename": filename, "chunks": chunks})

    @router.get("/preview/{filename:path}", response_model=None)
    async def files_preview(
        filename: str,
        kind: str,
        source: str | None = None,
    ) -> JSONResponse | FileResponse:
        a = _adapter_or_400(kind)
        if isinstance(a, JSONResponse):
            return a
        try:
            ref = FileRef(kind=kind, source=source, filename=filename)
            path = Path(store.file_path(ref))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if not path.is_file():
            return JSONResponse({"error": "not found"}, status_code=404)
        stat = path.stat()
        if stat.st_size == 0:
            return JSONResponse({"error": "no data yet"}, status_code=404)
        etag = f'"{stat.st_mtime_ns}-{stat.st_size}"'
        return FileResponse(
            path,
            media_type=a.media_type,
            headers={"Cache-Control": "no-cache", "ETag": etag},
        )

    @router.delete("/file/{filename:path}")
    async def files_delete(filename: str, kind: str, source: str | None = None) -> JSONResponse:
        a = _adapter_or_400(kind)
        if isinstance(a, JSONResponse):
            return a
        try:
            store.delete_file(FileRef(kind=kind, source=source, filename=filename))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"ok": True, "kind": kind, "source": source or None, "filename": filename})

    return router
