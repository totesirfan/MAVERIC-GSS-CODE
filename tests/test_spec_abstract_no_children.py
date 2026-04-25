import unittest
from pathlib import Path

from mav_gss_lib.platform.spec.errors import ParseError
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml

FIXTURES = Path(__file__).parent / "fixtures" / "spec"


class TestAbstractNoChildren(unittest.TestCase):
    def test_abstract_without_children_rejected(self):
        with self.assertRaises(ParseError):
            parse_yaml(FIXTURES / "invalid_abstract_no_children.yml", plugins={})


if __name__ == "__main__":
    unittest.main()
