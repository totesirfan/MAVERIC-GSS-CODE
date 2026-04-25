"""PacketCodec Protocol + CommandHeader.

PacketCodec is the mission-side wire envelope (header bytes + CRC).
Sits between the mission framer chain and the walker. The walker is
envelope-agnostic — codec implementations live in mission packages.

CommandHeader.id is the logical command id (mission.yml meta_commands key).
How that id reaches the wire is codec-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from .types import HeaderValue
from .walker_packet import WalkerPacket


@dataclass(frozen=True, slots=True)
class CommandHeader:
    id: str
    fields: Mapping[str, HeaderValue]


@runtime_checkable
class PacketCodec(Protocol):
    def complete_header(self, cmd_header: CommandHeader) -> CommandHeader: ...
    def wrap(self, cmd_header: CommandHeader, args_bytes: bytes) -> bytes: ...
    def unwrap(self, raw: bytes) -> WalkerPacket: ...


__all__ = ["CommandHeader", "PacketCodec"]
