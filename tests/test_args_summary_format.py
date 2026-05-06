"""Tests for ``platform.spec.format.format_args_summary``."""
import unittest

from mav_gss_lib.platform.spec.format import format_args_summary


class FormatArgsSummaryTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_args_summary([]), "")

    def test_basic_kv(self):
        self.assertEqual(
            format_args_summary([("chunk", 10), ("mode", 1)]),
            "chunk=10 | mode=1",
        )

    def test_skips_none(self):
        self.assertEqual(
            format_args_summary([("a", 1), ("b", None), ("c", 2)]),
            "a=1 | c=2",
        )

    def test_only_none_yields_empty(self):
        self.assertEqual(format_args_summary([("a", None)]), "")

    def test_bool_lowercase(self):
        self.assertEqual(
            format_args_summary([("flag", True), ("off", False)]),
            "flag=true | off=false",
        )

    def test_bytes_hex(self):
        self.assertEqual(
            format_args_summary([("blob", b"\x01\x0a\xff")]),
            "blob=010aff",
        )

    def test_dict_json_compact(self):
        self.assertEqual(
            format_args_summary([("reg", {"f1": True, "f2": False})]),
            'reg={"f1":true,"f2":false}',
        )

    def test_list_json_compact(self):
        self.assertEqual(
            format_args_summary([("v", [1, 2, 3])]),
            "v=[1,2,3]",
        )

    def test_max_items(self):
        items = [(f"k{i}", i) for i in range(15)]
        out = format_args_summary(items, max_items=3)
        self.assertEqual(out, "k0=0 | k1=1 | k2=2 | …+12 more")

    def test_max_items_exact(self):
        items = [(f"k{i}", i) for i in range(3)]
        out = format_args_summary(items, max_items=3)
        self.assertEqual(out, "k0=0 | k1=1 | k2=2")

    def test_max_chars_clip(self):
        items = [("verylongname", "x" * 500)]
        out = format_args_summary(items, max_chars=20)
        self.assertEqual(len(out), 20)
        self.assertTrue(out.endswith("…"))

    def test_custom_separator(self):
        self.assertEqual(
            format_args_summary([("a", 1), ("b", 2)], sep=", "),
            "a=1, b=2",
        )

    def test_string_value_kept_as_is(self):
        self.assertEqual(
            format_args_summary([("filename", "hello, world")]),
            "filename=hello, world",
        )


if __name__ == "__main__":
    unittest.main()
