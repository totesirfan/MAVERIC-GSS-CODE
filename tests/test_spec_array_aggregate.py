"""Tests for Array and Aggregate TypeCodec branches — ASCII and binary paths.

Exercises decode_ascii, encode_ascii, decode_binary, encode_binary for
ArrayParameterType and AggregateParameterType, including recursive
(array-of-aggregate) composition.
"""

import struct
import unittest

from mav_gss_lib.platform.spec.cursor import BitCursor, TokenCursor
from mav_gss_lib.platform.spec.parameter_types import (
    BUILT_IN_PARAMETER_TYPES,
    AggregateMember,
    AggregateParameterType,
    ArrayParameterType,
)
from mav_gss_lib.platform.spec.runtime import TypeCodec


class TestArrayDecodeAscii(unittest.TestCase):
    def test_float_array_three(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["F3"] = ArrayParameterType(
            name="F3", array_type_ref="f32_le", dimension_list=(3,),
        )
        codec = TypeCodec(types=types)
        cursor = TokenCursor(b"1.5 2.5 3.5")
        out = codec.decode_ascii("F3", cursor)
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 3)
        self.assertAlmostEqual(out[0], 1.5)
        self.assertAlmostEqual(out[1], 2.5)
        self.assertAlmostEqual(out[2], 3.5)

    def test_uint8_array_four(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["U4"] = ArrayParameterType(
            name="U4", array_type_ref="u8", dimension_list=(4,),
        )
        codec = TypeCodec(types=types)
        cursor = TokenCursor(b"10 20 30 40")
        out = codec.decode_ascii("U4", cursor)
        self.assertEqual(out, [10, 20, 30, 40])


class TestArrayEncodeAscii(unittest.TestCase):
    def test_float_array_encode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["F3"] = ArrayParameterType(
            name="F3", array_type_ref="f32_le", dimension_list=(3,),
        )
        codec = TypeCodec(types=types)
        s = codec.encode_ascii("F3", [1.5, 2.5, 3.5])
        # Tokens joined by single spaces
        parts = s.split(" ")
        self.assertEqual(len(parts), 3)
        self.assertAlmostEqual(float(parts[0]), 1.5)
        self.assertAlmostEqual(float(parts[1]), 2.5)
        self.assertAlmostEqual(float(parts[2]), 3.5)


class TestArrayBinary(unittest.TestCase):
    def test_u16_le_array_two_decode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["U2"] = ArrayParameterType(
            name="U2", array_type_ref="u16", dimension_list=(2,),
        )
        codec = TypeCodec(types=types)
        cursor = BitCursor(b"\x34\x12\x78\x56")
        self.assertEqual(codec.decode_binary("U2", cursor), [0x1234, 0x5678])

    def test_u16_le_array_two_encode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["U2"] = ArrayParameterType(
            name="U2", array_type_ref="u16", dimension_list=(2,),
        )
        codec = TypeCodec(types=types)
        self.assertEqual(codec.encode_binary("U2", [0x1234, 0x5678]), b"\x34\x12\x78\x56")

    def test_float_array_nine_binary_roundtrip(self):
        """f32_le[9] — covers the GNC rotation-matrix use case."""
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["F9"] = ArrayParameterType(
            name="F9", array_type_ref="f32_le", dimension_list=(9,),
        )
        codec = TypeCodec(types=types)
        values = [float(i) * 0.1 for i in range(9)]
        wire = codec.encode_binary("F9", values)
        self.assertEqual(len(wire), 36)  # 9 * 4 bytes
        cursor = BitCursor(wire)
        decoded = codec.decode_binary("F9", cursor)
        self.assertEqual(len(decoded), 9)
        for a, b in zip(values, decoded):
            self.assertAlmostEqual(a, b, places=5)


class TestAggregateDecodeAscii(unittest.TestCase):
    def test_simple_aggregate(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["XY"] = AggregateParameterType(
            name="XY",
            member_list=(
                AggregateMember(name="x", type_ref="f32_le"),
                AggregateMember(name="y", type_ref="f32_le"),
            ),
        )
        codec = TypeCodec(types=types)
        cursor = TokenCursor(b"1.5 2.5")
        out = codec.decode_ascii("XY", cursor)
        self.assertIsInstance(out, dict)
        self.assertAlmostEqual(out["x"], 1.5)
        self.assertAlmostEqual(out["y"], 2.5)

    def test_aggregate_encode_ascii(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["XY"] = AggregateParameterType(
            name="XY",
            member_list=(
                AggregateMember(name="x", type_ref="f32_le"),
                AggregateMember(name="y", type_ref="f32_le"),
            ),
        )
        codec = TypeCodec(types=types)
        s = codec.encode_ascii("XY", {"x": 1.5, "y": 2.5})
        parts = s.split(" ")
        self.assertEqual(len(parts), 2)
        self.assertAlmostEqual(float(parts[0]), 1.5)
        self.assertAlmostEqual(float(parts[1]), 2.5)

    def test_aggregate_missing_member_raises(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["XY"] = AggregateParameterType(
            name="XY",
            member_list=(
                AggregateMember(name="x", type_ref="f32_le"),
                AggregateMember(name="y", type_ref="f32_le"),
            ),
        )
        codec = TypeCodec(types=types)
        with self.assertRaises((KeyError, ValueError)):
            codec.encode_ascii("XY", {"x": 1.5})  # missing "y"


class TestAggregateBinary(unittest.TestCase):
    def test_aggregate_with_int_members_decode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["AB"] = AggregateParameterType(
            name="AB",
            member_list=(
                AggregateMember(name="a", type_ref="u16"),
                AggregateMember(name="b", type_ref="u16"),
            ),
        )
        codec = TypeCodec(types=types)
        cursor = BitCursor(b"\x34\x12\x78\x56")
        out = codec.decode_binary("AB", cursor)
        self.assertEqual(out, {"a": 0x1234, "b": 0x5678})

    def test_aggregate_with_int_members_encode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["AB"] = AggregateParameterType(
            name="AB",
            member_list=(
                AggregateMember(name="a", type_ref="u16"),
                AggregateMember(name="b", type_ref="u16"),
            ),
        )
        codec = TypeCodec(types=types)
        wire = codec.encode_binary("AB", {"a": 0x1234, "b": 0x5678})
        self.assertEqual(wire, b"\x34\x12\x78\x56")


class TestArrayOfAggregate(unittest.TestCase):
    def test_array_of_aggregate_ascii_decode(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["XY"] = AggregateParameterType(
            name="XY",
            member_list=(
                AggregateMember(name="x", type_ref="f32_le"),
                AggregateMember(name="y", type_ref="f32_le"),
            ),
        )
        types["TwoXY"] = ArrayParameterType(
            name="TwoXY", array_type_ref="XY", dimension_list=(2,),
        )
        codec = TypeCodec(types=types)
        cursor = TokenCursor(b"1.0 2.0 3.0 4.0")
        out = codec.decode_ascii("TwoXY", cursor)
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(out[0]["x"], 1.0)
        self.assertAlmostEqual(out[0]["y"], 2.0)
        self.assertAlmostEqual(out[1]["x"], 3.0)
        self.assertAlmostEqual(out[1]["y"], 4.0)

    def test_array_of_aggregate_binary_roundtrip(self):
        types = dict(BUILT_IN_PARAMETER_TYPES)
        types["XY"] = AggregateParameterType(
            name="XY",
            member_list=(
                AggregateMember(name="x", type_ref="f32_le"),
                AggregateMember(name="y", type_ref="f32_le"),
            ),
        )
        types["TwoXY"] = ArrayParameterType(
            name="TwoXY", array_type_ref="XY", dimension_list=(2,),
        )
        codec = TypeCodec(types=types)
        original = [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]
        wire = codec.encode_binary("TwoXY", original)
        self.assertEqual(len(wire), 16)  # 2 * 2 * 4 bytes
        cursor = BitCursor(wire)
        decoded = codec.decode_binary("TwoXY", cursor)
        self.assertEqual(len(decoded), 2)
        self.assertAlmostEqual(decoded[0]["x"], 1.0)
        self.assertAlmostEqual(decoded[1]["y"], 4.0)


if __name__ == "__main__":
    unittest.main()
