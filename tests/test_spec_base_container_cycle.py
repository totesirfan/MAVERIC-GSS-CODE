import unittest
from pathlib import Path

from mav_gss_lib.platform.spec.errors import ParseError
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml

FIXTURES = Path(__file__).parent / "fixtures" / "spec"


class TestBaseContainerChains(unittest.TestCase):
    def test_multi_level_chain_rejected(self):
        with self.assertRaises(ParseError):
            parse_yaml(FIXTURES / "invalid_multi_level_inheritance.yml", plugins={})


if __name__ == "__main__":
    unittest.main()
