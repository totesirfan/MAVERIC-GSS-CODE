"""Display formatting helpers for declarative-spec values.

`format_args_summary` joins (name, value) pairs into a compact one-line
string suitable for inline display in RX / TX row tables and as the
``header.args`` field on ``mission.facts``.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterable


def _value_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), default=str)


def _is_renderable(value: Any) -> bool:
    """Skip values that would surface as 'nan'/'inf' in the queue row.

    Non-finite floats render through ``str()`` as ``nan`` / ``inf`` /
    ``-inf``, which is operator-confusing and conflicts with the
    JSON-safe contract for downstream payloads. Treat them like None
    and drop them from the summary."""
    if value is None:
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return True


def format_args_summary(
    items: Iterable[tuple[str, Any]],
    *,
    max_items: int = 10,
    max_chars: int = 240,
    sep: str = " | ",
) -> str:
    """Render ``(name, value)`` pairs as ``name=value`` joined by ``sep``.

    None-valued and non-finite-float entries are skipped. Dicts and
    lists are JSON-encoded compactly. After ``max_items`` entries the
    helper appends ``…+N more`` (where N is the count of remaining
    items, ignoring the skipped ones). The final string is hard-clipped
    to ``max_chars`` with a trailing ``…`` when truncation occurs.
    """
    materialized = [(k, v) for k, v in items if _is_renderable(v)]
    if not materialized:
        return ""

    head = materialized[:max_items]
    rendered = sep.join(f"{k}={_value_str(v)}" for k, v in head)

    remaining = len(materialized) - len(head)
    if remaining > 0:
        rendered = f"{rendered}{sep}…+{remaining} more"

    if len(rendered) > max_chars:
        # leave room for the ellipsis
        cut = max(0, max_chars - 1)
        rendered = rendered[:cut] + "…"

    return rendered


__all__ = ["format_args_summary"]
