"""
mav_gss_lib.server.rx.service -- RX Service

Owns RX orchestration: ZMQ SUB → ingest records → decode → projections → UI.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from pathlib import Path
from queue import Empty
from typing import TYPE_CHECKING, Any

from mav_gss_lib.config import get_rx_zmq_addr

from .._atomics import AtomicStatus
from mav_gss_lib.platform.rx.frame_detect import detect_frame_type, is_noise_frame
from mav_gss_lib.platform.rx.records import RxIngestRecord, make_ingest_record
from mav_gss_lib.transport import SUB_STATUS, init_zmq_sub, poll_monitor, receive_pdu, zmq_cleanup

from .._broadcast import broadcast_safe
from .detail_store import RxDetailStore
from .events import rx_batch_event
from .journal import RxIngestJournal
from .projections import RxProjectionDeps, RxProjectionRunner
from .queueing import DropOldestQueue

if TYPE_CHECKING:
    from ..state import WebRuntime


class RxService:
    """Own RX transport, decode scheduling, projection fanout, and UI clients."""

    RX_QUEUE_MAX = 20_000

    def __init__(self, runtime: "WebRuntime") -> None:
        self.runtime = runtime
        self.status = AtomicStatus()
        self.detail_store = RxDetailStore(runtime.max_packets)
        self.queue: DropOldestQueue[Any] = DropOldestQueue(self.RX_QUEUE_MAX)
        self.stop = threading.Event()
        self.broadcast_stop = False
        self.decode_batch_limit = 1000
        self.clients: list = []
        self.lock = threading.Lock()
        self.log = None
        self.journal: RxIngestJournal | None = None
        self.thread_handle: threading.Thread | None = None
        self.broadcast_task = None
        self.pipeline = runtime.platform.rx.packet_pipeline
        self.last_rx_at: float = 0.0
        self._was_traffic_active: bool = False
        # Sliding windows for the platform alarm evaluator. Each entry is a
        # wall-clock millisecond timestamp; the evaluator filters by 60s window.
        self.crc_window: deque[int] = deque(maxlen=200)
        self.dup_window: deque[int] = deque(maxlen=200)
        # Per-container last-arrival timestamps in ms. Single source of truth
        # for "time since last received" — feeds both the container alarm
        # evaluator and the UI's freshness displays.
        self.last_arrival_ms: dict[str, int] = {}
        self._last_cache_flush = 0.0
        self.projections = RxProjectionRunner(RxProjectionDeps(
            runtime=runtime,
            last_arrival_ms=self.last_arrival_ms,
            crc_window=self.crc_window,
            dup_window=self.dup_window,
            get_rx_log=lambda: self.log,
            get_tx_log=lambda: self.runtime.tx.log,
        ))

    def open_journal(self, session_id: str) -> None:
        self.close_journal()
        path = Path(self.runtime.log_dir) / "rx" / f"{session_id}.rxj"
        self.journal = RxIngestJournal(path)

    def rename_journal(self, session_id: str) -> None:
        path = Path(self.runtime.log_dir) / "rx" / f"{session_id}.rxj"
        if self.journal is None:
            self.journal = RxIngestJournal(path)
            return
        self.journal.rename(path)

    def close_journal(self) -> None:
        if self.journal is None:
            return
        self.journal.close()
        self.journal = None

    def _should_drop_rx(self, now: float) -> bool:
        """Return True if *now* is inside the TX→RX blackout window.

        Reads ``runtime.tx_blackout_until`` without locking — plain float
        reads/writes are GIL-atomic on CPython, which is sufficient here.
        Matches a real deaf radio: the packet is dropped before the pipeline
        sees it, so rate/silence counters behave as if nothing arrived.
        """
        return now < self.runtime.tx_blackout_until

    def _should_drop_noise(self, meta: dict[str, Any], raw: bytes) -> bool:
        """Return True for gr-satellites AX.25 noise frames.

        Delegates to is_noise_frame after resolving the frame type from
        transport metadata. Mirrors _should_drop_rx: called before any
        state mutation so a dropped frame produces no side effects.
        """
        frame_type = detect_frame_type(meta)
        return is_noise_frame(frame_type, raw)

    def start_receiver(self) -> None:
        if self.thread_handle and self.thread_handle.is_alive():
            return
        self.stop.clear()
        self.thread_handle = threading.Thread(
            target=self._thread,
            daemon=True,
            name=f"{self.runtime.mission_id}-rx-sub",
        )
        self.thread_handle.start()

    def restart_receiver(self) -> None:
        self.stop.set()
        if self.thread_handle:
            self.thread_handle.join(timeout=1.0)
        self.stop.clear()
        self.thread_handle = threading.Thread(
            target=self._thread,
            daemon=True,
            name=f"{self.runtime.mission_id}-rx-sub",
        )
        self.thread_handle.start()

    def _thread(self) -> None:
        addr = get_rx_zmq_addr(self.runtime.platform_cfg)
        try:
            ctx, sock, monitor = init_zmq_sub(addr)
        except Exception as exc:
            logging.error("RX ZMQ init failed: %s", exc)
            return

        status = "OFFLINE"
        while not self.stop.is_set():
            status = poll_monitor(monitor, SUB_STATUS, status)
            self.status.set(status)
            result = receive_pdu(sock)
            if result is not None:
                received_at = time.time()
                received_mono_ns = time.monotonic_ns()
                if self._should_drop_rx(received_at):
                    continue  # deaf during TX→RX blackout window
                meta, raw = result
                self.queue.put(make_ingest_record(
                    self.runtime.session.session_generation,
                    meta,
                    raw,
                    received_at_ms=int(received_at * 1000),
                    received_mono_ns=received_mono_ns,
                ))

        zmq_cleanup(monitor, SUB_STATUS, status, sock, ctx)

    def _coerce_ingest(self, item: Any) -> RxIngestRecord:
        if isinstance(item, RxIngestRecord):
            return item
        item_gen, meta, raw = item
        return make_ingest_record(item_gen, meta, raw)

    async def broadcast(self, msg: dict[str, Any] | str) -> None:
        """Broadcast one JSON-serializable message to all RX websocket clients."""
        text = json.dumps(msg, separators=(",", ":")) if isinstance(msg, dict) else msg
        await broadcast_safe(self.clients, self.lock, text)

    async def broadcast_loop(self) -> None:
        """Drain received packets and push packet/status updates to clients."""
        version = self.runtime.version
        last_status_push = 0.0
        while True:
            drained = 0
            rx_events: list[dict[str, Any]] = []
            extra_events: list[dict[str, Any]] = []
            verifier_instances: list[Any] = []
            while drained < self.decode_batch_limit:
                try:
                    ingest = self._coerce_ingest(self.queue.get_nowait())
                except Empty:
                    break
                if ingest.session_generation < self.runtime.session.session_generation:
                    # Packet arrived against a prior session generation —
                    # drop the record entirely (broadcast AND log). This is
                    # by design: a new-session swap is an operator-driven
                    # context change, and carrying stale packets forward
                    # would mix them with the new session's data stream.
                    continue
                if self._should_drop_noise(ingest.transport_meta, ingest.raw):
                    continue  # gr-satellites noise — behave as if never received
                if self.journal is not None:
                    self.journal.append(ingest)
                result = self.runtime.platform.process_rx(ingest)
                pkt = result.packet
                projection = self.projections.project(result, version=version)
                self.detail_store.append_packet(pkt)
                rx_events.append(projection.rx_event)
                extra_events.extend(projection.extra_events)
                verifier_instances.extend(projection.verifier_instances)

                # Track last RX time and detect inactive→active transition
                self.last_rx_at = pkt.received_at_ms / 1000.0
                if not self._was_traffic_active:
                    self._was_traffic_active = True
                    traffic_msg = json.dumps({"type": "traffic_status", "active": True})
                    await broadcast_safe(self.runtime.session_clients, self.runtime.session_lock, traffic_msg)

                drained += 1

            for _inst in verifier_instances:
                asyncio.create_task(self.runtime.tx.broadcast_verifier_instance(_inst))

            if rx_events:
                msg = rx_events[0] if len(rx_events) == 1 else rx_batch_event(rx_events)
                await broadcast_safe(
                    self.clients,
                    self.lock,
                    json.dumps(msg, separators=(",", ":")),
                )

            for extra in extra_events:
                await broadcast_safe(
                    self.clients,
                    self.lock,
                    json.dumps(extra, separators=(",", ":")),
                )

            if self.broadcast_stop:
                if drained == 0:
                    self.runtime.parameter_cache.flush()
                    return
                continue

            now = time.time()
            if now - self._last_cache_flush > 0.5:
                self.runtime.parameter_cache.flush()
                self._last_cache_flush = now
            # Detect active→inactive traffic transition (10s timeout)
            if self._was_traffic_active and self.last_rx_at > 0 and (now - self.last_rx_at) > 10.0:
                self._was_traffic_active = False
                traffic_msg = json.dumps({"type": "traffic_status", "active": False})
                await broadcast_safe(self.runtime.session_clients, self.runtime.session_lock, traffic_msg)

            if drained == 0 and now - last_status_push > 1.0:
                last_status_push = now
                cutoff = now - 5
                recent = sum(1 for t in self.pipeline.pkt_times if t > cutoff)
                pkt_rate = round(recent * 12, 1) if recent else 0
                silence_s = round(now - self.pipeline.last_arrival, 1) if self.pipeline.last_arrival else 0
                status_msg = json.dumps(
                    {
                        "type": "status",
                        "zmq": self.status.get(),
                        "pkt_rate": pkt_rate,
                        "silence_s": silence_s,
                        "packet_count": self.pipeline.packet_count,
                        "rx_queue_dropped": self.queue.dropped_oldest,
                        "rx_journal_dropped": (
                            self.journal.dropped_records if self.journal is not None else 0
                        ),
                    }
                )
                await broadcast_safe(self.clients, self.lock, status_msg)

            await asyncio.sleep(0.05)
