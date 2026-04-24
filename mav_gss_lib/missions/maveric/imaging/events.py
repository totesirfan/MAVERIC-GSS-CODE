"""Imaging-plugin event source.

Watches inbound packets for the three imaging commands
(`img_cnt_chunks`, `img_get_chunks`, `cam_capture`), drives the
`ImageAssembler` state (registering totals and feeding chunks) and
returns progress messages for the platform to broadcast to connected
websocket clients.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from mav_gss_lib.missions.maveric.ui.formatters import ptype_of
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.platform import PacketEnvelope


@dataclass(slots=True)
class MavericImagingEvents:
    nodes: NodeTable
    image_assembler: Any

    def on_packet(self, packet: PacketEnvelope) -> Iterable[dict[str, Any]]:
        mission_data = packet.mission_payload if isinstance(packet.mission_payload, dict) else {}
        cmd = mission_data.get("cmd") or {}
        cmd_id = cmd.get("cmd_id", "")
        if cmd_id not in ("img_cnt_chunks", "img_get_chunks", "cam_capture"):
            return []

        expected = "FILE" if cmd_id == "img_get_chunks" else "RES"
        if self.nodes.ptype_name(ptype_of(mission_data)) != expected:
            return []

        if not cmd.get("schema_match") or not cmd.get("typed_args"):
            return []
        args_by_name = {ta["name"]: ta.get("value", "") for ta in cmd["typed_args"]}

        if cmd_id in ("img_cnt_chunks", "cam_capture"):
            return self._chunk_count_messages(args_by_name)
        return self._chunk_data_messages(args_by_name)

    def on_client_connect(self) -> Iterable[dict[str, Any]]:
        """Replay current per-file progress so a fresh client sees live state
        without a separate REST roundtrip to /api/plugins/imaging/status."""
        return [self._progress_msg(fn) for fn in self.image_assembler.known_filenames()]

    def _progress_msg(self, filename: str) -> dict[str, Any]:
        received, total = self.image_assembler.progress(filename)
        return {
            "type": "imaging_progress",
            "filename": filename,
            "received": received,
            "total": total,
            "complete": self.image_assembler.is_complete(filename),
        }

    def _chunk_count_messages(self, args_by_name: dict[str, Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for filename_key, total_key in (
            ("Filename", "Num Chunks"),
            ("Thumb Filename", "Thumb Num Chunks"),
        ):
            filename = str(args_by_name.get(filename_key, ""))
            if not filename:
                continue
            try:
                self.image_assembler.set_total(filename, int(args_by_name.get(total_key, "")))
            except (ValueError, TypeError):
                continue
            messages.append(self._progress_msg(filename))
        return messages

    def _chunk_data_messages(self, args_by_name: dict[str, Any]) -> list[dict[str, Any]]:
        filename = str(args_by_name.get("Filename", ""))
        if not filename:
            return []

        data = args_by_name.get("Data", b"")
        if isinstance(data, str):
            try:
                data = bytes.fromhex(data)
            except ValueError:
                data = data.encode()

        chunk_size = args_by_name.get("Chunk Size", None)
        try:
            size_int = int(chunk_size) if chunk_size is not None else len(data)
        except (ValueError, TypeError):
            size_int = len(data)
        data = data[:size_int]

        try:
            self.image_assembler.feed_chunk(
                filename,
                int(args_by_name.get("Chunk Number", "")),
                data,
                chunk_size=chunk_size,
            )
        except (ValueError, TypeError):
            return []
        return [self._progress_msg(filename)]
