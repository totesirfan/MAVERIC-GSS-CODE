"""Parameter.tags carries XTCE-1.3-style AncillaryData."""
from __future__ import annotations

import unittest

from mav_gss_lib.platform.spec.parameters import Parameter


class ParameterTagsTests(unittest.TestCase):
    def test_default_tags_is_empty_mapping(self) -> None:
        p = Parameter(name="X", type_ref="u8")
        self.assertEqual(dict(p.tags), {})

    def test_tags_carry_arbitrary_mission_metadata(self) -> None:
        p = Parameter(
            name="RATE", type_ref="vec3_rate", domain="gnc",
            tags={"module": 1, "register": 0x10},
        )
        self.assertEqual(dict(p.tags), {"module": 1, "register": 16})

    def test_parameter_remains_frozen_with_tags(self) -> None:
        p = Parameter(name="X", type_ref="u8", tags={"a": 1})
        with self.assertRaises(Exception):
            p.tags = {"b": 2}  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
