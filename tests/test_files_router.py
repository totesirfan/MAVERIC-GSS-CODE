"""Tests for /api/plugins/files HTTP surface."""

from __future__ import annotations

import shutil
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mav_gss_lib.missions.maveric.files.adapters import (
    AiiKindAdapter,
    ImageKindAdapter,
    MagKindAdapter,
)
from mav_gss_lib.missions.maveric.files.router import get_files_router
from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


class FilesRouterTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.store = ChunkFileStore(self.root)
        self.cfg = {"imaging": {"thumb_prefix": "tn_"}}
        self.adapters = [
            ImageKindAdapter(mission_cfg=self.cfg),
            AiiKindAdapter(),
            MagKindAdapter(),
        ]
        app = FastAPI()
        app.include_router(get_files_router(self.store, self.adapters))
        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_status_image_paired(self):
        ref = FileRef(kind="image", source="HLNV", filename="a.jpg")
        self.store.set_total(ref, 1)
        r = self.client.get("/api/plugins/files/status?kind=image")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(len(body["files"]), 1)
        self.assertEqual(body["files"][0]["full"]["filename"], "a.jpg")

    def test_status_aii_flat(self):
        ref = FileRef(kind="aii", source="HLNV", filename="i.json")
        self.store.set_total(ref, 1)
        r = self.client.get("/api/plugins/files/status?kind=aii")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["files"][0]["filename"], "i.json")
        self.assertIsNone(body["files"][0]["valid"])

    def test_status_unknown_kind_400(self):
        r = self.client.get("/api/plugins/files/status?kind=bogus")
        self.assertEqual(r.status_code, 400)

    def test_chunks_returns_received_indices(self):
        ref = FileRef(kind="aii", source="HLNV", filename="i.json")
        self.store.set_total(ref, 3)
        self.store.feed_chunk(ref, 0, b"a")
        self.store.feed_chunk(ref, 2, b"c")
        r = self.client.get("/api/plugins/files/chunks/i.json?kind=aii&source=HLNV")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["chunks"], [0, 2])

    def test_preview_image_jpeg_mime(self):
        ref = FileRef(kind="image", source="HLNV", filename="a.jpg")
        self.store.set_total(ref, 1)
        self.store.feed_chunk(ref, 0, b"\xff\xd8\xff\xd9")
        r = self.client.get("/api/plugins/files/preview/a.jpg?kind=image&source=HLNV")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "image/jpeg")

    def test_preview_aii_json_mime(self):
        ref = FileRef(kind="aii", source="HLNV", filename="i.json")
        self.store.set_total(ref, 1)
        self.store.feed_chunk(ref, 0, b'{"ok":true}')
        r = self.client.get("/api/plugins/files/preview/i.json?kind=aii&source=HLNV")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers["content-type"].startswith("application/json"))

    def test_preview_mag_octet_stream_mime(self):
        ref = FileRef(kind="mag", source="HLNV", filename="m.nvg")
        self.store.set_total(ref, 1)
        self.store.feed_chunk(ref, 0, b"\xde\xad\xbe\xef")
        r = self.client.get("/api/plugins/files/preview/m.nvg?kind=mag&source=HLNV")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/octet-stream")

    def test_delete_file_removes_state(self):
        ref = FileRef(kind="aii", source="HLNV", filename="i.json")
        self.store.set_total(ref, 1)
        r = self.client.delete("/api/plugins/files/file/i.json?kind=aii&source=HLNV")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.store.progress(ref), (0, None))

    def test_files_list_filtered_by_kind(self):
        self.store.set_total(FileRef(kind="image", source="HLNV", filename="a.jpg"), 1)
        self.store.set_total(FileRef(kind="aii", source="HLNV", filename="b.json"), 1)
        r = self.client.get("/api/plugins/files/files?kind=image")
        self.assertEqual(r.json()["files"], ["image/HLNV/a.jpg"])


if __name__ == "__main__":
    unittest.main()
