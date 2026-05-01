"""Tests for MagKindAdapter — NVG sensor file behavior."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from mav_gss_lib.missions.maveric.files.adapters import MagKindAdapter
from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


class MagKindAdapterTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.store = ChunkFileStore(self.root)
        self.adapter = MagKindAdapter()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_seed_from_cnt_yields_single_pair(self):
        seeds = list(self.adapter.seed_from_cnt({
            "status": "0", "filename": "mag_001.nvg", "num_chunks": "12",
        }))
        self.assertEqual(seeds, [("mag_001.nvg", 12)])

    def test_seed_from_capture_yields_nothing(self):
        seeds = list(self.adapter.seed_from_capture({"message": "ok"}))
        self.assertEqual(seeds, [])

    def test_partial_repair_is_noop(self):
        path = os.path.join(self.root, "test.nvg")
        with open(path, "wb") as f:
            f.write(b"\xde\xad\xbe\xef")
        self.adapter.partial_repair(path)
        self.assertEqual(open(path, "rb").read(), b"\xde\xad\xbe\xef")

    def test_on_complete_returns_empty(self):
        path = os.path.join(self.root, "test.nvg")
        with open(path, "wb") as f:
            f.write(b"\x00")
        self.assertEqual(self.adapter.on_complete(path), {})

    def test_status_view_flat_no_validity_field(self):
        ref = FileRef(kind="mag", source="HLNV", filename="mag_001.nvg")
        self.store.set_total(ref, 1)
        self.store.feed_chunk(ref, 0, b"\xde\xad\xbe\xef")
        view = self.adapter.status_view(self.store)
        leaf = view["files"][0]
        self.assertEqual(leaf["filename"], "mag_001.nvg")
        self.assertTrue(leaf["complete"])
        self.assertNotIn("valid", leaf)


if __name__ == "__main__":
    unittest.main()
