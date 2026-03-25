"""
mav_gss_lib.logging -- Session Logging

File-based logging for RX and TX sessions. Handles JSONL (machine-readable)
and text (human-readable) log files with periodic flush control.

Author:  Irfan Annuar - USC ISI SERC
"""

import json
import os
import time
from datetime import datetime

from mav_gss_lib.protocol import node_label, ptype_label


# =============================================================================
#  RX SESSION LOG
# =============================================================================

class SessionLog:
    """Manages JSONL and text log file handles for one RX session."""

    def __init__(self, log_dir, zmq_addr, version="", flush_every=10):
        os.makedirs(log_dir, exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.jsonl_path = os.path.join(log_dir, f"downlink_{session_ts}.jsonl")
        self.text_path  = os.path.join(log_dir, f"downlink_{session_ts}.txt")
        self._jsonl_f = open(self.jsonl_path, "a")
        self._text_f  = open(self.text_path, "w")
        self._flush_every = flush_every
        self._writes_since_flush = 0

        self._text_f.write(f"{'='*80}\n")
        self._text_f.write(f"  MAVERIC Ground Station Log  (MAV_RX2 v{version})\n")
        self._text_f.write(f"  Session started: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
        self._text_f.write(f"  ZMQ source:      {zmq_addr}\n")
        self._text_f.write(f"{'='*80}\n\n")
        self._text_f.flush()

    def _maybe_flush(self):
        self._writes_since_flush += 1
        if self._writes_since_flush >= self._flush_every:
            self._jsonl_f.flush()
            self._text_f.flush()
            self._writes_since_flush = 0

    def write_jsonl(self, record):
        self._jsonl_f.write(json.dumps(record) + "\n")
        self._maybe_flush()

    def write_text(self, pkt_num, gs_ts, frame_type, raw, inner_payload,
                   stripped_hdr, csp, csp_plausible, ts_result, cmd, cmd_tail,
                   text, warnings, delta_t, crc_status,
                   is_dup=False, is_uplink_echo=False):
        lines = []
        if delta_t is not None:
            lines.append(f"    Delta-T: {delta_t:.3f}s")
        flags = ""
        if is_dup:
            flags += " [DUP]"
        if is_uplink_echo:
            flags += " [UL]"
        lines.append("-" * 80)
        lines.append(
            f"Packet #{pkt_num:<4} | {gs_ts} | {frame_type:<7}{flags} | "
            f"PDU: {len(raw)} B -> Payload: {len(inner_payload)} B"
        )
        for w in warnings:
            lines.append(f"  WARNING: {w}")
        if stripped_hdr:
            lines.append(f"  AX.25 HDR   {stripped_hdr}")
        if csp:
            tag = "CSP V1" if csp_plausible else "CSP V1 [UNVERIFIED]"
            lines.append(
                f"  {tag}  Prio: {csp['prio']} | Src: {csp['src']} | "
                f"Dest: {csp['dest']} | DPort: {csp['dport']} | "
                f"SPort: {csp['sport']} | Flags: 0x{csp['flags']:02x}"
            )
        if ts_result:
            dt_utc, dt_local, raw_ms = ts_result
            lines.append(
                f"  SAT TIME    {dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
                f"{dt_local.strftime('%Y-%m-%d %H:%M:%S %Z')}  (epoch-ms: {raw_ms})"
            )
        else:
            lines.append(f"  SAT TIME    --")
        if cmd:
            lines.append(
                f"  CMD         Src: {node_label(cmd['src'])} | "
                f"Dest: {node_label(cmd['dest'])} | "
                f"Echo: {node_label(cmd['echo'])} | "
                f"Type: {ptype_label(cmd['pkt_type'])}"
            )
            lines.append(f"  CMD ID      {cmd['cmd_id']}")
            if cmd.get("schema_match"):
                for ta in cmd["typed_args"]:
                    label = ta["name"].upper()
                    if ta["type"] == "epoch_ms" and isinstance(ta["value"], dict):
                        lines.append(f"  {label:<12}  {ta['value']['ms']}")
                    else:
                        lines.append(f"  {label:<12}  {ta['value']}")
                for i, extra in enumerate(cmd["extra_args"]):
                    lines.append(f"  ARG +{i}       {extra}")
            else:
                if cmd.get("schema_warning"):
                    lines.append(f"  WARNING: {cmd['schema_warning']}")
                for i, arg in enumerate(cmd['args']):
                    lines.append(f"  ARG {i}       {arg}")

        lines.append(f"  HEX         {raw.hex(' ')}")
        if text:
            lines.append(f"  ASCII       {text}")

        if cmd and cmd.get('crc') is not None:
            tag = "OK" if cmd.get("crc_valid") else "FAIL"
            lines.append(f"  CRC-16      0x{cmd['crc']:04x}  [{tag}]")
        if crc_status["csp_crc32_valid"] is not None:
            tag = "OK" if crc_status["csp_crc32_valid"] else "FAIL"
            lines.append(f"  CRC-32C     0x{crc_status['csp_crc32_rx']:08x}  [{tag}]")

        lines.append("-" * 80)
        lines.append("")
        self._text_f.write("\n".join(lines) + "\n")
        self._maybe_flush()

    def write_summary(self, packet_count, session_start, first_pkt_ts, last_pkt_ts):
        duration = time.time() - session_start
        summary = [
            "", f"{'='*80}", f"  Session Summary", f"{'='*80}",
            f"  Packets received:  {packet_count}",
            f"  Session duration:  {duration:.1f}s ({duration/60:.1f} min)",
        ]
        if first_pkt_ts and last_pkt_ts:
            summary.append(f"  First packet:      {first_pkt_ts}")
            summary.append(f"  Last packet:       {last_pkt_ts}")
        summary.append(f"{'='*80}\n")
        self._text_f.write("\n".join(summary) + "\n")
        self._text_f.flush()

    def close(self):
        self._jsonl_f.close()
        self._text_f.close()


# =============================================================================
#  TX SESSION LOG
# =============================================================================

class TXLog:
    """Manages JSONL log file for one TX session."""

    def __init__(self, log_dir):
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(log_dir, f"uplink_{ts}.jsonl")
        self._f = open(self.path, "a")

    def write(self, n, dest, dest_label, cmd, args, payload, csp_enabled):
        rec = {
            "n": n,
            "ts": datetime.now().astimezone().isoformat(),
            "dest": dest,
            "dest_lbl": dest_label,
            "cmd": cmd,
            "args": args,
            "hex": payload.hex(),
            "len": len(payload),
            "csp": csp_enabled,
        }
        self._f.write(json.dumps(rec) + "\n")
        self._f.flush()

    def close(self):
        self._f.close()
