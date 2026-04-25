import unittest

from mav_gss_lib.platform.spec.packet_codec import CommandHeader, PacketCodec


class TestCommandHeader(unittest.TestCase):
    def test_command_header_carries_id_and_fields(self):
        h = CommandHeader(id="eps_hk", fields={"dest": "EPS", "ptype": "CMD"})
        self.assertEqual(h.id, "eps_hk")
        self.assertEqual(dict(h.fields), {"dest": "EPS", "ptype": "CMD"})


class TestPacketCodecProtocolShape(unittest.TestCase):
    def test_runtime_checkable_against_stub(self):
        class _Stub:
            def complete_header(self, h):
                return h

            def wrap(self, h, args):
                return b""

            def unwrap(self, raw):
                return None

        self.assertIsInstance(_Stub(), PacketCodec)


if __name__ == "__main__":
    unittest.main()
