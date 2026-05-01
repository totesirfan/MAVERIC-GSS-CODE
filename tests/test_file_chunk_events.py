"""Tests for MavericFileChunkEvents — registry-dispatched packet watcher."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from dataclasses import dataclass, field
from typing import Any

from mav_gss_lib.missions.maveric.files.adapters import (
    AiiKindAdapter,
    ImageKindAdapter,
    MagKindAdapter,
)
from mav_gss_lib.missions.maveric.files.events import MavericFileChunkEvents
from mav_gss_lib.missions.maveric.files.store import ChunkFileStore, FileRef


@dataclass(slots=True)
class _ParamUpdate:
    name: str
    value: Any
    display_only: bool = False


@dataclass(slots=True)
class _MissionPayload:
    header: dict
    args_raw: bytes


@dataclass(slots=True)
class _Packet:
    mission_payload: _MissionPayload
    parameters: list[_ParamUpdate] = field(default_factory=list)


def _packet(cmd_id: str, ptype: str, *, src: str = "HLNV",
            params: list[_ParamUpdate] | None = None,
            args_raw: bytes = b"") -> _Packet:
    return _Packet(
        mission_payload=_MissionPayload(
            header={"cmd_id": cmd_id, "ptype": ptype, "src": src},
            args_raw=args_raw,
        ),
        parameters=params or [],
    )


class MavericFileChunkEventsTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.store = ChunkFileStore(self.root)
        self.cfg = {"imaging": {"thumb_prefix": "tn_"}}
        self.events = MavericFileChunkEvents(
            store=self.store,
            adapters=[ImageKindAdapter(mission_cfg=self.cfg), AiiKindAdapter(), MagKindAdapter()],
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_unrelated_packet_returns_empty(self):
        pkt = _packet("eps_sw", "RES")
        self.assertEqual(list(self.events.on_packet(pkt)), [])

    def test_img_cnt_chunks_seeds_full_and_thumb(self):
        pkt = _packet("img_cnt_chunks", "RES", params=[
            _ParamUpdate("imaging.status", "0"),
            _ParamUpdate("imaging.filename", "capture.jpg"),
            _ParamUpdate("imaging.num_chunks", "10"),
            _ParamUpdate("imaging.thumb_filename", "tn_capture.jpg"),
            _ParamUpdate("imaging.thumb_num_chunks", "2"),
        ])
        msgs = list(self.events.on_packet(pkt))
        self.assertEqual(len(msgs), 2)
        self.assertEqual({m["kind"] for m in msgs}, {"image"})
        self.assertEqual({m["filename"] for m in msgs}, {"capture.jpg", "tn_capture.jpg"})

    def test_aii_cnt_chunks_seeds_one(self):
        pkt = _packet("aii_cnt_chunks", "RES", params=[
            _ParamUpdate("imaging.status", "0"),
            _ParamUpdate("imaging.filename", "inventory.json"),
            _ParamUpdate("imaging.num_chunks", "5"),
        ])
        msgs = list(self.events.on_packet(pkt))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["kind"], "aii")
        self.assertEqual(msgs[0]["filename"], "inventory.json")

    def test_mag_get_chunks_feeds_chunk(self):
        ref = FileRef(kind="mag", source="HLNV", filename="mag_001.nvg")
        self.store.set_total(ref, 1)
        args_raw = b"mag_001.nvg 0 4 \xde\xad\xbe\xef"
        pkt = _packet("mag_get_chunks", "FILE", params=[
            _ParamUpdate("hk.filename", "mag_001.nvg"),
            _ParamUpdate("hk.chunk_idx", "0"),
            _ParamUpdate("hk.chunk_len", "4"),
        ], args_raw=args_raw)
        msgs = list(self.events.on_packet(pkt))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["kind"], "mag")
        self.assertEqual(msgs[0]["received"], 1)
        self.assertTrue(msgs[0]["complete"])

    def test_cam_capture_twin_seeds_image_only(self):
        pkt = _packet("cam_capture", "RES", params=[
            _ParamUpdate("imaging.status", "0"),
            _ParamUpdate("imaging.filename", "capture.jpg"),
            _ParamUpdate("imaging.num_chunks", "10"),
            _ParamUpdate("imaging.thumb_filename", "tn_capture.jpg"),
            _ParamUpdate("imaging.thumb_num_chunks", "2"),
        ])
        msgs = list(self.events.on_packet(pkt))
        self.assertEqual(len(msgs), 2)
        for m in msgs:
            self.assertEqual(m["type"], "file_progress")
            self.assertEqual(m["kind"], "image")

    def test_on_client_connect_replays_known_files(self):
        self.store.set_total(FileRef(kind="image", source="HLNV", filename="a.jpg"), 1)
        self.store.set_total(FileRef(kind="aii", source="HLNV", filename="b.json"), 1)
        msgs = list(self.events.on_client_connect())
        self.assertEqual(len(msgs), 2)
        self.assertEqual({m["kind"] for m in msgs}, {"image", "aii"})

    def test_aii_completion_caches_valid_in_store(self):
        ref = FileRef(kind="aii", source="HLNV", filename="i.json")
        self.store.set_total(ref, 1)
        args_raw = b'i.json 0 12 {"ok": true}'
        pkt = _packet("aii_get_chunks", "FILE", params=[
            _ParamUpdate("imaging.filename", "i.json"),
            _ParamUpdate("imaging.chunk_idx", "0"),
            _ParamUpdate("imaging.chunk_len", "12"),
        ], args_raw=args_raw)
        msgs = list(self.events.on_packet(pkt))
        self.assertTrue(msgs[0]["complete"])
        self.assertTrue(msgs[0]["valid"])
        # Cached in store extras and persisted via meta sidecar.
        self.assertEqual(self.store.get_extras(ref), {"valid": True})

    def test_aii_invalid_completion_caches_false(self):
        ref = FileRef(kind="aii", source="HLNV", filename="bad.json")
        self.store.set_total(ref, 1)
        args_raw = b'bad.json 0 5 {"a:1'  # malformed
        pkt = _packet("aii_get_chunks", "FILE", params=[
            _ParamUpdate("imaging.filename", "bad.json"),
            _ParamUpdate("imaging.chunk_idx", "0"),
            _ParamUpdate("imaging.chunk_len", "5"),
        ], args_raw=args_raw)
        msgs = list(self.events.on_packet(pkt))
        self.assertTrue(msgs[0]["complete"])
        self.assertFalse(msgs[0]["valid"])
        self.assertEqual(self.store.get_extras(ref), {"valid": False})


if __name__ == "__main__":
    unittest.main()
