# Phase 4: Make MAVERIC a Mission Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all MAVERIC-specific code (node tables, command wire format, command schema, adapter implementation, imaging) into `missions/maveric/`, leaving `protocol.py` and `mission_adapter.py` as compatibility facades.

**Architecture:** Same pattern as Phase 3 — physically move code to its target location, leave facades with re-exports so all existing imports continue to work. Additionally, define a formal `MissionAdapter` Protocol in core and add `ADAPTER_API_VERSION = 1` to the MAVERIC mission package. No runtime behavior changes. No downstream import changes.

**Tech Stack:** Python 3.10+, PyYAML, crcmod

---

## Design Decisions

1. **`protocol.py` remains a facade.** After Phase 4, it re-exports from both `protocols/` (Phase 3) and `missions/maveric/wire_format` (Phase 4). All 22 downstream importers continue to work unchanged.

2. **`mission_adapter.py` remains a facade.** `ParsedPacket` (platform core) stays defined there. `MavericMissionAdapter` moves to `missions/maveric/adapter.py` and is re-exported. A formal `MissionAdapter` Protocol is defined in core alongside `ParsedPacket`.

3. **`imaging.py` becomes a facade.** `ImageAssembler` moves to `missions/maveric/imaging.py`.

4. **`config.py` is NOT changed in Phase 4.** The `_DEFAULTS` extraction is a Phase 5/6 concern per the inventory design note.

5. **TUI decision (Phase 4 final): the TUI is a MAVERIC-only legacy shell.** It does not consume the `MissionAdapter` Protocol and is not expected to work with non-MAVERIC missions. It continues importing from the `protocol.py` facade. If a future mission needs a TUI, it would be a new implementation. This is a closed decision, not a deferral.

6. **No `missions/maveric/mission.yml` in Phase 4.** Mission metadata YAML is a Phase 5/6 deliverable. The command schema (`maveric_commands.yml`) stays where it is.

7. **Dependency direction:** `missions/maveric/` imports from `protocols/` and stdlib only. Never from `protocol.py` or `mission_adapter.py`. Facades import from `missions/maveric/`. No cycles.

8. **Phase 5 prerequisite noted:** `web_runtime/state.py` directly instantiates `MavericMissionAdapter`. Phase 4 does not change this — the facade re-export keeps it working. But Phase 5 must replace direct construction with mission-selected adapter injection via `general.mission` config, as specified in the architecture spec. This is recorded here so it is not forgotten.

## File Plan

| Action | File | Responsibility |
|---|---|---|
| Create | `mav_gss_lib/missions/__init__.py` | Package marker |
| Create | `mav_gss_lib/missions/maveric/__init__.py` | MAVERIC mission package marker + ADAPTER_API_VERSION |
| Create | `mav_gss_lib/missions/maveric/wire_format.py` | All MAVERIC wire format: node tables, CommandFrame, command schema, parse_cmd_line, format_arg_value |
| Create | `mav_gss_lib/missions/maveric/adapter.py` | MavericMissionAdapter (moved from mission_adapter.py) |
| Create | `mav_gss_lib/missions/maveric/imaging.py` | ImageAssembler (moved from imaging.py) |
| Modify | `mav_gss_lib/protocol.py` | Facade: replace MAVERIC code with re-exports from missions/maveric/wire_format |
| Modify | `mav_gss_lib/mission_adapter.py` | Facade: keep ParsedPacket + MissionAdapter Protocol, re-export MavericMissionAdapter |
| Modify | `mav_gss_lib/imaging.py` | Facade: re-export from missions/maveric/imaging |

## Test Commands

```bash
# In-repo tests (44 tests)
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

# Parent-dir tests (24 tests)
cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

## Compatibility Rules

1. Every existing `from mav_gss_lib.protocol import X` continues to work.
2. Every existing `from mav_gss_lib.mission_adapter import X` continues to work.
3. Every existing `from mav_gss_lib.imaging import X` continues to work.
4. `missions/maveric/` modules must NOT import from `protocol.py` or `mission_adapter.py`.
5. `__init__.py` in `mav_gss_lib/` is not changed.

---

## Task 1: Create `missions/` Package Structure

**Files:**
- Create: `mav_gss_lib/missions/__init__.py`
- Create: `mav_gss_lib/missions/maveric/__init__.py`

- [ ] **Step 1: Create the missions package**

`mav_gss_lib/missions/__init__.py`:
```python
"""
mav_gss_lib.missions -- Mission Implementation Packages

Each subdirectory is a mission package providing:
  - wire_format.py: command/packet wire format
  - adapter.py: MissionAdapter implementation
  - mission.yml: mission metadata (future)
  - commands.yml: command schema (future)
"""
```

`mav_gss_lib/missions/maveric/__init__.py`:
```python
"""
mav_gss_lib.missions.maveric -- MAVERIC CubeSat Mission Implementation

Wire format, command schema, adapter, and imaging for the MAVERIC mission.
"""

ADAPTER_API_VERSION = 1
```

- [ ] **Step 2: Verify package imports**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
import mav_gss_lib.missions
import mav_gss_lib.missions.maveric
print('version:', mav_gss_lib.missions.maveric.ADAPTER_API_VERSION)
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/missions/
git commit -m "Add missions/ package structure with MAVERIC mission marker"
```

---

## Task 2: Create `missions/maveric/wire_format.py`

This is the largest task — all MAVERIC-specific wire format code moves here from `protocol.py`.

**Files:**
- Create: `mav_gss_lib/missions/maveric/wire_format.py`

- [ ] **Step 1: Create the wire format module**

This file contains everything that was MAVERIC-specific in `protocol.py`. It imports CRC from `protocols.crc` (never from `protocol.py`).

```python
"""
mav_gss_lib.missions.maveric.wire_format -- MAVERIC Command Wire Format

Node addressing, packet type tables, command frame encode/decode,
command schema loading/validation, TX command line parser, and
display formatting for the MAVERIC mission.

Author:  Irfan Annuar - USC ISI SERC
"""

import os
import warnings
from datetime import datetime, timezone

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

from mav_gss_lib.protocols.crc import crc16
from mav_gss_lib.protocols.csp import kiss_wrap


# =============================================================================
#  NODE & PACKET TYPE DEFINITIONS
# =============================================================================

NODE_NAMES = {}   # int -> str, populated by init_nodes()
NODE_IDS   = {}   # str -> int
PTYPE_NAMES = {}  # int -> str, populated by init_nodes()
PTYPE_IDS   = {}  # str -> int
GS_NODE     = 6   # default, updated by init_nodes()
_initialized = False


def init_nodes(cfg):
    """Populate node/ptype tables from a loaded config dict.

    Must be called once at startup after load_gss_config().
    """
    global NODE_NAMES, NODE_IDS, PTYPE_NAMES, PTYPE_IDS, GS_NODE, _initialized

    NODE_NAMES = {int(k): v for k, v in cfg["nodes"].items()}
    NODE_IDS   = {v: k for k, v in NODE_NAMES.items()}

    PTYPE_NAMES = {int(k): v for k, v in cfg["ptypes"].items()}
    PTYPE_IDS   = {v: k for k, v in PTYPE_NAMES.items()}

    gs_name = cfg.get("general", {}).get("gs_node", "GS")
    GS_NODE = NODE_IDS.get(gs_name, 6)
    _initialized = True


def _lookup_name(id_val, names):
    """Short name from ID: 'EPS' or '99' if unknown."""
    return names.get(id_val, str(id_val))

def _format_label(id_val, names):
    """Format ID for display: 'EPS' or '99' if unknown."""
    return names.get(id_val, str(id_val))

def _resolve_id(s, name_to_id, id_to_name):
    """Resolve a name ('EPS') or numeric string ('2') to an int ID.
    Returns int ID or None if unrecognized."""
    upper = s.upper()
    if upper in name_to_id:
        return name_to_id[upper]
    if s.isdigit():
        val = int(s)
        if val in id_to_name:
            return val
    return None

def node_name(node_id):    return _lookup_name(node_id, NODE_NAMES)
def ptype_name(ptype_id):  return _lookup_name(ptype_id, PTYPE_NAMES)
def node_label(node_id):   return _format_label(node_id, NODE_NAMES)
def ptype_label(ptype_id): return _format_label(ptype_id, PTYPE_NAMES)
def resolve_node(s):       return _resolve_id(s, NODE_IDS, NODE_NAMES)
def resolve_ptype(s):      return _resolve_id(s, PTYPE_IDS, PTYPE_NAMES)


# =============================================================================
#  COMMAND WIRE FORMAT
# =============================================================================

_CMD_HDR_LEN = 6  # origin, dest, echo, ptype, id_len, args_len

class CommandFrame:
    """Symmetric encode/decode for the MAVERIC command wire format."""
    __slots__ = ("src", "dest", "echo", "pkt_type", "cmd_id", "args_str",
                 "args_raw", "crc", "crc_valid", "csp_crc32")

    def __init__(self, src, dest, echo, pkt_type, cmd_id, args_str="",
                 args_raw=b"", crc=None, crc_valid=None, csp_crc32=None):
        self.src = src
        self.dest = dest
        self.echo = echo
        self.pkt_type = pkt_type
        self.cmd_id = cmd_id
        self.args_str = args_str
        self.args_raw = args_raw
        self.crc = crc
        self.crc_valid = crc_valid
        self.csp_crc32 = csp_crc32

    def to_bytes(self):
        """Encode to raw wire bytes including CRC-16."""
        header = bytes([self.src & 0xFF, self.dest & 0xFF,
                        self.echo & 0xFF, self.pkt_type & 0xFF,
                        len(self.cmd_id) & 0xFF, len(self.args_str) & 0xFF])
        packet = bytearray(header)
        packet.extend(self.cmd_id.encode('ascii'))
        packet.append(0x00)
        packet.extend(self.args_str.encode('ascii'))
        packet.append(0x00)
        crc_val = crc16(packet)
        packet.extend(crc_val.to_bytes(2, byteorder='little'))
        return packet

    @classmethod
    def from_bytes(cls, payload):
        """Decode wire bytes into (CommandFrame, tail) or (None, None)."""
        if len(payload) < _CMD_HDR_LEN:
            return None, None

        src, dest, echo, pkt_type = payload[0], payload[1], payload[2], payload[3]
        id_len, args_len = payload[4], payload[5]

        if _CMD_HDR_LEN + id_len + 1 + args_len + 1 > len(payload):
            return None, None

        id_start = _CMD_HDR_LEN
        cmd_id = payload[id_start:id_start + id_len].decode("ascii", errors="replace").lower()

        null_pos = id_start + id_len
        if null_pos < len(payload) and payload[null_pos] == 0x00:
            null_pos += 1

        args_end = null_pos + args_len
        args_raw = bytes(payload[null_pos:args_end])
        args_str = args_raw.decode("ascii", errors="replace").strip()

        tail_start = args_end
        if tail_start < len(payload) and payload[tail_start] == 0x00:
            tail_start += 1

        # CRC-16 XMODEM (command integrity)
        crc_val = None
        crc_valid = None
        if tail_start + 2 <= len(payload):
            crc_val = payload[tail_start] | (payload[tail_start + 1] << 8)
            crc_valid = crc_val == crc16(payload[:tail_start])
            tail_start += 2
        else:
            crc_valid = False  # truncated frame -- CRC missing

        # CRC-32C (CSP packet integrity) -- consume if exactly 4 bytes remain
        csp_crc32 = None
        tail = payload[tail_start:]
        if len(tail) == 4:
            csp_crc32 = int.from_bytes(tail, 'big')
            tail = b""

        frame = cls(src, dest, echo, pkt_type, cmd_id, args_str,
                    args_raw, crc_val, crc_valid, csp_crc32)
        return frame, tail

    def to_dict(self):
        """Convert to dict (backward-compatible with old try_parse_command output)."""
        d = {
            "src": self.src, "dest": self.dest, "echo": self.echo,
            "pkt_type": self.pkt_type, "cmd_id": self.cmd_id,
            "args": self.args_str.split(), "crc": self.crc,
            "crc_valid": self.crc_valid, "csp_crc32": self.csp_crc32,
        }
        if self.args_raw:
            d["args_raw"] = self.args_raw
        return d


def build_cmd_raw(dest, cmd, args="", echo=0, ptype=1, origin=None):
    """Build raw MAVERIC command payload with CRC-16."""
    if origin is None:
        origin = GS_NODE
    return CommandFrame(origin, dest, echo, ptype, cmd, args).to_bytes()


def build_kiss_cmd(dest, cmd, args="", echo=0, ptype=1, origin=None):
    """Build a complete KISS-wrapped command.
    Returns (kiss_bytes, raw_bytes)."""
    raw = build_cmd_raw(dest, cmd, args, echo, ptype, origin)
    return kiss_wrap(raw), raw


def try_parse_command(payload):
    """Attempt to parse a byte payload as a MAVERIC command structure.

    Returns (parsed_dict, remaining_bytes) or (None, None) on failure."""
    frame, tail = CommandFrame.from_bytes(payload)
    if frame is None:
        return None, None
    return frame.to_dict(), tail


# =============================================================================
#  COMMAND SCHEMA -- Deterministic Parsing
# =============================================================================

TS_MIN_MS = 1_704_067_200_000  # ~2024-01-01
TS_MAX_MS = 1_830_297_600_000  # ~2028-01-01

class _LazyEpochMs:
    """Lazy epoch-ms timestamp -- stores raw ms, resolves to datetime on access."""
    __slots__ = ('ms', '_resolved')

    def __init__(self, ms):
        self.ms = ms
        self._resolved = None

    def _ensure(self):
        if self._resolved is None:
            dt_utc = datetime.fromtimestamp(self.ms / 1000.0, tz=timezone.utc)
            self._resolved = {"ms": self.ms, "utc": dt_utc, "local": dt_utc.astimezone()}
        return self._resolved

    def __contains__(self, key):
        return key in ("ms", "utc", "local")

    def __getitem__(self, key):
        return self._ensure()[key]

    def get(self, key, default=None):
        return self._ensure().get(key, default)


def _parse_epoch_ms(value_str):
    """Convert string to a lazy timestamp wrapper."""
    try:
        ms = int(value_str)
        if TS_MIN_MS <= ms <= TS_MAX_MS:
            return _LazyEpochMs(ms)
    except (ValueError, TypeError, OSError):
        pass
    return value_str


_TYPE_PARSERS = {
    "str":      str,
    "int":      lambda s: int(s, 0),
    "float":    float,
    "epoch_ms": _parse_epoch_ms,
    "bool":     lambda s: s.lower() in ("true", "1", "yes"),
}


def _parse_arg_list(raw_list):
    """Parse a list of arg dicts from YAML into internal format."""
    args = []
    for a in (raw_list or []):
        name = a.get("name", f"arg{len(args)}")
        typ = a.get("type", "str")
        if typ not in _TYPE_PARSERS and typ != "blob":
            typ = "str"
        entry = {"name": name, "type": typ}
        if a.get("important"):
            entry["important"] = True
        args.append(entry)
    return args


def load_command_defs(path=None):
    """Load command definitions from YAML.

    Returns (defs, warning) where defs is a dict of command schemas.
    Returns (empty dict, warning) on any failure."""
    from pathlib import Path as _Path
    _cfg_dir = _Path(__file__).resolve().parent.parent.parent / "config"
    if path is None:
        path = str(_cfg_dir / "maveric_commands.yml")
    elif not os.path.isabs(path):
        path = str(_cfg_dir / path)
    if not _YAML_OK:
        msg = ("PyYAML not installed -- command schema unavailable. "
               "Install with: pip install pyyaml")
        warnings.warn(msg, stacklevel=2)
        return {}, msg
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
        # Global defaults
        gd = raw.get("defaults") or {}
        def_echo = resolve_node(str(gd.get("echo", "NONE")))
        def_ptype = resolve_ptype(str(gd.get("ptype", "CMD")))
        if def_echo is None:
            def_echo = 0
        if def_ptype is None:
            def_ptype = 1

        defs = {}
        for cmd_id, spec in (raw.get("commands") or {}).items():
            spec = spec or {}
            tx_args = _parse_arg_list(spec.get("tx_args"))
            rx_args = _parse_arg_list(spec.get("rx_args"))

            # Resolve routing
            dest = None
            if "dest" in spec:
                dest = resolve_node(str(spec["dest"]))
            echo = resolve_node(str(spec["echo"])) if "echo" in spec else def_echo
            ptype = resolve_ptype(str(spec["ptype"])) if "ptype" in spec else def_ptype

            defs[cmd_id.lower()] = {
                "tx_args":  tx_args,
                "rx_args":  rx_args,
                "variadic": spec.get("variadic", False),
                "rx_only":  spec.get("rx_only", False),
                "nodes":    spec.get("nodes", []),
                "dest":     dest,
                "echo":     echo if echo is not None else 0,
                "ptype":    ptype if ptype is not None else 1,
            }
        return defs, None
    except (OSError, yaml.YAMLError, AttributeError):
        msg = f"Could not load {path} -- all commands will be unrecognized"
        warnings.warn(msg, stacklevel=2)
        return {}, msg


def apply_schema(cmd, cmd_defs):
    """Enrich a parsed command dict with typed argument values.

    Returns True if schema was applied, False otherwise."""
    if not cmd_defs or cmd["cmd_id"] not in cmd_defs:
        cmd["schema_match"] = False
        cmd["schema_warning"] = (
            f"Unknown command '{cmd['cmd_id']}' "
            "-- add to maveric_commands.yml for typed parsing"
        )
        return False

    defn = cmd_defs[cmd["cmd_id"]]
    raw_args = cmd["args"]
    rx_args = defn["rx_args"]
    typed = []
    sat_time = None

    for i, arg_def in enumerate(rx_args):
        if arg_def["type"] == "blob":
            args_raw = cmd.get("args_raw", b"")
            offset = 0
            for _ in range(i):
                sp = args_raw.find(0x20, offset)
                if sp == -1:
                    break
                offset = sp + 1
            value = bytes(args_raw[offset:])
            typed.append({"name": arg_def["name"], "type": "blob", "value": value})
            break
        if i < len(raw_args):
            parser = _TYPE_PARSERS.get(arg_def["type"], str)
            try:
                value = parser(raw_args[i])
            except (ValueError, TypeError):
                value = raw_args[i]
            ta = {
                "name":  arg_def["name"],
                "type":  arg_def["type"],
                "value": value,
            }
            if arg_def.get("important"):
                ta["important"] = True
            typed.append(ta)
            if arg_def["type"] == "epoch_ms" and isinstance(value, (_LazyEpochMs, dict)) and sat_time is None:
                sat_time = (value["utc"], value["local"], value["ms"])

    extra = raw_args[len(rx_args):]

    cmd["typed_args"]   = typed
    cmd["extra_args"]   = extra
    cmd["sat_time"]     = sat_time
    cmd["schema_match"] = True
    cmd["dest_default"] = defn.get("dest")
    cmd["rx_only"]      = defn.get("rx_only", False)
    return True


def validate_args(cmd_id, args_str, cmd_defs):
    """Validate args string against schema before sending (TX side).

    Returns (is_valid, list_of_issues)."""
    if not cmd_defs or cmd_id not in cmd_defs:
        return True, []

    defn = cmd_defs[cmd_id]
    if defn.get("rx_only"):
        return False, [f"'{cmd_id}' is receive-only"]

    raw_args = args_str.split() if args_str else []
    tx_args = defn["tx_args"]
    issues = []

    if len(raw_args) < len(tx_args):
        issues.append(
            f"expected {len(tx_args)} args, got {len(raw_args)}"
        )

    if len(raw_args) > len(tx_args) and not defn["variadic"]:
        issues.append(
            f"extra args: expected {len(tx_args)}, got {len(raw_args)}"
        )

    for i, arg_def in enumerate(tx_args):
        if i >= len(raw_args):
            break
        parser = _TYPE_PARSERS.get(arg_def["type"], str)
        try:
            parser(raw_args[i])
        except (ValueError, TypeError):
            issues.append(
                f"arg '{arg_def['name']}': '{raw_args[i]}' is not valid {arg_def['type']}"
            )

    return not issues, issues


# =============================================================================
#  TX COMMAND LINE PARSER
# =============================================================================

def parse_cmd_line(line):
    """Parse command line: [SRC] DEST ECHO TYPE CMD [ARGS]

    SRC is optional -- if omitted, defaults to GS (node 6).
    Returns (src, dest, echo, ptype, cmd, args).
    Raises ValueError with a specific message on failure."""
    parts = line.split(None, 5)
    if len(parts) < 4:
        raise ValueError("need at least: <dest> <echo> <type> <cmd>")

    ptype3 = resolve_ptype(parts[3]) if len(parts) >= 5 else None
    if ptype3 is not None:
        offset, src = 1, resolve_node(parts[0])
        if src is None:
            raise ValueError(f"unknown source node '{parts[0]}'")
        ptype = ptype3
    else:
        offset, src = 0, GS_NODE
        ptype = resolve_ptype(parts[2])
        if ptype is None:
            raise ValueError(f"unknown packet type '{parts[2]}'")

    dest = resolve_node(parts[offset])
    if dest is None:
        raise ValueError(f"unknown destination node '{parts[offset]}'")
    echo = resolve_node(parts[offset + 1])
    if echo is None:
        raise ValueError(f"unknown echo node '{parts[offset + 1]}'")

    cmd_idx = offset + 3
    args = " ".join(parts[cmd_idx + 1:]) if len(parts) > cmd_idx + 1 else ""
    return (src, dest, echo, ptype, parts[cmd_idx].lower(), args)


# =============================================================================
#  UTILITIES
# =============================================================================

def format_arg_value(typed_arg):
    """Format a schema-typed argument value for display/logging."""
    if typed_arg["type"] == "epoch_ms" and isinstance(typed_arg["value"], (_LazyEpochMs, dict)):
        return str(typed_arg["value"]["ms"])
    return str(typed_arg["value"])
```

**Critical note on `load_command_defs`:** The `_cfg_dir` path computation changed from `Path(__file__).resolve().parent / "config"` to `Path(__file__).resolve().parent.parent.parent / "config"` because the file moved from `mav_gss_lib/` to `mav_gss_lib/missions/maveric/` — three levels up instead of one.

- [ ] **Step 2: Smoke test the module in isolation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.missions.maveric.wire_format import (
    init_nodes, node_name, resolve_node, CommandFrame, build_cmd_raw,
    load_command_defs, apply_schema, validate_args, parse_cmd_line,
    format_arg_value, GS_NODE,
)
# init_nodes needs a config dict
cfg = {
    'nodes': {0: 'NONE', 1: 'LPPM', 2: 'EPS', 6: 'GS'},
    'ptypes': {1: 'CMD', 2: 'RES'},
    'general': {'gs_node': 'GS'},
}
init_nodes(cfg)
print('node_name(2):', node_name(2))
print('resolve_node(\"EPS\"):', resolve_node('EPS'))
print('GS_NODE:', GS_NODE)
raw = build_cmd_raw(2, 'ping')
print('build_cmd_raw len:', len(raw))
print('OK')
"
```

Expected: prints values and `OK`.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/missions/maveric/wire_format.py
git commit -m "Add missions/maveric/wire_format.py with MAVERIC command wire format"
```

---

## Task 3: Create `missions/maveric/adapter.py`

**Files:**
- Create: `mav_gss_lib/missions/maveric/adapter.py`

- [ ] **Step 1: Create the MAVERIC adapter module**

This is `MavericMissionAdapter` moved from `mission_adapter.py`, with imports repointed to `missions/maveric/wire_format` and `protocols/`.

```python
"""
mav_gss_lib.missions.maveric.adapter -- MAVERIC Mission Adapter

MavericMissionAdapter implementation for the MAVERIC CubeSat mission.
Provides RX parsing, TX command building, CRC verification, duplicate
detection, and uplink-echo classification.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass

from mav_gss_lib.protocols.crc import verify_csp_crc32
from mav_gss_lib.protocols.csp import try_parse_csp_v1
from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame
from mav_gss_lib.missions.maveric.wire_format import (
    GS_NODE,
    apply_schema,
    build_cmd_raw,
    try_parse_command,
    validate_args,
)


@dataclass
class MavericMissionAdapter:
    """MAVERIC mission adapter implementation.

    RX parsing, CRC checks, uplink-echo classification, and TX command
    validation/building for the MAVERIC CubeSat mission.
    """

    cmd_defs: dict

    def detect_frame_type(self, meta) -> str:
        """Classify outer framing from GNU Radio/gr-satellites metadata."""
        return detect_frame_type(meta)

    def normalize_frame(self, frame_type: str, raw: bytes):
        """Strip outer framing and return inner payload."""
        return normalize_frame(frame_type, raw)

    def parse_packet(self, inner_payload, warnings=None):
        """Parse one normalized RX payload into a ParsedPacket."""
        from mav_gss_lib.mission_adapter import ParsedPacket
        warnings = [] if warnings is None else warnings
        csp, csp_plausible = try_parse_csp_v1(inner_payload)
        if len(inner_payload) <= 4:
            return ParsedPacket(csp=csp, csp_plausible=csp_plausible, warnings=warnings)

        cmd, cmd_tail = try_parse_command(inner_payload[4:])
        ts_result = None
        if cmd:
            apply_schema(cmd, self.cmd_defs)
            if cmd.get("sat_time"):
                ts_result = cmd["sat_time"]

        crc_valid, crc_rx, crc_comp = None, None, None
        if cmd and cmd.get("csp_crc32") is not None:
            crc_valid, crc_rx, crc_comp = verify_csp_crc32(inner_payload)
            if crc_valid is False:
                warnings.append(
                    f"CRC-32C mismatch: rx 0x{crc_rx:08x} != computed 0x{crc_comp:08x}"
                )

        return ParsedPacket(
            csp=csp,
            csp_plausible=csp_plausible,
            cmd=cmd,
            cmd_tail=cmd_tail,
            ts_result=ts_result,
            warnings=warnings,
            crc_status={
                "csp_crc32_valid": crc_valid,
                "csp_crc32_rx": crc_rx,
                "csp_crc32_comp": crc_comp,
            },
        )

    def parse_command(self, inner_payload):
        """Backward-compatible wrapper around parse_packet()."""
        parsed = self.parse_packet(inner_payload)
        return parsed.cmd, parsed.cmd_tail, parsed.ts_result

    def verify_crc(self, cmd, inner_payload, warnings):
        """Backward-compatible CRC wrapper."""
        parsed = self.parse_packet(inner_payload, warnings)
        return parsed.crc_status

    def duplicate_fingerprint(self, parsed):
        """Return a mission-specific duplicate fingerprint or None."""
        cmd = parsed.cmd
        if not (cmd and cmd.get("crc") is not None and cmd.get("csp_crc32") is not None):
            return None
        return cmd["crc"], cmd["csp_crc32"]

    def is_uplink_echo(self, cmd) -> bool:
        """Classify whether a decoded command is the ground-station echo."""
        from mav_gss_lib.mission_adapter import ParsedPacket
        cmd_obj = cmd.cmd if isinstance(cmd, ParsedPacket) else cmd
        return bool(cmd_obj and cmd_obj.get("src") == GS_NODE)

    def build_raw_command(self, src, dest, echo, ptype, cmd_id, args):
        """Build one raw mission command payload for TX."""
        return build_cmd_raw(dest, cmd_id, args, echo=echo, ptype=ptype, origin=src)

    def validate_tx_args(self, cmd_id, args):
        """Validate TX arguments using the active mission command schema."""
        return validate_args(cmd_id, args, self.cmd_defs)
```

**Note:** `parse_packet` and `is_uplink_echo` use a lazy import of `ParsedPacket` from `mission_adapter` to avoid a circular import — `ParsedPacket` is platform core and stays in `mission_adapter.py`, while `MavericMissionAdapter` is mission code. The lazy import breaks the cycle cleanly.

- [ ] **Step 2: Smoke test**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.missions.maveric.wire_format import init_nodes
cfg = {
    'nodes': {0: 'NONE', 1: 'LPPM', 2: 'EPS', 6: 'GS'},
    'ptypes': {1: 'CMD', 2: 'RES'},
    'general': {'gs_node': 'GS'},
}
init_nodes(cfg)
from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter
adapter = MavericMissionAdapter(cmd_defs={})
ft = adapter.detect_frame_type({'transmitter': 'AX.25 9k6'})
print('frame type:', ft)
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/missions/maveric/adapter.py
git commit -m "Add missions/maveric/adapter.py with MavericMissionAdapter"
```

---

## Task 4: Copy `imaging.py` to `missions/maveric/imaging.py`

**Files:**
- Create: `mav_gss_lib/missions/maveric/imaging.py`

- [ ] **Step 1: Copy the imaging module**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
cp mav_gss_lib/imaging.py mav_gss_lib/missions/maveric/imaging.py
```

No content changes. The file is self-contained.

- [ ] **Step 2: Smoke test**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.missions.maveric.imaging import ImageAssembler
asm = ImageAssembler('/tmp/test_img')
print('ImageAssembler:', type(asm).__name__)
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/missions/maveric/imaging.py
git commit -m "Copy imaging.py to missions/maveric/imaging.py"
```

---

## Task 5: Convert `protocol.py` to Full Facade

Replace all remaining MAVERIC code in `protocol.py` with re-exports from `missions/maveric/wire_format`.

**Files:**
- Modify: `mav_gss_lib/protocol.py`

- [ ] **Step 1: Replace protocol.py with a pure facade**

Replace the entire file content with:

```python
"""
mav_gss_lib.protocol -- Compatibility Facade

Re-exports from:
  - mav_gss_lib.protocols.*          (CRC, CSP, KISS, AX.25, frame detect)
  - mav_gss_lib.missions.maveric.*   (node tables, command wire format, schema)

New code should import directly from the canonical locations.

Author:  Irfan Annuar - USC ISI SERC
"""

# -- Protocol-family support (Phase 3) ----------------------------------------

from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32  # noqa: F401

from mav_gss_lib.protocols.csp import (  # noqa: F401
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig,
)

from mav_gss_lib.protocols.ax25 import AX25Config  # noqa: F401

from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame  # noqa: F401


# -- MAVERIC mission wire format (Phase 4) ------------------------------------

from mav_gss_lib.missions.maveric.wire_format import (  # noqa: F401
    # Node/ptype tables and lookup helpers — wide downstream usage
    NODE_NAMES, NODE_IDS, PTYPE_NAMES, PTYPE_IDS, GS_NODE,
    init_nodes, node_name, ptype_name, node_label, ptype_label,
    resolve_node, resolve_ptype,
    # Command wire format — CommandFrame used by tests
    CommandFrame,
    build_cmd_raw, build_kiss_cmd, try_parse_command,
    # Command schema — public API used by adapter, runtime, tests
    TS_MIN_MS, TS_MAX_MS,
    load_command_defs, apply_schema, validate_args,
    # TX and display — used by web_runtime, TUI, logging
    parse_cmd_line, format_arg_value,
)
# Note: _CMD_HDR_LEN, _LazyEpochMs, _TYPE_PARSERS, _parse_arg_list are
# internal to wire_format.py and intentionally NOT re-exported.


# -- Generic utilities (remain here) ------------------------------------------

_CLEAN_TABLE = bytearray(0xB7 for _ in range(256))  # middle dot
for _b in range(32, 127):
    _CLEAN_TABLE[_b] = _b
_CLEAN_TABLE = bytes(_CLEAN_TABLE)


def clean_text(data: bytes) -> str:
    """Printable ASCII representation with non-printable bytes as middle dot."""
    return data.translate(_CLEAN_TABLE).decode('latin-1')
```

- [ ] **Step 2: Verify all facade imports work**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.protocol import (
    # protocols/
    crc16, crc32c, verify_csp_crc32,
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig, AX25Config,
    detect_frame_type, normalize_frame,
    # missions/maveric/
    NODE_NAMES, init_nodes, node_name, resolve_node,
    CommandFrame, build_cmd_raw, try_parse_command,
    load_command_defs, apply_schema, validate_args,
    parse_cmd_line, format_arg_value, clean_text,
    GS_NODE, TS_MIN_MS, CommandFrame,
)
print('All protocol.py facade imports: OK')
"
```

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/protocol.py
git commit -m "Convert protocol.py to pure facade over protocols/ and missions/maveric/"
```

---

## Task 6: Convert `mission_adapter.py` to Facade + Protocol

Keep `ParsedPacket` (platform core) in place. Add a formal `MissionAdapter` Protocol. Re-export `MavericMissionAdapter` from the new location.

**Files:**
- Modify: `mav_gss_lib/mission_adapter.py`

- [ ] **Step 1: Replace mission_adapter.py content**

```python
"""
mav_gss_lib.mission_adapter -- Mission Adapter Interface + Facade

Platform core:
  - ParsedPacket: normalized packet parse result
  - MissionAdapter: formal Protocol defining the mission boundary

Facade:
  - MavericMissionAdapter: re-exported from missions.maveric.adapter

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# =============================================================================
#  PLATFORM CORE -- ParsedPacket
# =============================================================================

@dataclass
class ParsedPacket:
    """Normalized packet parse result returned by a mission adapter.

    Transitional compatibility note: the csp, cmd, cmd_tail, and
    ts_result fields reflect MAVERIC's packet model and are kept for
    backward compatibility during migration.  The platform's eventual
    packet record should carry mission-opaque semantic data via
    adapter-provided rendering payloads rather than baking in any
    one mission's field names.  These fields may be replaced or
    generalized in a future phase.
    """

    csp: dict | None = None          # transitional — MAVERIC CSP parse result
    csp_plausible: bool = False
    cmd: dict | None = None          # transitional — MAVERIC command dict
    cmd_tail: bytes | None = None    # transitional — unparsed tail bytes
    ts_result: tuple | None = None   # transitional — satellite timestamp
    warnings: list[str] = field(default_factory=list)
    crc_status: dict = field(default_factory=lambda: {
        "csp_crc32_valid": None,
        "csp_crc32_rx": None,
        "csp_crc32_comp": None,
    })


# =============================================================================
#  PLATFORM CORE -- MissionAdapter Protocol
# =============================================================================

@runtime_checkable
class MissionAdapter(Protocol):
    """Formal interface for mission adapter implementations.

    Missions provide an adapter that satisfies this protocol.
    The platform runtime calls these methods without knowing
    which mission is active.
    """

    def detect_frame_type(self, meta: dict) -> str: ...
    def normalize_frame(self, frame_type: str, raw: bytes) -> tuple: ...

    def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None) -> ParsedPacket: ...

    def duplicate_fingerprint(self, parsed: ParsedPacket) -> tuple | None: ...
    def is_uplink_echo(self, cmd) -> bool: ...

    def build_raw_command(self, src: int, dest: int, echo: int, ptype: int,
                          cmd_id: str, args: str) -> bytes: ...
    def validate_tx_args(self, cmd_id: str, args: str) -> tuple[bool, list[str]]: ...


# =============================================================================
#  FACADE -- re-export MAVERIC adapter
# =============================================================================

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter  # noqa: F401
```

- [ ] **Step 2: Verify imports and Protocol**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.mission_adapter import (
    ParsedPacket, MissionAdapter, MavericMissionAdapter,
)
from mav_gss_lib.missions.maveric.wire_format import init_nodes
cfg = {
    'nodes': {0: 'NONE', 2: 'EPS', 6: 'GS'},
    'ptypes': {1: 'CMD'},
    'general': {'gs_node': 'GS'},
}
init_nodes(cfg)
adapter = MavericMissionAdapter(cmd_defs={})
print('isinstance check:', isinstance(adapter, MissionAdapter))
print('ParsedPacket:', ParsedPacket())
print('OK')
"
```

Expected: `isinstance check: True`, prints ParsedPacket, `OK`.

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/mission_adapter.py
git commit -m "Add MissionAdapter Protocol, re-export MavericMissionAdapter from missions/"
```

---

## Task 7: Convert `imaging.py` to Facade

**Files:**
- Modify: `mav_gss_lib/imaging.py`

- [ ] **Step 1: Replace imaging.py with facade**

```python
"""
mav_gss_lib.imaging -- Compatibility facade

Canonical location: mav_gss_lib.missions.maveric.imaging
This module re-exports ImageAssembler for backward compatibility.
"""

from mav_gss_lib.missions.maveric.imaging import ImageAssembler  # noqa: F401
```

- [ ] **Step 2: Verify old imports still work**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.imaging import ImageAssembler
print('old path:', type(ImageAssembler).__name__)
from mav_gss_lib.missions.maveric.imaging import ImageAssembler as IA2
print('new path:', type(IA2).__name__)
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/imaging.py
git commit -m "Convert imaging.py to facade over missions/maveric/imaging"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Verify no circular imports**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
# Import in dependency order
import mav_gss_lib.protocols.crc
import mav_gss_lib.protocols.csp
import mav_gss_lib.protocols.ax25
import mav_gss_lib.protocols.frame_detect
import mav_gss_lib.protocols.golay
import mav_gss_lib.missions.maveric.wire_format
import mav_gss_lib.missions.maveric.adapter
import mav_gss_lib.missions.maveric.imaging
import mav_gss_lib.protocol
import mav_gss_lib.mission_adapter
import mav_gss_lib.imaging
import mav_gss_lib
print('No circular imports')
"
```

- [ ] **Step 2: Verify ADAPTER_API_VERSION**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.missions.maveric import ADAPTER_API_VERSION
print('ADAPTER_API_VERSION:', ADAPTER_API_VERSION)
assert ADAPTER_API_VERSION == 1
print('OK')
"
```

- [ ] **Step 3: Run both test suites one final time**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass.

- [ ] **Step 4: Verify dependency direction**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
# missions/maveric/ must NOT import from protocol.py or the old mission_adapter.py top-level definitions
grep -r "from mav_gss_lib\.protocol " mav_gss_lib/missions/ || echo "CLEAN: no protocol imports in missions/"
grep -r "import mav_gss_lib\.protocol" mav_gss_lib/missions/ || echo "CLEAN: no protocol imports in missions/"
```

Expected: Both print `CLEAN`.

**Note:** `missions/maveric/adapter.py` does lazily import `ParsedPacket` from `mav_gss_lib.mission_adapter` — this is allowed because `ParsedPacket` is platform core, and the import is lazy (inside methods, not at module level) to avoid cycles.

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add -A
git commit -m "Phase 4 complete: MAVERIC is a mission implementation under missions/maveric/"
```

---

## TUI Decision Record (Phase 4 Final)

**Decision: The TUI is a MAVERIC-only legacy shell. This is a closed decision.**

The TUI (`tui_rx.py`, `tui_tx.py`, `tui_common.py`) continues importing from the `protocol.py` facade. It works only with MAVERIC and does not consume the `MissionAdapter` Protocol.

Rationale:
- The TUI is backup control, not the primary interface
- It only runs with MAVERIC
- Adapter integration would require substantial UI refactoring for no immediate benefit
- If a future mission needs a TUI, it would be a new implementation

This satisfies the Phase 2 inventory requirement that Phase 4 must explicitly decide the TUI's fate rather than leaving it ambiguous.

---

## Post-Phase 4 State

```
mav_gss_lib/
  protocols/              # Phase 3 — protocol-family support
    crc.py, csp.py, ax25.py, frame_detect.py, golay.py

  missions/               # Phase 4 — mission implementations
    maveric/
      __init__.py          # ADAPTER_API_VERSION = 1
      wire_format.py       # Node tables, CommandFrame, schema, parse_cmd_line
      adapter.py           # MavericMissionAdapter
      imaging.py           # ImageAssembler

  protocol.py             # FACADE — re-exports from protocols/ + missions/maveric/
  mission_adapter.py      # CORE (ParsedPacket, MissionAdapter Protocol) + FACADE (MavericMissionAdapter)
  imaging.py              # FACADE — re-exports from missions/maveric/imaging

  # Unchanged:
  transport.py, config.py, parsing.py, logging.py
  tui_common.py, tui_rx.py, tui_tx.py
  web_runtime/, web/
```

**What moved:** Node tables, CommandFrame, command schema, parse_cmd_line, format_arg_value, MavericMissionAdapter, ImageAssembler.

**What was added:** `MissionAdapter` Protocol, `ADAPTER_API_VERSION`.

**What stayed:** `ParsedPacket` (platform core), `clean_text` (generic utility), all facades, all downstream imports.
