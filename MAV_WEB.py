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
from pathlib import Path
from queue import Queue, Empty

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── mav_gss_lib imports ──────────────────────────────────────────
from mav_gss_lib.config import load_gss_config, save_gss_config, apply_ax25, apply_csp, update_cfg_from_state
from mav_gss_lib.protocol import (
    init_nodes, load_command_defs, parse_cmd_line, build_cmd_raw,
    resolve_node, resolve_ptype, validate_args,
    CSPConfig, AX25Config,
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

app = FastAPI(title="MAVERIC GSS Web")

# ── Static file serving ──────────────────────────────────────────
if WEB_DIR.exists():
    if (WEB_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")

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
