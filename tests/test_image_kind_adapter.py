"""Tests for ImageKindAdapter — JPEG-specific behavior."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from mav_gss_lib.missions.maveric.files.adapters import ImageKindAdapter
from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


class ImageKindAdapterTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.store = ChunkFileStore(self.root)
        self.cfg: dict = {"imaging": {"thumb_prefix": "tn_"}}
        self.adapter = ImageKindAdapter(mission_cfg=self.cfg)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_seed_from_cnt_yields_full_and_thumb(self):
        seeds = list(self.adapter.seed_from_cnt({
            "filename": "capture.jpg", "num_chunks": "10",
            "thumb_filename": "tn_capture.jpg", "thumb_num_chunks": "2",
        }))
        self.assertEqual(seeds, [("capture.jpg", 10), ("tn_capture.jpg", 2)])

    def test_seed_from_capture_yields_full_and_thumb(self):
        seeds = list(self.adapter.seed_from_capture({
            "status": "0", "filename": "capture.jpg", "num_chunks": "10",
            "thumb_filename": "tn_capture.jpg", "thumb_num_chunks": "2",
        }))
        self.assertEqual(seeds, [("capture.jpg", 10), ("tn_capture.jpg", 2)])

    def test_seed_skips_empty_filenames(self):
        seeds = list(self.adapter.seed_from_cnt({
            "filename": "capture.jpg", "num_chunks": "10",
            "thumb_filename": "", "thumb_num_chunks": "0",
        }))
        self.assertEqual(seeds, [("capture.jpg", 10)])

    def test_partial_repair_appends_eoi_when_jpeg_truncated(self):
        path = os.path.join(self.root, "test.jpg")
        with open(path, "wb") as f:
            f.write(b"\xff\xd8\x00\x01\x02")
        self.adapter.partial_repair(path)
        self.assertTrue(open(path, "rb").read().endswith(b"\xff\xd9"))

    def test_partial_repair_noop_when_eoi_present(self):
        path = os.path.join(self.root, "test.jpg")
        original = b"\xff\xd8\x00\x01\xff\xd9"
        with open(path, "wb") as f:
            f.write(original)
        self.adapter.partial_repair(path)
        self.assertEqual(open(path, "rb").read(), original)

    def test_partial_repair_noop_when_not_jpeg(self):
        path = os.path.join(self.root, "test.bin")
        with open(path, "wb") as f:
            f.write(b"\x00\x00\xab\xcd")
        self.adapter.partial_repair(path)
        self.assertEqual(open(path, "rb").read(), b"\x00\x00\xab\xcd")

    def test_on_complete_returns_empty(self):
        path = os.path.join(self.root, "test.jpg")
        with open(path, "wb") as f:
            f.write(b"\xff\xd8\xff\xd9")
        self.assertEqual(self.adapter.on_complete(path), {})

    def test_status_view_pairs_full_and_thumb(self):
        full = FileRef(kind="image", source="HLNV", filename="capture.jpg")
        thumb = FileRef(kind="image", source="HLNV", filename="tn_capture.jpg")
        self.store.set_total(full, 10)
        self.store.set_total(thumb, 2)
        view = self.adapter.status_view(self.store)
        files = view["files"]
        self.assertEqual(len(files), 1)
        pair = files[0]
        self.assertEqual(pair["stem"], "capture.jpg")
        self.assertEqual(pair["full"]["filename"], "capture.jpg")
        self.assertEqual(pair["thumb"]["filename"], "tn_capture.jpg")

    def test_status_view_placeholder_when_only_one_side_present(self):
        only_full = FileRef(kind="image", source="HLNV", filename="capture.jpg")
        self.store.set_total(only_full, 10)
        view = self.adapter.status_view(self.store)
        pair = view["files"][0]
        self.assertEqual(pair["full"]["received"], 0)
        self.assertIsNone(pair["thumb"]["total"])

    def test_status_view_live_thumb_prefix_from_config(self):
        self.cfg["imaging"]["thumb_prefix"] = "th_"
        full = FileRef(kind="image", source="HLNV", filename="capture.jpg")
        thumb = FileRef(kind="image", source="HLNV", filename="th_capture.jpg")
        self.store.set_total(full, 1)
        self.store.set_total(thumb, 1)
        view = self.adapter.status_view(self.store)
        self.assertEqual(view["files"][0]["thumb"]["filename"], "th_capture.jpg")

    def test_status_view_no_pairing_when_prefix_empty(self):
        self.cfg["imaging"]["thumb_prefix"] = ""
        ref = FileRef(kind="image", source="HLNV", filename="capture.jpg")
        self.store.set_total(ref, 1)
        view = self.adapter.status_view(self.store)
        files = view["files"]
        self.assertEqual(len(files), 1)
        self.assertIsNone(files[0]["thumb"])

    def test_status_view_pair_id_consistent_for_sourceless_files(self):
        """Regression: pair id must match FileRef.id when source is None
        — no ``image//<filename>`` double-slash from `f"{kind}/{source or ''}/..."`."""
        ref = FileRef(kind="image", source=None, filename="capture.jpg")
        self.store.set_total(ref, 1)
        view = self.adapter.status_view(self.store)
        pair = view["files"][0]
        self.assertEqual(pair["id"], ref.id)
        self.assertEqual(pair["id"], "image/capture.jpg")
        self.assertNotIn("//", pair["id"])


if __name__ == "__main__":
    unittest.main()
