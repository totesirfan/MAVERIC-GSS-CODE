import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from mav_gss_lib.platform.contract.commands import EncodedCommand, FramedCommand
from mav_gss_lib.platform.spec.command_codec import build_declarative_command_ops
from mav_gss_lib.platform.spec.errors import (
    HeaderFieldNotOverridable,
    HeaderValueNotAllowed,
    MissingRequiredHeaderField,
    NonJsonSafeArg,
)
from mav_gss_lib.platform.spec.packet_codec import CommandHeader
from mav_gss_lib.platform.spec.yaml_parse import parse_yaml

FIXTURE = Path(__file__).parent / "fixtures" / "spec" / "minimal_mission.yml"
ECHO_FIXTURE = Path(__file__).parent / "fixtures" / "spec" / "echo_v2_mission.yml"


class _StubCodec:
    REQUIRED = ("src", "dest", "echo", "ptype")

    def complete_header(self, h: CommandHeader) -> CommandHeader:
        f = dict(h.fields)
        f.setdefault("src", "GS")
        for r in self.REQUIRED:
            if r not in f:
                raise MissingRequiredHeaderField(h.id, r)
        return CommandHeader(id=h.id, fields=f)

    def wrap(self, h: CommandHeader, args: bytes) -> bytes:
        return f"<{h.id}:{h.fields['dest']}:{len(args)}:".encode() + args + b">"

    def unwrap(self, raw):
        raise NotImplementedError


class _StubFramer:
    def frame(self, encoded: EncodedCommand) -> FramedCommand:
        return FramedCommand(wire=encoded.raw, frame_label="STUB")


class TestCommandOps(unittest.TestCase):
    def setUp(self):
        m = parse_yaml(FIXTURE, plugins={})
        self.ops = build_declarative_command_ops(
            m, plugins={}, packet_codec=_StubCodec(), framer=_StubFramer(),
        )

    def test_encode_no_args(self):
        # gnc_get_mode has no argument_list
        draft = self.ops.parse_input({"cmd_id": "gnc_get_mode", "args": {}})
        encoded = self.ops.encode(draft)
        self.assertIsInstance(encoded, EncodedCommand)
        self.assertEqual(encoded.cmd_id, "gnc_get_mode")
        # Codec defaulted src is on facts.header
        self.assertEqual(encoded.mission_facts["header"]["src"], "GS")
        self.assertEqual(encoded.mission_facts["header"]["dest"], "NODE_A")

    def test_encode_rejects_disallowed_override(self):
        # gnc_get_mode has dest pinned in packet:; not in allowed_packet
        draft = self.ops.parse_input({
            "cmd_id": "gnc_get_mode",
            "args": {},
            "packet": {"dest": "OTHER"},
        })
        with self.assertRaises(HeaderFieldNotOverridable):
            self.ops.encode(draft)

    def test_correlation_key_returns_cmd_id_dest_tuple(self):
        draft = self.ops.parse_input({"cmd_id": "gnc_get_mode", "args": {}})
        encoded = self.ops.encode(draft)
        key = self.ops.correlation_key(encoded)
        self.assertEqual(key[0], "gnc_get_mode")
        self.assertIn(("dest", "NODE_A"), key[1])

    def test_frame_delegates_to_supplied_framer(self):
        draft = self.ops.parse_input({"cmd_id": "gnc_get_mode", "args": {}})
        encoded = self.ops.encode(draft)
        framed = self.ops.frame(encoded)
        self.assertIsInstance(framed, FramedCommand)
        self.assertEqual(framed.frame_label, "STUB")

    def test_bytes_arg_normalised_to_hex_dict(self):
        from mav_gss_lib.platform.spec.command_codec import _json_normalize
        out = _json_normalize({"blob": b"\x01\x02\x03"})
        self.assertEqual(out["blob"], {"hex": "010203", "len": 3})

    def test_unsupported_arg_type_raises(self):
        from mav_gss_lib.platform.spec.command_codec import _json_normalize
        with self.assertRaises(NonJsonSafeArg):
            _json_normalize({"x": object()}, cmd_id="cmd")

    def test_arg_parameters_follow_meta_command_schema(self):
        m = parse_yaml(ECHO_FIXTURE, plugins={})
        ops = build_declarative_command_ops(
            m, plugins={}, packet_codec=_StubCodec(), framer=_StubFramer(),
        )

        draft = ops.parse_input({"cmd_id": "echo", "args": {"payload": "hello"}})
        self.assertEqual(ops.validate(draft), [])
        encoded = ops.encode(draft)

        self.assertEqual([p.name for p in encoded.parameters], ["payload"])
        self.assertEqual(encoded.parameters[0].value, "hello")
        self.assertNotIn("args", encoded.mission_facts["protocol"])

    def test_unknown_arg_key_is_rejected(self):
        m = parse_yaml(ECHO_FIXTURE, plugins={})
        ops = build_declarative_command_ops(
            m, plugins={}, packet_codec=_StubCodec(), framer=_StubFramer(),
        )

        draft = ops.parse_input({"cmd_id": "echo", "args": {"wrong": "hello"}})
        issues = ops.validate(draft)

        self.assertTrue(any(issue.field == "wrong" for issue in issues))
        self.assertTrue(any(issue.field == "payload" for issue in issues))


if __name__ == "__main__":
    unittest.main()
