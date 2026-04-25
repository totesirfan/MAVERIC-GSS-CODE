import unittest
from pathlib import Path

from mav_gss_lib.platform.spec.errors import ContainerConflict
from mav_gss_lib.platform.spec.mission import ContainerShadow
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml

FIXTURES = Path(__file__).parent / "fixtures" / "spec"


class TestContainerOverlap(unittest.TestCase):
    def test_equal_signature_raises_container_conflict(self):
        with self.assertRaises(ContainerConflict):
            parse_yaml(FIXTURES / "invalid_container_conflict.yml", plugins={})

    def test_subset_signature_emits_shadow_warning(self):
        m = parse_yaml(FIXTURES / "invalid_container_shadow.yml", plugins={})
        shadows = [w for w in m.parse_warnings if isinstance(w, ContainerShadow)]
        self.assertTrue(shadows)
        self.assertEqual(shadows[0].broader, "broad_container")
        self.assertEqual(shadows[0].specific, "specific_container")


if __name__ == "__main__":
    unittest.main()
