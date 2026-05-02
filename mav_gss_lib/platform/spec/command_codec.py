"""build_declarative_command_ops factory + DeclarativeCommandOpsAdapter.

Implements the §3.6 encode pipeline:
  1. start with meta_cmd.packet defaults (copy)
  2. merge operator overrides; check allowed_packet allowlist
  3. packet_codec.complete_header(...) — codec injects defaults and validates
     any mission-required envelope fields
  4. packet_codec.wrap(completed_header, args_bytes) -> raw

`encoded.mission_facts['header']` is the COMPLETED header (post defaulting),
mirroring the RX MissionFacts shape. Header fields remain mission facts; the
platform does not promote them into typed routing fields.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from mav_gss_lib.platform.contract.commands import (
    CommandDraft,
    CommandOps,
    EncodedCommand,
    FramedCommand,
    ValidationIssue,
)
from mav_gss_lib.platform.contract.parameters import ParamUpdate

from .commands import MetaCommand
from .errors import (
    HeaderFieldNotOverridable,
    HeaderValueNotAllowed,
    NonJsonSafeArg,
)
from .mission import Mission
from .packet_codec import CommandHeader, PacketCodec
from .runtime import DeclarativeWalker


def _json_normalize(value: Any, *, cmd_id: str = "?", path: str = "") -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        b = bytes(value)
        return {"hex": b.hex(), "len": len(b)}
    if isinstance(value, dict):
        return {k: _json_normalize(v, cmd_id=cmd_id, path=f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_normalize(v, cmd_id=cmd_id, path=f"{path}[{i}]") for i, v in enumerate(value)]
    raise NonJsonSafeArg(cmd_id=cmd_id, arg_name=path or "?", value_type=type(value))


def _hashable_json(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(k), _hashable_json(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_hashable_json(v) for v in value)
    return value


class DeclarativeCommandOpsAdapter:
    def __init__(
        self,
        *,
        mission: Mission,
        walker: DeclarativeWalker,
        packet_codec: PacketCodec,
        framer: Any,
    ) -> None:
        self._mission = mission
        self._walker = walker
        self._packet_codec = packet_codec
        self._framer = framer
        self._meta_by_id: Mapping[str, MetaCommand] = mission.meta_commands

    # CommandOps protocol --------------------------------------------------

    def parse_input(self, value: str | dict[str, Any]) -> CommandDraft:
        if isinstance(value, str):
            # Raw CLI: split into "cmd_id arg1 arg2 ..."
            parts = value.strip().split()
            if not parts:
                raise ValueError("empty command input")
            cmd_id = parts[0]
            tokens = parts[1:]
            meta = self._meta_by_id.get(cmd_id)
            args: dict[str, Any] = {}
            if meta:
                for arg, token in zip(meta.argument_list, tokens):
                    args[arg.name] = _coerce_token(token)
            return CommandDraft(payload={"cmd_id": cmd_id, "args": args, "packet": {}})
        return CommandDraft(payload={
            "cmd_id": value["cmd_id"],
            "args": dict(value.get("args", {})),
            "packet": dict(value.get("packet", {})),
        })

    def validate(self, draft: CommandDraft) -> list[ValidationIssue]:
        meta = self._meta_by_id.get(draft.payload["cmd_id"])
        if meta is None:
            return [ValidationIssue(message=f"Unknown command {draft.payload['cmd_id']!r}")]
        issues: list[ValidationIssue] = []
        args = draft.payload["args"]
        known_args = {arg.name for arg in meta.argument_list}
        for name in args:
            if name not in known_args:
                issues.append(ValidationIssue(
                    message=f"{name!r} is not an argument for {meta.id!r}",
                    field=name,
                ))
        for arg in meta.argument_list:
            if arg.name not in args or args[arg.name] in (None, ""):
                issues.append(ValidationIssue(
                    message=f"missing required argument {arg.name!r}",
                    field=arg.name,
                ))
                continue
            v = args[arg.name]
            if arg.valid_range is not None:
                lo, hi = arg.valid_range
                if not (lo <= v <= hi):
                    issues.append(ValidationIssue(
                        message=f"{arg.name}={v} outside valid_range {arg.valid_range}",
                        field=arg.name,
                    ))
            if arg.invalid_values is not None and v in arg.invalid_values:
                issues.append(ValidationIssue(
                    message=f"{arg.name}={v} is reserved (invalid_values)",
                    field=arg.name,
                ))
            if arg.valid_values is not None and v not in arg.valid_values:
                issues.append(ValidationIssue(
                    message=f"{arg.name}={v} not in valid_values",
                    field=arg.name,
                ))
        return issues

    def encode(self, draft: CommandDraft) -> EncodedCommand:
        cmd_id = draft.payload["cmd_id"]
        args = draft.payload["args"]
        operator_packet = draft.payload.get("packet", {})
        meta = self._meta_by_id[cmd_id]

        working = dict(meta.packet)
        for field, value in operator_packet.items():
            if field not in meta.allowed_packet:
                raise HeaderFieldNotOverridable(cmd_id, field)
            if value not in meta.allowed_packet[field]:
                raise HeaderValueNotAllowed(
                    cmd_id, field, value, allowed=tuple(meta.allowed_packet[field]),
                )
            working[field] = value
        args_bytes = self._walker.encode_args(cmd_id, args)
        completed = self._packet_codec.complete_header(CommandHeader(id=cmd_id, fields=working))
        raw = self._packet_codec.wrap(completed, args_bytes)

        completed_fields = dict(completed.fields)
        normalized_args = {
            arg.name: _json_normalize(args[arg.name], cmd_id=cmd_id, path=arg.name)
            for arg in meta.argument_list
            if arg.name in args
        }
        # Surface header (cmd_id + routing) for declarative TX columns.
        mission_facts = {
            "header": {"cmd_id": cmd_id, **completed_fields},
            "protocol": {
                "args_hex": args_bytes.hex(),
                "args_len": len(args_bytes),
                "wire_len": len(raw),
            },
        }
        # Typed args -> parameters (mirrors RX walker emit). The command's
        # argument_list, not operator payload keys, owns names and order.
        params = tuple(
            ParamUpdate(name=name, value=value, ts_ms=0)
            for name, value in normalized_args.items()
        )

        return EncodedCommand(
            raw=raw,
            cmd_id=cmd_id,
            src=str(completed_fields.get("src", "")),
            guard=meta.guard,
            mission_facts=mission_facts,
            parameters=params,
        )

    def frame(self, encoded: EncodedCommand) -> FramedCommand:
        return self._framer.frame(encoded)

    def correlation_key(self, encoded: EncodedCommand) -> tuple:
        facts = encoded.mission_facts if isinstance(encoded.mission_facts, dict) else {}
        header = facts.get("header") if isinstance(facts, dict) else None
        return (encoded.cmd_id, _hashable_json(header or {}))

    def schema(self) -> dict[str, Any]:
        return {
            "commands": {
                cmd.id: {
                    "argument_list": [
                        {"name": a.name, "type": a.type_ref, "description": a.description}
                        for a in cmd.argument_list
                    ],
                    "guard": cmd.guard,
                    "no_response": cmd.no_response,
                    "deprecated": cmd.deprecated,
                }
                for cmd in self._meta_by_id.values()
            }
        }


def _coerce_token(token: str) -> Any:
    try:
        return int(token, 0)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def build_declarative_command_ops(
    mission: Mission,
    plugins: Mapping[str, Callable],
    *,
    packet_codec: PacketCodec,
    framer: Any,
) -> CommandOps:
    walker = DeclarativeWalker(mission, plugins)
    return DeclarativeCommandOpsAdapter(
        mission=mission, walker=walker,
        packet_codec=packet_codec, framer=framer,
    )


__all__ = [
    "DeclarativeCommandOpsAdapter",
    "build_declarative_command_ops",
]
