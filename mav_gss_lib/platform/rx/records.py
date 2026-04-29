"""Typed RX records shared by ingest, decode, and server projections."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from mav_gss_lib.platform._log_envelope import new_event_id
from mav_gss_lib.platform.contract.packets import PacketEnvelope


@dataclass(frozen=True, slots=True)
class RxIngestRecord:
    """Immutable platform-owned record stamped at packet receive time."""

    session_generation: int
    event_id: str
    received_at_ms: int
    received_mono_ns: int
    transport_meta: dict[str, Any]
    raw: bytes


@dataclass(slots=True)
class RxDecodedRecord:
    """Decoded packet plus the ingest metadata it was derived from."""

    ingest: RxIngestRecord
    packet: PacketEnvelope
    container_id: str | None = None


def make_ingest_record(
    session_generation: int,
    meta: dict[str, Any],
    raw: bytes,
    *,
    event_id: str | None = None,
    received_at_ms: int | None = None,
    received_mono_ns: int | None = None,
) -> RxIngestRecord:
    """Build an immutable ingest record, stamping clocks when omitted."""

    return RxIngestRecord(
        session_generation=session_generation,
        event_id=event_id or new_event_id(),
        received_at_ms=received_at_ms if received_at_ms is not None else int(time.time() * 1000),
        received_mono_ns=received_mono_ns if received_mono_ns is not None else time.monotonic_ns(),
        transport_meta=dict(meta),
        raw=bytes(raw),
    )


__all__ = ["RxDecodedRecord", "RxIngestRecord", "make_ingest_record"]
