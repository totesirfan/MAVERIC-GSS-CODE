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

from mav_gss_lib.missions.maveric import log_format as _log_format
from mav_gss_lib.missions.maveric import rendering as _rendering, rx_ops, tx_ops
from mav_gss_lib.missions.maveric.wire_format import GS_NODE


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
    image_assembler: object = None  # ImageAssembler, set by init_mission

    def detect_frame_type(self, meta) -> str:
        """Classify outer framing from GNU Radio/gr-satellites metadata."""
        return rx_ops.detect(meta)

    def normalize_frame(self, frame_type: str, raw: bytes):
        """Strip mission-specific outer framing and return inner payload."""
        return rx_ops.normalize(frame_type, raw)

    def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None):
        """Parse one normalized RX payload into a mission-neutral result."""
        return rx_ops.parse_packet(inner_payload, self.cmd_defs, warnings)

    @staticmethod
    def _md(pkt) -> dict:
        """Read mission data from a packet."""
        return getattr(pkt, "mission_data", {}) or {}

    def duplicate_fingerprint(self, parsed):
        """Return a mission-specific duplicate fingerprint or None."""
        return rx_ops.duplicate_fingerprint(self._md(parsed))

    def is_uplink_echo(self, cmd) -> bool:
        """Classify whether a decoded command is the ground-station echo."""
        from mav_gss_lib.mission_adapter import ParsedPacket
        md = self._md(cmd) if isinstance(cmd, ParsedPacket) else {"cmd": cmd}
        return rx_ops.is_uplink_echo(md)

    def build_raw_command(self, src, dest, echo, ptype, cmd_id: str, args: str) -> bytes:
        """Build one raw mission command payload for TX."""
        return tx_ops.build_raw_command(src, dest, echo, ptype, cmd_id, args)

    def validate_tx_args(self, cmd_id: str, args: str):
        """Validate TX arguments using the active mission command schema."""
        return tx_ops.validate_tx_args(cmd_id, args, self.cmd_defs)

    def build_tx_command(self, payload):
        """Build a mission command from structured input.

        Accepts: {cmd_id, args: str | {name: value, ...}, src?, dest, echo, ptype, guard?}
        - args as a flat string: CLI path — positional tokens matched to tx_args schema
        - args as a dict: mission builder path — {name: value} mapping
        - src (optional): override source node; defaults to GS_NODE
        Returns: {raw_cmd: bytes, display: dict, guard: bool}
        Raises ValueError on validation failure.
        """
        return tx_ops.build_tx_command(payload, self.cmd_defs)

    # =========================================================================
    #  Adapter boundary
    #
    #  This adapter implements the MissionAdapter protocol defined in
    #  mav_gss_lib/mission_adapter.py. The platform calls these methods
    #  without knowing which mission is active.
    #
    #  RX: detect_frame_type → normalize_frame → parse_packet
    #  TX: cmd_line_to_payload, build_tx_command, tx_queue_columns
    #  UI: packet_list_columns/row, packet_detail_blocks, protocol/integrity
    #  Log: build_log_mission_data, format_log_lines, is_unknown_packet
    #  Resolution: gs_node, node_name, ptype_name, resolve_node, resolve_ptype
    # =========================================================================

    # -- Rendering-slot contract (architecture spec) --

    def packet_list_columns(self): return _rendering.packet_list_columns()
    def packet_list_row(self, pkt): return _rendering.packet_list_row(pkt)
    def protocol_blocks(self, pkt): return _rendering.protocol_blocks(pkt)
    def integrity_blocks(self, pkt): return _rendering.integrity_blocks(pkt)
    def packet_detail_blocks(self, pkt): return _rendering.packet_detail_blocks(pkt)

    # -- Logging-slot contract --

    def build_log_mission_data(self, pkt) -> dict:
        return _log_format.build_log_mission_data(pkt)

    def format_log_lines(self, pkt) -> list[str]:
        return _log_format.format_log_lines(pkt)

    def is_unknown_packet(self, parsed) -> bool:
        return _log_format.is_unknown_packet(self._md(parsed))

    # -- Resolution contract --

    @property
    def gs_node(self) -> int:
        return GS_NODE

    def node_name(self, node_id: int) -> str:
        from mav_gss_lib.missions.maveric.wire_format import node_name as _wire_node_name
        return _wire_node_name(node_id)

    def ptype_name(self, ptype_id: int) -> str:
        from mav_gss_lib.missions.maveric.wire_format import ptype_name as _wire_ptype_name
        return _wire_ptype_name(ptype_id)

    def node_label(self, node_id: int) -> str:
        from mav_gss_lib.missions.maveric.wire_format import node_label
        return node_label(node_id)

    def ptype_label(self, ptype_id: int) -> str:
        from mav_gss_lib.missions.maveric.wire_format import ptype_label
        return ptype_label(ptype_id)

    def resolve_node(self, s: str) -> int | None:
        from mav_gss_lib.missions.maveric.wire_format import resolve_node
        return resolve_node(s)

    def resolve_ptype(self, s: str) -> int | None:
        from mav_gss_lib.missions.maveric.wire_format import resolve_ptype
        return resolve_ptype(s)

    def parse_cmd_line(self, line: str) -> tuple:
        from mav_gss_lib.missions.maveric.wire_format import parse_cmd_line
        return parse_cmd_line(line)

    def tx_queue_columns(self): return _rendering.tx_queue_columns()

    def cmd_line_to_payload(self, line: str) -> dict:
        """Convert raw CLI text to a payload dict for build_tx_command.

        Handles two input formats:
        - Shortcut: CMD_ID [ARGS]  (when cmd_id has routing defaults in schema)
        - Full:     [SRC] DEST ECHO TYPE CMD_ID [ARGS]

        Returns: {cmd_id, args, dest, echo, ptype[, src]} for build_tx_command.
        Only includes 'src' when explicitly provided in full format.
        Raises ValueError on parse failure or unknown command.
        """
        return tx_ops.cmd_line_to_payload(line, self.cmd_defs)

    # -- Plugin hook --

    def on_packet_received(self, pkt) -> list[dict] | None:
        """Feed image chunks to the assembler and return progress messages."""
        if not self.image_assembler:
            return None
        md = self._md(pkt)
        cmd = md.get("cmd")
        if not cmd:
            return None

        cmd_id = cmd.get("cmd_id", "")
        if cmd_id not in ("img_cnt_chunks", "img_get_chunk"):
            return None

        # Extract args from typed_args (schema match) or raw args
        if cmd.get("schema_match") and cmd.get("typed_args"):
            args_by_name = {ta["name"]: ta.get("value", "") for ta in cmd["typed_args"]}
        else:
            return None  # can't extract without schema

        # RX arg names from commands.yml:
        #   img_cnt_chunks RX: Filename, Num Chunks
        #   img_get_chunk  RX: Filename, Chunk Number, Chunk Size, Data
        filename = str(args_by_name.get("Filename", ""))
        if not filename:
            return None

        if cmd_id == "img_cnt_chunks":
            count = args_by_name.get("Num Chunks", "")
            try:
                self.image_assembler.set_total(filename, int(count))
            except (ValueError, TypeError):
                return None
        elif cmd_id == "img_get_chunk":
            chunk_num = args_by_name.get("Chunk Number", "")
            chunk_size = args_by_name.get("Chunk Size", None)
            data = args_by_name.get("Data", b"")
            if isinstance(data, str):
                try:
                    data = bytes.fromhex(data)
                except ValueError:
                    data = data.encode()
            try:
                self.image_assembler.feed_chunk(filename, int(chunk_num), data, chunk_size=chunk_size)
            except (ValueError, TypeError):
                return None

        received, total = self.image_assembler.progress(filename)
        return [{
            "type": "imaging_progress",
            "filename": filename,
            "received": received,
            "total": total,
            "complete": self.image_assembler.is_complete(filename),
        }]
