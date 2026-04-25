import unittest

from mav_gss_lib.platform.spec import errors


class TestErrorHierarchy(unittest.TestCase):
    def test_all_errors_inherit_from_parse_error_or_runtime_error(self):
        # ParseError families
        self.assertTrue(issubclass(errors.UnknownTypeRef, errors.ParseError))
        self.assertTrue(issubclass(errors.DuplicateTypeName, errors.ParseError))
        self.assertTrue(issubclass(errors.ContainerConflict, errors.ParseError))
        self.assertTrue(issubclass(errors.IncompatibleSchemaVersion, errors.ParseError))
        self.assertTrue(issubclass(errors.InvalidDynamicRef, errors.ParseError))
        self.assertTrue(issubclass(errors.PagedFrameTargetEmpty, errors.ParseError))
        self.assertTrue(issubclass(errors.MissingPluginError, errors.ParseError))

        # Codec/runtime errors inherit from SpecRuntimeError
        self.assertTrue(issubclass(errors.MissingRequiredHeaderField, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.HeaderFieldNotOverridable, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.HeaderValueNotAllowed, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.UnknownHeaderValue, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.ArgsTooLong, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.CmdIdTooLong, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.CrcMismatch, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.NodeIdOutOfRange, errors.SpecRuntimeError))
        self.assertTrue(issubclass(errors.NonJsonSafeArg, errors.SpecRuntimeError))

    def test_parse_error_carries_path_and_message(self):
        err = errors.UnknownTypeRef("V_volts", source="parameter_types.V_volts.type")
        self.assertEqual(err.name, "V_volts")
        self.assertEqual(err.source, "parameter_types.V_volts.type")
        self.assertIn("V_volts", str(err))


if __name__ == "__main__":
    unittest.main()
