"""
mav_gss_lib.missions.maveric.adapter -- MAVERIC Mission Adapter

Thin boundary around current MAVERIC protocol behavior.
RX parsing, CRC checks, uplink-echo classification, and TX command
validation/building all pass through here so a future mission has
one obvious replacement seam.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass

from mav_gss_lib.protocols.crc import verify_csp_crc32
from mav_gss_lib.protocols.csp import try_parse_csp_v1
from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame
from mav_gss_lib.missions.maveric.wire_format import (
    GS_NODE,
    apply_schema,
    build_cmd_raw,
    try_parse_command,
    validate_args,
)


# =============================================================================
#  MAVERIC MISSION ADAPTER
# =============================================================================


@dataclass
class MavericMissionAdapter:
    """Thin boundary around current MAVERIC protocol behavior.

    RX parsing, CRC checks, uplink-echo classification, and TX command
    validation/building all pass through here so a future mission has
    one obvious replacement seam.
    """

    cmd_defs: dict

    def detect_frame_type(self, meta) -> str:
        """Classify outer framing from GNU Radio/gr-satellites metadata."""
        return detect_frame_type(meta)

    def normalize_frame(self, frame_type: str, raw: bytes):
        """Strip mission-specific outer framing and return inner payload."""
        return normalize_frame(frame_type, raw)

    def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None):
        """Parse one normalized RX payload into a mission-neutral result."""
        from mav_gss_lib.mission_adapter import ParsedPacket

        warnings = [] if warnings is None else warnings
        csp, csp_plausible = try_parse_csp_v1(inner_payload)
        if len(inner_payload) <= 4:
            return ParsedPacket(csp=csp, csp_plausible=csp_plausible, warnings=warnings)

        cmd, cmd_tail = try_parse_command(inner_payload[4:])
        ts_result = None
        if cmd:
            apply_schema(cmd, self.cmd_defs)
            if cmd.get("sat_time"):
                ts_result = cmd["sat_time"]

        crc_valid, crc_rx, crc_comp = None, None, None
        if cmd and cmd.get("csp_crc32") is not None:
            crc_valid, crc_rx, crc_comp = verify_csp_crc32(inner_payload)
            if crc_valid is False:
                warnings.append(
                    f"CRC-32C mismatch: rx 0x{crc_rx:08x} != computed 0x{crc_comp:08x}"
                )

        return ParsedPacket(
            csp=csp,
            csp_plausible=csp_plausible,
            cmd=cmd,
            cmd_tail=cmd_tail,
            ts_result=ts_result,
            warnings=warnings,
            crc_status={
                "csp_crc32_valid": crc_valid,
                "csp_crc32_rx": crc_rx,
                "csp_crc32_comp": crc_comp,
            },
        )

    def parse_command(self, inner_payload: bytes):
        """Backward-compatible wrapper around parse_packet()."""
        parsed = self.parse_packet(inner_payload)
        return parsed.cmd, parsed.cmd_tail, parsed.ts_result

    def verify_crc(self, cmd, inner_payload: bytes, warnings: list[str]):
        """Backward-compatible CRC wrapper around parse_packet()."""
        parsed = self.parse_packet(inner_payload, warnings)
        return parsed.crc_status

    def duplicate_fingerprint(self, parsed):
        """Return a mission-specific duplicate fingerprint or None."""
        cmd = parsed.cmd
        if not (cmd and cmd.get("crc") is not None and cmd.get("csp_crc32") is not None):
            return None
        return cmd["crc"], cmd["csp_crc32"]

    def is_uplink_echo(self, cmd) -> bool:
        """Classify whether a decoded command is the ground-station echo."""
        from mav_gss_lib.mission_adapter import ParsedPacket
        cmd_obj = cmd.cmd if isinstance(cmd, ParsedPacket) else cmd
        return bool(cmd_obj and cmd_obj.get("src") == GS_NODE)

    def build_raw_command(self, src, dest, echo, ptype, cmd_id: str, args: str) -> bytes:
        """Build one raw mission command payload for TX."""
        return build_cmd_raw(dest, cmd_id, args, echo=echo, ptype=ptype, origin=src)

    def validate_tx_args(self, cmd_id: str, args: str):
        """Validate TX arguments using the active mission command schema."""
        return validate_args(cmd_id, args, self.cmd_defs)
