"""
mav_gss_lib.missions.maveric.tx_ops -- MAVERIC TX Command Building

Extracted TX logic from adapter.py. All functions take cmd_defs as a
parameter instead of relying on self, so they can be called from the
adapter via delegation or tested independently.

Author:  Irfan Annuar - USC ISI SERC
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


def build_tx_command(payload, cmd_defs: dict):
    """Build a mission command from structured input.

    Accepts: {cmd_id, args: str | {name: value, ...}, src?, dest, echo, ptype, guard?}
    - args as a flat string: CLI path — positional tokens matched to tx_args schema
    - args as a dict: mission builder path — {name: value} mapping
    - src (optional): override source node; defaults to GS_NODE
    Returns: {raw_cmd: bytes, display: dict, guard: bool}
    Raises ValueError on validation failure.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    cmd_id = str(payload.get("cmd_id", "")).lower()
    args_input = payload.get("args", {})
    dest_name = str(payload.get("dest", ""))
    echo_name = str(payload.get("echo", "NONE"))
    ptype_name = str(payload.get("ptype", "CMD"))

    # Resolve src: explicit payload value overrides GS_NODE default
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
    ptype = resolve_ptype(ptype_name)
    if ptype is None:
        raise ValueError(f"unknown packet type '{ptype_name}'")

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
        # CLI path: flat string goes to wire directly; split for display matching
        args_str = args_input
        tokens = args_str.split() if args_str.strip() else []
        args_dict = {}
        for i, arg_def in enumerate(tx_args_schema):
            if i < len(tokens):
                args_dict[arg_def["name"]] = tokens[i]
        extra_tokens = tokens[len(tx_args_schema):]
    else:
        # Mission builder path: reconstruct args_str from dict
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

    valid, issues = validate_args(cmd_id, args_str, cmd_defs)
    if not valid:
        raise ValueError("; ".join(issues))

    raw_cmd = bytes(build_cmd_raw(dest, cmd_id, args_str, echo=echo, ptype=ptype, origin=src))

    guard = payload.get("guard", defn.get("guard", False))

    row = {
        "src": _node_name(src),
        "dest": _node_name(dest),
        "echo": _node_name(echo),
        "ptype": _ptype_name(ptype),
        "cmd": (f"{cmd_id} {args_str}".strip() if args_str else cmd_id),
    }

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

    Handles two input formats:
    - Shortcut: CMD_ID [ARGS]  (when cmd_id has routing defaults in schema)
    - Full:     [SRC] DEST ECHO TYPE CMD_ID [ARGS]

    Returns: {cmd_id, args, dest, echo, ptype[, src]} for build_tx_command.
    Only includes 'src' when explicitly provided in full format.
    Raises ValueError on parse failure or unknown command.
    """
    line = line.strip()
    if not line:
        raise ValueError("empty command input")

    parts = line.split()
    candidate = parts[0].lower()
    defn = cmd_defs.get(candidate)

    if defn and not defn.get("rx_only") and defn.get("dest") is not None:
        # Shortcut path: cmd_id [args...]
        args = " ".join(parts[1:])
        return {
            "cmd_id": candidate,
            "args": args,
            "dest": _node_name(defn["dest"]),
            "echo": _node_name(defn["echo"]),
            "ptype": _ptype_name(defn["ptype"]),
        }

    # Full parse path: [SRC] DEST ECHO TYPE CMD [ARGS]
    src, dest, echo, ptype, cmd_id, args = parse_cmd_line(line)
    result = {
        "cmd_id": cmd_id,
        "args": args,
        "dest": _node_name(dest),
        "echo": _node_name(echo),
        "ptype": _ptype_name(ptype),
    }
    # Include explicit src only when it differs from GS_NODE
    if src != GS_NODE:
        result["src"] = _node_name(src)
    return result
