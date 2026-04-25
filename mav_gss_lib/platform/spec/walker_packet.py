"""WalkerPacket Protocol — the walker's input boundary.

Produced by the mission's PacketCodec.unwrap. Carries the post-envelope,
post-CRC payload (`args_raw`) plus a decoded-envelope header dict the
walker reads through `restriction_criteria.packet:` lookups.

Header values are restricted to str/int/bool so YAML literal comparisons
work without coercion ambiguity.
"""

from __future__ import annotations

from typing import Mapping, Protocol, runtime_checkable

from .types import HeaderValue


@runtime_checkable
class WalkerPacket(Protocol):
    args_raw: bytes
    header: Mapping[str, HeaderValue]


__all__ = ["WalkerPacket"]
