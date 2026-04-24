"""MAVERIC operator-CLI parser.

Turns raw operator CLI text (entered in the TX console or loaded from an
import file) into the structured command payload `tx_ops.build_tx_command`
consumes. Two surface grammars:

  * shortcut  — `CMD_ID [ARGS]`, routing filled in from the schema default
  * full      — `[SRC] DEST ECHO TYPE CMD_ID [ARGS]`, everything explicit

`cmd_line_to_payload` dispatches between them by looking the first token
up in the mission command schema.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mav_gss_lib.missions.maveric.nodes import NodeTable


def parse_cmd_line(line: str, nodes: NodeTable) -> tuple:
    """Parse the full grammar: `[SRC] DEST ECHO TYPE CMD [ARGS]`.

    SRC is optional — if omitted, defaults to `nodes.gs_node`.
    Detection: with 5+ tokens, if parts[3] resolves as a ptype then the
    first token is SRC; otherwise the 4-token form is assumed.

    Returns (src, dest, echo, ptype, cmd, args). Raises ValueError on
    unrecognized tokens.
    """
    parts = line.split(None, 5)
    if len(parts) < 4:
        raise ValueError("need at least: <dest> <echo> <type> <cmd>")

    ptype3 = nodes.resolve_ptype(parts[3]) if len(parts) >= 5 else None
    if ptype3 is not None:
        offset, src = 1, nodes.resolve_node(parts[0])
        if src is None:
            raise ValueError(f"unknown source node '{parts[0]}'")
        ptype = ptype3
    else:
        offset, src = 0, nodes.gs_node
        ptype = nodes.resolve_ptype(parts[2])
        if ptype is None:
            raise ValueError(f"unknown packet type '{parts[2]}'")

    dest = nodes.resolve_node(parts[offset])
    if dest is None:
        raise ValueError(f"unknown destination node '{parts[offset]}'")
    echo = nodes.resolve_node(parts[offset + 1])
    if echo is None:
        raise ValueError(f"unknown echo node '{parts[offset + 1]}'")

    cmd_idx = offset + 3
    args = " ".join(parts[cmd_idx + 1:]) if len(parts) > cmd_idx + 1 else ""
    return (src, dest, echo, ptype, parts[cmd_idx].lower(), args)


def parse_shortcut_cli(line: str, cmd_defs: dict, nodes: NodeTable) -> dict:
    """Parse `CMD_ID [ARGS]` — routing defaults come from the schema.

    Precondition: `line.split()[0].lower()` must exist in `cmd_defs` with
    a non-None `dest` and must not be `rx_only`. `cmd_line_to_payload`
    enforces that before delegating here.
    """
    parts = line.split()
    cmd_id = parts[0].lower()
    defn = cmd_defs[cmd_id]
    args = " ".join(parts[1:])
    return {
        "cmd_id": cmd_id,
        "args": args,
        "dest": nodes.node_name(defn["dest"]),
        "echo": nodes.node_name(defn["echo"]),
        "ptype": nodes.ptype_name(defn["ptype"]),
    }


def parse_full_cli(line: str, nodes: NodeTable) -> dict:
    """Parse `[SRC] DEST ECHO TYPE CMD_ID [ARGS]` into the payload dict."""
    src, dest, echo, ptype, cmd_id, args = parse_cmd_line(line, nodes)
    result = {
        "cmd_id": cmd_id,
        "args": args,
        "dest": nodes.node_name(dest),
        "echo": nodes.node_name(echo),
        "ptype": nodes.ptype_name(ptype),
    }
    if src != nodes.gs_node:
        result["src"] = nodes.node_name(src)
    return result


def cmd_line_to_payload(line: str, cmd_defs: dict, nodes: NodeTable) -> dict:
    """Convert raw CLI text into the payload dict `build_tx_command` consumes.

    Picks shortcut vs full grammar by schema lookup: the first token is a
    known cmd_id iff it exists in `cmd_defs` with routing defaults (and is
    not rx_only). Otherwise the line is parsed as the full grammar.
    """
    line = line.strip()
    if not line:
        raise ValueError("empty command input")

    candidate = line.split()[0].lower()
    defn = cmd_defs.get(candidate)
    if defn and not defn.get("rx_only") and defn.get("dest") is not None:
        return parse_shortcut_cli(line, cmd_defs, nodes)
    return parse_full_cli(line, nodes)
