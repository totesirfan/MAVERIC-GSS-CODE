"""Operations-focused protocol and mission-adapter tests for MAVERIC GSS."""

from __future__ import annotations

import json
import unittest

from ops_test_support import CMD_DEFS, NODES

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter
from mav_gss_lib.missions.maveric import tx_ops
from mav_gss_lib.protocols.ax25 import AX25Config
from mav_gss_lib.protocols.csp import CSPConfig
from mav_gss_lib.protocols.crc import verify_csp_crc32
from mav_gss_lib.missions.maveric.wire_format import CommandFrame, build_cmd_raw
from mav_gss_lib.missions.maveric.schema import enrich_cmd_in_place, validate_args


class TestProtocolCore(unittest.TestCase):
    """Covers protocol truth plus the current mission-adapter seam."""

    def setUp(self):
        self.adapter = MavericMissionAdapter(cmd_defs=CMD_DEFS, nodes=NODES)

    def test_schema_loads_from_repo(self):
        self.assertGreater(len(CMD_DEFS), 0)
        self.assertIn("com_ping", CMD_DEFS)
        self.assertIn("gnc_set_mode", CMD_DEFS)

    def test_command_roundtrip_ping(self):
        raw = build_cmd_raw(6, 2, "com_ping", "")
        decoded, tail = CommandFrame.from_bytes(raw)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.cmd_id, "com_ping")
        self.assertEqual(decoded.args_str, "")
        self.assertTrue(decoded.crc_valid)
        self.assertEqual(tail, b"")

    def test_csp_crc_roundtrip(self):
        raw = build_cmd_raw(6, 2, "com_ping", "")
        packet = CSPConfig().wrap(raw)
        is_valid, rx_crc, comp_crc = verify_csp_crc32(packet)
        self.assertTrue(is_valid)
        self.assertEqual(rx_crc, comp_crc)

    def test_ax25_wrap_contains_ui_pid_marker(self):
        raw = build_cmd_raw(6, 2, "com_ping", "")
        ax25_payload = AX25Config().wrap(CSPConfig().wrap(raw))
        self.assertEqual(ax25_payload[14:16], b"\x03\xf0")

    def test_enrich_cmd_in_place_uses_current_definition(self):
        # ppm_get_time has 7 typed int rx_args — confirms the schema
        # enrich path wires up typed_args by name and type.
        cmd = {"cmd_id": "ppm_get_time",
               "args": ["3", "4", "22", "2026", "13", "45", "12"]}
        matched = enrich_cmd_in_place(cmd, CMD_DEFS)
        self.assertTrue(matched)
        self.assertTrue(cmd["schema_match"])
        typed = cmd.get("typed_args", [])
        self.assertEqual(len(typed), 7)
        names = [arg["name"] for arg in typed]
        self.assertEqual(names,
                         ["Weekday", "Month", "Day", "Year",
                          "Hour", "Minute", "Second"])
        self.assertEqual(typed[3]["value"], 2026)

    def test_enrich_cmd_in_place_tlm_beacon_is_schema_match_without_typed_args(self):
        """tlm_beacon is a binary-payload command; rx_args is intentionally
        empty so the schema does not invite text-token parsing of the
        packed struct. Enrichment still matches the schema — typed_args
        is simply empty and downstream rendering hides the raw args."""
        cmd = {"cmd_id": "tlm_beacon", "args": [], "args_raw": b""}
        matched = enrich_cmd_in_place(cmd, CMD_DEFS)
        self.assertTrue(matched)
        self.assertTrue(cmd["schema_match"])
        self.assertEqual(cmd.get("typed_args", []), [])
        self.assertTrue(cmd.get("rx_only"))

    def test_validate_args_rejects_missing_required_value(self):
        valid, issues = validate_args("gnc_set_mode", "", CMD_DEFS)
        self.assertFalse(valid)
        self.assertGreater(len(issues), 0)

    def test_truncated_command_payload_fails_cleanly(self):
        decoded, tail = CommandFrame.from_bytes(b"\x06\x02\x00")
        self.assertIsNone(decoded)
        self.assertIsNone(tail)

    def test_corrupted_csp_crc_is_detected(self):
        raw = build_cmd_raw(6, 2, "com_ping", "")
        packet = bytearray(CSPConfig().wrap(raw))
        packet[-1] ^= 0xFF
        is_valid, _rx_crc, _comp_crc = verify_csp_crc32(bytes(packet))
        self.assertFalse(is_valid)

    def test_adapter_detects_frame_types(self):
        self.assertEqual(self.adapter.detect_frame_type({"transmitter": "9k6 FSK AX.25 downlink"}), "AX.25")
        self.assertEqual(self.adapter.detect_frame_type({"transmitter": "9k6 FSK AX100 ASM+Golay downlink"}), "ASM+GOLAY")
        self.assertEqual(self.adapter.detect_frame_type({"transmitter": "mystery"}), "UNKNOWN")

    def test_adapter_normalizes_ax25_and_parses_schema_matched_command(self):
        raw = build_cmd_raw(6, 2, "gnc_set_mode", "NOMINAL")
        wrapped = AX25Config().wrap(CSPConfig().wrap(raw))
        inner, stripped, warnings = self.adapter.normalize_frame("AX.25", wrapped)
        self.assertEqual(inner, CSPConfig().wrap(raw))
        self.assertIsNotNone(stripped)
        self.assertEqual(warnings, [])

        parsed = self.adapter.parse_packet(inner)
        md = parsed.mission_data
        cmd, tail, ts_result = md["cmd"], md["cmd_tail"], md["ts_result"]
        self.assertEqual(cmd["cmd_id"], "gnc_set_mode")
        self.assertEqual(cmd["args"], ["NOMINAL"])
        self.assertTrue(cmd["schema_match"])
        self.assertEqual(tail, b"")
        self.assertIsNone(ts_result)

    def test_adapter_crc_and_uplink_echo_behavior(self):
        inner = CSPConfig().wrap(build_cmd_raw(6, 2, "com_ping", ""))
        warnings = []
        parsed = self.adapter.parse_packet(inner, warnings)
        cmd = parsed.mission_data["cmd"]
        clean = parsed.mission_data["crc_status"]
        self.assertTrue(clean["csp_crc32_valid"])
        self.assertEqual(warnings, [])

        corrupted = bytearray(inner)
        corrupted[-1] ^= 0xFF
        warnings = []
        bad_parsed = self.adapter.parse_packet(bytes(corrupted), warnings)
        bad = bad_parsed.mission_data["crc_status"]
        self.assertFalse(bad["csp_crc32_valid"])
        self.assertTrue(any("CRC-32C mismatch" in msg for msg in warnings))
        self.assertTrue(self.adapter.is_uplink_echo({"src": 6}))
        self.assertFalse(self.adapter.is_uplink_echo({"src": 2}))

    def test_adapter_build_and_validate_tx_command(self):
        raw = tx_ops.build_raw_command(6, 2, 0, 1, "gnc_set_mode", "NOMINAL")
        self.assertIsInstance(raw, (bytes, bytearray))
        self.assertGreater(len(raw), 0)
        valid, issues = tx_ops.validate_tx_args("gnc_set_mode", "NOMINAL", self.adapter.cmd_defs)
        self.assertTrue(valid)
        self.assertEqual(issues, [])

    def test_loggable_command_payload_is_json_safe(self):
        raw = build_cmd_raw(6, 2, "set_mode", "NOMINAL")
        packet = {
            "raw_hex": raw.hex(),
            "cmd_id": "set_mode",
            "args": ["NOMINAL"],
        }
        encoded = json.dumps(packet, sort_keys=True)
        self.assertIn("set_mode", encoded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
