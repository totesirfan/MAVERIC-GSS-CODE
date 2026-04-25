"""Primitive type aliases shared across the spec package.

ByteOrder is the byte-order discriminator for IntegerParameterType /
FloatParameterType / EnumeratedParameterType / AbsoluteTimeParameterType.

HeaderValue is the value type of a `WalkerPacket.header` mapping —
restricted to str / int / bool so YAML restriction_criteria.packet:
literal comparisons work without coercion ambiguity.
"""

from __future__ import annotations

from typing import Literal

ByteOrder = Literal["little", "big"]
HeaderValue = str | int | bool
