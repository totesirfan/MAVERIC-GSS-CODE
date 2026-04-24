"""Telemetry contract — what missions implement for telemetry extraction and merge.

Runtime types (TelemetryFragment, MergePolicy, EntryLoader) live in
`mav_gss_lib.platform.telemetry`; the contract references them.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Protocol

from ..telemetry import EntryLoader, MergePolicy, TelemetryFragment, lww_by_ts

if TYPE_CHECKING:
    from .packets import PacketEnvelope

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
