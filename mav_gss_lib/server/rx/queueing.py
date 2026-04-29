"""Bounded RX queue helpers with explicit overload policy."""

from __future__ import annotations

import threading
from collections import deque
from queue import Empty
from typing import Generic, TypeVar

T = TypeVar("T")


class DropOldestQueue(Generic[T]):
    """Small Queue-like wrapper used at RX ingress.

    Policy is intentionally explicit: if the consumer falls behind long enough
    to fill the queue, the oldest queued record is discarded and the newest one
    is admitted. That preserves the freshest live telemetry instead of letting
    memory grow without bound.
    """

    def __init__(self, maxlen: int) -> None:
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self.maxlen = maxlen
        self.dropped_oldest = 0
        self._items: deque[T] = deque()
        self._lock = threading.Lock()

    def put(self, item: T) -> None:
        with self._lock:
            if len(self._items) >= self.maxlen:
                self._items.popleft()
                self.dropped_oldest += 1
            self._items.append(item)

    def get_nowait(self) -> T:
        with self._lock:
            if not self._items:
                raise Empty
            return self._items.popleft()

    def qsize(self) -> int:
        with self._lock:
            return len(self._items)


__all__ = ["DropOldestQueue"]
