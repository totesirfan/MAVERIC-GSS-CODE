import unittest


class TestPublicApi(unittest.TestCase):
    def test_top_level_imports_resolve(self):
        from mav_gss_lib.platform.spec import (
            BUILT_IN_PARAMETER_TYPES,
            CommandHeader,
            DeclarativeWalker,
            Mission,
            MissionDocument,
            PacketCodec,
            WalkerPacket,
            build_declarative_command_ops,
            build_declarative_telemetry_ops,
            parse_yaml,
            parse_yaml_for_tooling,
        )
        self.assertTrue(callable(parse_yaml))
        self.assertTrue(callable(parse_yaml_for_tooling))
        self.assertTrue(callable(build_declarative_telemetry_ops))
        self.assertTrue(callable(build_declarative_command_ops))

    def test_platform_exposes_spec_namespace(self):
        from mav_gss_lib.platform import spec
        self.assertTrue(hasattr(spec, "parse_yaml"))


if __name__ == "__main__":
    unittest.main()
