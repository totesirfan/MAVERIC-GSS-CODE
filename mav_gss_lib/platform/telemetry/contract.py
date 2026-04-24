"""Telemetry contracts for the platform v2 mission boundary.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Protocol

from .fragment import TelemetryFragment
from .policy import MergePolicy, lww_by_ts
from .state import EntryLoader

if TYPE_CHECKING:
    from ..packets import PacketEnvelope

CatalogProvider = Callable[[], Any]


@dataclass(frozen=True, slots=True)
class TelemetryDomainSpec:
    merge: MergePolicy = lww_by_ts
    load_entries: EntryLoader | None = None
    catalog: CatalogProvider | None = None

    def router_kwargs(self) -> dict[str, Any]:
        return {
            "merge": self.merge,
            "load_entries": self.load_entries,
            "catalog": self.catalog,
        }


class TelemetryExtractor(Protocol):
    def extract(self, packet: PacketEnvelope) -> Iterable[TelemetryFragment]: ...


@dataclass(frozen=True, slots=True)
class TelemetryOps:
    domains: dict[str, TelemetryDomainSpec] = field(default_factory=dict)
    extractors: list[TelemetryExtractor] = field(default_factory=list)
