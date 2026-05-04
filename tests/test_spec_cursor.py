import unittest

from mav_gss_lib.platform.spec.cursor import BitCursor, MarkerBoundedTokenCursor, TokenCursor


class TestBitCursor(unittest.TestCase):
    def test_read_bytes_advances_byte_aligned(self):
        c = BitCursor(b"\x01\x02\x03\x04")
        self.assertEqual(c.read_bytes(2), b"\x01\x02")
        self.assertEqual(c.remaining_bytes(), 2)
        self.assertEqual(c.read_bytes(2), b"\x03\x04")
        self.assertEqual(c.remaining_bytes(), 0)

    def test_read_bits_lsb_first(self):
        # 0b10110001 — read LSB first 3 bits → 0b001 = 1, then 5 bits → 0b10110 = 22
        c = BitCursor(b"\xb1")
        self.assertEqual(c.read_bits(3), 0b001)
        self.assertEqual(c.read_bits(5), 0b10110)

    def test_remaining_bits_after_read_bytes(self):
        c = BitCursor(b"\x01\x02\x03")
        c.read_bytes(1)
        self.assertEqual(c.remaining_bits(), 16)


class TestTokenCursor(unittest.TestCase):
    def test_read_token_splits_on_whitespace(self):
        c = TokenCursor(b"alpha 12 3.14")
        self.assertEqual(c.read_token(), "alpha")
        self.assertEqual(c.read_token(), "12")
        self.assertEqual(c.read_token(), "3.14")
        self.assertEqual(c.remaining_tokens(), 0)

    def test_read_remaining_bytes_returns_post_whitespace_blob(self):
        c = TokenCursor(b"file.bin 4 \x01\x02\x03\x04")
        self.assertEqual(c.read_token(), "file.bin")
        self.assertEqual(c.read_token(), "4")
        self.assertEqual(c.read_remaining_bytes(), b"\x01\x02\x03\x04")

    def test_remaining_tokens_counts_unread(self):
        c = TokenCursor(b"a b c")
        self.assertEqual(c.remaining_tokens(), 3)
        c.read_token()
        self.assertEqual(c.remaining_tokens(), 2)


class TestMarkerBoundedTokenCursor(unittest.TestCase):
    def test_reports_zero_remaining_at_marker(self):
        inner = TokenCursor(b"0.1 0.2 1,33 0")
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_token(), "0.1")
        self.assertEqual(bounded.read_token(), "0.2")
        self.assertEqual(bounded.remaining_tokens(), 0)
        with self.assertRaises(IndexError):
            bounded.read_token()
        # Underlying cursor stays parked at the marker for the outer loop.
        self.assertEqual(inner.read_token(), "1,33")

    def test_zero_remaining_when_first_token_is_marker(self):
        # The Q2 case: marker immediately follows another marker with no payload.
        inner = TokenCursor(b"1,78 1,133 1,139")
        inner.read_token()  # outer loop already consumed the 1,78 marker
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.remaining_tokens(), 0)
        with self.assertRaises(IndexError):
            bounded.read_token()
        self.assertEqual(inner.read_token(), "1,133")

    def test_passes_through_when_no_marker_ahead(self):
        inner = TokenCursor(b"1.0 2.0 3.0")
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.remaining_tokens(), 3)
        self.assertEqual(bounded.read_token(), "1.0")
        self.assertEqual(bounded.remaining_tokens(), 2)

    def test_read_remaining_bytes_stops_at_next_marker(self):
        # Two registers in one buffer:
        #   "1,17 line1 line2 line3 1,103 ..."
        #   register 17 is the TLE; its payload is the three line tokens.
        # Bounded cursor must give us the bytes up to the "1,103" marker.
        inner = TokenCursor(b"1,17 line1 line2 line3 1,103 mtq")
        # outer paged-frame loop consumes the marker then bounds the child:
        self.assertEqual(inner.read_token(), "1,17")
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_remaining_bytes(), b"line1 line2 line3")
        # Underlying cursor parked at the next marker for the outer loop.
        self.assertEqual(inner.read_token(), "1,103")

    def test_read_remaining_bytes_preserves_internal_whitespace(self):
        # `to_end` strings (e.g. MAVERIC's TLE register) are
        # whitespace-preserving inside the bytes view — the inner
        # buffer slice is returned verbatim.
        inner = TokenCursor(b"1,17 a  b\tc 1,103 mtq")
        inner.read_token()  # consume "1,17"
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_remaining_bytes(), b"a  b\tc")
        self.assertEqual(inner.read_token(), "1,103")

    def test_read_remaining_bytes_no_marker_falls_through(self):
        # Final register in a paged frame: no further marker, slurp to end.
        inner = TokenCursor(b"1,17 line1 line2 line3")
        inner.read_token()
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_remaining_bytes(), b"line1 line2 line3")

    def test_read_remaining_bytes_empty_when_at_marker(self):
        # No payload between two adjacent markers.
        inner = TokenCursor(b"1,17 1,103 mtq")
        inner.read_token()
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_remaining_bytes(), b"")
        self.assertEqual(inner.read_token(), "1,103")

    def test_read_remaining_bytes_after_partial_token_reads(self):
        # Mixed: read one token, then slurp the rest up to marker.
        inner = TokenCursor(b"1,5 head body1 body2 1,9 next")
        inner.read_token()  # "1,5"
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertEqual(bounded.read_token(), "head")
        self.assertEqual(bounded.read_remaining_bytes(), b"body1 body2")
        self.assertEqual(inner.read_token(), "1,9")

    def test_is_a_token_cursor_for_isinstance_dispatch(self):
        inner = TokenCursor(b"a")
        bounded = MarkerBoundedTokenCursor(inner, ",")
        self.assertIsInstance(bounded, TokenCursor)


if __name__ == "__main__":
    unittest.main()
