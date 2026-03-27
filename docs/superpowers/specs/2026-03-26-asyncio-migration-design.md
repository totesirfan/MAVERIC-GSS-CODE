# Asyncio Migration — MAVERIC GSS

## Purpose

Migrate all threading in MAVERIC GSS to asyncio for code simplification, better Textual framework integration, and future flexibility. Eliminates OS threads, thread-safe queues, and explicit locks in favor of cooperative async tasks running on Textual's event loop.

## Scope

**Files modified (4):**
- `mav_gss_lib/transport.py` — async ZMQ send/recv
- `mav_gss_lib/logging.py` — async log writer task
- `MAV_RX.py` — async receiver task, async cleanup
- `MAV_TX.py` — async send worker, async cleanup

**Files unchanged (7):**
- `mav_gss_lib/protocol.py` — pure computation
- `mav_gss_lib/parsing.py` — pure data transformation
- `mav_gss_lib/config.py` — startup-only I/O (before event loop)
- `mav_gss_lib/tui_common.py` — widgets/helpers
- `mav_gss_lib/tui_rx.py` — RX widgets (read-only)
- `mav_gss_lib/tui_tx.py` — TX widgets (read-only)
- `mav_gss_lib/__init__.py` — re-exports

## Design

### 1. Transport Layer (`transport.py`)

**ZMQ context:** Replace `zmq.Context()` with `zmq.asyncio.Context()`. Socket creation stays synchronous (happens in `__init__` before the event loop starts). Only `recv()`/`send()` become async.

```python
import zmq
import zmq.asyncio

def init_zmq_sub(addr, timeout_ms=200):
    context = zmq.asyncio.Context()
    sock = context.socket(zmq.SUB)
    # ... same socket options ...
    monitor = sock.get_monitor_socket()
    sock.connect(addr)
    return context, sock, monitor

def init_zmq_pub(addr, settle_ms=300):
    context = zmq.asyncio.Context()
    sock = context.socket(zmq.PUB)
    monitor = sock.get_monitor_socket()
    sock.bind(addr)
    time.sleep(settle_ms / 1000.0)  # Pre-event-loop, harmless
    return context, sock, monitor
```

**Async send/recv:**

```python
async def receive_pdu(sock, on_error=None):
    try:
        msg = await sock.recv()
    except zmq.Again:
        return None
    # ... PMT deserialization unchanged ...

async def send_pdu(sock, payload):
    # ... PMT serialization ...
    try:
        await sock.send(pmt.serialize_str(pmt.cons(meta, vec)))
        return True
    except zmq.ZMQError:
        return False
```

**Unchanged:** `poll_monitor()` stays synchronous — it uses `zmq.NOBLOCK` and is already non-blocking. `zmq_cleanup()` stays synchronous (shutdown path).

### 2. RX Receiver (`MAV_RX.py`)

**Before:** `threading.Thread` running `_receiver_thread()`, blocking on `receive_pdu()` with 200ms timeout, feeding `queue.Queue`.

**After:** `asyncio.Task` running `_receiver_loop()`, awaiting `receive_pdu()`, feeding `asyncio.Queue`.

```python
async def _receiver_loop(sock, pkt_queue, stop_event, monitor, status_holder, on_error=None):
    while not stop_event.is_set():
        result = await receive_pdu(sock, on_error=on_error)
        if result is not None:
            await pkt_queue.put(result)
        status_holder[0] = poll_monitor(monitor, SUB_STATUS, status_holder[0])
```

**Drain in `_tick()`:** Same pattern, `asyncio.Queue.get_nowait()` replaces `queue.Queue.get_nowait()`.

**Startup:** Task created in `on_mount()` via `asyncio.create_task()`.

**Cleanup:** `_cleanup()` becomes `async def`. Cancels the task and awaits it:
```python
async def _cleanup(self):
    self._stop_event.set()
    self._rx_task.cancel()
    try:
        await self._rx_task
    except asyncio.CancelledError:
        pass
    # ... close log, cleanup ZMQ ...
```

**State changes:**
- `self._stop_event`: `threading.Event()` → `asyncio.Event()`
- `self._pkt_queue`: `queue.Queue()` → `asyncio.Queue()`
- Remove: `threading` import, `_rx_thread` reference

### 3. TX Send Worker (`MAV_TX.py`)

**Before:** `threading.Thread` per send, `threading.Lock` for state protection, `threading.Event` for abort, `time.sleep()` for delays.

**After:** `asyncio.Task` per send, `asyncio.Lock` (defense in depth), `asyncio.Event` for abort, `asyncio.sleep()` for delays.

```python
async def _send_worker(state, snapshot, delay_ms, sock):
    sent = 0
    for i, (src, dest, echo, ptype, cmd, args, raw_cmd) in enumerate(snapshot):
        if state.send_abort.is_set():
            break
        async with state.send_lock:
            state.sending["idx"] = i
        if i > 0 and delay_ms > 0:
            try:
                await asyncio.wait_for(state.send_abort.wait(), timeout=delay_ms / 1000.0)
                break  # abort was set during delay
            except asyncio.TimeoutError:
                pass  # normal: delay elapsed, continue sending
        payload = state.ax25.wrap(state.csp.wrap(raw_cmd))
        if not await send_pdu(sock, payload):
            state.status.set("ZMQ send error — aborting send", 5)
            break
        state.tx_count += 1
        sent += 1
        # ... update history, log ...
    # ... finalize ...
```

**Key improvement:** `asyncio.wait_for(abort.wait(), timeout=delay)` replaces the busy-wait sleep loop (`while remaining > 0: time.sleep(0.05)`). Abort is now instantaneous — no 50ms polling granularity.

**State changes in `TxState`:**
- `send_abort: threading.Event` → `asyncio.Event`
- `send_lock: threading.Lock` → `asyncio.Lock`

**Startup:** `_start_send()` becomes `async def`, uses `asyncio.create_task()`.

### 4. Logging (`logging.py`)

**Before:** `threading.Thread` running `_writer_loop()`, draining `queue.Queue`, writing to files with `flush()`.

**After:** `asyncio.Task` running `_writer_loop()`, draining `asyncio.Queue`, file writes via `asyncio.get_event_loop().run_in_executor()`.

```python
async def _writer_loop(self):
    loop = asyncio.get_event_loop()
    while True:
        item = await self._q.get()
        if item is self._SENTINEL:
            break
        kind, data = item
        if kind == "jsonl":
            await loop.run_in_executor(None, self._write_and_flush_jsonl, data)
        elif kind == "text":
            await loop.run_in_executor(None, self._jsonl_f.write, data)
        elif kind == "text_flush":
            await loop.run_in_executor(None, self._write_and_flush_text, data)
```

Helper methods `_write_and_flush_jsonl()` / `_write_and_flush_text()` encapsulate the write+flush into a single executor call (avoids two round-trips).

**Changes:**
- `queue.Queue` → `asyncio.Queue`
- `threading.Thread` → `asyncio.Task` (started by caller after event loop is running)
- `close()` → `async def close()`: puts sentinel, awaits task, then flushes and closes files
- `write_jsonl()` and `_write_entry()` become sync methods that put to the asyncio queue (non-blocking `put_nowait()`)
- **Init split:** File opens stay in `__init__()` (sync). New `start()` method creates the writer `asyncio.Task` — called from `on_mount()` after the event loop is running. Until `start()` is called, `write_jsonl()` / `_write_entry()` buffer to the queue (which is fine since no packets arrive before mount).

### 5. Textual App Changes

**Methods that become `async def`:**

| App | Method | Reason |
|-----|--------|--------|
| Both | `_cleanup()` | Awaits task cancellation and log close |
| Both | `action_quit_or_close()` | Awaits `_cleanup()` |
| RX | `action_close_panel()` | No — stays sync |
| RX | `_toggle_logging()` | Awaits log close |
| RX | `_on_config_done()` | Calls `_toggle_logging()` |
| TX | `action_close_or_cancel()` | No — stays sync (abort is just setting an event) |
| TX | `action_send_queue()` | Spawns async task |

**`_tick()` stays as regular `def`:** Textual's `set_interval` handles both sync and async callbacks. Since `_tick()` only does non-blocking work (queue drain with `get_nowait()`, monitor poll with `NOBLOCK`), it doesn't need to be async.

**`on_mount()`:** Starts the receiver task (RX) and the log writer task (both apps).

### 6. Removed Threading Artifacts

| Removed | Replacement |
|---------|------------|
| `import threading` (MAV_RX.py) | `import asyncio` |
| `import threading` (MAV_TX.py) | `import asyncio` (already partial) |
| `import queue` (MAV_RX.py) | `asyncio.Queue` |
| `import queue` (logging.py) | `asyncio.Queue` |
| `threading.Thread` | `asyncio.create_task()` |
| `threading.Event` | `asyncio.Event` |
| `threading.Lock` | `asyncio.Lock` |
| `queue.Queue` | `asyncio.Queue` |
| `thread.join(timeout)` | `task.cancel()` + `await task` |
| `time.sleep()` in send worker | `asyncio.sleep()` / `asyncio.wait_for()` |

### 7. Dependencies

No new dependencies. `zmq.asyncio` is part of PyZMQ (already installed). `asyncio` is stdlib.

### 8. Verification

1. `python3 -c "from mav_gss_lib import *"` — imports still work
2. `python3 -c "import zmq.asyncio"` — verify zmq.asyncio available
3. `python3 MAV_RX.py --nosplash` — launches, shows ZMQ status, receives packets if GNU Radio running
4. `python3 MAV_TX.py --nosplash` — launches, queue/send/import work, config saves on exit
5. TX: queue a command, send it (Ctrl+S), abort mid-send (Ctrl+C during send) — verify abort is instant
6. RX: verify no "WARNING: RX thread did not terminate cleanly" on exit
7. Both: verify log files are written correctly (text + JSONL)
