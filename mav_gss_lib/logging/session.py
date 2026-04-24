"""RX session log — JSONL + text entries for inbound platform v2 packets.

Author:  Irfan Annuar - USC ISI SERC
"""

from mav_gss_lib.constants import DEFAULT_MISSION_NAME

from ._base import _BaseLog


class SessionLog(_BaseLog):
    """RX session log — JSONL + text."""

    def __init__(self, log_dir, zmq_addr, version="", mission_name=DEFAULT_MISSION_NAME,
                 *, station: str = "", operator: str = "", host: str = ""):
        super().__init__(log_dir, "downlink", version, "RX Monitor", zmq_addr,
                         mission_name=mission_name,
                         station=station, operator=operator, host=host)

    def write_packet_v2(self, packet, text_lines=None):
        """Write one platform v2 RX packet entry."""
        lines = []
        label = f"#{packet.seq}"
        extras = f"{packet.frame_type}  {len(packet.raw)}B -> {len(packet.payload)}B"
        if packet.flags.is_duplicate:
            extras += "  [DUP]"
        if packet.flags.is_uplink_echo:
            extras += "  [UL]"
        lines.append(self._separator(label, extras))
        if packet.flags.is_uplink_echo:
            lines.append("  UPLINK ECHO")

        for warning in packet.warnings:
            lines.append(self._field("WARNING", warning))

        lines.extend(text_lines or [])
        lines.extend(self._hex_lines(packet.raw, "HEX"))

        try:
            text = packet.raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            text = ""
        if text:
            lines.append(self._field("ASCII", text))

        self._write_entry(lines)
