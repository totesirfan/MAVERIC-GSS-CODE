import unittest

from mav_gss_lib.platform.spec.cursor import TokenCursor
from mav_gss_lib.platform.spec.parameter_types import (
    BUILT_IN_PARAMETER_TYPES,
    EnumeratedParameterType,
    EnumValue,
    FloatParameterType,
    IntegerParameterType,
    StringParameterType,
)
from mav_gss_lib.platform.spec.runtime import TypeCodec


class TestTypeCodecAsciiDecode(unittest.TestCase):
    def setUp(self):
        self.types = dict(BUILT_IN_PARAMETER_TYPES)

    def test_int_decimal_token(self):
        codec = TypeCodec(types=self.types)
        cursor = TokenCursor(b"42")
        self.assertEqual(codec.decode_ascii("u32", cursor), 42)

    def test_float_token(self):
        codec = TypeCodec(types=self.types)
        cursor = TokenCursor(b"3.14159")
        self.assertAlmostEqual(codec.decode_ascii("f32_le", cursor), 3.14159, places=5)

    def test_enum_decode_returns_raw_int(self):
        types = dict(self.types)
        types["GncMode"] = EnumeratedParameterType(
            name="GncMode", size_bits=8,
            values=(EnumValue(raw=0, label="Safe"), EnumValue(raw=1, label="Auto")),
        )
        codec = TypeCodec(types=types)
        cursor = TokenCursor(b"1")
        self.assertEqual(codec.decode_ascii("GncMode", cursor), 1)

    def test_ascii_token_string_preserves_verbatim(self):
        codec = TypeCodec(types=self.types)
        cursor = TokenCursor(b"0x1FAB")
        self.assertEqual(codec.decode_ascii("ascii_token", cursor), "0x1FAB")

    def test_ascii_blob_consumes_to_end(self):
        codec = TypeCodec(types=self.types)
        cursor = TokenCursor(b"alpha rest of cursor with spaces")
        cursor.read_token()  # consume "alpha"
        self.assertEqual(
            codec.decode_ascii("ascii_blob", cursor).strip(),
            "rest of cursor with spaces",
        )


class TestTypeCodecAsciiEncode(unittest.TestCase):
    def setUp(self):
        self.types = dict(BUILT_IN_PARAMETER_TYPES)

    def test_int_encodes_as_decimal_str(self):
        codec = TypeCodec(types=self.types)
        self.assertEqual(codec.encode_ascii("u32", 42), "42")

    def test_float_uses_repr_for_full_precision(self):
        codec = TypeCodec(types=self.types)
        # repr(1927.793121) preserves all 10 sig digits — format(v, 'g') would truncate
        self.assertEqual(codec.encode_ascii("f32_le", 1927.793121), repr(1927.793121))

    def test_ascii_token_writes_verbatim(self):
        codec = TypeCodec(types=self.types)
        self.assertEqual(codec.encode_ascii("ascii_token", "0x1FAB"), "0x1FAB")


if __name__ == "__main__":
    unittest.main()
