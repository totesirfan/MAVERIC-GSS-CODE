"""Mission-owned packet event contracts .

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from .packets import PacketEnvelope


class PacketEventSource(Protocol):
    """Optional mission hook for plugin-facing packet side effects."""

    def on_packet(self, packet: PacketEnvelope) -> Iterable[dict[str, Any]]: ...

    def on_client_connect(self) -> Iterable[dict[str, Any]]: ...

@dataclass(frozen=True, slots=True)
class EventOps:
    sources: list[PacketEventSource] = field(default_factory=list)
