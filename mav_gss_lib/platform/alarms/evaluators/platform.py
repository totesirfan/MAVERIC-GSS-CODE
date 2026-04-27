"""Platform-level alarm evaluator — silence / ZMQ / CRC / DUP.

Pure: takes a snapshot of inputs (the producer trims windows before
calling) and returns Verdicts. The producer (RxService) tracks the
underlying CRC/DUP event timestamps in deques.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mav_gss_lib.platform.alarms.contract import AlarmSource, Severity
from mav_gss_lib.platform.alarms.registry import Verdict


SILENCE_WARNING_S = 200
SILENCE_CRITICAL_S = 600
CRC_WINDOW_MS = 60_000
CRC_WARNING_THRESHOLD = 3
CRC_CRITICAL_THRESHOLD = 10
DUP_WINDOW_MS = 60_000
DUP_WARNING_THRESHOLD = 5


@dataclass(frozen=True, slots=True)
class PlatformAlarmInputs:
    silence_s: float
    zmq_state: str  # "OK" | "RETRY" | "DOWN"
    crc_event_ms: tuple[int, ...] = field(default_factory=tuple)
    dup_event_ms: tuple[int, ...] = field(default_factory=tuple)


def evaluate_platform(inputs: PlatformAlarmInputs, now_ms: int) -> list[Verdict]:
    return [
        _silence(inputs.silence_s),
        _zmq(inputs.zmq_state),
        _crc(inputs.crc_event_ms, now_ms),
        _dup(inputs.dup_event_ms, now_ms),
    ]


def _silence(silence_s: float) -> Verdict:
    if silence_s >= SILENCE_CRITICAL_S:
        sev, detail = Severity.CRITICAL, f"no packet for {int(silence_s)}s"
    elif silence_s >= SILENCE_WARNING_S:
        sev, detail = Severity.WARNING, f"no packet for {int(silence_s)}s"
    else:
        sev, detail = None, ""
    return Verdict(id="platform.silence", source=AlarmSource.PLATFORM,
                   label="SILENCE", severity=sev, detail=detail)


def _zmq(state: str) -> Verdict:
    state = (state or "").upper()
    if state == "DOWN":
        sev, detail = Severity.CRITICAL, "ZMQ socket disconnected"
    elif state == "RETRY":
        sev, detail = Severity.WARNING, "ZMQ socket reconnecting"
    else:
        sev, detail = None, ""
    return Verdict(id="platform.zmq", source=AlarmSource.PLATFORM, label="ZMQ",
                   severity=sev, detail=detail)


def _crc(event_ms: tuple[int, ...], now_ms: int) -> Verdict:
    cutoff = now_ms - CRC_WINDOW_MS
    count = sum(1 for t in event_ms if t > cutoff)
    if count >= CRC_CRITICAL_THRESHOLD:
        sev = Severity.CRITICAL
    elif count >= CRC_WARNING_THRESHOLD:
        sev = Severity.WARNING
    else:
        sev = None
    return Verdict(id="platform.crc", source=AlarmSource.PLATFORM, label="CRC",
                   severity=sev, detail=f"{count} errors in 60s" if sev else "",
                   context={"count": count, "window_ms": CRC_WINDOW_MS})


def _dup(event_ms: tuple[int, ...], now_ms: int) -> Verdict:
    cutoff = now_ms - DUP_WINDOW_MS
    count = sum(1 for t in event_ms if t > cutoff)
    sev = Severity.WATCH if count >= DUP_WARNING_THRESHOLD else None
    return Verdict(id="platform.dup", source=AlarmSource.PLATFORM, label="DUP",
                   severity=sev, detail=f"{count} duplicates in 60s" if sev else "",
                   context={"count": count, "window_ms": DUP_WINDOW_MS})


__all__ = [
    "CRC_CRITICAL_THRESHOLD", "CRC_WARNING_THRESHOLD", "CRC_WINDOW_MS",
    "DUP_WARNING_THRESHOLD", "DUP_WINDOW_MS", "PlatformAlarmInputs",
    "SILENCE_CRITICAL_S", "SILENCE_WARNING_S", "evaluate_platform",
]
