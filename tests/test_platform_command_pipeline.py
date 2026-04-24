from dataclasses import dataclass
from typing import Any

import pytest

from mav_gss_lib.platform import (
    Cell,
    CommandDraft,
    CommandOps,
    CommandRendering,
    EncodedCommand,
    MissionConfigSpec,
    MissionSpec,
    ValidationIssue,
)
from mav_gss_lib.platform.tx.commands import CommandRejected, prepare_command
from mav_gss_lib.platform.loader import load_mission_spec
from mav_gss_lib.missions.echo_v2.mission import EchoPacketOps, EchoUiOps


def test_prepare_command_success_for_echo(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    prepared = prepare_command(spec, "ping hello")

    assert prepared.encoded.raw == b"ping hello"
    assert prepared.encoded.guard is False
    assert prepared.rendering.title == "ping"
    assert prepared.rendering.row["cmd"].value == "ping hello"


def test_prepare_command_rejects_non_commandable_mission(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    with pytest.raises(CommandRejected) as exc:
        prepare_command(spec, "anything")

    assert exc.value.issues[0].message == "mission does not support commands"


@dataclass(slots=True)
class RejectingCommandOps(CommandOps):
    encode_called: bool = False

    def parse_input(self, value: str | dict[str, Any]) -> CommandDraft:
        return CommandDraft({"line": value})

    def validate(self, draft: CommandDraft) -> list[ValidationIssue]:
        return [ValidationIssue("bad command", field="line")]

    def encode(self, draft: CommandDraft) -> EncodedCommand:
        self.encode_called = True
        return EncodedCommand(raw=b"should-not-happen")

    def render(self, encoded: EncodedCommand) -> CommandRendering:
        return CommandRendering(title="bad", row={"cmd": Cell("bad")})

    def schema(self) -> dict[str, Any]:
        return {}

    def tx_columns(self):
        return []


def test_prepare_command_validation_failure_blocks_encode():
    ops = RejectingCommandOps()
    spec = MissionSpec(
        id="rejecting",
        name="Rejecting",
        packets=EchoPacketOps(),
        ui=EchoUiOps(),
        config=MissionConfigSpec(),
        commands=ops,
    )

    with pytest.raises(CommandRejected) as exc:
        prepare_command(spec, "bad")

    assert exc.value.issues[0].message == "bad command"
    assert ops.encode_called is False
