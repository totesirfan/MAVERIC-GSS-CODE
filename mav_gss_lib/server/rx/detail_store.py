"""In-memory decoded packet detail/replay store keyed by RX event id."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

from mav_gss_lib.platform.contract.packets import PacketEnvelope

from .events import rx_packet_event

StoredRxDetail = PacketEnvelope | dict[str, Any]


def _event_id(detail: StoredRxDetail) -> str:
    if isinstance(detail, PacketEnvelope):
        return detail.event_id
    return str((detail.get("packet") or {}).get("event_id") or "")


def _to_event(detail: StoredRxDetail, *, replay: bool = False) -> dict[str, Any]:
    if isinstance(detail, PacketEnvelope):
        return rx_packet_event(detail, replay=replay)
    event = dict(detail)
    if replay:
        event["replay"] = True
    return event


class RxDetailStore:
    def __init__(self, maxlen: int) -> None:
        self._details: deque[StoredRxDetail] = deque(maxlen=maxlen)
        self._by_event_id: dict[str, StoredRxDetail] = {}
        self._lock = threading.Lock()

    def append_packet(self, packet: PacketEnvelope) -> None:
        self._append(packet)

    def append_event(self, event: dict[str, Any]) -> None:
        """Compatibility hook for tests/stubs that already hold wire events."""

        self._append(event)

    def append(self, detail: StoredRxDetail) -> None:
        self._append(detail)

    def _append(self, detail: StoredRxDetail) -> None:
        event_id = _event_id(detail)
        with self._lock:
            if self._details.maxlen and len(self._details) == self._details.maxlen:
                removed = self._details[0]
                removed_id = _event_id(removed)
                if removed_id:
                    self._by_event_id.pop(removed_id, None)
            self._details.append(detail)
            if event_id:
                self._by_event_id[event_id] = detail

    def replay(self, *, replay: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            return [_to_event(detail, replay=replay) for detail in self._details]

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            detail = self._by_event_id.get(event_id)
            return _to_event(detail) if detail is not None else None

    def clear(self) -> None:
        with self._lock:
            self._details.clear()
            self._by_event_id.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._details)


__all__ = ["RxDetailStore"]
