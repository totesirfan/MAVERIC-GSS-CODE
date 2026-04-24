from .eps_hk import extract as extract_eps_hk
from .gnc_res import extract as extract_gnc_res
from .tlm_beacon import extract as extract_tlm_beacon

# Tuple ordering is load-bearing: the telemetry extractor iterates in order,
# the resulting fragment list preserves it, and that order drives text-log
# line order and packet-detail block order. Append, don't insert, unless
# shifting display order is the intent.
EXTRACTORS = (extract_eps_hk, extract_gnc_res, extract_tlm_beacon)

__all__ = ["EXTRACTORS"]
