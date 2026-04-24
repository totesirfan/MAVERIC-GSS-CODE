"""TX session log — JSONL + text entries for outbound mission commands.

Author:  Irfan Annuar - USC ISI SERC
"""

from datetime import datetime

from mav_gss_lib.constants import DEFAULT_MISSION_NAME
from mav_gss_lib.textutil import clean_text

from ._base import _BaseLog


class TXLog(_BaseLog):
    """TX session log — JSONL + text."""

    def __init__(self, log_dir, zmq_addr, version="", mission_name=DEFAULT_MISSION_NAME,
                 *, station: str = "", operator: str = "", host: str = ""):
        super().__init__(log_dir, "uplink", version, "TX Dashboard", zmq_addr,
                         mission_name=mission_name,
                         station=station, operator=operator, host=host)

    def write_mission_command(self, n, display, mission_payload,
                              raw_cmd, payload,
                              *, frame_label="", log_fields=None, log_text=None,
                              operator="", station=""):
        """Write one mission-built TX command entry.

        `frame_label`, `log_fields`, and `log_text` are provided by the
        mission's framer (platform.FramedCommand). The platform writes the
        envelope (separator, command title, RAW CMD / FULL HEX / ASCII dumps,
        JSONL metadata); mission banner lines are inserted verbatim; mission
        metadata is merged into the JSONL record.
        """
        title = display.get("title", "?")
        subtitle = display.get("subtitle", "")
        log_fields = dict(log_fields or {})
        log_text = list(log_text or [])

        lines = [self._separator(f"#{n}", subtitle)]
        if frame_label:
            lines.append(self._field("MODE", frame_label))
        lines.append(self._field("COMMAND", title))
        for block in display.get("detail_blocks", []):
            for field in block.get("fields", []):
                lines.append(self._field(field["name"].upper(), str(field["value"])))
        lines.extend(log_text)
        lines.extend(self._hex_lines(raw_cmd, "RAW CMD"))
        lines.extend(self._hex_lines(payload, "FULL HEX"))
        ascii_text = clean_text(raw_cmd)
        if ascii_text:
            lines.append(self._field("ASCII", ascii_text))

        self._write_entry(lines)

        rec = {
            "n": n, "ts": datetime.now().astimezone().isoformat(),
            "type": "mission_cmd",
            "operator": operator, "station": station,
            "display": display,
            "mission_payload": mission_payload,
            "raw_hex": raw_cmd.hex(), "raw_len": len(raw_cmd),
            "hex": payload.hex(), "len": len(payload),
        }
        if frame_label:
            rec["frame_label"] = frame_label
        # Legacy JSONL field — preserve `uplink_mode` for replay compatibility
        # when the mission populates it.
        if "uplink_mode" in log_fields:
            rec["uplink_mode"] = log_fields["uplink_mode"]
        for key, value in log_fields.items():
            if key in ("uplink_mode",):
                continue
            rec[key] = value
        self.write_jsonl(rec)
