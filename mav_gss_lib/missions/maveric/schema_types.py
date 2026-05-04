"""MAVERIC's /api/schema extension fields.

The platform `CommandSchemaItem` is mission-agnostic. MAVERIC adds
CSP-style routing fields (dest/echo/ptype) and node-directory hints
(nodes) here. The TypedDict subclass keeps Required/NotRequired
inherited from the platform base; new fields are NotRequired since
not every command has a fixed dest (some are operator-routable).
"""

from __future__ import annotations

from typing import NotRequired

from mav_gss_lib.platform.contract.commands import CommandSchemaItem


class MavericCommandSchemaItem(CommandSchemaItem):
    """MAVERIC routing extension on top of the platform contract.

    `dest`/`echo`/`ptype` are CSP-style routing fields; `nodes` is the
    list of allowed dest names for the operator UI. None/absent means
    'operator chooses' (no fixed routing constraint).

    Schema invariant: routing values are ALWAYS symbolic node / ptype
    NAMES (`"LPPM"`, `"CMD"` …), never wire bytes. The MAVERIC schema
    producer (`_MaverCommandOpsWrapper.schema()` in `declarative.py`)
    runs every routing value through `_resolve_node_value` /
    `_resolve_ptype_value`, which look up the symbolic name in the
    mission's node/ptype directory regardless of whether the YAML
    declared `dest: LPPM` or `dest: 1`. Numeric polymorphism stays
    inside the packet codec at encode time — it does NOT leak to
    `/api/schema`. (See test_command_schema_contract.py::
    TestMavericExtensionAgainstLocalMission for the runtime invariant
    and TestMavericSchemaResolvesNumericRoutingValues for the
    numeric-input case.)
    """
    dest: NotRequired[str | None]
    echo: NotRequired[str | None]
    ptype: NotRequired[str | None]
    nodes: NotRequired[list[str]]


__all__ = ["MavericCommandSchemaItem"]
