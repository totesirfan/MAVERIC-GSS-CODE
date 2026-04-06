# Phase 5b-i: Rendering-Slot Contract

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the architecture spec's actual rendering-slot methods (`packet_list_columns`, `packet_list_row`, `packet_detail_blocks`, `protocol_blocks`, `integrity_blocks`) to the `MissionAdapter` Protocol, implement them in `MavericMissionAdapter`, and serve the structured data alongside the existing transitional JSON over the WebSocket.

**Architecture:** Define `ProtocolBlock` and `IntegrityBlock` dataclasses in platform core (`mission_adapter.py`). Add five rendering-slot methods to the `MissionAdapter` Protocol. Implement them in `MavericMissionAdapter`. The WebSocket broadcast adds a `_rendering` key to each packet JSON containing the structured rendering data. The frontend ignores this key until Phase 5b-ii. The existing transitional JSON (`packet_to_json`) continues to be served unchanged for backward compatibility.

**Tech Stack:** Python 3.10+, dataclasses

---

## Design Decisions

1. **`ProtocolBlock` and `IntegrityBlock` are platform core.** They go in `mission_adapter.py` alongside `ParsedPacket`. These are the spec's standardized contracts — the platform owns how they are rendered.

2. **Five rendering-slot methods go on the `MissionAdapter` Protocol.** These are the spec's actual rendering contract, not transitional shims:
   - `packet_list_columns() -> list[dict]`
   - `packet_list_row(pkt) -> dict`
   - `packet_detail_blocks(pkt) -> list[dict]`
   - `protocol_blocks(pkt) -> list[dict]`
   - `integrity_blocks(pkt) -> list[dict]`

3. **WebSocket adds `_rendering` key to each packet.** The packet broadcast becomes `{"type": "packet", "data": {<existing flat JSON>, "_rendering": {row, detail_blocks, protocol_blocks, integrity_blocks}}}`. The underscore prefix signals this is a parallel structure, not yet consumed by the frontend.

4. **Column definitions are sent as a separate `columns` message on WebSocket connect.** `packet_list_columns()` returns the same value for every packet — it's called once and sent as `{"type": "columns", "data": [...]}` immediately after `accept()`, before any packet replay. Columns are NOT included in per-packet `_rendering` since they are static.

5. **The Phase 5a transitional methods remain.** They coexist until Phase 5b-ii migrates the frontend to consume `_rendering` instead.

## File Plan

| Action | File | Change |
|---|---|---|
| Modify | `mav_gss_lib/mission_adapter.py` | Add `ProtocolBlock`, `IntegrityBlock` dataclasses + 5 rendering-slot methods to Protocol |
| Modify | `mav_gss_lib/missions/maveric/adapter.py` | Implement 5 rendering-slot methods |
| Modify | `mav_gss_lib/web_runtime/services.py` | Include `_rendering` in packet broadcast |
| Modify | `mav_gss_lib/web_runtime/rx.py` | Send `columns` message on WebSocket connect before packet replay |

## Test Commands

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

---

## Task 1: Add Platform Core Dataclasses

**Files:**
- Modify: `mav_gss_lib/mission_adapter.py`

- [ ] **Step 1: Add ProtocolBlock and IntegrityBlock dataclasses**

In `mav_gss_lib/mission_adapter.py`, add these two dataclasses after `ParsedPacket` and before the `MissionAdapter` Protocol:

```python
# =============================================================================
#  PLATFORM CORE -- Rendering Contracts
# =============================================================================

@dataclass
class ProtocolBlock:
    """Standardized protocol/wrapper information for the detail view.

    The platform owns how these are rendered. Missions provide the data.
    """
    kind: str        # e.g. "csp", "ax25"
    label: str       # e.g. "CSP V1", "AX.25"
    fields: list     # list of {"name": str, "value": str}


@dataclass
class IntegrityBlock:
    """Standardized integrity check result for the detail view.

    The platform owns how these are rendered. Missions provide the data.
    """
    kind: str                    # e.g. "crc16", "crc32c"
    label: str                   # e.g. "CRC-16", "CRC-32C"
    scope: str                   # e.g. "command", "csp"
    ok: bool | None              # True/False/None (unknown)
    received: str | None = None  # e.g. "0x1234"
    computed: str | None = None  # e.g. "0x1234"
```

- [ ] **Step 2: Add rendering-slot methods to MissionAdapter Protocol**

Add these five methods to the `MissionAdapter` Protocol class, after the existing `validate_tx_args`:

```python
    # -- Rendering-slot contract (architecture spec §4) --
    def packet_list_columns(self) -> list[dict]: ...
    def packet_list_row(self, pkt) -> dict: ...
    def packet_detail_blocks(self, pkt) -> list[dict]: ...
    def protocol_blocks(self, pkt) -> list: ...
    def integrity_blocks(self, pkt) -> list: ...
```

- [ ] **Step 3: Update the facade re-export**

At the bottom of `mission_adapter.py`, update the existing imports section to also export the new dataclasses. The re-export line for `MavericMissionAdapter` stays as-is. Just ensure `ProtocolBlock` and `IntegrityBlock` are importable:

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.mission_adapter import (
    ParsedPacket, MissionAdapter, MavericMissionAdapter,
    ProtocolBlock, IntegrityBlock,
)
print('ProtocolBlock:', ProtocolBlock(kind='csp', label='CSP V1', fields=[{'name': 'Src', 'value': '2'}]))
print('IntegrityBlock:', IntegrityBlock(kind='crc32c', label='CRC-32C', scope='csp', ok=True, received='0x1234', computed='0x1234'))
print('OK')
"
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add mav_gss_lib/mission_adapter.py
git commit -m "Add ProtocolBlock, IntegrityBlock, and rendering-slot methods to MissionAdapter Protocol"
```

---

## Task 2: Implement `packet_list_columns` and `packet_list_row` in MAVERIC Adapter

**Files:**
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Add `packet_list_columns` method**

Add to `MavericMissionAdapter`, after the existing transitional methods:

```python
    # -- Rendering-slot contract (architecture spec) --

    def packet_list_columns(self) -> list[dict]:
        """Return column definitions for the RX packet list.

        Each column has: id (data key), label (header text), and optional
        width hint. The platform renders these; the mission defines them.
        """
        return [
            {"id": "num",   "label": "#",         "align": "right", "width": "w-10"},
            {"id": "time",  "label": "time",      "width": "w-[72px]"},
            {"id": "frame", "label": "frame",     "width": "w-[76px]", "toggle": "showFrame"},
            {"id": "src",   "label": "src",       "width": "w-[84px]"},
            {"id": "echo",  "label": "echo",      "width": "w-[84px]", "toggle": "showEcho"},
            {"id": "ptype", "label": "type",       "width": "w-[52px]", "badge": True},
            {"id": "cmd",   "label": "cmd / args", "flex": True},
            {"id": "flags", "label": "",           "width": "w-[76px]", "align": "right"},
            {"id": "size",  "label": "size",       "align": "right", "width": "w-12"},
        ]
```

- [ ] **Step 2: Add `packet_list_row` method**

```python
    def packet_list_row(self, pkt) -> dict:
        """Return row values keyed by column ID for one packet.

        Values are display-ready strings/primitives. The platform renders
        them in the column slots defined by packet_list_columns().
        """
        cmd = pkt.cmd
        # Build args summary
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

        # Build flags list
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
            "num": pkt.pkt_num,
            "time": pkt.gs_ts_short,
            "frame": pkt.frame_type,
            "src": node_name(cmd["src"]) if cmd else "",
            "echo": node_name(cmd["echo"]) if cmd else "",
            "ptype": ptype_name(cmd["pkt_type"]) if cmd else "",
            "cmd": cmd["cmd_id"] if cmd else "",
            "args": args_str,
            "flags": flags,
            "size": len(pkt.raw),
            "opacity": 0.5 if pkt.is_unknown else 1.0,
        }
```

- [ ] **Step 3: Smoke test**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.missions.maveric.wire_format import init_nodes
cfg = {'nodes': {0: 'NONE', 2: 'EPS', 6: 'GS'}, 'ptypes': {1: 'CMD'}, 'general': {'gs_node': 'GS'}}
init_nodes(cfg)
from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter
adapter = MavericMissionAdapter(cmd_defs={})
cols = adapter.packet_list_columns()
print('columns:', len(cols))
for c in cols:
    print(f'  {c[\"id\"]:8s} -> {c[\"label\"]}')
print('OK')
"
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add mav_gss_lib/missions/maveric/adapter.py
git commit -m "Implement packet_list_columns and packet_list_row in MavericMissionAdapter"
```

---

## Task 3: Implement `packet_detail_blocks`, `protocol_blocks`, `integrity_blocks`

**Files:**
- Modify: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Add import for platform dataclasses**

**Import strategy:** `mission_adapter.py` imports `MavericMissionAdapter` from this file at module level (facade re-export). If we import `ProtocolBlock`/`IntegrityBlock` from `mission_adapter.py` at module level here, we create a circular import. Use lazy imports inside the methods that need them, matching the existing pattern used for `ParsedPacket`:

```python
    # Inside each method that needs them:
    from mav_gss_lib.mission_adapter import ProtocolBlock, IntegrityBlock
```

- [ ] **Step 2: Add `protocol_blocks` method**

```python
    def protocol_blocks(self, pkt) -> list:
        """Return protocol/wrapper blocks for the detail view.

        These are rendered by the platform in a fixed protocol section.
        """
        blocks = []
        if pkt.csp:
            blocks.append(ProtocolBlock(
                kind="csp",
                label="CSP V1",
                fields=[{"name": k.capitalize(), "value": str(v)} for k, v in pkt.csp.items()],
            ))
        if pkt.stripped_hdr:
            blocks.append(ProtocolBlock(
                kind="ax25",
                label="AX.25",
                fields=[{"name": "Header", "value": pkt.stripped_hdr}],
            ))
        return blocks
```

- [ ] **Step 3: Add `integrity_blocks` method**

```python
    def integrity_blocks(self, pkt) -> list:
        """Return integrity check blocks for the detail view.

        These are rendered by the platform in a fixed integrity section.
        """
        blocks = []
        cmd = pkt.cmd
        # Command-level CRC-16
        if cmd and cmd.get("crc") is not None:
            blocks.append(IntegrityBlock(
                kind="crc16",
                label="CRC-16",
                scope="command",
                ok=cmd.get("crc_valid"),
                received=f"0x{cmd['crc']:04X}" if cmd.get("crc") is not None else None,
            ))
        # CSP-level CRC-32C
        crc_status = pkt.crc_status
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
```

- [ ] **Step 4: Add `packet_detail_blocks` method**

```python
    def packet_detail_blocks(self, pkt) -> list[dict]:
        """Return mission-specific semantic blocks for the detail view.

        These are rendered by the platform in the mission semantic area.
        Protocol and integrity blocks are separate (protocol_blocks / integrity_blocks).
        """
        cmd = pkt.cmd
        blocks = []

        # Time block
        time_block = {"kind": "time", "label": "Time", "fields": [
            {"name": "GS Time", "value": pkt.gs_ts},
        ]}
        if pkt.ts_result:
            dt_utc, dt_local, ms = pkt.ts_result
            if dt_utc:
                time_block["fields"].append({"name": "SAT UTC", "value": dt_utc.strftime("%H:%M:%S") + " UTC"})
            if dt_local:
                time_block["fields"].append({"name": "SAT Local", "value": dt_local.strftime("%H:%M:%S %Z")})
        blocks.append(time_block)

        # Routing block (mission-semantic: MAVERIC src/dest/echo/ptype)
        if cmd:
            blocks.append({"kind": "routing", "label": "Routing", "fields": [
                {"name": "Src", "value": node_name(cmd["src"])},
                {"name": "Dest", "value": node_name(cmd["dest"])},
                {"name": "Echo", "value": node_name(cmd["echo"])},
                {"name": "Type", "value": ptype_name(cmd["pkt_type"])},
                {"name": "Cmd", "value": cmd["cmd_id"]},
            ]})

        # Args block
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
```

- [ ] **Step 5: Smoke test**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
import json
from dataclasses import asdict
from mav_gss_lib.missions.maveric.wire_format import init_nodes
cfg = {'nodes': {0: 'NONE', 2: 'EPS', 6: 'GS'}, 'ptypes': {1: 'CMD'}, 'general': {'gs_node': 'GS'}}
init_nodes(cfg)

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter
from mav_gss_lib.mission_adapter import MissionAdapter
adapter = MavericMissionAdapter(cmd_defs={})

# Verify Protocol conformance
print('isinstance:', isinstance(adapter, MissionAdapter))

# Test protocol_blocks and integrity_blocks with a mock packet
class MockPkt:
    cmd = {'src': 6, 'dest': 2, 'echo': 0, 'pkt_type': 1, 'cmd_id': 'ping', 'args': [], 'crc': 0x1234, 'crc_valid': True}
    csp = {'prio': 2, 'src': 0, 'dest': 8}
    stripped_hdr = 'aa bb cc'
    crc_status = {'csp_crc32_valid': True, 'csp_crc32_rx': 0x12345678, 'csp_crc32_comp': 0x12345678}
    gs_ts = '2026-04-06T10:30:00'
    gs_ts_short = '10:30:00'
    ts_result = None
    pkt_num = 1
    frame_type = 'AX.25'
    raw = b'test'
    is_uplink_echo = False
    is_dup = False
    is_unknown = False
    warnings = []

pkt = MockPkt()
pb = adapter.protocol_blocks(pkt)
print('protocol_blocks:', len(pb))
for b in pb:
    print(f'  {b.kind}: {b.label}')

ib = adapter.integrity_blocks(pkt)
print('integrity_blocks:', len(ib))
for b in ib:
    print(f'  {b.kind}: {b.label} ok={b.ok}')

db = adapter.packet_detail_blocks(pkt)
print('detail_blocks:', len(db))
for b in db:
    print(f'  {b[\"kind\"]}: {b[\"label\"]} ({len(b[\"fields\"])} fields)')

print('OK')
"
```

- [ ] **Step 6: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -q
```

- [ ] **Step 7: Commit**

```bash
git add mav_gss_lib/missions/maveric/adapter.py
git commit -m "Implement protocol_blocks, integrity_blocks, packet_detail_blocks in MAVERIC adapter"
```

---

## Task 4: Serve Rendering Data via WebSocket

**Files:**
- Modify: `mav_gss_lib/web_runtime/services.py`

- [ ] **Step 1: Add rendering data to packet broadcast**

In `RxService.broadcast_loop()`, find where `pkt_json` is constructed (around line 119):

```python
                pkt_json = self.packet_to_json(pkt)
```

After this line, add the rendering data:

```python
                pkt_json["_rendering"] = self._build_rendering(pkt)
```

- [ ] **Step 2: Add `_build_rendering` helper to RxService**

Add this method to `RxService`, after `packet_to_json`:

```python
    def _build_rendering(self, pkt) -> dict:
        """Build structured rendering-slot data for one packet."""
        from dataclasses import asdict
        adapter = self.runtime.adapter
        return {
            "row": adapter.packet_list_row(pkt),
            "detail_blocks": adapter.packet_detail_blocks(pkt),
            "protocol_blocks": [asdict(b) for b in adapter.protocol_blocks(pkt)],
            "integrity_blocks": [asdict(b) for b in adapter.integrity_blocks(pkt)],
        }
```

- [ ] **Step 3: Add column definitions to WebSocket connect**

In `mav_gss_lib/web_runtime/rx.py`, the WebSocket handler accepts the connection, then immediately replays buffered packets before adding the client to the live broadcast list. Column definitions must arrive **before** any packet data so the frontend can interpret `_rendering.row` fields correctly.

Insert the columns message right after `accept()` (line 20) and before the packet replay loop (line 22):

```python
    await websocket.accept()
    runtime.had_clients = True
    # Send column definitions before any packet data
    columns = runtime.adapter.packet_list_columns()
    await websocket.send_text(json.dumps({"type": "columns", "data": columns}))
    for pkt_json in list(runtime.rx.packets):
```

`json` is already imported at the top of `rx.py`.

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -q
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/web_runtime/services.py mav_gss_lib/web_runtime/rx.py
git commit -m "Serve rendering-slot data alongside packet JSON over WebSocket"
```

---

## Task 5: Final Verification

- [ ] **Step 1: Verify full rendering pipeline end-to-end**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
import json
from dataclasses import asdict
from mav_gss_lib.web_runtime.state import WebRuntime
from mav_gss_lib.mission_adapter import MissionAdapter, ProtocolBlock, IntegrityBlock

rt = WebRuntime()
adapter = rt.adapter

# Verify Protocol conformance with new methods
print('isinstance:', isinstance(adapter, MissionAdapter))

# Verify columns
cols = adapter.packet_list_columns()
print('columns:', [c['id'] for c in cols])

# Verify dataclass serialization
pb = ProtocolBlock(kind='csp', label='CSP V1', fields=[{'name': 'Src', 'value': '2'}])
print('protocol block JSON:', json.dumps(asdict(pb)))

ib = IntegrityBlock(kind='crc32c', label='CRC-32C', scope='csp', ok=True)
print('integrity block JSON:', json.dumps(asdict(ib)))

print('OK')
"
```

- [ ] **Step 2: Run both test suites**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add -A
git commit -m "Phase 5b-i complete: rendering-slot contract on MissionAdapter Protocol"
```

---

## Post-Phase 5b-i State

**What was added:**
- `ProtocolBlock` and `IntegrityBlock` dataclasses in platform core
- 5 rendering-slot methods on `MissionAdapter` Protocol (the spec's actual contract)
- `MavericMissionAdapter` implements all 5 methods
- WebSocket sends `_rendering` key with structured data alongside each packet
- WebSocket sends `columns` message on connect

**What coexists (transitional):**
- Phase 5a's `packet_to_json`, `queue_item_to_json`, `history_entry` on `MavericMissionAdapter`
- The flat MAVERIC JSON fields in the packet broadcast
- Frontend consuming the flat fields

**What Phase 5b-ii will do:**
- Migrate frontend components to render from `_rendering` data
- Remove flat MAVERIC fields from packet broadcast
- Remove Phase 5a transitional methods from adapter

**Spec coverage check:**
- Architecture spec §2 ProtocolBlock contract → Task 1 ✓
- Architecture spec §3 IntegrityBlock contract → Task 1 ✓
- Architecture spec §4 Rendering slots → Tasks 2–3 ✓
- Architecture spec adapter contract `packet_list_columns` → Task 2 ✓
- Architecture spec adapter contract `packet_list_row` → Task 2 ✓
- Architecture spec adapter contract `packet_detail_blocks` → Task 3 ✓
- Architecture spec adapter contract `protocol_blocks` → Task 3 ✓
- Architecture spec adapter contract `integrity_blocks` → Task 3 ✓
