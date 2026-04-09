# MAVERIC GSS Focused Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce module sizes, fix contract drift, consolidate scattered TX queue logic, decompose the MAVERIC adapter, add log pagination, and surgically extract tangled frontend state into hooks.

**Architecture:** No new architecture. This is a cleanup pass that moves logic into better-scoped modules without changing public contracts. The `MissionAdapter` Protocol, ZMQ transport, and component APIs all stay unchanged. Platform/mission boundary preserved — all adapter changes are internal to `missions/maveric/`.

**Tech Stack:** Python 3.10+ (FastAPI, asyncio, ZMQ), React 18 + TypeScript + Vite, Tailwind CSS

**Test commands:**
- Backend: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q`
- Frontend build: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build`
- Frontend lint: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run lint`

**Key runtime references:**
- Runtime state: `WebRuntime` in `mav_gss_lib/web_runtime/state.py` — config is `runtime.cfg` (not `.config`)
- Protocol objects: `runtime.csp` (`CSPConfig`), `runtime.ax25` (`AX25Config`)
- MTU validation: `build_send_context(runtime)` returns `(uplink_mode, send_csp, send_ax25)`; use `send_csp.wrap(raw_cmd)` for CSP wrapping
- Queue file: `runtime.queue_file()` returns `Path`
- Mission adapter: `runtime.adapter`, command defs: `runtime.cmd_defs`

**Commit strategy:** Logical checkpoints, not per-task commits:
1. After Tasks 1-2 (test fixes — green suite)
2. After Task 3 (TX queue consolidation)
3. After Tasks 4-7 (adapter split complete)
4. After Tasks 8-9 (log pagination + hook)
5. After Tasks 10-12 (remaining frontend hooks)

---

## Task 1: Fix Failing Test — Import File Comment Parsing

**Context:** `parse_import_file()` converts `//` comment lines into note items via `make_note()`. The test expects comments to be silently ignored — 2 items (mission_cmd + delay), not 3. This is a contract regression.

**Files:**
- Modify: `mav_gss_lib/web_runtime/api.py:222-226`
- Test: `tests/test_ops_web_runtime.py:81-96` (class: `TestWebRuntimeWorkflows`)

- [ ] **Step 1: Run failing test to confirm the failure**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_ops_web_runtime.py::TestWebRuntimeWorkflows::test_parse_import_file_produces_mission_cmd_items -v
```

Expected: FAIL with `AssertionError: 3 != 2`

- [ ] **Step 2: Fix the comment handling in parse_import_file**

In `mav_gss_lib/web_runtime/api.py`, change lines 222-226 from:

```python
        if line.startswith("//"):
            text = line.lstrip("/").strip()
            if text:
                items.append(make_note(text))
            continue
```

To:

```python
        if line.startswith("//"):
            continue
```

This makes `//` lines pure comments that are silently skipped, not converted to notes.

- [ ] **Step 3: Run the test to verify it passes**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_ops_web_runtime.py::TestWebRuntimeWorkflows::test_parse_import_file_produces_mission_cmd_items -v
```

Expected: PASS

- [ ] **Step 4: Run full test suite to check for regressions**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: 1 fewer failure (the other failing test is Task 2)

---

## Task 2: Fix Failing Test — Node Whitelist Validation

**Context:** `build_tx_command` in `adapter.py` has correct node-whitelist validation code at lines 171-173 that checks `defn.get("nodes", [])`. The test expects `com_ping` sent to `FTDI` to raise `ValueError`. The validation code is correct — the issue is likely that `com_ping`'s schema definition in `commands.yml` (gitignored, local only) is missing or has an empty `nodes` field.

**Files:**
- Investigate: `mav_gss_lib/missions/maveric/adapter.py:166-173`
- Investigate: `mav_gss_lib/missions/maveric/commands.yml` (gitignored — read locally only)
- Test: `tests/test_tx_plugin.py:257-268` (class: `TestMavericBuildTxCommand`)

- [ ] **Step 1: Run the failing test to confirm**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_tx_plugin.py::TestMavericBuildTxCommand::test_build_tx_command_rejects_invalid_node_for_cmd -v
```

Expected: FAIL with `AssertionError: ValueError not raised`

- [ ] **Step 2: Investigate the root cause**

The validation code at `adapter.py:171-173` is:

```python
allowed_nodes = defn.get("nodes", [])
if allowed_nodes and dest_name not in allowed_nodes:
    raise ValueError(...)
```

This only triggers if the schema definition has a non-empty `nodes` list. Check `com_ping`'s schema:

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python3 -c "
from mav_gss_lib.config import load_gss_config
from mav_gss_lib.mission_adapter import load_mission_adapter
cfg = load_gss_config()
adapter = load_mission_adapter(cfg)
defn = adapter.cmd_defs.get('com_ping', {})
print('com_ping nodes field:', defn.get('nodes', []))
print('com_ping full defn keys:', list(defn.keys()))
"
```

- [ ] **Step 3: Fix the root cause**

Based on investigation:

**If `com_ping` is missing `nodes` in `commands.yml`:** Add `nodes: [LPPM, EPS, UPPM, HLNV, ASTR]` to the `com_ping` definition in the local `mav_gss_lib/missions/maveric/commands.yml`. The test docstring says it should be valid for those nodes only.

**If the issue is case sensitivity:** `dest_name` at `adapter.py:138` is `str(payload.get("dest", ""))` preserving case. If `allowed_nodes` in the schema uses different casing, normalize the comparison at line 172. But check the actual casing first before changing code.

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_tx_plugin.py::TestMavericBuildTxCommand::test_build_tx_command_rejects_invalid_node_for_cmd -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite — should be fully green**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass (0 failures)

- [ ] **Step 6: Commit checkpoint — green test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/api.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Fix two contract regressions: import comment parsing, node whitelist
EOF
)"
```

Note: if the fix was in `commands.yml` (gitignored), only commit the code files that changed. The schema file is intentionally not tracked.

---

## Task 3: Create tx_queue.py — Extract Pure Queue Operations

**Context:** TX queue mutation logic is scattered across `api.py` (import/export), `runtime.py` (make_delay, make_note, validate_mission_cmd, sanitize_queue_items), and `services.py` (persistence, renumber, summary). This task consolidates pure queue operations into one module.

**Critical constraint:** `TxService` remains the runtime state owner — it holds `queue`, `history`, `sending`. The new module owns stateless logic only. All method signatures, return shapes, and persistence semantics must match the current code exactly.

**Files:**
- Create: `mav_gss_lib/web_runtime/tx_queue.py`
- Modify: `mav_gss_lib/web_runtime/runtime.py` (remove moved functions, re-export)
- Modify: `mav_gss_lib/web_runtime/services.py` (delegate to tx_queue)
- Modify: `mav_gss_lib/web_runtime/api.py` (import from tx_queue)
- Modify: `mav_gss_lib/web_runtime/tx.py` (import from tx_queue)

- [ ] **Step 1: Create tx_queue.py with item construction functions**

Create `mav_gss_lib/web_runtime/tx_queue.py` moving functions from `runtime.py`. These must match the current signatures and behavior exactly:

```python
"""
mav_gss_lib.web_runtime.tx_queue -- Pure TX queue operations

Item construction, validation, import/export, and persistence helpers.
TxService remains the runtime state owner (queue, history, sending).
This module owns stateless logic only.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import WebRuntime

log = logging.getLogger(__name__)

try:
    from mav_gss_lib.protocols.golay import MAX_PAYLOAD as GOLAY_MAX_PAYLOAD
except ImportError:
    GOLAY_MAX_PAYLOAD = 223


# ---------------------------------------------------------------------------
#  Item construction (moved from runtime.py)
# ---------------------------------------------------------------------------

def make_delay(delay_ms) -> dict:
    """Build one delay queue item."""
    return {"type": "delay", "delay_ms": delay_ms}


def make_note(text) -> dict:
    """Build one note queue item."""
    return {"type": "note", "text": " ".join(str(text).split())}


def make_mission_cmd(payload, adapter=None) -> dict:
    """Build one mission-command queue item via the adapter.

    Does NOT check MTU — use validate_mission_cmd() for full admission.
    """
    result = adapter.build_tx_command(payload)
    return {
        "type": "mission_cmd",
        "raw_cmd": result["raw_cmd"],
        "display": result.get("display", {}),
        "guard": result.get("guard", False),
        "payload": payload,
    }


def validate_mission_cmd(payload, runtime: "WebRuntime | None" = None) -> dict:
    """Validate and build a mission-command queue item.

    Full admission check: builds the command, then checks ASM+Golay
    payload limit via CSP wrapping if that uplink mode is active.
    """
    from .state import ensure_runtime
    from .runtime import build_send_context

    runtime = ensure_runtime(runtime)
    item = make_mission_cmd(payload, adapter=runtime.adapter)

    uplink_mode, send_csp, _send_ax25 = build_send_context(runtime)
    if uplink_mode == "ASM+Golay":
        csp_packet = send_csp.wrap(item["raw_cmd"])
        if len(csp_packet) > GOLAY_MAX_PAYLOAD:
            raise ValueError(
                f"command too large for ASM+Golay RS payload "
                f"({len(csp_packet)}B > {GOLAY_MAX_PAYLOAD}B)"
            )
    return item


def sanitize_queue_items(items, runtime: "WebRuntime | None" = None) -> tuple[list, int]:
    """Filter a queue restore/import set down to valid command/delay items."""
    from .state import ensure_runtime

    runtime = ensure_runtime(runtime)
    accepted = []
    skipped = 0
    for item in items:
        if item["type"] in ("delay", "note"):
            accepted.append(item)
            continue
        if item["type"] == "mission_cmd":
            try:
                rebuilt = validate_mission_cmd(
                    item.get("payload", {}),
                    runtime=runtime,
                )
                if item.get("guard"):
                    rebuilt["guard"] = True
                accepted.append(rebuilt)
            except ValueError:
                skipped += 1
            continue
        skipped += 1
    return accepted, skipped


# ---------------------------------------------------------------------------
#  Persistence helpers (moved from services.py)
# ---------------------------------------------------------------------------

def item_to_json(item: dict) -> dict:
    """Serialize a queue item for persistence (strips raw_cmd bytes)."""
    return {key: value for key, value in item.items() if key != "raw_cmd"}


def save_queue(queue: list, queue_file: Path) -> None:
    """Atomically persist queue items to a JSONL file.

    Deletes the file when queue is empty (matches current TxService behavior).
    """
    if not queue:
        try:
            os.remove(queue_file)
        except FileNotFoundError:
            pass
        return
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(queue_file.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            for item in queue:
                handle.write(json.dumps(item_to_json(item)) + "\n")
        os.replace(tmp, str(queue_file))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_queue(queue_file: Path, runtime: "WebRuntime | None" = None) -> list:
    """Load persisted queue items from a JSONL file."""
    if not queue_file.is_file():
        return []
    items = []
    with open(queue_file) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                items.append(json_to_item(payload, runtime=runtime))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                log.warning("Skipped corrupted queue entry: %s", exc)
    return items


def json_to_item(payload: dict, runtime: "WebRuntime | None" = None) -> dict:
    """Convert one persisted JSON payload back into a runtime queue item.

    Raises ValueError for unsupported item types (matches TxService behavior).
    """
    if payload["type"] == "delay":
        return make_delay(payload.get("delay_ms", 0))
    if payload["type"] == "note":
        return make_note(payload.get("text", ""))
    if payload["type"] == "mission_cmd":
        item = validate_mission_cmd(
            payload.get("payload", {}),
            runtime=runtime,
        )
        if "guard" in payload:
            item["guard"] = payload["guard"]
        return item
    raise ValueError(f"unsupported queue item type: {payload['type']}")


# ---------------------------------------------------------------------------
#  Queue operations (pure — operate on a list, don't own state)
# ---------------------------------------------------------------------------

def renumber_queue(queue: list) -> None:
    """Assign sequential display numbers to mission_cmd items in-place."""
    count = 0
    for item in queue:
        if item["type"] == "mission_cmd":
            count += 1
            item["num"] = count


def queue_summary(queue: list, cfg: dict) -> dict:
    """Summarize queue: command count, guard count, estimated execution time.

    Uses inter-command delay from cfg (matches TxService.queue_summary).
    """
    cmds = sum(1 for item in queue if item["type"] == "mission_cmd")
    guards = sum(1 for item in queue if item.get("guard"))
    delay_total = sum(item.get("delay_ms", 0) for item in queue if item["type"] == "delay")
    default_delay = cfg.get("tx", {}).get("delay_ms", 500)
    inter_cmd_ms = default_delay * max(cmds - 1, 0)
    est_time_s = (delay_total + inter_cmd_ms) / 1000.0
    return {"cmds": cmds, "guards": guards, "est_time_s": round(est_time_s, 1)}


def queue_items_json(queue: list) -> list:
    """Project the queue into websocket/API JSON shape.

    Preserves size and payload fields for mission_cmd items
    (matches TxService.queue_items_json contract with frontend).
    """
    result = []
    for item in queue:
        if item["type"] == "delay":
            result.append({"type": "delay", "delay_ms": item["delay_ms"]})
            continue
        if item["type"] == "note":
            result.append({"type": "note", "text": item["text"]})
            continue
        result.append({
            "type": "mission_cmd",
            "num": item.get("num", 0),
            "display": item.get("display", {}),
            "guard": item.get("guard", False),
            "size": len(item.get("raw_cmd", b"")),
            "payload": item.get("payload", {}),
        })
    return result


# ---------------------------------------------------------------------------
#  Import / export (moved from api.py)
# ---------------------------------------------------------------------------

def parse_import_file(filepath: Path, runtime: "WebRuntime | None" = None) -> tuple[list, int]:
    """Parse a queue import JSONL file into runtime queue items.

    - Lines starting with // are comments (silently skipped)
    - Inline // comments after JSON are stripped
    - Supports mission_cmd, delay, and note item types
    """
    items = []
    skipped = 0
    for raw_line in filepath.read_text().strip().split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("//"):
            continue
        # Strip inline comments outside of strings
        in_str, escaped, out = False, False, []
        for index, ch in enumerate(line):
            if escaped:
                escaped = False
                out.append(ch)
                continue
            if ch == "\\" and in_str:
                escaped = True
                out.append(ch)
                continue
            if ch == '"':
                in_str = not in_str
                out.append(ch)
                continue
            if not in_str and ch == "/" and index + 1 < len(line) and line[index + 1] == "/":
                break
            out.append(ch)
        line = "".join(out).rstrip().rstrip(",")
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                if obj.get("type") == "delay":
                    items.append(make_delay(max(0, min(300_000, int(obj.get("delay_ms", 0))))))
                elif obj.get("type") == "note":
                    text = str(obj.get("text", "")).strip()
                    if text:
                        items.append(make_note(text))
                elif obj.get("type") == "mission_cmd" and "payload" in obj:
                    item = validate_mission_cmd(obj["payload"], runtime=runtime)
                    if obj.get("guard"):
                        item["guard"] = True
                    items.append(item)
                else:
                    skipped += 1
            else:
                skipped += 1
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            skipped += 1
    return items, skipped
```

- [ ] **Step 2: Update runtime.py — remove moved functions, re-export**

In `mav_gss_lib/web_runtime/runtime.py`, remove the function bodies for `make_delay`, `make_note`, `make_mission_cmd`, `validate_mission_cmd`, and `sanitize_queue_items` (lines 82-154). Replace with re-exports:

```python
# Re-export from tx_queue for backward compatibility during migration
from .tx_queue import (  # noqa: F401
    make_delay,
    make_note,
    make_mission_cmd,
    validate_mission_cmd,
    sanitize_queue_items,
)
```

Also remove the `GOLAY_MAX_PAYLOAD` import at the top of `runtime.py` (lines 24-27) since it moves to `tx_queue.py`.

Keep in `runtime.py`: `check_shutdown`, `schedule_shutdown_check`, `deep_merge`, `build_send_context`.

- [ ] **Step 3: Update services.py — delegate to tx_queue**

In `mav_gss_lib/web_runtime/services.py`:

Replace the `item_to_json` function at line 586 with:

```python
from .tx_queue import item_to_json  # noqa: F401
```

In `TxService`, update methods to delegate to `tx_queue` while preserving the method signatures on `TxService` (callers still call `self.save_queue()`, etc.):

```python
from . import tx_queue as _tq

# Inside TxService:
def save_queue(self) -> None:
    _tq.save_queue(self.queue, self.queue_file())

def load_queue(self):
    return _tq.load_queue(self.queue_file(), runtime=self.runtime)

def json_to_item(self, payload):
    return _tq.json_to_item(payload, runtime=self.runtime)

def renumber_queue(self) -> None:
    _tq.renumber_queue(self.queue)

def queue_summary(self):
    return _tq.queue_summary(self.queue, self.runtime.cfg)

def queue_items_json(self):
    return _tq.queue_items_json(self.queue)
```

Remove the old method bodies but keep the methods as thin wrappers.

- [ ] **Step 4: Update api.py — import parse_import_file from tx_queue**

In `mav_gss_lib/web_runtime/api.py`:

Remove the `parse_import_file` function definition (lines 212-267). Add at the top:

```python
from .tx_queue import parse_import_file, make_delay, sanitize_queue_items, validate_mission_cmd, item_to_json
```

Remove the now-redundant imports from `.runtime` and `.services` for those same names. All call sites stay the same — only the import source changes.

- [ ] **Step 5: Update tx.py — import from tx_queue**

In `mav_gss_lib/web_runtime/tx.py`, change:

```python
from .runtime import make_delay, schedule_shutdown_check
```

To:

```python
from .tx_queue import make_delay
from .runtime import schedule_shutdown_check
```

- [ ] **Step 6: Run all tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass. No functional change — just reorganized imports and delegation.

- [ ] **Step 7: Commit checkpoint — TX queue consolidation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/tx_queue.py mav_gss_lib/web_runtime/runtime.py mav_gss_lib/web_runtime/services.py mav_gss_lib/web_runtime/api.py mav_gss_lib/web_runtime/tx.py
git commit -m "$(cat <<'EOF'
Consolidate TX queue operations into tx_queue.py

Pure queue logic (item construction, validation, import/export,
persistence, renumber/summary) extracted from runtime.py, services.py,
and api.py. TxService remains the runtime state owner with thin
wrapper methods.
EOF
)"
```

---

## Task 4: Split MAVERIC Adapter — Extract rx_ops.py

**Context:** `MavericMissionAdapter` at 700 lines mixes 5 concerns. This task extracts RX operations into a focused helper module. The adapter becomes a thin facade that delegates. Platform never imports these internal modules.

**Files:**
- Create: `mav_gss_lib/missions/maveric/rx_ops.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create rx_ops.py with RX helper functions**

Create `mav_gss_lib/missions/maveric/rx_ops.py`:

```python
"""
mav_gss_lib.missions.maveric.rx_ops -- RX packet parsing and classification

Extracted from adapter.py. Internal helpers called by MavericMissionAdapter.
The platform never imports this module directly.
"""

from __future__ import annotations

from mav_gss_lib.protocols.crc import verify_csp_crc32
from mav_gss_lib.protocols.csp import try_parse_csp_v1
from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame
from mav_gss_lib.missions.maveric.wire_format import (
    GS_NODE,
    apply_schema,
    try_parse_command,
)


def detect(meta) -> str:
    """Classify outer framing from GNU Radio/gr-satellites metadata."""
    return detect_frame_type(meta)


def normalize(frame_type: str, raw: bytes):
    """Strip mission-specific outer framing and return inner payload."""
    return normalize_frame(frame_type, raw)


def parse_packet(inner_payload: bytes, cmd_defs: dict, warnings: list[str] | None = None):
    """Parse one normalized RX payload into a ParsedPacket."""
    from mav_gss_lib.mission_adapter import ParsedPacket

    warnings = [] if warnings is None else warnings
    csp, csp_plausible = try_parse_csp_v1(inner_payload)
    if len(inner_payload) <= 4:
        return ParsedPacket(
            mission_data={"csp": csp, "csp_plausible": csp_plausible},
            warnings=warnings,
        )

    cmd, cmd_tail = try_parse_command(inner_payload[4:])
    ts_result = None
    if cmd:
        apply_schema(cmd, cmd_defs)
        if cmd.get("sat_time"):
            ts_result = cmd["sat_time"]

    crc_valid, crc_rx, crc_comp = None, None, None
    if cmd and cmd.get("csp_crc32") is not None:
        crc_valid, crc_rx, crc_comp = verify_csp_crc32(inner_payload)
        if crc_valid is False:
            warnings.append(
                f"CRC-32C mismatch: rx 0x{crc_rx:08x} != computed 0x{crc_comp:08x}"
            )

    mission_data = {
        "csp": csp, "csp_plausible": csp_plausible,
        "cmd": cmd, "cmd_tail": cmd_tail,
        "ts_result": ts_result,
        "crc_status": {
            "csp_crc32_valid": crc_valid,
            "csp_crc32_rx": crc_rx,
            "csp_crc32_comp": crc_comp,
        },
    }
    return ParsedPacket(
        mission_data=mission_data,
        warnings=warnings,
    )


def duplicate_fingerprint(mission_data: dict):
    """Return a mission-specific duplicate fingerprint or None."""
    cmd = mission_data.get("cmd")
    if not (cmd and cmd.get("crc") is not None and cmd.get("csp_crc32") is not None):
        return None
    return cmd["crc"], cmd["csp_crc32"]


def is_uplink_echo(mission_data: dict) -> bool:
    """Classify whether a decoded command is the ground-station echo."""
    cmd = mission_data.get("cmd")
    return bool(cmd and cmd.get("src") == GS_NODE)
```

- [ ] **Step 2: Update adapter.py to delegate RX methods to rx_ops**

In `mav_gss_lib/missions/maveric/adapter.py`, add import and replace RX method bodies:

```python
from mav_gss_lib.missions.maveric import rx_ops

# ... inside MavericMissionAdapter:

def detect_frame_type(self, meta) -> str:
    return rx_ops.detect(meta)

def normalize_frame(self, frame_type: str, raw: bytes):
    return rx_ops.normalize(frame_type, raw)

def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None):
    return rx_ops.parse_packet(inner_payload, self.cmd_defs, warnings)

def duplicate_fingerprint(self, parsed):
    md = self._md(parsed)
    return rx_ops.duplicate_fingerprint(md)

def is_uplink_echo(self, cmd) -> bool:
    from mav_gss_lib.mission_adapter import ParsedPacket
    md = self._md(cmd) if isinstance(cmd, ParsedPacket) else cmd
    return rx_ops.is_uplink_echo(md if isinstance(md, dict) else {"cmd": md})
```

Remove the old inline implementations (the method bodies from lines 47-114 approximately).

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

---

## Task 5: Split MAVERIC Adapter — Extract tx_ops.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/tx_ops.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create tx_ops.py with TX helper functions**

Create `mav_gss_lib/missions/maveric/tx_ops.py`. This must match the exact behavior of `adapter.py:build_tx_command` (lines 124-244), including:
- `validate_args()` returns `(valid, issues)` tuple
- `guard` reads from `payload.get("guard", defn.get("guard", False))`
- `detail_blocks` starts with routing block, then args
- `display.subtitle` format: `"{src} → {dest}"`
- Args dict path only appends non-empty values to `args_parts`

```python
"""
mav_gss_lib.missions.maveric.tx_ops -- TX command building and validation

Extracted from adapter.py. Internal helpers for MavericMissionAdapter.
"""

from __future__ import annotations

from mav_gss_lib.missions.maveric.wire_format import (
    GS_NODE,
    build_cmd_raw,
    node_name as _node_name,
    ptype_name as _ptype_name,
    resolve_node,
    resolve_ptype,
    validate_args,
    parse_cmd_line,
)


def build_raw_command(src, dest, echo, ptype, cmd_id: str, args: str) -> bytes:
    """Build one raw mission command payload for TX."""
    return build_cmd_raw(dest, cmd_id, args, echo=echo, ptype=ptype, origin=src)


def validate_tx_args(cmd_id: str, args: str, cmd_defs: dict):
    """Validate TX arguments using the active mission command schema."""
    return validate_args(cmd_id, args, cmd_defs)


def build_tx_command(payload: dict, cmd_defs: dict) -> dict:
    """Build a mission command from structured input.

    Accepts: {cmd_id, args: str | {name: value, ...}, src?, dest, echo, ptype, guard?}
    Returns: {raw_cmd: bytes, display: dict, guard: bool}
    Raises ValueError on validation failure.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    cmd_id = str(payload.get("cmd_id", "")).lower()
    args_input = payload.get("args", {})
    dest_name = str(payload.get("dest", ""))
    echo_name = str(payload.get("echo", "NONE"))
    ptype_name_val = str(payload.get("ptype", "CMD"))

    # Resolve src
    src_name = str(payload.get("src", ""))
    if src_name:
        src = resolve_node(src_name)
        if src is None:
            raise ValueError(f"unknown source node '{src_name}'")
    else:
        src = GS_NODE

    dest = resolve_node(dest_name)
    if dest is None:
        raise ValueError(f"unknown destination node '{dest_name}'")
    echo = resolve_node(echo_name)
    if echo is None:
        raise ValueError(f"unknown echo node '{echo_name}'")
    ptype = resolve_ptype(ptype_name_val)
    if ptype is None:
        raise ValueError(f"unknown packet type '{ptype_name_val}'")

    if cmd_defs and cmd_id not in cmd_defs:
        raise ValueError(f"'{cmd_id}' not in schema")
    defn = cmd_defs.get(cmd_id, {})
    if defn.get("rx_only"):
        raise ValueError(f"'{cmd_id}' is receive-only")
    allowed_nodes = defn.get("nodes", [])
    if allowed_nodes and dest_name not in allowed_nodes:
        raise ValueError(f"'{cmd_id}' not valid for node '{dest_name}' (allowed: {', '.join(allowed_nodes)})")

    tx_args_schema = defn.get("tx_args", [])

    # Normalize args_input to args_str (wire) and args_dict (display)
    if isinstance(args_input, str):
        args_str = args_input
        tokens = args_str.split() if args_str.strip() else []
        args_dict = {}
        for i, arg_def in enumerate(tx_args_schema):
            if i < len(tokens):
                args_dict[arg_def["name"]] = tokens[i]
        extra_tokens = tokens[len(tx_args_schema):]
    else:
        if not isinstance(args_input, dict):
            raise ValueError("args must be a str or dict")
        args_dict = args_input
        args_parts = []
        for arg_def in tx_args_schema:
            val = args_dict.get(arg_def["name"], "")
            if val:
                args_parts.append(str(val))
        args_str = " ".join(args_parts)
        extra_tokens = []

    # Validate args
    valid, issues = validate_args(cmd_id, args_str, cmd_defs)
    if not valid:
        raise ValueError("; ".join(issues))

    # Build raw command
    raw_cmd = bytes(build_cmd_raw(dest, cmd_id, args_str, echo=echo, ptype=ptype, origin=src))

    guard = payload.get("guard", defn.get("guard", False))

    # Row values for queue/history rendering
    row = {
        "src": _node_name(src),
        "dest": _node_name(dest),
        "echo": _node_name(echo),
        "ptype": _ptype_name(ptype),
        "cmd": (f"{cmd_id} {args_str}".strip() if args_str else cmd_id),
    }

    # Detail blocks: routing + args
    routing_block = {"kind": "routing", "label": "Routing", "fields": [
        {"name": "Src", "value": _node_name(src)},
        {"name": "Dest", "value": _node_name(dest)},
        {"name": "Echo", "value": _node_name(echo)},
        {"name": "Type", "value": _ptype_name(ptype)},
    ]}

    args_fields = []
    for arg_def in tx_args_schema:
        val = args_dict.get(arg_def["name"], "")
        if val:
            args_fields.append({"name": arg_def["name"], "value": str(val)})
    if isinstance(args_input, str):
        parts = args_str.split() if args_str else []
        for i, extra in enumerate(parts[len(tx_args_schema):]):
            args_fields.append({"name": f"arg{len(tx_args_schema) + i}", "value": extra})

    detail_blocks = [routing_block]
    if args_fields:
        detail_blocks.append({"kind": "args", "label": "Arguments", "fields": args_fields})

    display = {
        "title": cmd_id,
        "subtitle": f"{_node_name(src)} \u2192 {_node_name(dest)}",
        "row": row,
        "detail_blocks": detail_blocks,
    }

    return {"raw_cmd": raw_cmd, "display": display, "guard": guard}


def cmd_line_to_payload(line: str, cmd_defs: dict) -> dict:
    """Convert raw CLI text to a payload dict for build_tx_command."""
    line = line.strip()
    if not line:
        raise ValueError("empty command input")

    parts = line.split()
    candidate = parts[0].lower()
    defn = cmd_defs.get(candidate)

    if defn and not defn.get("rx_only") and defn.get("dest") is not None:
        args = " ".join(parts[1:])
        return {
            "cmd_id": candidate,
            "args": args,
            "dest": _node_name(defn["dest"]),
            "echo": _node_name(defn["echo"]),
            "ptype": _ptype_name(defn["ptype"]),
        }

    src, dest, echo, ptype, cmd_id, args = parse_cmd_line(line)
    result = {
        "cmd_id": cmd_id,
        "args": args,
        "dest": _node_name(dest),
        "echo": _node_name(echo),
        "ptype": _ptype_name(ptype),
    }
    if src != GS_NODE:
        result["src"] = _node_name(src)
    return result
```

- [ ] **Step 2: Update adapter.py to delegate TX methods**

```python
from mav_gss_lib.missions.maveric import tx_ops

# ... inside MavericMissionAdapter:

def build_raw_command(self, src, dest, echo, ptype, cmd_id: str, args: str) -> bytes:
    return tx_ops.build_raw_command(src, dest, echo, ptype, cmd_id, args)

def validate_tx_args(self, cmd_id: str, args: str):
    return tx_ops.validate_tx_args(cmd_id, args, self.cmd_defs)

def build_tx_command(self, payload):
    return tx_ops.build_tx_command(payload, self.cmd_defs)

def cmd_line_to_payload(self, line: str) -> dict:
    return tx_ops.cmd_line_to_payload(line, self.cmd_defs)
```

Remove the old inline implementations and clean up now-unused imports from the top of `adapter.py` (e.g., `build_cmd_raw`, `validate_args` if only used by removed methods).

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

---

## Task 6: Split MAVERIC Adapter — Extract rendering.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/rendering.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create rendering.py**

Extract these methods from `adapter.py` into `mav_gss_lib/missions/maveric/rendering.py` as module-level functions:
- `packet_list_columns()` (line 262)
- `packet_list_row(pkt)` (line 276) — needs `_md()` helper
- `protocol_blocks(pkt)` (line 322)
- `integrity_blocks(pkt)` (line 354)
- `packet_detail_blocks(pkt)` (line 380)
- `tx_queue_columns()` (line 591)

Include a local `_md(pkt)` helper (same as adapter's `_md`). Import `node_name` and `ptype_name` from `wire_format`. Import `ProtocolBlock`, `IntegrityBlock` from `mission_adapter` inside functions (lazy, matching current pattern).

Copy the exact method bodies — no behavior changes.

- [ ] **Step 2: Update adapter.py to delegate rendering methods**

```python
from mav_gss_lib.missions.maveric import rendering as _rendering

def packet_list_columns(self) -> list[dict]:
    return _rendering.packet_list_columns()

def packet_list_row(self, pkt) -> dict:
    return _rendering.packet_list_row(pkt)

def protocol_blocks(self, pkt) -> list:
    return _rendering.protocol_blocks(pkt)

def integrity_blocks(self, pkt) -> list:
    return _rendering.integrity_blocks(pkt)

def packet_detail_blocks(self, pkt) -> list[dict]:
    return _rendering.packet_detail_blocks(pkt)

def tx_queue_columns(self) -> list[dict]:
    return _rendering.tx_queue_columns()
```

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

---

## Task 7: Split MAVERIC Adapter — Extract log_format.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/log_format.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create log_format.py**

Extract these methods from `adapter.py` into `mav_gss_lib/missions/maveric/log_format.py`:
- `build_log_mission_data(pkt)` (line 430)
- `format_log_lines(pkt)` (line 482)
- `is_unknown_packet(mission_data)` (line 554 — takes `mission_data` dict, not `parsed`)

Include `_md(pkt)` helper. Import `node_name`, `ptype_name`, `format_arg_value` from `wire_format`. Copy exact method bodies.

- [ ] **Step 2: Update adapter.py to delegate logging methods**

```python
from mav_gss_lib.missions.maveric import log_format as _log_format

def build_log_mission_data(self, pkt) -> dict:
    return _log_format.build_log_mission_data(pkt)

def format_log_lines(self, pkt) -> list[str]:
    return _log_format.format_log_lines(pkt)

def is_unknown_packet(self, parsed) -> bool:
    return _log_format.is_unknown_packet(self._md(parsed))
```

- [ ] **Step 3: Verify adapter.py is now a thin facade**

After all extractions (Tasks 4-7), `adapter.py` should contain: the class definition, `_md()` helper, delegation methods for RX/TX/rendering/logging, resolution pass-throughs (gs_node, node_name, ptype_name, node_label, ptype_label, resolve_node, resolve_ptype, parse_cmd_line), and the `on_packet_received` imaging hook. The goal is clearer separation, not an arbitrary line count.

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit checkpoint — adapter split complete**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/rx_ops.py mav_gss_lib/missions/maveric/tx_ops.py mav_gss_lib/missions/maveric/rendering.py mav_gss_lib/missions/maveric/log_format.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Split MAVERIC adapter into facade + focused helper modules

adapter.py is now a thin facade delegating to:
  rx_ops.py, tx_ops.py, rendering.py, log_format.py
Platform boundary (MissionAdapter Protocol) unchanged.
EOF
)"
```

---

## Task 8: Backend Log Pagination

**Context:** `/api/logs/{session_id}` reads entire JSONL files and returns all entries. Add `offset`/`limit` params with streaming filtered scan. Server scans line-by-line, applies filters, returns first `limit` matches after `offset`. `has_more` computed by finding one match past limit. No `total` in this pass.

**Files:**
- Modify: `mav_gss_lib/web_runtime/api.py` (the `/api/logs/{session_id}` endpoint, lines 449-497)
- Modify: `mav_gss_lib/web/src/components/logs/LogViewer.tsx`

- [ ] **Step 1: Update the /api/logs/{session_id} endpoint**

In `mav_gss_lib/web_runtime/api.py`, modify `api_log_entries` to accept pagination params. Preserve the existing session path validation (exact `log_dir / f"{session_id}.jsonl"` with parent check):

```python
@router.get("/api/logs/{session_id}")
async def api_log_entries(
    session_id: str,
    request: Request,
    cmd: Optional[str] = None,
    time_from: Optional[str] = Query(None, alias="from"),
    time_to: Optional[str] = Query(None, alias="to"),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
):
    runtime = get_runtime(request)
    log_dir = (Path(runtime.cfg.get("general", {}).get("log_dir", "logs")) / "json").resolve()
    log_file = (log_dir / f"{session_id}.jsonl").resolve()
    if log_file.parent != log_dir:
        return JSONResponse(status_code=400, content={"error": "invalid session_id"})
    if not log_file.is_file():
        return JSONResponse(status_code=404, content={"error": "session not found"})

    # Streaming scan with filter + pagination
    matched = 0
    results = []
    has_more = False

    with open(log_file) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            normalized = parse_replay_entry(entry, runtime.cmd_defs, adapter=runtime.adapter)
            if normalized is None:
                continue

            # Apply cmd filter
            if cmd:
                row_cmd = ""
                r = normalized.get("_rendering")
                if isinstance(r, dict):
                    row_vals = r.get("row", {})
                    if isinstance(row_vals, dict):
                        row_cmd = str(row_vals.get("values", {}).get("cmd", ""))
                if cmd.lower() not in row_cmd.lower():
                    continue
            # Apply time filters
            if time_from is not None and normalized["time"] < str(time_from):
                continue
            if time_to is not None and normalized["time"] > str(time_to):
                continue

            # This entry passes all filters
            if matched < offset:
                matched += 1
                continue
            if len(results) < limit:
                results.append(normalized)
                matched += 1
            else:
                has_more = True
                break

    return {"entries": results, "has_more": has_more, "offset": offset, "limit": limit}
```

**Note:** This changes the response shape from a plain list to `{entries, has_more, offset, limit}`. The frontend must be updated to match.

- [ ] **Step 2: Update LogViewer.tsx to consume paginated response**

In `mav_gss_lib/web/src/components/logs/LogViewer.tsx`, update the `fetchEntries` callback to handle the new response shape and add "Load more" support:

Add state variables:

```typescript
const [hasMore, setHasMore] = useState(false)
const [currentOffset, setCurrentOffset] = useState(0)
const PAGE_SIZE = 200
```

Update `fetchEntries`:

```typescript
const fetchEntries = useCallback((sessionId: string, append = false) => {
  setLoading(true)
  if (!append) {
    setExpandedSet(new Set())
    setCurrentOffset(0)
  }
  const off = append ? currentOffset : 0
  const params = new URLSearchParams()
  if (debouncedCmd) params.set('cmd', debouncedCmd)
  if (debouncedFrom) params.set('from', debouncedFrom)
  if (debouncedTo) params.set('to', debouncedTo)
  params.set('offset', String(off))
  params.set('limit', String(PAGE_SIZE))
  const qs = params.toString()
  fetch(`/api/logs/${sessionId}?${qs}`)
    .then((r) => r.json())
    .then((data: { entries: LogEntry[]; has_more: boolean }) => {
      if (append) {
        setEntries(prev => [...prev, ...data.entries])
      } else {
        setEntries(data.entries)
      }
      setHasMore(data.has_more)
      setCurrentOffset(off + data.entries.length)
      setLoading(false)
    })
    .catch(() => { setEntries([]); setLoading(false) })
}, [debouncedCmd, debouncedFrom, debouncedTo, currentOffset])
```

Add a "Load more" button at the bottom of the entry list:

```tsx
{hasMore && (
  <button
    onClick={() => selected && fetchEntries(selected, true)}
    className="w-full py-2 text-xs text-center hover:underline"
    style={{ color: colors.active }}
  >
    Load more entries...
  </button>
)}
```

Reset `hasMore` and `currentOffset` in the close/reset effect.

- [ ] **Step 3: Run tests and build**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build
```

Expected: All tests pass, build succeeds.

- [ ] **Step 4: Commit checkpoint — log pagination**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/api.py mav_gss_lib/web/src/components/logs/LogViewer.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Add pagination to log replay endpoint

/api/logs/{session_id} accepts offset/limit params. Streams JSONL
with filters applied, returns bounded results with has_more flag.
LogViewer shows "Load more" for incremental loading.
EOF
)"
```

---

## Task 9: Extract useLogQuery Hook

**Context:** `LogViewer.tsx` has 14+ state variables. The filter/fetch/pagination logic is the highest-value extraction — reduces the component by ~60 lines and isolates the query state machine.

**Files:**
- Create: `mav_gss_lib/web/src/hooks/useLogQuery.ts`
- Modify: `mav_gss_lib/web/src/components/logs/LogViewer.tsx`

- [ ] **Step 1: Create useLogQuery.ts**

```typescript
import { useState, useCallback } from 'react'
import { useDebouncedValue } from './useDebouncedValue'
import type { ColumnDef } from '@/lib/types'

type LogEntry = Record<string, unknown>

const PAGE_SIZE = 200

export function useLogQuery() {
  const [sessions, setSessions] = useState<Record<string, unknown>[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [currentOffset, setCurrentOffset] = useState(0)

  // Filters
  const [cmdFilter, setCmdFilter] = useState('')
  const [fromTime, setFromTime] = useState('')
  const [toTime, setToTime] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const debouncedCmd = useDebouncedValue(cmdFilter, 300)
  const debouncedFrom = useDebouncedValue(fromTime, 300)
  const debouncedTo = useDebouncedValue(toTime, 300)

  // Columns
  const [rxColumns, setRxColumns] = useState<ColumnDef[]>([])
  const [txColumns, setTxColumns] = useState<ColumnDef[]>([])

  const fetchSessions = useCallback(() => {
    fetch('/api/logs')
      .then((r) => r.json())
      .then((data: Record<string, unknown>[]) => setSessions(data))
      .catch(() => {})
  }, [])

  const fetchColumns = useCallback(() => {
    fetch('/api/columns')
      .then((r) => r.json())
      .then((data: ColumnDef[]) => setRxColumns(data))
      .catch(() => {})
    fetch('/api/tx-columns')
      .then((r) => r.json())
      .then((data: ColumnDef[]) => {
        const full: ColumnDef[] = [
          { id: 'num', label: '#', align: 'right', width: 'w-9' },
          { id: 'time', label: 'time', width: 'w-[68px]' },
          ...data,
          { id: 'size', label: 'size', align: 'right', width: 'w-10' },
        ]
        setTxColumns(full)
      })
      .catch(() => {})
  }, [])

  const fetchEntries = useCallback((sessionId: string, append = false) => {
    setLoading(true)
    const off = append ? currentOffset : 0
    if (!append) setCurrentOffset(0)
    const params = new URLSearchParams()
    if (debouncedCmd) params.set('cmd', debouncedCmd)
    if (debouncedFrom) params.set('from', debouncedFrom)
    if (debouncedTo) params.set('to', debouncedTo)
    params.set('offset', String(off))
    params.set('limit', String(PAGE_SIZE))
    const qs = params.toString()
    fetch(`/api/logs/${sessionId}?${qs}`)
      .then((r) => r.json())
      .then((data: { entries: LogEntry[]; has_more: boolean }) => {
        if (append) {
          setEntries(prev => [...prev, ...data.entries])
        } else {
          setEntries(data.entries)
        }
        setHasMore(data.has_more)
        setCurrentOffset(off + data.entries.length)
        setLoading(false)
      })
      .catch(() => { setEntries([]); setLoading(false) })
  }, [debouncedCmd, debouncedFrom, debouncedTo, currentOffset])

  const reset = useCallback(() => {
    setSelected(null)
    setEntries([])
    setCmdFilter('')
    setFromTime('')
    setToTime('')
    setDateFilter('')
    setHasMore(false)
    setCurrentOffset(0)
  }, [])

  return {
    sessions, selected, setSelected, entries, loading,
    hasMore, fetchEntries, fetchSessions, fetchColumns, reset,
    cmdFilter, setCmdFilter, fromTime, setFromTime,
    toTime, setToTime, dateFilter, setDateFilter,
    rxColumns, txColumns,
  }
}
```

- [ ] **Step 2: Update LogViewer.tsx to use useLogQuery**

Replace the individual state variables (sessions, selected, entries, loading, cmdFilter, fromTime, toTime, dateFilter, rxColumns, txColumns, debounced values, hasMore, currentOffset) with the hook. Keep `expandedSet` and DOM refs local to the component.

- [ ] **Step 3: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

Expected: Build and lint pass.

---

## Task 10: Extract useRxToggles and useReceivingDetection Hooks

**Files:**
- Create: `mav_gss_lib/web/src/hooks/useRxToggles.ts`
- Create: `mav_gss_lib/web/src/hooks/useReceivingDetection.ts`
- Modify: `mav_gss_lib/web/src/components/rx/RxPanel.tsx`

- [ ] **Step 1: Create useRxToggles.ts**

```typescript
import { useState } from 'react'

interface UseRxTogglesOptions {
  externalShowHex?: boolean
  externalShowFrame?: boolean
  externalShowWrapper?: boolean
  externalHideUplink?: boolean
  onToggleHex?: () => void
  onToggleFrame?: () => void
  onToggleWrapper?: () => void
  onToggleUplink?: () => void
}

export function useRxToggles(opts: UseRxTogglesOptions = {}) {
  const [localShowHex, setLocalShowHex] = useState(false)
  const [localShowFrame, setLocalShowFrame] = useState(false)
  const [localShowWrapper, setLocalShowWrapper] = useState(false)
  const [localHideUplink, setLocalHideUplink] = useState(true)

  return {
    showHex: opts.externalShowHex ?? localShowHex,
    showFrame: opts.externalShowFrame ?? localShowFrame,
    showWrapper: opts.externalShowWrapper ?? localShowWrapper,
    hideUplink: opts.externalHideUplink ?? localHideUplink,
    toggleHex: opts.onToggleHex ?? (() => setLocalShowHex(v => !v)),
    toggleFrame: opts.onToggleFrame ?? (() => setLocalShowFrame(v => !v)),
    toggleWrapper: opts.onToggleWrapper ?? (() => setLocalShowWrapper(v => !v)),
    toggleUplink: opts.onToggleUplink ?? (() => setLocalHideUplink(v => !v)),
  }
}
```

- [ ] **Step 2: Create useReceivingDetection.ts**

```typescript
import { useState, useEffect, useRef } from 'react'

const RECEIVE_TIMEOUT_MS = 2000

export function useReceivingDetection(lastPktNum: number) {
  const [receiving, setReceiving] = useState(false)
  const prevLastNum = useRef(-1)
  const receiveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (lastPktNum > prevLastNum.current) {
      setReceiving(true)
      if (receiveTimer.current) clearTimeout(receiveTimer.current)
      receiveTimer.current = setTimeout(() => setReceiving(false), RECEIVE_TIMEOUT_MS)
    }
    prevLastNum.current = lastPktNum
  }, [lastPktNum])

  useEffect(() => () => {
    if (receiveTimer.current) clearTimeout(receiveTimer.current)
  }, [])

  return receiving
}
```

- [ ] **Step 3: Update RxPanel.tsx to use the new hooks**

Replace toggle state block (lines 130-141) and receiving detection (lines 143, 166-177) with hook calls. Remove old state variables and effects.

- [ ] **Step 4: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

---

## Task 11: Extract usePopOutBootstrap Hook

**Files:**
- Create: `mav_gss_lib/web/src/hooks/usePopOutBootstrap.ts`
- Modify: `mav_gss_lib/web/src/App.tsx`

- [ ] **Step 1: Create usePopOutBootstrap.ts**

```typescript
import { useState, useEffect } from 'react'
import type { GssConfig } from '@/lib/types'

/**
 * Shared config bootstrap for pop-out windows.
 * Pop-out windows don't live inside AppProvider, so they fetch config independently.
 */
export function usePopOutBootstrap() {
  const [config, setConfig] = useState<GssConfig | null>(null)

  useEffect(() => {
    fetch('/api/config')
      .then(r => r.json())
      .then(setConfig)
      .catch(() => {})
  }, [])

  return { config }
}
```

- [ ] **Step 2: Update PopOutTx and PopOutRx in App.tsx**

Replace the duplicated `useState<GssConfig | null>(null)` + `useEffect` fetch blocks in both `PopOutTx` (lines 185-188) and `PopOutRx` (lines 218-221) with `const { config } = usePopOutBootstrap()`.

- [ ] **Step 3: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

---

## Task 12: Extract useQueueSync Hook (skip by default)

**Status:** Skip unless there is time and explicit behavior verification. The UID sync logic in TxQueue depends on a global `nextUid` counter and an `ignoreNextSync` ref coupled to the drag-drop handler. Extracting this into a hook mostly relocates the complexity without materially reducing risk.

**If proceeding:** Create `mav_gss_lib/web/src/hooks/useQueueSync.ts` containing the UID mapping, backend sync effect (lines 74-109), and flash animation state. Expose `skipNextSync()` for the drag handler. Verify drag-drop reorder still works correctly by manual testing.

---

## Task 13: Final Verification and Commit

- [ ] **Step 1: Run full backend test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -v
```

Expected: All tests pass, 0 failures.

- [ ] **Step 2: Run frontend build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

Expected: Clean build, no lint errors.

- [ ] **Step 3: Verify new file structure**

```bash
ls "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/missions/maveric/"
ls "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web_runtime/"
ls "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web/src/hooks/"
```

Expected new files:
- `missions/maveric/rx_ops.py`
- `missions/maveric/tx_ops.py`
- `missions/maveric/rendering.py`
- `missions/maveric/log_format.py`
- `web_runtime/tx_queue.py`
- `web/src/hooks/useLogQuery.ts`
- `web/src/hooks/useRxToggles.ts`
- `web/src/hooks/useReceivingDetection.ts`
- `web/src/hooks/usePopOutBootstrap.ts`

- [ ] **Step 4: Commit checkpoint — frontend hooks**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web/src/hooks/ mav_gss_lib/web/src/components/ mav_gss_lib/web/src/App.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Extract frontend hooks: useLogQuery, useRxToggles,
useReceivingDetection, usePopOutBootstrap
EOF
)"
```

---

## Task Dependency Graph

```
Task 1 (fix import test)  ──┐
Task 2 (fix node test)    ──┴── commit checkpoint 1
Task 3 (tx_queue.py)      ──── commit checkpoint 2
Task 4 (rx_ops.py)        ──┐
Task 5 (tx_ops.py)        ──┤ sequential (each modifies adapter.py)
Task 6 (rendering.py)     ──┤
Task 7 (log_format.py)    ──┴── commit checkpoint 3
Task 8 (log pagination)   ──┐
Task 9 (useLogQuery)      ──┴── commit checkpoint 4
Task 10 (useRxToggles)    ──┐
Task 11 (usePopOut)        ──┤
Task 12 (useQueueSync)    ──┴── commit checkpoint 5 (skip 12 by default)
Task 13 (verification)    ──── after all others
```

Tasks 1-2 first. Then 3 and 4-7 can run in parallel (different file sets). 8-9 sequential. 10-11 parallel. 13 last.
