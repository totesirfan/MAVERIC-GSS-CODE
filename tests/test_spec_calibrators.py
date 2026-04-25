import unittest

from mav_gss_lib.platform.spec.calibrators import (
    Calibrator,
    PolynomialCalibrator,
    PythonCalibrator,
)


class TestCalibrators(unittest.TestCase):
    def test_polynomial_dataclass_is_frozen(self):
        c = PolynomialCalibrator(coefficients=(0.0, 0.001), unit="V")
        with self.assertRaises(Exception):
            c.unit = "A"

    def test_polynomial_default_unit_is_empty_string(self):
        c = PolynomialCalibrator(coefficients=(1.0,))
        self.assertEqual(c.unit, "")

    def test_polynomial_coefficients_is_tuple(self):
        c = PolynomialCalibrator(coefficients=(0.0, 0.001))
        self.assertIsInstance(c.coefficients, tuple)

    def test_python_calibrator_carries_callable_ref_and_unit(self):
        c = PythonCalibrator(callable_ref="eps.compute_pwr", unit="W")
        self.assertEqual(c.callable_ref, "eps.compute_pwr")
        self.assertEqual(c.unit, "W")

    def test_calibrator_union_accepts_none(self):
        cal: Calibrator = None
        self.assertIsNone(cal)


if __name__ == "__main__":
    unittest.main()
