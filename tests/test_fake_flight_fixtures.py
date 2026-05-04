"""Smoke + round-trip tests for the fake_flight file-fixture path.

Exercises the per-kind chunk inventory + the byte-slicing inside
``_send_file_chunks``. No ZMQ, no codec — we stub ``_publish`` and
``_build_binary_response`` to capture the streamed args_raw.
"""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]


def _import_fake_flight():
    import importlib
    import sys
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    return importlib.import_module("scripts.fake_flight")


class FixtureLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ff = _import_fake_flight()
        self.state = self.ff.SpacecraftState()
        self.summaries, self.missing = self.ff._load_fixtures(self.state)

    def test_loads_all_four_fixtures(self) -> None:
        kinds = sorted(k for k, _ in self.state.fixtures)
        self.assertEqual(kinds, ["aii", "img", "img", "mag"])

    def test_fixture_chunk_counts_match_byte_lengths(self) -> None:
        for (kind, fname), data in self.state.fixtures.items():
            registry = {
                "img": self.state.img_chunks,
                "aii": self.state.aii_chunks,
                "mag": self.state.mag_chunks,
            }[kind]
            self.assertIn(fname, registry,
                          f"{kind}/{fname} not registered in chunk dict")
            expected = self.ff._chunks_needed(len(data))
            self.assertEqual(
                registry[fname], expected,
                f"chunk count mismatch for {kind}/{fname}",
            )

    def test_summaries_describe_each_fixture(self) -> None:
        joined = " | ".join(self.summaries)
        for fname in ("test.jpg", "tn_test.jpg",
                      "test.json", "test.nvg"):
            self.assertIn(fname, joined)

    def test_missing_list_is_empty_when_all_present(self) -> None:
        self.assertEqual(self.missing, [])


class CamCaptureFormatTests(unittest.TestCase):
    """``_ov_cam_capture`` must match the real-flight wire format
    (``1 a.jpg 406 tn_a.jpg 6``)."""

    def setUp(self) -> None:
        self.ff = _import_fake_flight()
        self.state = self.ff.SpacecraftState()

    def test_qty1_emits_bare_filename_with_tn_prefix(self) -> None:
        out = self.ff._ov_cam_capture(self.state, "a.jpg 1")
        parts = out.split()
        self.assertEqual(parts[0], "1")
        self.assertEqual(parts[1], "a.jpg")
        self.assertTrue(parts[2].isdigit())
        self.assertEqual(parts[3], "tn_a.jpg")
        self.assertTrue(parts[4].isdigit())

    def test_qty1_chunk_counts_match_subsequent_cnt_chunks(self) -> None:
        cap = self.ff._ov_cam_capture(self.state, "a.jpg 1")
        cap_parts = cap.split()
        cap_full_n = int(cap_parts[2])
        cap_thumb_n = int(cap_parts[4])
        cnt = self.ff._ov_img_cnt_chunks(self.state, "a.jpg 1")
        cnt_parts = cnt.split()
        self.assertEqual(int(cnt_parts[2]), cap_full_n,
                         "cam_capture full-chunks must equal img_cnt_chunks reply")
        self.assertEqual(int(cnt_parts[4]), cap_thumb_n,
                         "cam_capture thumb-chunks must equal img_cnt_chunks reply")

    def test_qty_gt_1_uses_indexed_stems_with_tn_prefix(self) -> None:
        out = self.ff._ov_cam_capture(self.state, "burst.jpg 3")
        chunks = out.split()
        # Each shot is a 5-token group: "1 <name> <n> <thumb> <m>"
        self.assertEqual(len(chunks) % 5, 0)
        names = [chunks[i + 1] for i in range(0, len(chunks), 5)]
        thumbs = [chunks[i + 3] for i in range(0, len(chunks), 5)]
        self.assertEqual(names, ["burst_0.jpg", "burst_1.jpg", "burst_2.jpg"])
        for n, t in zip(names, thumbs):
            self.assertEqual(t, f"tn_{n}")
        self.assertNotIn("thumb_", out)

    def test_default_filename_when_args_empty(self) -> None:
        # Bare ``cam_capture`` (no args) — default to ``img.jpg``,
        # not the fixture name (avoids overwriting fixture chunk counts).
        out = self.ff._ov_cam_capture(self.state, "")
        parts = out.split()
        self.assertEqual(parts[1], "img.jpg")
        self.assertEqual(parts[3], "tn_img.jpg")


class ChunkRoundtripTests(unittest.IsolatedAsyncioTestCase):
    """Slice each fixture through _send_file_chunks; verify reassembled
    bytes equal the original fixture."""

    async def _roundtrip(self, kind: str, fname: str) -> None:
        ff = _import_fake_flight()
        state = ff.SpacecraftState()
        ff._load_fixtures(state)
        original = state.fixtures[(kind, fname)]
        total = ff._resolve_total_chunks(state, kind, fname)

        captured: list[tuple[str, bytes]] = []

        def fake_build(codec, src, ptype, cmd_id, args_raw):
            captured.append((cmd_id, bytes(args_raw)))
            return b"FAKE_WIRE"

        published: list[bytes] = []

        def fake_publish(sock, payload, label, loopback=None):
            published.append(payload)

        with mock.patch.object(ff, "_build_binary_response", side_effect=fake_build), \
             mock.patch.object(ff, "_publish", side_effect=fake_publish), \
             mock.patch.object(ff.asyncio, "sleep",
                               new=mock.AsyncMock(return_value=None)):
            await ff._send_file_chunks(
                pub_sock=None, codec=None, state=state,
                res_src="HLNV", kind=kind, fname=fname,
                start_chunk=0, num_chunks=total, loopback=None,
            )

        self.assertEqual(len(captured), total,
                         f"emitted {len(captured)} chunks, expected {total}")
        self.assertEqual(len(published), total)
        # Every captured packet should carry the right cmd_id for its kind.
        expected_cmd = ff._KIND_GET_CMD[kind]
        for cmd_id, _ in captured:
            self.assertEqual(cmd_id, expected_cmd)

        # Reassemble payload. Each args_raw is `<fname> <idx> <len> <bytes>`.
        prefix = f"{fname} ".encode("ascii")
        reassembled = bytearray()
        for cmd_id, args_raw in captured:
            self.assertTrue(args_raw.startswith(prefix),
                            f"missing filename prefix in {args_raw[:40]!r}")
            rest = args_raw[len(prefix):]
            sp1 = rest.find(b" ")
            sp2 = rest.find(b" ", sp1 + 1)
            self.assertGreater(sp1, 0)
            self.assertGreater(sp2, sp1)
            length = int(rest[sp1 + 1:sp2])
            payload = rest[sp2 + 1:]
            self.assertEqual(len(payload), length)
            reassembled.extend(payload)
        self.assertEqual(bytes(reassembled), original)

    async def test_image_full_roundtrip(self) -> None:
        await self._roundtrip("img", "test.jpg")

    async def test_image_thumb_roundtrip(self) -> None:
        await self._roundtrip("img", "tn_test.jpg")

    async def test_aii_roundtrip(self) -> None:
        await self._roundtrip("aii", "test.json")

    async def test_mag_roundtrip(self) -> None:
        await self._roundtrip("mag", "test.nvg")


class CntChunksOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ff = _import_fake_flight()
        self.state = self.ff.SpacecraftState()
        self.ff._load_fixtures(self.state)

    def test_img_cnt_chunks_uses_fixture_count(self) -> None:
        out = self.ff._ov_img_cnt_chunks(self.state, "test.jpg 1")
        # shape: "1 test.jpg <imgN> tn_test.jpg <thumbN>"
        parts = out.split()
        self.assertEqual(parts[0], "1")
        self.assertEqual(parts[1], "test.jpg")
        self.assertEqual(parts[3], "tn_test.jpg")
        self.assertEqual(int(parts[2]), self.state.img_chunks["test.jpg"])
        self.assertEqual(int(parts[4]), self.state.img_chunks["tn_test.jpg"])

    def test_aii_cnt_chunks_uses_fixture_count(self) -> None:
        out = self.ff._ov_aii_cnt_chunks(self.state, "test.json")
        parts = out.split()
        self.assertEqual(parts, ["1", "test.json",
                                 str(self.state.aii_chunks["test.json"])])

    def test_mag_cnt_chunks_uses_fixture_count(self) -> None:
        out = self.ff._ov_mag_cnt_chunks(self.state, "test.nvg")
        parts = out.split()
        self.assertEqual(parts, ["1", "test.nvg",
                                 str(self.state.mag_chunks["test.nvg"])])


class NegativeStartChunkTests(unittest.IsolatedAsyncioTestCase):
    """A negative ``start_chunk`` must be clamped to 0 — never produce
    negative chunk_idx on the wire and never negative-slice a fixture."""

    async def test_negative_start_clamps_to_zero(self) -> None:
        ff = _import_fake_flight()
        state = ff.SpacecraftState()
        ff._load_fixtures(state)

        captured: list[bytes] = []

        def fake_build(codec, src, ptype, cmd_id, args_raw):
            captured.append(bytes(args_raw))
            return b"FAKE"

        with mock.patch.object(ff, "_build_binary_response", side_effect=fake_build), \
             mock.patch.object(ff, "_publish", lambda *a, **k: None), \
             mock.patch.object(ff.asyncio, "sleep",
                               new=mock.AsyncMock(return_value=None)):
            await ff._send_file_chunks(
                pub_sock=None, codec=None, state=state,
                res_src="HLNV", kind="img", fname="test.jpg",
                start_chunk=-5, num_chunks=3, loopback=None,
            )

        # First emitted packet must report idx 0, not -5.
        first = captured[0]
        prefix = b"test.jpg "
        self.assertTrue(first.startswith(prefix))
        rest = first[len(prefix):]
        first_idx = int(rest.split(b" ", 1)[0])
        self.assertEqual(first_idx, 0)


class ArgsLenOverflowTests(unittest.TestCase):
    """``_build_binary_response`` must raise loudly above the 1-byte
    args_len ceiling instead of silently truncating with ``& 0xFF``."""

    class _StubCodec:
        gs_node_name = "GS"
        def node_id_for(self, _name: str) -> int: return 4
        def ptype_id_for(self, _name: str) -> int: return 6

    def test_oversized_args_raises(self) -> None:
        ff = _import_fake_flight()
        with self.assertRaises(ValueError):
            ff._build_binary_response(self._StubCodec(), "HLNV", "FILE",
                                      "img_get_chunks",
                                      b"x" * 256)

    def test_args_len_255_succeeds(self) -> None:
        ff = _import_fake_flight()
        wire = ff._build_binary_response(self._StubCodec(), "HLNV", "FILE",
                                         "img_get_chunks",
                                         b"x" * 255)
        self.assertGreater(len(wire), 255)


class EchoNoneTests(unittest.TestCase):
    """RES/ACK echo byte must be 0 (NONE), matching every observed
    real-flight downlink (binary builder already does this; text-arg
    builder used to set echo=GS)."""

    def test_text_arg_response_uses_none_for_echo(self) -> None:
        ff = _import_fake_flight()
        captured: dict = {}

        class StubCodec:
            gs_node_name = "GS"
            def complete_header(self, hdr):
                captured["echo"] = hdr.fields.get("echo")
                return hdr
            def wrap(self, _hdr, _args): return b"INNER"

        ff._build_response(StubCodec(), "HLNV", "RES", "img_cnt_chunks",
                           "1 a.jpg 10 tn_a.jpg 2")
        self.assertEqual(captured["echo"], "NONE")


class TimingModelTests(unittest.TestCase):
    """Median-matched against the Apr 28 real-flight log."""

    def setUp(self) -> None:
        self.ff = _import_fake_flight()

    def test_constants_match_observed_real_flight(self) -> None:
        # UPPM gateway ACK ~1.12s in flight; 1.10s nominal here.
        self.assertAlmostEqual(self.ff.UPPM_ACK_DELAY_S, 1.10, places=2)
        # Dest ACK arrives ~0.20s after UPPM ACK in flight.
        self.assertAlmostEqual(self.ff.DEST_ACK_GAP_S, 0.20, places=2)

    def test_astr_flow_has_no_dest_ack(self) -> None:
        # Real flight: zero ACK packets observed from src=ASTR.
        second_ack, res_src = self.ff.FLOWS["ASTR"]
        self.assertIsNone(second_ack)
        self.assertEqual(res_src, "ASTR")

    def test_hlnv_flow_still_has_dest_ack(self) -> None:
        second_ack, res_src = self.ff.FLOWS["HLNV"]
        self.assertEqual(second_ack, "HLNV")
        self.assertEqual(res_src, "HLNV")

    def test_res_delay_overrides_match_log(self) -> None:
        # cam_capture takes ~3.2s post-ACK in flight (n=2 each on HLNV/ASTR)
        self.assertAlmostEqual(self.ff._res_delay_s("cam_capture", "HLNV"),
                               3.20, places=2)
        self.assertAlmostEqual(self.ff._res_delay_s("cam_capture", "ASTR"),
                               3.20, places=2)
        # img_cnt_chunks splits by dest in flight: HLNV ~2.3s, ASTR ~0.3s
        self.assertAlmostEqual(self.ff._res_delay_s("img_cnt_chunks", "HLNV"),
                               2.30, places=2)
        self.assertAlmostEqual(self.ff._res_delay_s("img_cnt_chunks", "ASTR"),
                               0.30, places=2)

    def test_unknown_cmd_uses_default_delay(self) -> None:
        self.assertAlmostEqual(
            self.ff._res_delay_s("nonexistent_cmd", "HLNV"),
            self.ff.RES_DELAY_DEFAULT_S, places=3)

    def test_res_delay_dest_lookup_is_case_insensitive(self) -> None:
        self.assertEqual(
            self.ff._res_delay_s("cam_capture", "hlnv"),
            self.ff._res_delay_s("cam_capture", "HLNV"))


class TimingFlowTotalsTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end timing of respond() — verify the published packet
    sequence honors the new constants by mocking out ``asyncio.sleep``
    and recording the elapsed delays."""

    async def _record_sleep_sequence(self, cmd_id: str, dest: str) -> list[float]:
        ff = _import_fake_flight()
        sleeps: list[float] = []

        async def fake_sleep(s):
            sleeps.append(float(s))

        with mock.patch.object(ff.asyncio, "sleep", new=fake_sleep), \
             mock.patch.object(ff, "_publish", lambda *a, **k: None), \
             mock.patch.object(ff, "_build_response",
                               lambda *a, **k: b"FAKE"), \
             mock.patch.object(ff, "_build_binary_response",
                               lambda *a, **k: b"FAKE"):

            class _StubMission:
                meta_commands: dict = {}
            await ff.respond(
                pub_sock=None, codec=None, mission=_StubMission(),
                state=ff.SpacecraftState(),
                cmd_id=cmd_id, dest=dest, args_in="",
                skips=set(), loopback=None,
            )
        return sleeps

    async def test_hlnv_cam_capture_sequence(self) -> None:
        # UPPM ACK -> dest ACK -> RES (heavy, override 3.20s)
        sleeps = await self._record_sleep_sequence("cam_capture", "HLNV")
        self.assertEqual(sleeps, [1.10, 0.20, 3.20])
        self.assertAlmostEqual(sum(sleeps), 4.50, places=2)

    async def test_astr_cam_capture_sequence_skips_dest_ack(self) -> None:
        # ASTR has no dest ACK in flight: only UPPM ACK + RES
        sleeps = await self._record_sleep_sequence("cam_capture", "ASTR")
        self.assertEqual(sleeps, [1.10, 3.20])
        self.assertAlmostEqual(sum(sleeps), 4.30, places=2)

    async def test_astr_img_cnt_chunks_is_fast(self) -> None:
        # Light ASTR cmd: 1.10 (UPPM ACK) + 0.30 (RES) = 1.40s
        sleeps = await self._record_sleep_sequence("img_cnt_chunks", "ASTR")
        self.assertEqual(sleeps, [1.10, 0.30])

    async def test_hlnv_img_cnt_chunks_uses_dest_ack_path(self) -> None:
        # HLNV: 1.10 + 0.20 + 2.30 = 3.60s
        sleeps = await self._record_sleep_sequence("img_cnt_chunks", "HLNV")
        self.assertEqual(sleeps, [1.10, 0.20, 2.30])


if __name__ == "__main__":
    unittest.main()
