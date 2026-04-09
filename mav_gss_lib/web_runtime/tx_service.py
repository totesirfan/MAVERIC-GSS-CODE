"""
mav_gss_lib.web_runtime.tx_service -- TX Service

Owns the TX side of the web runtime: queue, send state, history, and ZMQ PUB.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING

from mav_gss_lib.protocols.ax25 import build_ax25_gfsk_frame
from mav_gss_lib.transport import PUB_STATUS, init_zmq_pub, send_pdu, zmq_cleanup

from ._broadcast import broadcast_safe

if TYPE_CHECKING:
    from .state import WebRuntime

try:
    from mav_gss_lib.protocols.golay import _GR_RS_OK, build_asm_golay_frame
    GOLAY_OK = _GR_RS_OK
except ImportError:
    GOLAY_OK = False


class TxService:
    """Own the TX side of the web runtime: queue, send state, and history."""

    def __init__(self, runtime: "WebRuntime") -> None:
        self.runtime = runtime
        self.clients: list = []
        self.lock = threading.Lock()
        self.log = None
        self.count = 0
        self.zmq_ctx = None
        self.zmq_sock = None
        self.zmq_monitor = None
        self.queue: list = []
        self.history: list = []
        self.sending = {"active": False, "idx": -1, "total": 0, "guarding": False, "sent_at": 0, "waiting": False}
        self.abort = threading.Event()
        self.guard_ok = threading.Event()
        self.send_lock = threading.Lock()
        self.send_task = None

    def queue_file(self):
        """Return the queue persistence file path used by this runtime."""
        return self.runtime.queue_file()

    def restart_pub(self, addr: str) -> None:
        """Recreate the TX PUB socket at *addr*."""
        if self.zmq_sock:
            try:
                zmq_cleanup(self.zmq_monitor, PUB_STATUS, self.status[0], self.zmq_sock, self.zmq_ctx)
            except Exception:
                pass
        self.zmq_ctx = self.zmq_sock = self.zmq_monitor = None
        try:
            self.zmq_ctx, self.zmq_sock, self.zmq_monitor = init_zmq_pub(addr)
            self.status[0] = "BOUND"
        except Exception as exc:
            self.status[0] = "OFFLINE"
            logging.error("TX ZMQ PUB init failed: %s", exc)

    @property
    def status(self):
        return self.runtime.tx_status

    def save_queue(self) -> None:
        """Persist the current queue to disk as JSONL."""
        from . import tx_queue as _tq
        _tq.save_queue(self.queue, self.queue_file())

    def load_queue(self):
        """Load any persisted queue items from disk."""
        from . import tx_queue as _tq
        return _tq.load_queue(self.queue_file(), runtime=self.runtime)

    def json_to_item(self, payload):
        """Convert one persisted JSON payload back into a runtime queue item."""
        from . import tx_queue as _tq
        return _tq.json_to_item(payload, runtime=self.runtime)

    def renumber_queue(self) -> None:
        """Assign sequential display numbers to queued command items."""
        from . import tx_queue as _tq
        _tq.renumber_queue(self.queue)

    def queue_summary(self):
        """Summarize queue size, guard count, and rough execution time."""
        from . import tx_queue as _tq
        return _tq.queue_summary(self.queue, self.runtime.cfg)

    def queue_items_json(self):
        """Project the current queue into the websocket/API JSON shape."""
        from . import tx_queue as _tq
        return _tq.queue_items_json(self.queue)

    async def broadcast(self, msg):
        """Broadcast one JSON-serializable message to all TX websocket clients."""
        text = json.dumps(msg) if isinstance(msg, dict) else msg
        await broadcast_safe(self.clients, self.lock, text)

    async def send_queue_update(self):
        """Broadcast the current queue plus send-state snapshot."""
        await self.broadcast({"type": "queue_update", "items": self.queue_items_json(), "summary": self.queue_summary(), "sending": self.sending.copy()})

    async def run_send(self):
        """Run the serialized TX send loop until queue exhaustion or abort."""
        if self.zmq_sock is None:
            await self.broadcast({"type": "send_error", "error": "TX ZMQ socket not initialized"})
            with self.send_lock:
                self.sending.update(active=False, idx=-1, total=0, guarding=False, sent_at=0, waiting=False)
            await self.send_queue_update()
            return

        sock = self.zmq_sock
        with self.runtime.cfg_lock:
            uplink_mode = self.runtime.cfg.get("tx", {}).get("uplink_mode", "AX.25")
            default_delay = self.runtime.cfg.get("tx", {}).get("delay_ms", 500)
            send_csp = copy.copy(self.runtime.csp)
            send_ax25 = copy.copy(self.runtime.ax25)

        sent = 0
        total = self.sending.get("total", len(self.queue))
        prev_was_cmd = False

        try:
            while not self.abort.is_set():
                with self.send_lock:
                    if not self.queue:
                        break
                    item = self.queue[0]
                    self.sending["idx"] = 0
                    self.sending["waiting"] = False

                await self.send_queue_update()

                if item["type"] == "note":
                    with self.send_lock:
                        if self.queue:
                            self.queue.pop(0)
                        self.save_queue()
                    continue

                if item["type"] == "delay":
                    with self.send_lock:
                        self.sending["sent_at"] = 0
                        self.sending["waiting"] = True
                    await self.broadcast({"type": "send_progress", "sent": sent, "total": total, "current": f"delay {item['delay_ms']}ms", "waiting": True})
                    prev_was_cmd = False
                    remaining_ms = item["delay_ms"]
                    while remaining_ms > 0 and not self.abort.is_set():
                        await asyncio.sleep(0.1)
                        remaining_ms -= 100
                    with self.send_lock:
                        self.sending["waiting"] = False
                    if self.abort.is_set():
                        break
                    with self.send_lock:
                        if self.queue:
                            self.queue.pop(0)
                        self.renumber_queue()
                        self.save_queue()
                    continue

                if prev_was_cmd and default_delay > 0:
                    with self.send_lock:
                        self.sending["waiting"] = True
                    remaining_ms = default_delay
                    while remaining_ms > 0 and not self.abort.is_set():
                        await asyncio.sleep(0.1)
                        remaining_ms -= 100
                    with self.send_lock:
                        self.sending["waiting"] = False
                    if self.abort.is_set():
                        break

                if item.get("guard"):
                    with self.send_lock:
                        self.sending["guarding"] = True
                    self.guard_ok.clear()
                    display = item.get("display", {})
                    await self.broadcast({
                        "type": "guard_confirm", "index": 0,
                        "display": display,
                    })
                    while not self.guard_ok.is_set() and not self.abort.is_set():
                        await asyncio.sleep(0.1)
                    with self.send_lock:
                        self.sending["guarding"] = False
                    if self.abort.is_set():
                        break

                raw_cmd = item.get("raw_cmd", b"")
                if not raw_cmd:
                    await self.broadcast({"type": "send_error", "error": f"empty raw_cmd for {item.get('display', {}).get('title', '?')}"})
                    with self.send_lock:
                        if self.queue:
                            self.queue.pop(0)
                        self.renumber_queue()
                        self.save_queue()
                    break

                try:
                    csp_packet = send_csp.wrap(raw_cmd)
                    if uplink_mode == "ASM+Golay" and GOLAY_OK:
                        payload = build_asm_golay_frame(csp_packet)
                    else:
                        ax25_frame = send_ax25.wrap(csp_packet)
                        payload = build_ax25_gfsk_frame(ax25_frame)
                except Exception as exc:
                    logging.error("Frame build failed for %s: %s", item.get("cmd", "?"), exc)
                    await self.broadcast({"type": "send_error", "error": f"frame build failed: {exc}"})
                    with self.send_lock:
                        if self.queue:
                            self.queue.pop(0)
                        self.renumber_queue()
                        self.save_queue()
                    break

                if not send_pdu(sock, payload):
                    logging.error("ZMQ send failed for %s", item.get("cmd", "?"))
                    await self.broadcast({"type": "send_error", "error": "ZMQ send failed"})
                    with self.send_lock:
                        if self.queue:
                            self.queue.pop(0)
                        self.renumber_queue()
                        self.save_queue()
                    break

                with self.send_lock:
                    self.sending["sent_at"] = time.time()
                self.count += 1
                sent += 1

                if self.log:
                    try:
                        self.log.write_mission_command(
                            self.count,
                            item.get("display", {}),
                            item.get("payload", {}),
                            raw_cmd, payload, send_ax25, send_csp,
                            uplink_mode=uplink_mode,
                        )
                    except Exception as exc:
                        logging.warning("TX log write failed: %s", exc)

                hist_entry = {
                    "n": self.count,
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "type": "mission_cmd",
                    "display": item.get("display", {}),
                    "payload": item.get("payload", {}),
                    "size": len(payload),
                }
                self.history.append(hist_entry)
                if len(self.history) > self.runtime.max_history:
                    del self.history[: len(self.history) - self.runtime.max_history]

                await self.broadcast({"type": "sent", "data": hist_entry})
                current_label = item.get("display", {}).get("title", "?")
                await self.broadcast({"type": "send_progress", "sent": sent, "total": total, "current": current_label, "waiting": False})

                await asyncio.sleep(0.5)
                with self.send_lock:
                    if self.queue:
                        self.queue.pop(0)
                    self.sending["sent_at"] = 0
                    self.renumber_queue()
                    self.save_queue()
                prev_was_cmd = True
        finally:
            with self.send_lock:
                self.save_queue()
                self.sending.update(active=False, idx=-1, total=0, guarding=False, sent_at=0, waiting=False)

            remaining = len(self.queue)
            if self.abort.is_set():
                await self.broadcast({"type": "send_aborted", "sent": sent, "remaining": remaining})
            else:
                await self.broadcast({"type": "send_complete", "sent": sent})

            await self.send_queue_update()
            await self.broadcast({"type": "history", "items": self.history[-self.runtime.max_history :]})
