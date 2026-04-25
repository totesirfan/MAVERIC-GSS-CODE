import unittest

from mav_gss_lib.platform.spec.parameters import Parameter


class TestParameter(unittest.TestCase):
    def test_parameter_carries_name_type_ref_description(self):
        p = Parameter(name="V_BUS", type_ref="V_volts", description="Unregulated bus")
        self.assertEqual(p.name, "V_BUS")
        self.assertEqual(p.type_ref, "V_volts")

    def test_parameter_default_description_empty(self):
        p = Parameter(name="V_BUS", type_ref="V_volts")
        self.assertEqual(p.description, "")


if __name__ == "__main__":
    unittest.main()
