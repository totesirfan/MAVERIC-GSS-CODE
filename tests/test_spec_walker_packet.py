import unittest
from dataclasses import dataclass

from mav_gss_lib.platform.spec.walker_packet import WalkerPacket


@dataclass(frozen=True, slots=True)
class _StubPacket:
    args_raw: bytes
    header: dict


class TestWalkerPacket(unittest.TestCase):
    def test_runtime_checkable_against_stub_with_required_fields(self):
        p = _StubPacket(args_raw=b"\x01\x02", header={"cmd_id": "eps_hk", "ptype": "RES"})
        self.assertIsInstance(p, WalkerPacket)

    def test_runtime_checkable_rejects_missing_args_raw(self):
        @dataclass(frozen=True, slots=True)
        class NoArgs:
            header: dict

        self.assertNotIsInstance(NoArgs(header={}), WalkerPacket)


if __name__ == "__main__":
    unittest.main()
