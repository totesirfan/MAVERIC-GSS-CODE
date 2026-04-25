"""Parameter — named measurement / argument bound to a ParameterType.

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


__all__ = ["Parameter"]
