#!/usr/bin/env python3
"""MAV_WEB — Web dashboard for MAVERIC GSS.

Serves a React SPA and bridges ZMQ ↔ WebSocket for real-time
RX packet monitoring and TX command queue management.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── mav_gss_lib imports ──────────────────────────────────────────
from mav_gss_lib.config import load_gss_config, save_gss_config, apply_ax25, apply_csp, update_cfg_from_state
from mav_gss_lib.protocol import (
    init_nodes, load_command_defs, parse_cmd_line, build_cmd_raw,
    resolve_node, resolve_ptype, validate_args,
    CSPConfig, AX25Config, node_name, ptype_name,
)
from mav_gss_lib.transport import (
    init_zmq_sub, init_zmq_pub, receive_pdu, send_pdu,
    poll_monitor, zmq_cleanup, SUB_STATUS, PUB_STATUS,
)
from mav_gss_lib.parsing import RxPipeline, Packet, build_rx_log_record
from mav_gss_lib.logging import SessionLog, TXLog

# ── Constants ─────────────────────────────────────────────────────
WEB_DIR = Path(__file__).parent / "web" / "dist"
HOST = "127.0.0.1"
PORT = 8080
MAX_PACKETS = 500
MAX_HISTORY = 500

# ── Global state ──────────────────────────────────────────────────
cfg = load_gss_config()
init_nodes(cfg)
cmd_defs, cmd_warn = load_command_defs(cfg["general"].get("command_defs", "maveric_commands.yml"))

# ── ZMQ status holders (mutable list so threads can update) ───────
rx_status = ["OFFLINE"]
tx_status = ["OFFLINE"]

# ── Protocol objects ──────────────────────────────────────────────
csp = CSPConfig()
ax25 = AX25Config()
apply_csp(cfg, csp)
apply_ax25(cfg, ax25)

# ── RX state ──────────────────────────────────────────────────────
rx_packets: deque = deque(maxlen=MAX_PACKETS)
rx_queue: Queue = Queue()
rx_stop = threading.Event()
rx_clients: list[WebSocket] = []
rx_lock = threading.Lock()
rx_log: SessionLog | None = None

pipeline = RxPipeline(cmd_defs, {})

app = FastAPI(title="MAVERIC GSS Web")

# ── Static asset mount ────────────────────────────────────────────
if WEB_DIR.exists() and (WEB_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")


# =====================================================================
#  REST ENDPOINTS
# =====================================================================

@app.get("/api/status")
async def api_status():
    """System status: version, ZMQ, uplink mode, frequency."""
    return {
        "version": cfg.get("general", {}).get("version", ""),
        "zmq_rx": rx_status[0],
        "zmq_tx": tx_status[0],
        "uplink_mode": cfg.get("tx", {}).get("uplink_mode", "AX.25"),
        "frequency": cfg.get("tx", {}).get("frequency", ""),
    }


@app.get("/api/config")
async def api_config_get():
    """Return full config dict."""
    return cfg


@app.put("/api/config")
async def api_config_put(update: dict):
    """Partial config update — deep-merge, save, re-apply protocol objects."""
    def _deep_merge(base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                _deep_merge(base[k], v)
            else:
                base[k] = v

    _deep_merge(cfg, update)
    save_gss_config(cfg)
    apply_csp(cfg, csp)
    apply_ax25(cfg, ax25)
    return {"ok": True}


@app.get("/api/schema")
async def api_schema():
    """Return command schema definitions."""
    return cmd_defs


@app.get("/api/logs")
async def api_logs():
    """List log sessions from logs/json/*.jsonl, sorted by mtime descending."""
    log_dir = Path(cfg.get("general", {}).get("log_dir", "logs")) / "json"
    if not log_dir.is_dir():
        return []
    sessions = []
    for p in log_dir.glob("*.jsonl"):
        sessions.append({
            "session_id": p.stem,
            "filename": p.name,
            "size": p.stat().st_size,
            "mtime": p.stat().st_mtime,
        })
    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


@app.get("/api/logs/{session_id}")
async def api_log_entries(
    session_id: str,
    cmd: Optional[str] = None,
    time_from: Optional[float] = Query(None, alias="from"),
    time_to: Optional[float] = Query(None, alias="to"),
):
    """Return filtered entries from a log session."""
    log_dir = Path(cfg.get("general", {}).get("log_dir", "logs")) / "json"
    log_file = log_dir / f"{session_id}.jsonl"
    if not log_file.is_file():
        return JSONResponse(status_code=404, content={"error": "session not found"})
    entries = []
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Filter by command name
            if cmd and entry.get("cmd", {}).get("cmd_id") != cmd.lower():
                continue
            # Filter by time range
            if time_from is not None or time_to is not None:
                ts = entry.get("gs_ts", "")
                try:
                    dt = datetime.strptime(ts.rsplit(" ", 1)[0], "%Y-%m-%d %H:%M:%S")
                    epoch = dt.timestamp()
                    if time_from is not None and epoch < time_from:
                        continue
                    if time_to is not None and epoch > time_to:
                        continue
                except (ValueError, IndexError):
                    pass
            entries.append(entry)
    return entries


# =====================================================================
#  RX WEBSOCKET
# =====================================================================

def _rx_thread():
    """Background thread: ZMQ SUB -> rx_queue."""
    addr = cfg.get("rx", {}).get("zmq_addr", "tcp://127.0.0.1:52001")
    try:
        ctx, sock, monitor = init_zmq_sub(addr)
    except Exception as e:
        logging.error("RX ZMQ init failed: %s", e)
        return

    status = "OFFLINE"
    while not rx_stop.is_set():
        status = poll_monitor(monitor, SUB_STATUS, status)
        rx_status[0] = status
        result = receive_pdu(sock)
        if result is not None:
            rx_queue.put(result)

    zmq_cleanup(monitor, SUB_STATUS, status, sock, ctx)


def _packet_to_json(pkt: Packet) -> dict:
    """Convert a Packet dataclass to a JSON-serializable dict."""
    cmd = pkt.cmd
    d = {
        "num": pkt.pkt_num,
        "time": pkt.gs_ts,
        "time_utc": pkt.gs_ts,
        "frame": pkt.frame_type,
        "src": node_name(cmd["src"]) if cmd else "",
        "dest": node_name(cmd["dest"]) if cmd else "",
        "echo": node_name(cmd["echo"]) if cmd else "",
        "ptype": ptype_name(cmd["pkt_type"]) if cmd else "",
        "cmd": cmd["cmd_id"] if cmd else "",
        "args": "",
        "size": len(pkt.raw),
        "crc16_ok": cmd.get("crc_valid") if cmd else None,
        "crc32_ok": pkt.crc_status.get("csp_crc32_valid"),
        "is_echo": pkt.is_uplink_echo,
        "is_dup": pkt.is_dup,
        "is_unknown": pkt.is_unknown,
        "raw_hex": pkt.raw.hex(),
        "warnings": pkt.warnings,
        "csp_header": pkt.csp,
        "ax25_header": pkt.stripped_hdr,
    }
    # Format args
    if cmd and cmd.get("schema_match") and cmd.get("typed_args"):
        parts = []
        for ta in cmd["typed_args"]:
            if ta["type"] == "epoch_ms" and hasattr(ta["value"], "ms"):
                parts.append(str(ta["value"].ms))
            elif ta["type"] == "epoch_ms" and isinstance(ta["value"], dict) and "ms" in ta["value"]:
                parts.append(str(ta["value"]["ms"]))
            else:
                parts.append(str(ta["value"]))
        d["args"] = " ".join(parts)
    elif cmd:
        d["args"] = " ".join(cmd.get("args", []))
    return d


async def _rx_broadcast():
    """Async coroutine: drain rx_queue, process via pipeline, broadcast JSON."""
    last_status_push = 0.0
    while True:
        drained = 0
        while True:
            try:
                meta, raw = rx_queue.get_nowait()
            except Empty:
                break
            pkt = pipeline.process(meta, raw)
            pkt_json = _packet_to_json(pkt)
            rx_packets.append(pkt_json)
            msg = json.dumps({"type": "packet", "data": pkt_json})
            with rx_lock:
                dead = []
                for ws in rx_clients:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    rx_clients.remove(ws)
            drained += 1

        # Periodic status push (every 2 seconds when idle)
        now = time.time()
        if drained == 0 and now - last_status_push > 2.0:
            last_status_push = now
            status_msg = json.dumps({
                "type": "status",
                "data": {
                    "zmq_rx": rx_status[0],
                    "zmq_tx": tx_status[0],
                    "packet_count": pipeline.packet_count,
                    "unknown_count": pipeline.unknown_count,
                    "echo_count": pipeline.uplink_echo_count,
                },
            })
            with rx_lock:
                dead = []
                for ws in rx_clients:
                    try:
                        await ws.send_text(status_msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    rx_clients.remove(ws)

        await asyncio.sleep(0.05)


@app.websocket("/ws/rx")
async def ws_rx(websocket: WebSocket):
    """RX WebSocket: send packet backlog, then stream live updates."""
    await websocket.accept()
    # Send backlog
    for pkt_json in list(rx_packets):
        try:
            await websocket.send_text(json.dumps({"type": "packet", "data": pkt_json}))
        except Exception:
            return
    with rx_lock:
        rx_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive / client pings
    except WebSocketDisconnect:
        pass
    finally:
        with rx_lock:
            if websocket in rx_clients:
                rx_clients.remove(websocket)


@app.on_event("startup")
async def on_startup():
    """Start RX ZMQ thread and broadcast coroutine."""
    t = threading.Thread(target=_rx_thread, daemon=True)
    t.start()
    asyncio.create_task(_rx_broadcast())


# ── SPA catch-all (MUST be last) ─────────────────────────────────
if WEB_DIR.exists():
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        file_path = WEB_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIR / "index.html")

# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"MAVERIC GSS Web → http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
