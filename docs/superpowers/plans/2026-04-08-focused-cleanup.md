# MAVERIC GSS Focused Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce module sizes, fix contract drift, consolidate scattered TX queue logic, decompose the MAVERIC adapter, add log pagination, and surgically extract tangled frontend state into hooks.

**Architecture:** No new architecture. This is a cleanup pass that moves logic into better-scoped modules without changing public contracts. The `MissionAdapter` Protocol, ZMQ transport, and component APIs all stay unchanged. Platform/mission boundary preserved — all adapter changes are internal to `missions/maveric/`.

**Tech Stack:** Python 3.10+ (FastAPI, asyncio, ZMQ), React 18 + TypeScript + Vite, Tailwind CSS

**Test commands:**
- Backend: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q`
- Frontend build: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build`
- Frontend lint: `cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run lint`

---

## Task 1: Fix Failing Test — Import File Comment Parsing

**Context:** `parse_import_file()` converts `//` comment lines into note items. The test expects comments to be silently ignored. This is a contract regression — comments in import files are authoring aids, not queue items.

**Files:**
- Modify: `mav_gss_lib/web_runtime/api.py:222-226`
- Test: `tests/test_ops_web_runtime.py:81-96`

- [ ] **Step 1: Run failing test to confirm the failure**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_ops_web_runtime.py::WebRuntimeOpsTest::test_parse_import_file_produces_mission_cmd_items -v
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
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_ops_web_runtime.py::WebRuntimeOpsTest::test_parse_import_file_produces_mission_cmd_items -v
```

Expected: PASS

- [ ] **Step 4: Run full test suite to check for regressions**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: 1 fewer failure (the other failing test is Task 2)

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/api.py
git commit -m "$(cat <<'EOF'
Fix import file comment parsing: // lines are comments, not notes
EOF
)"
```

---

## Task 2: Fix Failing Test — Node Whitelist Validation

**Context:** `build_tx_command` in the adapter has correct node-whitelist validation code at lines 171-173, but `com_ping` may be missing its `nodes` constraint in `commands.yml`. The test expects `com_ping` sent to `FTDI` to raise `ValueError`.

**Files:**
- Investigate: `mav_gss_lib/missions/maveric/adapter.py:166-173`
- Investigate: `missions/maveric/commands.yml` (gitignored — read locally)
- Test: `tests/test_tx_plugin.py:257-268`

- [ ] **Step 1: Run the failing test to confirm**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_tx_plugin.py::TestMavericBuildTxCommand::test_build_tx_command_rejects_invalid_node_for_cmd -v
```

Expected: FAIL with `AssertionError: ValueError not raised`

- [ ] **Step 2: Investigate the root cause**

Check if `com_ping` has a `nodes` field in the schema. The validation code at `adapter.py:171-173` is:

```python
allowed_nodes = defn.get("nodes", [])
if allowed_nodes and dest_name not in allowed_nodes:
    raise ValueError(...)
```

This only triggers if the schema definition for `com_ping` contains a non-empty `nodes` list. Run this diagnostic:

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python3 -c "
from mav_gss_lib.config import load_gss_config
from mav_gss_lib.mission_adapter import load_mission_adapter
cfg = load_gss_config()
adapter = load_mission_adapter(cfg)
defn = adapter.cmd_defs.get('com_ping', {})
print('com_ping definition:', defn)
print('nodes field:', defn.get('nodes', []))
print('dest_name would be: FTDI')
"
```

If `nodes` is empty or missing, the validation at line 172 is skipped — that is the bug.

- [ ] **Step 3: Fix the root cause**

Two possible fixes depending on investigation:

**If `com_ping` is missing the `nodes` field in `commands.yml`:** Add the `nodes` constraint to the `com_ping` definition. The test says it should be `[LPPM, EPS, UPPM, HLNV, ASTR]`. Edit `commands.yml` (local file, gitignored) to add `nodes: [LPPM, EPS, UPPM, HLNV, ASTR]` under `com_ping`.

**If the issue is case sensitivity:** The `dest_name` at `adapter.py:138` is `str(payload.get("dest", ""))` which preserves case. The `allowed_nodes` from schema may use different casing. If so, normalize the comparison at line 172:

```python
if allowed_nodes and dest_name.upper() not in [n.upper() for n in allowed_nodes]:
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/test_tx_plugin.py::TestMavericBuildTxCommand::test_build_tx_command_rejects_invalid_node_for_cmd -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass (0 failures)

- [ ] **Step 6: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/adapter.py  # or commands.yml if that was changed
git commit -m "$(cat <<'EOF'
Fix node whitelist validation for com_ping command routing
EOF
)"
```

---

## Task 3: Create tx_queue.py — Extract Pure Queue Operations

**Context:** TX queue mutation logic is scattered across `api.py` (import/export), `runtime.py` (make_delay, make_note, validate_mission_cmd, sanitize_queue_items), and `services.py` (persistence, renumber, summary). This task consolidates pure queue operations into one module. `TxService` remains the runtime state owner — it holds `queue`, `history`, `sending`. The new module owns logic, not state.

**Files:**
- Create: `mav_gss_lib/web_runtime/tx_queue.py`
- Modify: `mav_gss_lib/web_runtime/runtime.py` (remove moved functions)
- Modify: `mav_gss_lib/web_runtime/services.py` (delegate to tx_queue)
- Modify: `mav_gss_lib/web_runtime/api.py` (import from tx_queue)
- Modify: `mav_gss_lib/web_runtime/tx.py` (import from tx_queue)
- Test: `tests/test_ops_web_runtime.py` (update imports)

- [ ] **Step 1: Create tx_queue.py with item construction functions**

Create `mav_gss_lib/web_runtime/tx_queue.py` with the functions moved from `runtime.py`:

```python
"""
mav_gss_lib.web_runtime.tx_queue -- Pure TX queue operations

Item construction, validation, import/export, and persistence helpers.
TxService remains the runtime state owner (queue, history, sending).
This module owns logic, not state.
"""

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import WebRuntime

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Item construction
# ---------------------------------------------------------------------------

def make_delay(delay_ms) -> dict:
    return {"type": "delay", "delay_ms": int(delay_ms)}


def make_note(text) -> dict:
    return {"type": "note", "text": " ".join(str(text).split())}


def make_mission_cmd(payload, adapter=None) -> dict:
    """Build a queue-ready mission command via the adapter.

    Does NOT validate MTU — use validate_mission_cmd() for full admission.
    """
    if adapter is None:
        raise ValueError("no mission adapter configured")
    result = adapter.build_tx_command(payload)
    raw_cmd = result.get("raw_cmd", b"")
    display = result.get("display", {})
    guard = bool(result.get("guard", False))
    return {
        "type": "mission_cmd",
        "raw_cmd": raw_cmd,
        "display": display,
        "guard": guard,
        "payload": payload,
    }


def validate_mission_cmd(payload, runtime: "WebRuntime | None" = None) -> dict:
    """Build + validate MTU for a mission command.

    Full admission check: builds the command, then checks ASM+Golay
    payload limit if that uplink mode is active.
    """
    adapter = getattr(runtime, "adapter", None) if runtime else None
    item = make_mission_cmd(payload, adapter=adapter)
    cfg = getattr(runtime, "config", {}) if runtime else {}
    uplink_mode = cfg.get("tx", {}).get("uplink_mode", "")
    if uplink_mode == "ASM+Golay":
        try:
            from mav_gss_lib.protocols.golay import MAX_PAYLOAD as GOLAY_MAX_PAYLOAD
        except ImportError:
            GOLAY_MAX_PAYLOAD = None
        if GOLAY_MAX_PAYLOAD is not None:
            from mav_gss_lib.protocols.csp import csp_wrap
            csp_cfg = cfg.get("csp", {})
            wrapped = csp_wrap(item["raw_cmd"], csp_cfg)
            if len(wrapped) > GOLAY_MAX_PAYLOAD:
                raise ValueError(
                    f"CSP-wrapped payload ({len(wrapped)} B) exceeds "
                    f"ASM+Golay limit ({GOLAY_MAX_PAYLOAD} B)"
                )
    return item


# ---------------------------------------------------------------------------
#  Queue sanitization (import / restore)
# ---------------------------------------------------------------------------

def sanitize_queue_items(items, runtime: "WebRuntime | None" = None) -> tuple[list, int]:
    """Filter and validate a list of queue items for import or restore.

    Returns (accepted_items, skipped_count).
    """
    accepted = []
    skipped = 0
    for item in items:
        t = item.get("type")
        if t == "delay":
            accepted.append(make_delay(item.get("delay_ms", 0)))
        elif t == "note":
            text = str(item.get("text", "")).strip()
            if text:
                accepted.append(make_note(text))
            else:
                skipped += 1
        elif t == "mission_cmd" and "payload" in item:
            try:
                built = validate_mission_cmd(item["payload"], runtime=runtime)
                if item.get("guard"):
                    built["guard"] = True
                accepted.append(built)
            except (ValueError, KeyError, TypeError) as exc:
                log.debug("sanitize skip: %s", exc)
                skipped += 1
        else:
            skipped += 1
    return accepted, skipped


# ---------------------------------------------------------------------------
#  Persistence helpers
# ---------------------------------------------------------------------------

def item_to_json(item: dict) -> dict:
    """Strip raw_cmd bytes from a queue item for JSON persistence."""
    out = {k: v for k, v in item.items() if k != "raw_cmd"}
    return out


def save_queue(queue: list, filepath: Path) -> None:
    """Atomically persist queue items to a JSONL file."""
    try:
        fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            for item in queue:
                f.write(json.dumps(item_to_json(item)) + "\n")
        os.replace(tmp, filepath)
    except Exception:
        log.exception("queue save failed")
        try:
            os.unlink(tmp)
        except OSError:
            pass


def load_queue(filepath: Path, runtime: "WebRuntime | None" = None) -> list:
    """Load persisted queue items from a JSONL file."""
    if not filepath.exists():
        return []
    items = []
    for line in filepath.read_text().strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            item = json_to_item(obj, runtime=runtime)
            if item:
                items.append(item)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            log.debug("queue load skip: %s", exc)
    return items


def json_to_item(payload: dict, runtime: "WebRuntime | None" = None) -> dict | None:
    """Reconstruct a single queue item from persisted JSON."""
    t = payload.get("type")
    if t == "delay":
        return make_delay(payload.get("delay_ms", 0))
    if t == "note":
        text = str(payload.get("text", "")).strip()
        return make_note(text) if text else None
    if t == "mission_cmd" and "payload" in payload:
        try:
            item = validate_mission_cmd(payload["payload"], runtime=runtime)
            if payload.get("guard"):
                item["guard"] = True
            return item
        except (ValueError, KeyError, TypeError):
            return None
    return None


# ---------------------------------------------------------------------------
#  Queue operations (pure — mutate a list, don't own state)
# ---------------------------------------------------------------------------

def renumber_queue(queue: list) -> None:
    """Assign sequential display numbers to mission_cmd items in-place."""
    count = 0
    for item in queue:
        if item.get("type") in ("cmd", "mission_cmd"):
            count += 1
            item["num"] = count


def queue_summary(queue: list, default_delay_ms: int = 0) -> dict:
    """Compute queue summary: command count, guard count, estimated time."""
    cmds = 0
    guards = 0
    delay_ms = 0
    for item in queue:
        t = item.get("type")
        if t in ("cmd", "mission_cmd"):
            cmds += 1
            if item.get("guard"):
                guards += 1
            delay_ms += default_delay_ms
        elif t == "delay":
            delay_ms += item.get("delay_ms", 0)
    return {
        "cmds": cmds,
        "guards": guards,
        "est_time_s": round(delay_ms / 1000, 1) if delay_ms else 0,
    }


def queue_items_json(queue: list) -> list:
    """Project queue items to JSON shape for WebSocket/API transport."""
    result = []
    for item in queue:
        t = item.get("type")
        if t in ("cmd", "mission_cmd"):
            entry = {
                "type": "mission_cmd",
                "num": item.get("num"),
                "display": item.get("display", {}),
                "guard": item.get("guard", False),
            }
            result.append(entry)
        elif t == "delay":
            result.append({"type": "delay", "delay_ms": item.get("delay_ms", 0)})
        elif t == "note":
            result.append({"type": "note", "text": item.get("text", "")})
    return result


# ---------------------------------------------------------------------------
#  Import / export
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

- [ ] **Step 2: Update runtime.py — remove moved functions, re-export for compatibility**

In `mav_gss_lib/web_runtime/runtime.py`, remove the function bodies for `make_delay`, `make_note`, `make_mission_cmd`, `validate_mission_cmd`, and `sanitize_queue_items`. Replace with re-exports from `tx_queue`:

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

Keep `deep_merge`, `build_send_context`, `check_shutdown`, `schedule_shutdown_check` in `runtime.py` — those are not queue operations.

- [ ] **Step 3: Update services.py — delegate persistence/summary to tx_queue**

In `mav_gss_lib/web_runtime/services.py`:

Replace the `item_to_json` function at the bottom of the file with a re-export:

```python
from .tx_queue import item_to_json  # noqa: F401
```

In `TxService`, update methods to delegate to `tx_queue`:

- `save_queue()`: call `tx_queue.save_queue(self.queue, self.queue_file())`
- `load_queue()`: call `tx_queue.load_queue(self.queue_file(), runtime=self.runtime)`
- `json_to_item()`: call `tx_queue.json_to_item(payload, runtime=self.runtime)`
- `renumber_queue()`: call `tx_queue.renumber_queue(self.queue)`
- `queue_summary()`: call `tx_queue.queue_summary(self.queue, default_delay_ms)`
- `queue_items_json()`: call `tx_queue.queue_items_json(self.queue)`

Keep the methods as thin wrappers on `TxService` so callers don't need to change yet.

- [ ] **Step 4: Update api.py — import parse_import_file from tx_queue**

In `mav_gss_lib/web_runtime/api.py`:

Remove the `parse_import_file` function definition (lines 212-267). Add an import at the top:

```python
from .tx_queue import parse_import_file, make_delay, sanitize_queue_items, validate_mission_cmd, item_to_json
```

Remove the corresponding imports from `.runtime`:

```python
# Remove: from .runtime import ... make_delay, sanitize_queue_items, validate_mission_cmd
# Remove: from .services import item_to_json
```

Update the remaining `api.py` imports to use `tx_queue` instead. All call sites stay the same — only the import source changes.

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

Also update the `validate_mission_cmd` import if used (check line-by-line).

- [ ] **Step 6: Run all tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass. No functional change — just reorganized imports.

- [ ] **Step 7: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/tx_queue.py mav_gss_lib/web_runtime/runtime.py mav_gss_lib/web_runtime/services.py mav_gss_lib/web_runtime/api.py mav_gss_lib/web_runtime/tx.py
git commit -m "$(cat <<'EOF'
Consolidate TX queue operations into tx_queue.py

Pure queue logic (item construction, validation, import/export,
persistence, renumber/summary) extracted from runtime.py, services.py,
and api.py into a single module. TxService remains the runtime state
owner.
EOF
)"
```

---

## Task 4: Split MAVERIC Adapter — Extract rx_ops.py

**Context:** `MavericMissionAdapter` at 700 lines mixes 5 concerns. This task extracts RX operations into a focused helper module. The adapter becomes a thin facade that delegates.

**Files:**
- Create: `mav_gss_lib/missions/maveric/rx_ops.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create rx_ops.py with RX helper functions**

Create `mav_gss_lib/missions/maveric/rx_ops.py`:

```python
"""
mav_gss_lib.missions.maveric.rx_ops -- RX packet parsing and classification

Extracted from adapter.py. These are internal helpers called by
MavericMissionAdapter — the platform never imports this module directly.
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

In `mav_gss_lib/missions/maveric/adapter.py`, replace the RX method implementations with delegation:

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

Remove the old inline implementations of these methods (the bodies from lines 47-114).

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/rx_ops.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Extract RX operations from adapter into maveric/rx_ops.py
EOF
)"
```

---

## Task 5: Split MAVERIC Adapter — Extract tx_ops.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/tx_ops.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create tx_ops.py with TX helper functions**

Create `mav_gss_lib/missions/maveric/tx_ops.py`:

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
    """Convert raw CLI text to a payload dict for build_tx_command.

    Handles shortcut format (CMD_ID [ARGS]) and full format
    ([SRC] DEST ECHO TYPE CMD_ID [ARGS]).
    """
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

- [ ] **Step 2: Update adapter.py to delegate TX methods to tx_ops**

In `mav_gss_lib/missions/maveric/adapter.py`, replace TX method bodies:

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

Remove the old inline implementations and the now-unused local imports (`resolve_node`, `resolve_ptype`, etc. that were only used by the removed bodies).

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/tx_ops.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Extract TX operations from adapter into maveric/tx_ops.py
EOF
)"
```

---

## Task 6: Split MAVERIC Adapter — Extract rendering.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/rendering.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create rendering.py with UI slot functions**

Create `mav_gss_lib/missions/maveric/rendering.py`:

```python
"""
mav_gss_lib.missions.maveric.rendering -- RX/TX rendering slot helpers

Packet list columns/rows, detail blocks, protocol/integrity blocks,
and TX queue column definitions. Internal to the MAVERIC mission package.
"""

from __future__ import annotations

from mav_gss_lib.missions.maveric.wire_format import (
    node_name as _node_name,
    ptype_name as _ptype_name,
)


def _md(pkt) -> dict:
    """Read mission data from a packet."""
    return getattr(pkt, "mission_data", {}) or {}


def packet_list_columns() -> list[dict]:
    """Return column definitions for the RX packet list."""
    return [
        {"id": "num",   "label": "#",         "align": "right", "width": "w-9"},
        {"id": "time",  "label": "time",      "width": "w-[68px]"},
        {"id": "frame", "label": "frame",     "width": "w-[72px]", "toggle": "showFrame"},
        {"id": "src",   "label": "src",       "width": "w-[52px]"},
        {"id": "echo",  "label": "echo",      "width": "w-[52px]", "toggle": "showEcho"},
        {"id": "ptype", "label": "type",      "width": "w-[52px]", "badge": True},
        {"id": "cmd",   "label": "id / args", "flex": True},
        {"id": "flags", "label": "",          "width": "w-[72px]", "align": "right"},
        {"id": "size",  "label": "size",      "align": "right", "width": "w-10"},
    ]


def packet_list_row(pkt) -> dict:
    """Return row values keyed by column ID for one packet."""
    md = _md(pkt)
    cmd = md.get("cmd")
    args_str = ""
    if cmd and cmd.get("schema_match") and cmd.get("typed_args"):
        important = [ta for ta in cmd["typed_args"] if ta.get("important")]
        show = important if important else cmd["typed_args"]
        parts = []
        for ta in show:
            val = ta.get("value", "")
            if ta["type"] == "epoch_ms":
                val = val.ms if hasattr(val, "ms") else (val["ms"] if isinstance(val, dict) and "ms" in val else val)
            if isinstance(val, (bytes, bytearray)):
                val = val.hex()
            parts.append(str(val))
        args_str = " ".join(parts)
    elif cmd:
        raw = cmd.get("args", [])
        args_str = " ".join(str(a) for a in raw) if isinstance(raw, list) else str(raw)

    flags = []
    if cmd and cmd.get("crc_valid") is False:
        flags.append({"tag": "CRC", "tone": "danger"})
    if pkt.is_uplink_echo:
        flags.append({"tag": "UL", "tone": "info"})
    if pkt.is_dup:
        flags.append({"tag": "DUP", "tone": "warning"})
    if pkt.is_unknown:
        flags.append({"tag": "UNK", "tone": "danger"})

    return {
        "values": {
            "num": pkt.pkt_num,
            "time": pkt.gs_ts_short,
            "frame": pkt.frame_type,
            "src": _node_name(cmd["src"]) if cmd else "",
            "echo": _node_name(cmd["echo"]) if cmd else "",
            "ptype": _ptype_name(cmd["pkt_type"]) if cmd else "",
            "cmd": ((cmd["cmd_id"] + " " + args_str).strip() if args_str else cmd["cmd_id"]) if cmd else "",
            "flags": flags,
            "size": len(pkt.raw),
        },
        "_meta": {"opacity": 0.5 if pkt.is_unknown else 1.0},
    }


def protocol_blocks(pkt) -> list:
    """Return protocol/wrapper blocks for the detail view."""
    from mav_gss_lib.mission_adapter import ProtocolBlock
    from mav_gss_lib.protocols.ax25 import ax25_decode_header
    md = _md(pkt)
    csp = md.get("csp")
    blocks = []
    if csp:
        blocks.append(ProtocolBlock(
            kind="csp",
            label="CSP V1",
            fields=[{"name": k.capitalize(), "value": str(v)} for k, v in csp.items()],
        ))
    if pkt.stripped_hdr:
        ax25_fields = [{"name": "Header", "value": pkt.stripped_hdr}]
        try:
            decoded = ax25_decode_header(bytes.fromhex(pkt.stripped_hdr.replace(" ", "")))
            ax25_fields = [
                {"name": "Dest", "value": f"{decoded['dest']['callsign']}-{decoded['dest']['ssid']}"},
                {"name": "Src", "value": f"{decoded['src']['callsign']}-{decoded['src']['ssid']}"},
                {"name": "Control", "value": decoded["control_hex"]},
                {"name": "PID", "value": decoded["pid_hex"]},
            ]
        except Exception:
            pass
        blocks.append(ProtocolBlock(
            kind="ax25",
            label="AX.25",
            fields=ax25_fields,
        ))
    return blocks


def integrity_blocks(pkt) -> list:
    """Return integrity check blocks for the detail view."""
    from mav_gss_lib.mission_adapter import IntegrityBlock
    md = _md(pkt)
    blocks = []
    cmd = md.get("cmd")
    if cmd and cmd.get("crc") is not None:
        blocks.append(IntegrityBlock(
            kind="crc16",
            label="CRC-16",
            scope="command",
            ok=cmd.get("crc_valid"),
            received=f"0x{cmd['crc']:04X}" if cmd.get("crc") is not None else None,
        ))
    crc_status = md.get("crc_status", {})
    if crc_status.get("csp_crc32_valid") is not None:
        blocks.append(IntegrityBlock(
            kind="crc32c",
            label="CRC-32C",
            scope="csp",
            ok=crc_status["csp_crc32_valid"],
            received=f"0x{crc_status['csp_crc32_rx']:08X}" if crc_status.get("csp_crc32_rx") is not None else None,
            computed=f"0x{crc_status['csp_crc32_comp']:08X}" if crc_status.get("csp_crc32_comp") is not None else None,
        ))
    return blocks


def packet_detail_blocks(pkt) -> list[dict]:
    """Return mission-specific semantic blocks for the detail view."""
    md = _md(pkt)
    cmd = md.get("cmd")
    ts_result = md.get("ts_result")
    blocks = []

    time_block = {"kind": "time", "label": "Time", "fields": [
        {"name": "GS Time", "value": pkt.gs_ts},
    ]}
    if ts_result:
        dt_utc, dt_local, ms = ts_result
        if dt_utc:
            time_block["fields"].append({"name": "SAT UTC", "value": dt_utc.strftime("%H:%M:%S") + " UTC"})
        if dt_local:
            time_block["fields"].append({"name": "SAT Local", "value": dt_local.strftime("%H:%M:%S %Z")})
    blocks.append(time_block)

    if cmd:
        blocks.append({"kind": "routing", "label": "Routing", "fields": [
            {"name": "Src", "value": _node_name(cmd["src"])},
            {"name": "Dest", "value": _node_name(cmd["dest"])},
            {"name": "Echo", "value": _node_name(cmd["echo"])},
            {"name": "Type", "value": _ptype_name(cmd["pkt_type"])},
            {"name": "Cmd", "value": cmd["cmd_id"]},
        ]})

    if cmd and cmd.get("schema_match") and cmd.get("typed_args"):
        args_fields = []
        for ta in cmd["typed_args"]:
            val = ta.get("value", "")
            if ta["type"] == "epoch_ms":
                val = val.ms if hasattr(val, "ms") else (val["ms"] if isinstance(val, dict) and "ms" in val else val)
            if isinstance(val, (bytes, bytearray)):
                val = val.hex()
            args_fields.append({"name": ta["name"], "value": str(val)})
        for i, extra in enumerate(cmd.get("extra_args", [])):
            args_fields.append({"name": f"arg{len(cmd.get('typed_args', [])) + i}", "value": str(extra)})
        if args_fields:
            blocks.append({"kind": "args", "label": "Arguments", "fields": args_fields})
    elif cmd:
        raw = cmd.get("args", [])
        if raw:
            args_fields = [{"name": f"arg{i}", "value": str(a)} for i, a in enumerate(raw)]
            blocks.append({"kind": "args", "label": "Arguments", "fields": args_fields})

    return blocks


def tx_queue_columns() -> list[dict]:
    """Return column definitions for the TX queue/history list."""
    return [
        {"id": "src",   "label": "src",       "width": "w-[52px]", "hide_if_all": ["GS"]},
        {"id": "dest",  "label": "dest",      "width": "w-[52px]"},
        {"id": "echo",  "label": "echo",      "width": "w-[52px]", "hide_if_all": ["NONE"]},
        {"id": "ptype", "label": "type",      "width": "w-[52px]", "badge": True},
        {"id": "cmd",   "label": "id / args", "flex": True},
    ]
```

- [ ] **Step 2: Update adapter.py to delegate rendering methods**

```python
from mav_gss_lib.missions.maveric import rendering as _rendering

# ... inside MavericMissionAdapter:

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

Remove the old inline implementations.

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/rendering.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Extract rendering slots from adapter into maveric/rendering.py
EOF
)"
```

---

## Task 7: Split MAVERIC Adapter — Extract log_format.py

**Files:**
- Create: `mav_gss_lib/missions/maveric/log_format.py`
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create log_format.py with logging helper functions**

Create `mav_gss_lib/missions/maveric/log_format.py`:

```python
"""
mav_gss_lib.missions.maveric.log_format -- Mission log formatting

JSONL mission data builder and text log formatter.
Internal to the MAVERIC mission package.
"""

from __future__ import annotations

from mav_gss_lib.missions.maveric.wire_format import (
    node_name as _node_name,
    ptype_name as _ptype_name,
    format_arg_value,
)


def _md(pkt) -> dict:
    return getattr(pkt, "mission_data", {}) or {}


def build_log_mission_data(pkt) -> dict:
    """Return MAVERIC-specific fields for the JSONL log mission block."""
    md = _md(pkt)
    data = {}
    csp = md.get("csp")
    if csp:
        data["csp_candidate"] = csp
        data["csp_plausible"] = md.get("csp_plausible", False)
    ts_result = md.get("ts_result")
    if ts_result:
        data["sat_ts_ms"] = ts_result[2]
    crc_status = md.get("crc_status", {})
    if crc_status.get("csp_crc32_valid") is not None:
        data["csp_crc32"] = {
            "valid": crc_status["csp_crc32_valid"],
            "received": f"0x{crc_status['csp_crc32_rx']:08x}",
        }
    cmd = md.get("cmd")
    if cmd:
        cmd_log = {
            "src": cmd["src"], "dest": cmd["dest"],
            "echo": cmd["echo"], "pkt_type": cmd["pkt_type"],
            "cmd_id": cmd["cmd_id"], "crc": cmd["crc"],
            "crc_valid": cmd.get("crc_valid"),
        }
        if cmd.get("schema_match"):
            typed_log = {}
            for ta in cmd["typed_args"]:
                if ta["type"] == "epoch_ms" and "ms" in ta["value"]:
                    typed_log[ta["name"]] = ta["value"]["ms"]
                elif ta["type"] == "blob" and isinstance(ta["value"], (bytes, bytearray)):
                    typed_log[ta["name"]] = ta["value"].hex()
                else:
                    typed_log[ta["name"]] = ta["value"]
            cmd_log["args"] = typed_log
            if cmd["extra_args"]:
                cmd_log["extra_args"] = cmd["extra_args"]
        else:
            cmd_log["args"] = cmd["args"]
            if cmd.get("schema_warning"):
                cmd_log["schema_warning"] = cmd["schema_warning"]
        data["cmd"] = cmd_log
        cmd_tail = md.get("cmd_tail")
        if cmd_tail:
            data["tail_hex"] = cmd_tail.hex()
    return data


def format_log_lines(pkt) -> list[str]:
    """Return MAVERIC-specific text log lines for one packet."""
    md = _md(pkt)
    lines = []

    # AX.25 header
    if pkt.stripped_hdr:
        from mav_gss_lib.protocols.ax25 import ax25_decode_header
        try:
            decoded = ax25_decode_header(bytes.fromhex(pkt.stripped_hdr.replace(" ", "")))
            lines.append(
                f"  {'AX.25 HDR':<12}"
                f"Dest:{decoded['dest']['callsign']}-{decoded['dest']['ssid']}  "
                f"Src:{decoded['src']['callsign']}-{decoded['src']['ssid']}  "
                f"Ctrl:{decoded['control_hex']}  PID:{decoded['pid_hex']}"
            )
        except Exception:
            lines.append(f"  {'AX.25 HDR':<12}{pkt.stripped_hdr}")

    # CSP header
    csp = md.get("csp")
    if csp:
        tag = "CSP V1" if md.get("csp_plausible") else "CSP V1 [?]"
        lines.append(f"  {tag:<12}"
            f"Prio:{csp['prio']}  Src:{csp['src']}  Dest:{csp['dest']}  "
            f"DPort:{csp['dport']}  SPort:{csp['sport']}  Flags:0x{csp['flags']:02X}")

    # Satellite time
    ts_result = md.get("ts_result")
    if ts_result:
        dt_utc, dt_local, raw_ms = ts_result
        lines.append(f"  {'SAT TIME':<12}"
            f"{dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} \u2502 "
            f"{dt_local.strftime('%Y-%m-%d %H:%M:%S %Z')}  ({raw_ms})")

    # Command
    cmd = md.get("cmd")
    if cmd:
        lines.append(f"  {'CMD':<12}"
            f"Src:{_node_name(cmd['src'])}  Dest:{_node_name(cmd['dest'])}  "
            f"Echo:{_node_name(cmd['echo'])}  Type:{_ptype_name(cmd['pkt_type'])}")
        lines.append(f"  {'CMD ID':<12}{cmd['cmd_id']}")

        if cmd.get("schema_match"):
            for ta in cmd.get("typed_args", []):
                lines.append(f"  {ta['name'].upper():<12}{format_arg_value(ta)}")
            for i, extra in enumerate(cmd.get("extra_args", [])):
                lines.append(f"  {f'ARG +{i}':<12}{extra}")
        else:
            if cmd.get("schema_warning"):
                lines.append(f"  {'\u26a0 SCHEMA':<12}{cmd['schema_warning']}")
            for i, arg in enumerate(cmd.get("args", [])):
                lines.append(f"  {f'ARG {i}':<12}{arg}")

    # CRC
    if cmd and cmd.get("crc") is not None:
        tag = "OK" if cmd.get("crc_valid") else "FAIL"
        lines.append(f"  {'CRC-16':<12}0x{cmd['crc']:04x} [{tag}]")
    crc_status = md.get("crc_status", {})
    if crc_status.get("csp_crc32_valid") is not None:
        tag = "OK" if crc_status["csp_crc32_valid"] else "FAIL"
        lines.append(f"  {'CRC-32C':<12}0x{crc_status['csp_crc32_rx']:08x} [{tag}]")

    return lines


def is_unknown_packet(mission_data: dict) -> bool:
    """MAVERIC: a packet is unknown when no command was decoded."""
    cmd = mission_data.get("cmd")
    return cmd is None
```

- [ ] **Step 2: Update adapter.py to delegate logging methods**

```python
from mav_gss_lib.missions.maveric import log_format as _log_format

# ... inside MavericMissionAdapter:

def build_log_mission_data(self, pkt) -> dict:
    return _log_format.build_log_mission_data(pkt)

def format_log_lines(self, pkt) -> list[str]:
    return _log_format.format_log_lines(pkt)

def is_unknown_packet(self, parsed) -> bool:
    return _log_format.is_unknown_packet(self._md(parsed))
```

Remove the old inline implementations.

- [ ] **Step 3: Verify adapter.py is now a thin facade**

After all extractions (Tasks 4-7), `adapter.py` should be approximately 80-120 lines: the class definition, `_md()` helper, resolution pass-throughs (gs_node, node_name, ptype_name, etc.), and the `on_packet_received` imaging hook. Count the lines to confirm.

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/missions/maveric/log_format.py mav_gss_lib/missions/maveric/adapter.py
git commit -m "$(cat <<'EOF'
Extract logging format from adapter into maveric/log_format.py

Adapter is now a thin facade (~100 lines) delegating to:
  rx_ops.py, tx_ops.py, rendering.py, log_format.py
EOF
)"
```

---

## Task 8: Backend Log Pagination

**Context:** `/api/logs/{session_id}` reads entire JSONL files. Add `offset`/`limit` params with streaming scan. Server scans line-by-line, applies filters, returns first `limit` matches after `offset`. `has_more` computed by scanning one past limit. No `total` in this pass.

**Files:**
- Modify: `mav_gss_lib/web_runtime/api.py` (the `/api/logs/{session_id}` endpoint)
- Modify: `mav_gss_lib/web/src/components/logs/LogViewer.tsx` (add "Load more" button)
- Test: Backend test for pagination behavior

- [ ] **Step 1: Write a test for paginated log entries**

Add to `tests/test_ops_web_runtime.py`:

```python
def test_log_pagination_returns_limited_entries(self):
    """Paginated log endpoint should respect offset and limit."""
    from mav_gss_lib.web_runtime.api import parse_replay_entry
    # This test validates the pagination logic conceptually;
    # full endpoint test requires running the FastAPI app
    entries = [{"n": i, "time": f"2026-04-08T00:00:{i:02d}"} for i in range(10)]
    # Simulate offset=3, limit=4: should get entries 3,4,5,6
    offset, limit = 3, 4
    page = entries[offset:offset + limit]
    has_more = len(entries) > offset + limit
    self.assertEqual(len(page), 4)
    self.assertTrue(has_more)
    self.assertEqual(page[0]["n"], 3)
```

- [ ] **Step 2: Update the /api/logs/{session_id} endpoint**

In `mav_gss_lib/web_runtime/api.py`, modify the `api_log_entries` endpoint to accept `offset` and `limit` params:

```python
@router.get("/api/logs/{session_id}")
async def api_log_entries(
    session_id: str,
    request: Request,
    cmd: str = Query(None),
    time_from: str = Query(None, alias="from"),
    time_to: str = Query(None, alias="to"),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
):
    runtime = get_runtime(request)
    log_dir = Path(runtime.config.get("general", {}).get("log_dir", "logs")) / "json"

    # Validate session_id (no path traversal)
    if "/" in session_id or "\\" in session_id or ".." in session_id:
        return JSONResponse({"error": "invalid session_id"}, status_code=400)

    # Find matching log file
    candidates = list(log_dir.glob(f"{session_id}*.jsonl"))
    if not candidates:
        return JSONResponse({"error": "session not found"}, status_code=404)
    filepath = candidates[0]

    adapter = runtime.adapter
    cmd_defs = getattr(adapter, "cmd_defs", {})

    # Streaming scan with filter + pagination
    matched = 0
    skipped = 0
    results = []
    has_more = False

    for raw_line in filepath.open():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        parsed = parse_replay_entry(entry, cmd_defs, adapter=adapter)
        if parsed is None:
            continue

        # Apply filters
        if cmd:
            rendering = parsed.get("_rendering", {})
            row_vals = rendering.get("row", {}).get("values", {})
            cmd_val = str(row_vals.get("cmd", ""))
            if cmd.lower() not in cmd_val.lower():
                continue
        if time_from:
            entry_time = str(parsed.get("time", ""))
            if entry_time < time_from:
                continue
        if time_to:
            entry_time = str(parsed.get("time", ""))
            if entry_time > time_to:
                continue

        # This entry matches filters
        if matched < offset:
            matched += 1
            continue
        if len(results) < limit:
            results.append(parsed)
            matched += 1
        else:
            # Found one past limit — has_more is true
            has_more = True
            break

    return {"entries": results, "has_more": has_more, "offset": offset, "limit": limit}
```

**Important:** The existing endpoint returns a plain list. The new endpoint returns `{entries, has_more, offset, limit}`. Update the frontend to match.

- [ ] **Step 3: Update LogViewer.tsx to consume paginated response**

In `mav_gss_lib/web/src/components/logs/LogViewer.tsx`, update the `fetchEntries` callback:

```typescript
const [hasMore, setHasMore] = useState(false)
const [currentOffset, setCurrentOffset] = useState(0)
const PAGE_SIZE = 200

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
    .then((data: { entries: LogEntry[]; has_more: boolean; offset: number; limit: number }) => {
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

- [ ] **Step 4: Run tests and build**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE" && conda run -n gnuradio python -m pytest tests/ -q
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build
```

Expected: All tests pass, build succeeds.

- [ ] **Step 5: Commit (including dist/)**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/api.py mav_gss_lib/web/src/components/logs/LogViewer.tsx tests/test_ops_web_runtime.py mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Add pagination to log replay endpoint

/api/logs/{session_id} now accepts offset/limit params. Streams
JSONL with filters, returns bounded results with has_more flag.
LogViewer shows "Load more" button for incremental loading.
EOF
)"
```

---

## Task 9: Extract useLogQuery Hook

**Context:** `LogViewer.tsx` has 14 state variables. The filter/fetch/pagination logic (6 state vars + callbacks) is the highest-value extraction.

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
      .then((data: { entries: LogEntry[]; has_more: boolean; offset: number; limit: number }) => {
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

Replace the state variables and fetch logic in `LogViewer.tsx` with the hook:

```typescript
import { useLogQuery } from '@/hooks/useLogQuery'

export function LogViewer({ open, onClose, onStartReplay }: LogViewerProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<Element | null>(null)
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set())
  const query = useLogQuery()

  // On open: fetch sessions and columns
  useEffect(() => {
    if (!open) return
    query.fetchSessions()
    query.fetchColumns()
  }, [open])

  // On close: reset
  useEffect(() => {
    if (!open) { query.reset(); setExpandedSet(new Set()) }
  }, [open])

  // When selected session or filters change: refetch
  useEffect(() => {
    if (query.selected) query.fetchEntries(query.selected)
  }, [query.selected, query.fetchEntries])

  // ... rest of component uses query.entries, query.sessions, etc.
```

Remove all the individual `useState` calls that were moved into the hook (sessions, selected, entries, loading, cmdFilter, fromTime, toTime, dateFilter, rxColumns, txColumns, and the debounced values).

- [ ] **Step 3: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

Expected: Build and lint pass.

- [ ] **Step 4: Commit (including dist/)**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web/src/hooks/useLogQuery.ts mav_gss_lib/web/src/components/logs/LogViewer.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Extract useLogQuery hook from LogViewer

Filter state, pagination, session/column fetching extracted into
reusable hook. LogViewer reduced by ~60 lines.
EOF
)"
```

---

## Task 10: Extract useRxToggles and useReceivingDetection Hooks

**Files:**
- Create: `mav_gss_lib/web/src/hooks/useRxToggles.ts`
- Create: `mav_gss_lib/web/src/hooks/useReceivingDetection.ts`
- Modify: `mav_gss_lib/web/src/components/rx/RxPanel.tsx`

- [ ] **Step 1: Create useRxToggles.ts**

```typescript
import { useState, useCallback } from 'react'

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

  const showHex = opts.externalShowHex ?? localShowHex
  const showFrame = opts.externalShowFrame ?? localShowFrame
  const showWrapper = opts.externalShowWrapper ?? localShowWrapper
  const hideUplink = opts.externalHideUplink ?? localHideUplink

  const toggleHex = opts.onToggleHex ?? (() => setLocalShowHex(v => !v))
  const toggleFrame = opts.onToggleFrame ?? (() => setLocalShowFrame(v => !v))
  const toggleWrapper = opts.onToggleWrapper ?? (() => setLocalShowWrapper(v => !v))
  const toggleUplink = opts.onToggleUplink ?? (() => setLocalHideUplink(v => !v))

  return {
    showHex, showFrame, showWrapper, hideUplink,
    toggleHex, toggleFrame, toggleWrapper, toggleUplink,
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

Replace the toggle state block (lines 130-141) with:

```typescript
import { useRxToggles } from '@/hooks/useRxToggles'
import { useReceivingDetection } from '@/hooks/useReceivingDetection'

// Inside RxPanel:
const { showHex, showFrame, showWrapper, hideUplink, toggleHex, toggleFrame, toggleWrapper, toggleUplink } = useRxToggles({
  externalShowHex, externalShowFrame, externalShowWrapper, externalHideUplink,
  onToggleHex, onToggleFrame, onToggleWrapper, onToggleUplink,
})

const lastPktNum = packets.length > 0 ? packets[packets.length - 1].num : -1
const receiving = useReceivingDetection(lastPktNum)
```

Remove the old local toggle state (lines 130-141), the receiving state/effect (lines 143, 166-177), and the `prevLastNum` ref.

- [ ] **Step 4: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

Expected: Build and lint pass.

- [ ] **Step 5: Commit (including dist/)**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web/src/hooks/useRxToggles.ts mav_gss_lib/web/src/hooks/useReceivingDetection.ts mav_gss_lib/web/src/components/rx/RxPanel.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Extract useRxToggles and useReceivingDetection from RxPanel
EOF
)"
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
 * Shared bootstrap for pop-out windows: fetches config on mount.
 * Pop-out windows don't live inside AppProvider, so they need their own config.
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

- [ ] **Step 2: Update App.tsx to use the hook**

Replace the duplicated config fetch in `PopOutTx` and `PopOutRx`:

```typescript
import { usePopOutBootstrap } from '@/hooks/usePopOutBootstrap'

function PopOutTx() {
  const { config } = usePopOutBootstrap()
  const tx = useTxSocket()
  const uplinkMode = config?.tx?.uplink_mode ?? ''
  // ... rest unchanged
}

function PopOutRx() {
  const { config } = usePopOutBootstrap()
  const rx = useRxSocket()
  // ... rest unchanged
}
```

Remove the individual `useState<GssConfig | null>(null)` and `useEffect` blocks from both pop-out components.

- [ ] **Step 3: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

Expected: Build and lint pass.

- [ ] **Step 4: Commit (including dist/)**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web/src/hooks/usePopOutBootstrap.ts mav_gss_lib/web/src/App.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Extract usePopOutBootstrap hook from App.tsx pop-out windows
EOF
)"
```

---

## Task 12: Extract useQueueSync Hook (conditional)

**Context:** Only extract if behavior-preservation can be verified. The UID mapping and sync logic in TxQueue is complex. This task should be skipped if the extraction introduces risk.

**Files:**
- Create: `mav_gss_lib/web/src/hooks/useQueueSync.ts`
- Modify: `mav_gss_lib/web/src/components/tx/TxQueue.tsx`

- [ ] **Step 1: Assess extraction feasibility**

Read `TxQueue.tsx` lines 46-109. The UID sync logic depends on:
- `nextUid` module-level counter
- `ignoreNextSync` ref (set by drag handler, read by sync effect)
- `prevLenRef` (tracks queue length changes)
- `flashUid` state (visual feedback)
- `scrollRef` (auto-scroll on grow)

If these can be cleanly extracted without breaking the drag-drop interaction, proceed. If the `ignoreNextSync` coupling to `handleDragEnd` makes extraction unsafe, **skip this task** and leave a comment explaining why.

- [ ] **Step 2: Create useQueueSync.ts (if feasible)**

```typescript
import { useState, useEffect, useRef } from 'react'
import type { TxQueueItem } from '@/lib/types'

let nextUid = 1

interface UidItem {
  item: TxQueueItem
  uid: number
}

export function useQueueSync(queue: TxQueueItem[]) {
  const [uidItems, setUidItems] = useState<UidItem[]>(() =>
    queue.map(item => ({ item, uid: nextUid++ }))
  )
  const [flashUid, setFlashUid] = useState<number | null>(null)
  const ignoreNextSync = useRef(false)
  const prevLenRef = useRef(queue.length)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ignoreNextSync.current) {
      ignoreNextSync.current = false
      prevLenRef.current = queue.length
      return
    }
    setUidItems(prev => {
      const prevLen = prev.length
      const newLen = queue.length
      if (newLen === 0) return []
      if (newLen < prevLen) {
        const removed = prevLen - newLen
        return prev.slice(removed).map((entry, i) => ({ item: queue[i], uid: entry.uid }))
      }
      const kept = prev.map((entry, i) => ({ item: queue[i], uid: entry.uid }))
      const added = queue.slice(prevLen).map(item => ({ item, uid: nextUid++ }))
      const result = [...kept, ...added]
      if (added.length > 0) {
        const newestUid = added[added.length - 1].uid
        setFlashUid(newestUid)
        setTimeout(() => setFlashUid(null), 300)
      }
      return result
    })
    const grew = queue.length > prevLenRef.current
    prevLenRef.current = queue.length
    if (grew) {
      requestAnimationFrame(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = 0
      })
    }
  }, [queue])

  const skipNextSync = () => { ignoreNextSync.current = true }

  return { uidItems, setUidItems, flashUid, scrollRef, skipNextSync }
}
```

- [ ] **Step 3: Update TxQueue.tsx to use the hook**

Replace lines 46-109 with:

```typescript
import { useQueueSync } from '@/hooks/useQueueSync'

// Inside TxQueue:
const { uidItems, setUidItems, flashUid, scrollRef, skipNextSync } = useQueueSync(queue)
```

Update `handleDragEnd` to call `skipNextSync()` instead of `ignoreNextSync.current = true`.

- [ ] **Step 4: Build and lint**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web" && npm run build && npm run lint
```

- [ ] **Step 5: Commit (including dist/)**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web/src/hooks/useQueueSync.ts mav_gss_lib/web/src/components/tx/TxQueue.tsx mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Extract useQueueSync hook from TxQueue
EOF
)"
```

---

## Task 13: Final Verification

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

- [ ] **Step 3: Verify adapter.py line count**

```bash
wc -l "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/missions/maveric/adapter.py"
```

Expected: ~80-120 lines (thin facade).

- [ ] **Step 4: Verify file structure**

```bash
ls -la "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/missions/maveric/"
ls -la "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web_runtime/"
ls -la "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE/mav_gss_lib/web/src/hooks/"
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
- `web/src/hooks/useQueueSync.ts` (if Task 12 was not skipped)

- [ ] **Step 5: Bump version in gss.yml**

Update `general.version` in `gss.yml` to reflect the cleanup release.

- [ ] **Step 6: Final commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add gss.yml mav_gss_lib/web/dist/
git commit -m "$(cat <<'EOF'
Bump version for cleanup release
EOF
)"
```

---

## Task Dependency Graph

```
Task 1 (fix import test) ──── standalone
Task 2 (fix node test)   ──── standalone
Task 3 (tx_queue.py)     ──── standalone (after Tasks 1-2 for green tests)
Task 4 (rx_ops.py)       ──┐
Task 5 (tx_ops.py)       ──┤ sequential — each modifies adapter.py
Task 6 (rendering.py)    ──┤
Task 7 (log_format.py)   ──┘
Task 8 (log pagination)  ──── standalone (after Task 3 for tx_queue imports)
Task 9 (useLogQuery)     ──── after Task 8 (pagination changes LogViewer)
Task 10 (useRxToggles)   ──── standalone
Task 11 (usePopOut)       ──── standalone
Task 12 (useQueueSync)   ──── standalone, conditional
Task 13 (verification)   ──── after all others
```

Tasks 1-2 first. Then Tasks 3 and 4-7 can run in parallel. Tasks 8-12 can run in parallel after their dependencies. Task 13 is always last.
