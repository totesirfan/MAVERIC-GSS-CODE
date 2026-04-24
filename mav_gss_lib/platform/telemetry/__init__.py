"""Platform telemetry — contract types plus runtime fragment/policy/state/router.

Contract (what missions implement):
    TelemetryOps, TelemetryDomainSpec, TelemetryExtractor

Runtime (what the platform uses to collect, merge, and persist fragments):
    TelemetryFragment, MergePolicy, lww_by_ts, EntryLoader, DomainState, TelemetryRouter

Author:  Irfan Annuar - USC ISI SERC
"""

from .contract import CatalogProvider, TelemetryDomainSpec, TelemetryExtractor, TelemetryOps
from .fragment import TelemetryFragment
from .policy import MergePolicy, lww_by_ts
from .router import TelemetryRouter
from .state import DomainState, EntryLoader

__all__ = [
    "CatalogProvider",
    "DomainState",
    "EntryLoader",
    "MergePolicy",
    "TelemetryDomainSpec",
    "TelemetryExtractor",
    "TelemetryFragment",
    "TelemetryOps",
    "TelemetryRouter",
    "lww_by_ts",
]
