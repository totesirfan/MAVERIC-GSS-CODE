"""MaverPacketCodec tests.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import unittest

from mav_gss_lib.missions.maveric.codec import MaverPacketCodec
from mav_gss_lib.missions.maveric.errors import (
    DuplicateNodeId,
    DuplicatePtypeId,
    NodeIdOutOfRange,
    PtypeIdOutOfRange,
    UnknownNodeId,
    UnknownPtypeId,
)


class CodecConstructionTest(unittest.TestCase):
    def _ext(self, **overrides):
        base = {
            "nodes": {"NONE": 0, "LPPM": 1, "GS": 6},
            "ptypes": {"CMD": 1, "RES": 2},
            "gs_node": "GS",
        }
        base.update(overrides)
        return base

    def test_constructs_with_valid_extensions(self) -> None:
        codec = MaverPacketCodec(extensions=self._ext())
        self.assertEqual(codec.gs_node_id, 6)
        self.assertEqual(codec.node_id_for("LPPM"), 1)
        self.assertEqual(codec.node_name_for(1), "LPPM")
        self.assertEqual(codec.ptype_id_for("CMD"), 1)
        self.assertEqual(codec.ptype_name_for(2), "RES")

    def test_rejects_duplicate_node_id(self) -> None:
        with self.assertRaises(DuplicateNodeId):
            MaverPacketCodec(
                extensions=self._ext(nodes={"NONE": 0, "LPPM": 1, "GS": 1}),
            )

    def test_rejects_duplicate_ptype_id(self) -> None:
        with self.assertRaises(DuplicatePtypeId):
            MaverPacketCodec(
                extensions=self._ext(ptypes={"CMD": 1, "RES": 1}),
            )

    def test_rejects_node_out_of_range(self) -> None:
        with self.assertRaises(NodeIdOutOfRange):
            MaverPacketCodec(
                extensions=self._ext(nodes={"NONE": 0, "LPPM": 1, "GS": 999}),
            )

    def test_rejects_ptype_out_of_range(self) -> None:
        with self.assertRaises(PtypeIdOutOfRange):
            MaverPacketCodec(
                extensions=self._ext(ptypes={"CMD": 1, "RES": 300}),
            )


if __name__ == "__main__":
    unittest.main()
