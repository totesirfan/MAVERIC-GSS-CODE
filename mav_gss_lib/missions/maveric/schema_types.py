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
from mav_gss_lib.platform.spec.types import HeaderValue


class MavericCommandSchemaItem(CommandSchemaItem):
    """MAVERIC routing extension on top of the platform contract.

    `dest`/`echo`/`ptype` are CSP-style routing fields; `nodes` is the
    list of allowed dest names for the operator UI. None/absent means
    'operator chooses' (no fixed routing constraint).

    Field value type mirrors `HeaderValue` (`str | int | bool`): the
    YAML parser preserves whatever the operator wrote in the command
    header (`dest: LPPM` parses to "LPPM"; `dest: 1` would parse to
    int 1). Wire mapping happens later in the packet codec, not here —
    the schema must reflect that polymorphism so consumers don't get a
    silent type mismatch when an author switches a header from a
    symbolic name to a numeric byte.
    """
    dest: NotRequired[HeaderValue | None]
    echo: NotRequired[HeaderValue | None]
    ptype: NotRequired[HeaderValue | None]
    nodes: NotRequired[list[HeaderValue]]


__all__ = ["MavericCommandSchemaItem"]
