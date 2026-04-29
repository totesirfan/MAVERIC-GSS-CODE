"""JSON-safe value coercion shared by live telemetry and persistence."""

from __future__ import annotations

import math
from typing import Any


def json_safe(value: Any) -> Any:
    """Return *value* with non-standard JSON floats replaced by ``None``."""
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, list):
        return [json_safe(x) for x in value]
    if isinstance(value, tuple):
        return [json_safe(x) for x in value]
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    return value


__all__ = ["json_safe"]
