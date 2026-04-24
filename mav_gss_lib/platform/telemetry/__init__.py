"""Platform telemetry runtime — fragments, merge policy, state, router.

The telemetry contract (TelemetryOps, TelemetryDomainSpec, TelemetryExtractor)
lives under `mav_gss_lib.platform.contract.telemetry`. This subpackage only
holds the runtime types the platform uses to collect, merge, and persist
telemetry fragments.

Author:  Irfan Annuar - USC ISI SERC
"""

from .fragment import TelemetryFragment
from .policy import MergePolicy, lww_by_ts
from .router import TelemetryRouter
from .state import DomainState, EntryLoader

__all__ = [
    "DomainState",
    "EntryLoader",
    "MergePolicy",
    "TelemetryFragment",
    "TelemetryRouter",
    "lww_by_ts",
]
