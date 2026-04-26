"""Parameter — named measurement / argument bound to a ParameterType.

The XTCE-lite analogue of `<Parameter>` inside `<SpaceSystem>`: a parameter
carries identity, type binding, and (optionally) the subsystem it belongs
to. ``domain`` is the analogue of XTCE's SpaceSystem name — when set, it
overrides the container's domain at fragment emission and routes the
parameter into the matching domain catalog. When unset, the container's
domain is used as fallback.

Description rides into the catalog entry surfaced at
`GET /api/telemetry/{domain}/catalog`. UI rendering choices (icons,
sections, format strings) live in mission Python — never declared here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type_ref: str
    description: str = ""
    domain: str | None = None


__all__ = ["Parameter"]
