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

from mav_gss_lib.missions.maveric import rendering as _rendering, rx_ops, tx_ops
from mav_gss_lib.missions.maveric import log_format as _log_format
from mav_gss_lib.missions.maveric.display_helpers import md as _md_helper, ptype_of as _ptype_of
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.web_runtime.telemetry import TelemetryFragment


# =============================================================================
#  MAVERIC MISSION ADAPTER
# =============================================================================


@dataclass
class MavericMissionAdapter:
    """Thin boundary around current MAVERIC protocol behavior.

    Owns explicit references to all mission state: cmd_defs, nodes,
    image_assembler. Per-domain telemetry state lives in the platform
    router at `self.telemetry`, populated by the extractors at
    `self.extractors` from every parsed packet. No per-domain store
    attributes, no module globals.
    """

    cmd_defs: dict
    nodes: NodeTable
    image_assembler: object = None
    # Attached post-construction by load_mission_adapter (Task 4a);
    # populated by WebRuntime.__init__ (Task 5). Declared here so the
    # dataclass advertises the full shape of the adapter surface.
    telemetry: object = None          # TelemetryRouter
    extractors: tuple = ()            # tuple[Callable, ...]

    def detect_frame_type(self, meta) -> str:
        return rx_ops.detect(meta)

    def normalize_frame(self, frame_type: str, raw: bytes):
        return rx_ops.normalize(frame_type, raw)

    def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None):
        return rx_ops.parse_packet(inner_payload, self.cmd_defs, warnings)

    def duplicate_fingerprint(self, parsed):
        return rx_ops.duplicate_fingerprint(_md_helper(parsed))

    def is_uplink_echo(self, cmd) -> bool:
        from mav_gss_lib.mission_adapter import ParsedPacket
        md = _md_helper(cmd) if isinstance(cmd, ParsedPacket) else {"cmd": cmd}
        return rx_ops.is_uplink_echo(md, self.nodes.gs_node)

    def build_tx_command(self, payload):
        """Build a mission command from structured input.

        Accepts: {cmd_id, args: str | {name: value, ...}, src?, dest, echo, ptype, guard?}
        Returns: {raw_cmd: bytes, display: dict, guard: bool}
        Raises ValueError on validation failure.
        """
        return tx_ops.build_tx_command(payload, self.cmd_defs, self.nodes)

    # -- Rendering-slot contract --

    def packet_list_columns(self): return _rendering.packet_list_columns()
    def packet_list_row(self, pkt): return _rendering.packet_list_row(pkt, self.nodes)
    def protocol_blocks(self, pkt): return _rendering.protocol_blocks(pkt)
    def integrity_blocks(self, pkt): return _rendering.integrity_blocks(pkt)
    def packet_detail_blocks(self, pkt): return _rendering.packet_detail_blocks(pkt, self.nodes)

    # -- Logging-slot contract --

    def build_log_mission_data(self, pkt) -> dict:
        return _log_format.build_log_mission_data(pkt)

    def format_log_lines(self, pkt) -> list[str]:
        return _log_format.format_log_lines(pkt, self.nodes)

    def is_unknown_packet(self, parsed) -> bool:
        return _log_format.is_unknown_packet(_md_helper(parsed))

    # -- Resolution contract --

    @property
    def gs_node(self) -> int:
        return self.nodes.gs_node

    def node_name(self, node_id: int) -> str:
        return self.nodes.node_name(node_id)

    def ptype_name(self, ptype_id: int) -> str:
        return self.nodes.ptype_name(ptype_id)

    def resolve_node(self, s: str) -> int | None:
        return self.nodes.resolve_node(s)

    def resolve_ptype(self, s: str) -> int | None:
        return self.nodes.resolve_ptype(s)

    def parse_cmd_line(self, line: str) -> tuple:
        from mav_gss_lib.missions.maveric.cmd_parser import parse_cmd_line
        return parse_cmd_line(line, self.nodes)

    def tx_queue_columns(self): return _rendering.tx_queue_columns()

    def cmd_line_to_payload(self, line: str) -> dict:
        """Convert raw CLI text to a payload dict for build_tx_command."""
        return tx_ops.cmd_line_to_payload(line, self.cmd_defs, self.nodes)

    # -- Plugin hooks --

    def attach_fragments(self, pkt) -> list[TelemetryFragment]:
        """Run mission extractors against pkt, attach the serialized fragment
        list to pkt.mission_data["fragments"], and return the raw list.

        Called by rx_service.broadcast_loop AFTER pipeline.process(meta, raw)
        and BEFORE build_rx_log_record(pkt, ...). The ordering is mandatory:
        log formatter, JSONL serializer, and _rendering snapshot all run
        inside build_rx_log_record + its adapter hooks and need fragments
        to be on the packet by then. Attaching from on_packet_received (the
        post-broadcast hook) is too late — those consumers would see no
        fragments.

        Always set the dict key (even to []) so consumers don't need to
        distinguish "no fragments" from "key missing".

        Derives ``ts_result`` from a ``spacecraft.time`` fragment when the
        command-level schema path didn't set one (the new binary beacon
        has no ``epoch_ms`` typed_arg). Keeps the Time block's SAT UTC
        / SAT Local rows and the text log's ``SAT TIME`` line available
        for every packet that carries a spacecraft clock.
        """
        import time
        from datetime import datetime, timezone
        now_ms = int(time.time() * 1000)
        frags: list[TelemetryFragment] = []
        for extract in self.extractors:
            frags.extend(extract(pkt, self.nodes, now_ms))
        pkt.mission_data["fragments"] = [f.to_dict() for f in frags]

        if pkt.mission_data.get("ts_result") is None:
            for f in frags:
                if f.domain != "spacecraft" or f.key != "time":
                    continue
                unix_ms = f.value.get("unix_ms") if isinstance(f.value, dict) else None
                if unix_ms is None:
                    break
                try:
                    dt_utc = datetime.fromtimestamp(unix_ms / 1000.0, tz=timezone.utc)
                    dt_local = dt_utc.astimezone()
                except (OSError, OverflowError, ValueError):
                    break
                pkt.mission_data["ts_result"] = (dt_utc, dt_local, unix_ms)
                break

        return frags

    def on_packet_received(self, pkt) -> list[dict] | None:
        """Emit custom WS messages for plugin consumers.

        Fragments were extracted and attached earlier in the pipeline by
        rx_service calling self.attach_fragments(pkt). Re-hydrate the
        dicts into TelemetryFragment and hand them to the router. Running
        self.extractors again here would be a double-decode.

        Imaging progress messaging is unchanged and lives behind
        self._image_messages(pkt).
        """
        fragments_data = pkt.mission_data.get("fragments") or []
        frags = [TelemetryFragment(**d) for d in fragments_data]
        messages: list[dict] = self.telemetry.ingest(frags) if frags else []
        img = self._image_messages(pkt) if self.image_assembler else None
        if img:
            messages.extend(img)
        return messages or None

    def _image_messages(self, pkt) -> list[dict] | None:
        """Imaging-plugin message generation, unchanged behavior.

        Returns a list of imaging_progress messages (possibly empty),
        or None if the packet is not an imaging command at all. Cut
        verbatim from the previous on_packet_received body.
        """
        md = _md_helper(pkt)
        cmd = md.get("cmd") or {}
        cmd_id = cmd.get("cmd_id", "")
        if cmd_id not in ("img_cnt_chunks", "img_get_chunk", "cam_capture_imgs"):
            return None

        # Only feed the assembler from the real satellite response — skip
        # uplink echoes (CMD) and ACKs, whose wire args alias rx_args and
        # would poison chunk 0 before the real data arrives.
        expected_ptype = "FILE" if cmd_id == "img_get_chunk" else "RES"
        if self.nodes.ptype_name(_ptype_of(md)) != expected_ptype:
            return None

        if cmd.get("schema_match") and cmd.get("typed_args"):
            args_by_name = {ta["name"]: ta.get("value", "") for ta in cmd["typed_args"]}
        else:
            return None

        def _progress_msg(fn: str) -> dict:
            received, total = self.image_assembler.progress(fn)
            return {
                "type": "imaging_progress",
                "filename": fn,
                "received": received,
                "total": total,
                "complete": self.image_assembler.is_complete(fn),
            }

        messages: list[dict] = []

        if cmd_id in ("img_cnt_chunks", "cam_capture_imgs"):
            # Four-field paired response: full filename + count, optional
            # thumb filename + count. Populate whichever sides are present.
            full_fn = str(args_by_name.get("Filename", ""))
            if full_fn:
                try:
                    self.image_assembler.set_total(full_fn, int(args_by_name.get("Num Chunks", "")))
                    messages.append(_progress_msg(full_fn))
                except (ValueError, TypeError):
                    pass

            thumb_fn = str(args_by_name.get("Thumb Filename", ""))
            if thumb_fn:
                try:
                    self.image_assembler.set_total(thumb_fn, int(args_by_name.get("Thumb Num Chunks", "")))
                    messages.append(_progress_msg(thumb_fn))
                except (ValueError, TypeError):
                    pass

            return messages

        # img_get_chunk: unchanged per-chunk blob path (single filename).
        filename = str(args_by_name.get("Filename", ""))
        if not filename:
            return None

        chunk_num = args_by_name.get("Chunk Number", "")
        chunk_size = args_by_name.get("Chunk Size", None)
        data = args_by_name.get("Data", b"")
        if isinstance(data, str):
            try:
                data = bytes.fromhex(data)
            except ValueError:
                data = data.encode()
        # Truncate to declared Chunk Size — the OBC appends a trailing NUL
        # to each blob (C-string terminator) that the generic blob parser
        # otherwise includes in the chunk data.
        try:
            size_int = int(chunk_size) if chunk_size is not None else len(data)
        except (ValueError, TypeError):
            size_int = len(data)
        data = data[:size_int]
        try:
            self.image_assembler.feed_chunk(filename, int(chunk_num), data, chunk_size=chunk_size)
        except (ValueError, TypeError):
            return None

        messages.append(_progress_msg(filename))
        return messages

    # -- Client connect hook --
    #
    # Called by `web_runtime.rx` after a fresh /ws/rx client has been
    # sent the packet history but before live broadcasts begin.
    # Returns a list of synthetic WS messages that bring the client's
    # plugin state up to last-known — replaces the prior REST-seed
    # pattern so consumers see one ordered stream instead of racing
    # a REST response against the live subscription.
    def on_client_connect(self) -> list[dict]:
        return list(self.telemetry.replay())
