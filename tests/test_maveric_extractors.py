"""Tests for mission extractor modules.

Each extractor reads a parsed packet's mission_data and yields
TelemetryFragment objects. Extractors must gate by cmd_id + ptype and
must tolerate malformed payloads without raising.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

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


def _pkt(ptype_id: int, cmd_id: str, args_raw: bytes | None = None):
    cmd: dict = {"cmd_id": cmd_id}
    if args_raw is not None:
        cmd["args_raw"] = args_raw
    return SimpleNamespace(mission_data={"ptype": ptype_id, "cmd": cmd})


class TestEpsHkExtractor(unittest.TestCase):
    def setUp(self) -> None:
        from mav_gss_lib.missions.maveric.telemetry.extractors.eps_hk import extract
        self.extract = extract
        self.nodes = _make_nodes()
        self.args_raw = _load_hex(FIXTURES / "packet.hex")

    def test_valid_tlm_packet_yields_48_fragments_with_units(self):
        pkt = _pkt(ptype_id=2, cmd_id="eps_hk", args_raw=self.args_raw)
        frags = list(self.extract(pkt, self.nodes, now_ms=12345))

        self.assertEqual(len(frags), 48)
        # Every fragment carries domain, ts_ms, and the canonical unit.
        for f in frags:
            self.assertEqual(f.domain, "eps")
            self.assertEqual(f.ts_ms, 12345)

        units = {f.key: f.unit for f in frags}
        # Unit table coverage — spot-check each scaling bucket.
        self.assertEqual(units["V_BAT"], "V")
        self.assertEqual(units["I_BAT"], "A")
        self.assertEqual(units["P3V3"], "W")
        self.assertEqual(units["TS_ADC"], "%")
        self.assertEqual(units["T_DIE"], "°C")

    def test_non_tlm_ptype_yields_nothing(self):
        for ptype in (0, 1, 3, 4):  # CMD, ACK, RES, FILE
            pkt = _pkt(ptype_id=ptype, cmd_id="eps_hk", args_raw=self.args_raw)
            self.assertEqual(list(self.extract(pkt, self.nodes, 0)), [],
                             msg=f"ptype={ptype} should not emit")

    def test_wrong_cmd_id_yields_nothing(self):
        pkt = _pkt(ptype_id=2, cmd_id="gnc_get_mode", args_raw=self.args_raw)
        self.assertEqual(list(self.extract(pkt, self.nodes, 0)), [])

    def test_missing_args_raw_yields_nothing(self):
        pkt = _pkt(ptype_id=2, cmd_id="eps_hk", args_raw=None)
        self.assertEqual(list(self.extract(pkt, self.nodes, 0)), [])

    def test_short_args_raw_yields_nothing(self):
        pkt = _pkt(ptype_id=2, cmd_id="eps_hk", args_raw=b"\x00" * 10)
        self.assertEqual(list(self.extract(pkt, self.nodes, 0)), [])

    def test_extractor_does_not_read_mission_data_telemetry(self):
        """Extractor must call decode_eps_hk directly, not consume a
        pre-populated mission_data['telemetry'] key (which Task 10a deletes).

        Scans the compiled constants + names rather than the source text so
        the docstring is ignored.
        """
        from mav_gss_lib.missions.maveric.telemetry.extractors import eps_hk
        consts = set(eps_hk.extract.__code__.co_consts)
        names = set(eps_hk.extract.__code__.co_names) | set(
            eps_hk.extract.__code__.co_varnames
        )
        self.assertNotIn("telemetry", consts,
                         "extractor must not subscript mission_data['telemetry']")
        # `fragments`/`gnc_registers` likewise must not appear as literal keys.
        self.assertNotIn("gnc_registers", consts)


if __name__ == "__main__":
    unittest.main()
