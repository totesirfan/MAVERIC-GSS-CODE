"""EPS adapter tests — decoder round-trip + v2 telemetry message emission.

Consumes ``docs/eps-port/fixtures/packet.hex`` (synthetic 96-byte args_raw)
and ``docs/eps-port/fixtures/decoded.json`` (expected engineering values).

Post-v2:
  * ``decode_eps_hk`` still produces 48 TelemetryField entries matching
    the golden decoded.json fixture.
  * The adapter's split hook (``attach_fragments`` → ``on_packet_received``)
    emits a `{type: "telemetry", domain: "eps", changes: {...}}` message
    for real TLM frames, nothing for CMD echoes / ACKs.
  * ``on_client_connect`` returns the platform router's replay, which
    carries ``replay: true`` on every entry.

No ``EpsStore`` / ``eps_store`` kwarg anywhere — per-domain canonical
state lives in the platform ``DomainState`` now (coverage in
tests/test_telemetry_state.py).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "docs" / "eps-port" / "fixtures"


def _load_hex(p: Path) -> bytes:
    raw = p.read_text()
    cleaned = "".join(ch for ch in raw if ch not in " \n\r\t")
    return bytes.fromhex(cleaned)


def _make_nodes():
    from mav_gss_lib.missions.maveric.nodes import NodeTable
    return NodeTable(
        node_names={0: "GS", 1: "SAT"},
        node_ids={"GS": 0, "SAT": 1},
        ptype_names={0: "CMD", 1: "ACK", 2: "TLM", 3: "RES", 4: "FILE"},
        ptype_ids={"CMD": 0, "ACK": 1, "TLM": 2, "RES": 3, "FILE": 4},
        gs_node=0,
    )


def _make_packet(ptype_id: int, pkt_num: int, args_raw: bytes):
    """Build a packet fixture with the real 96-byte args_raw so
    attach_fragments can run decode_eps_hk exactly the way production does."""
    from mav_gss_lib.parsing import Packet
    return Packet(
        pkt_num=pkt_num,
        mission_data={
            "ptype": ptype_id,
            "cmd": {"cmd_id": "eps_hk", "args_raw": args_raw},
        },
    )


def _run_pkt(adapter, pkt):
    """Mirror rx_service's production order: attach_fragments before
    on_packet_received. Every test that drives the adapter at the packet
    level goes through this helper."""
    adapter.attach_fragments(pkt)
    return adapter.on_packet_received(pkt) or []


def _make_adapter(tmp_path):
    from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter
    from mav_gss_lib.missions.maveric.telemetry.extractors import EXTRACTORS
    from mav_gss_lib.web_runtime.telemetry.router import TelemetryRouter

    adapter = MavericMissionAdapter(cmd_defs={}, nodes=_make_nodes())
    router = TelemetryRouter(tmp_path / ".telemetry")
    router.register_domain("eps")
    router.register_domain("gnc")
    adapter.telemetry = router
    adapter.extractors = EXTRACTORS
    return adapter, router


class TestEpsDecoderFixture(unittest.TestCase):
    def setUp(self) -> None:
        from mav_gss_lib.missions.maveric.telemetry.semantics.eps import decode_eps_hk
        self.decode_eps_hk = decode_eps_hk
        self.args_raw = _load_hex(FIXTURES / "packet.hex")
        self.expected = json.loads((FIXTURES / "decoded.json").read_text())

    def test_packet_size_is_96_bytes(self) -> None:
        self.assertEqual(len(self.args_raw), 96)

    def test_decoder_matches_golden_fields(self) -> None:
        fields = self.decode_eps_hk({"args_raw": self.args_raw})
        self.assertEqual(len(fields), 48)
        got = {f.name: f.value for f in fields}
        want = self.expected["fields"]
        self.assertEqual(set(got.keys()), set(want.keys()))
        manifest = json.loads(
            (ROOT / "docs" / "eps-port" / "eps_fields.json").read_text()
        )
        digits_by_name = {f["name"]: f["digits"] for f in manifest["fields"]}
        for name, expected_value in want.items():
            places = digits_by_name.get(name, 3)
            self.assertAlmostEqual(
                got[name], expected_value, places=places,
                msg=f"field {name}: got {got[name]}, want {expected_value}",
            )


class TestAdapterPtypeGating(unittest.TestCase):
    """The EPS fragments must only be ingested for TLM frames."""

    def setUp(self) -> None:
        import tempfile
        self._tmp_root = Path(tempfile.mkdtemp())
        self.adapter, self.router = _make_adapter(self._tmp_root)
        self.args_raw = _load_hex(FIXTURES / "packet.hex")
        self.expected = json.loads((FIXTURES / "decoded.json").read_text())

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp_root, ignore_errors=True)

    def test_tlm_emits_single_eps_telemetry_message(self) -> None:
        pkt = _make_packet(ptype_id=2, pkt_num=7, args_raw=self.args_raw)
        msgs = _run_pkt(self.adapter, pkt)

        eps_msgs = [m for m in msgs
                    if m.get("type") == "telemetry" and m.get("domain") == "eps"]
        self.assertEqual(len(eps_msgs), 1,
                         f"expected one eps telemetry message, got {msgs}")
        changes = eps_msgs[0]["changes"]
        # Forty-eight keys from decode_eps_hk.
        self.assertEqual(len(changes), 48)
        # Each change entry carries {v, t}.
        v_bus_entry = changes["V_BUS"]
        self.assertIn("v", v_bus_entry)
        self.assertIn("t", v_bus_entry)
        self.assertAlmostEqual(v_bus_entry["v"], self.expected["fields"]["V_BUS"], places=4)

    def test_cmd_does_not_emit_eps(self) -> None:
        pkt = _make_packet(ptype_id=0, pkt_num=8, args_raw=self.args_raw)
        msgs = _run_pkt(self.adapter, pkt)
        eps_msgs = [m for m in msgs
                    if m.get("type") == "telemetry" and m.get("domain") == "eps"]
        self.assertEqual(eps_msgs, [], "CMD echoes must not emit eps telemetry")

    def test_ack_does_not_emit_eps(self) -> None:
        pkt = _make_packet(ptype_id=1, pkt_num=9, args_raw=self.args_raw)
        msgs = _run_pkt(self.adapter, pkt)
        eps_msgs = [m for m in msgs
                    if m.get("type") == "telemetry" and m.get("domain") == "eps"]
        self.assertEqual(eps_msgs, [], "ACK frames must not emit eps telemetry")

    def test_attach_fragments_sets_key_even_when_gated_out(self) -> None:
        pkt = _make_packet(ptype_id=0, pkt_num=10, args_raw=self.args_raw)
        self.adapter.attach_fragments(pkt)
        self.assertEqual(pkt.mission_data.get("fragments"), [],
                         "fragments key must exist (possibly empty) after attach")


class TestAdapterClientConnectReplay(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp_root = Path(tempfile.mkdtemp())
        self.adapter, self.router = _make_adapter(self._tmp_root)
        self.args_raw = _load_hex(FIXTURES / "packet.hex")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp_root, ignore_errors=True)

    def test_replay_empty_router_emits_nothing(self) -> None:
        msgs = self.adapter.on_client_connect()
        self.assertEqual(msgs, [])

    def test_replay_populated_router_marks_replay(self) -> None:
        # Drive a real TLM packet through the split hook so the router
        # has canonical state, then replay.
        pkt = _make_packet(ptype_id=2, pkt_num=42, args_raw=self.args_raw)
        _run_pkt(self.adapter, pkt)

        msgs = self.adapter.on_client_connect()
        eps_msgs = [m for m in msgs
                    if m.get("type") == "telemetry" and m.get("domain") == "eps"]
        self.assertEqual(len(eps_msgs), 1)
        msg = eps_msgs[0]
        self.assertTrue(msg.get("replay"))
        # Changes carry the same engineering values; format is {v, t}.
        self.assertIn("V_BUS", msg["changes"])
        self.assertIn("v", msg["changes"]["V_BUS"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
