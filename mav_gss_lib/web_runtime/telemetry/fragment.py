from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryFragment:
    """One key's value at one moment, tagged with its target domain.

    No meta, no source_cmd_id, no pkt_num. Forensics live in the RX log;
    canonical state holds only what's needed to render and to merge.

    `unit` is optional display metadata (e.g. "V" / "A" / "°C" for EPS
    scalars). It's populated by extractors that already have unit info
    from their semantic decoder (eps_hk via semantics/eps.py's scale
    table), and consumed by the mission's log formatter when rendering
    text and JSONL. The default merge policy `lww_by_ts` does NOT
    serialize `unit` into the on-disk `{v, t}` entry — unit is emit-time
    display metadata, not canonical state. A mission that needs unit at
    render time on the frontend reads it from the domain catalog instead.
    """
    domain: str
    key: str
    value: Any
    ts_ms: int
    unit: str = ""

    def to_dict(self) -> dict:
        """Serialize to the JSON-friendly shape stored on `pkt.mission_data["fragments"]`
        and consumed by log/JSONL/rendering. Field order preserved for readability."""
        return {
            "domain": self.domain, "key": self.key, "value": self.value,
            "ts_ms": self.ts_ms, "unit": self.unit,
        }
