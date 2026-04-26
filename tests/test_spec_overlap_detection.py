import unittest
from pathlib import Path

from mav_gss_lib.platform.spec.mission import ContainerShadow
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml

FIXTURES = Path(__file__).parent / "fixtures" / "spec"


class TestContainerOverlap(unittest.TestCase):
    def test_equal_signature_allows_fan_out(self):
        # Equal packet signatures on top-level containers are legal — the
        # walker dispatches each matching container with its own cursor,
        # supporting multi-domain emission for a single packet.
        m = parse_yaml(FIXTURES / "invalid_container_conflict.yml", plugins={})
        self.assertIn("a", m.sequence_containers)
        self.assertIn("b", m.sequence_containers)

    def test_subset_signature_emits_shadow_warning(self):
        m = parse_yaml(FIXTURES / "invalid_container_shadow.yml", plugins={})
        shadows = [w for w in m.parse_warnings if isinstance(w, ContainerShadow)]
        self.assertTrue(shadows)
        self.assertEqual(shadows[0].broader, "broad_container")
        self.assertEqual(shadows[0].specific, "specific_container")


if __name__ == "__main__":
    unittest.main()
