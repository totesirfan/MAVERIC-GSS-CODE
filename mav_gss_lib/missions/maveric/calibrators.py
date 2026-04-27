"""Calibrator registry for MAVERIC's declarative mission.yml.

Calibrator signature (per spec §3.5):
    (raw: int | float) -> tuple[Any, str]

Where ``Any`` is JSON-serializable. The returned ``unit`` string overrides
the type's declared unit at fragment emission and catalog projection.

Calibrators are referenced from mission.yml via
``calibrator: {python: <key>}`` and resolved by
``parse_yaml(path, plugins=CALIBRATORS)``. The platform parser parameter
is named ``plugins`` because it accepts arbitrary Python escape-hatch
callables; the mission's local vocabulary is calibrators.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any, Callable

CalibratorCallable = Callable[..., tuple[Any, str]]


def _bcd_byte(value: int) -> int:
    """Convert a single BCD-encoded byte (0xVV) to decimal V*10 + V."""
    high = (value >> 4) & 0x0F
    low = value & 0x0F
    return high * 10 + low


def _maveric_bcd_time(raw: int) -> tuple[dict, str]:
    """uint32 LE BCD time -> {hour, minute, second, display}.

    Byte layout (LE): byte[0]=unused, byte[1]=second, byte[2]=minute, byte[3]=hour.
    """
    second = _bcd_byte((int(raw) >> 8) & 0xFF)
    minute = _bcd_byte((int(raw) >> 16) & 0xFF)
    hour = _bcd_byte((int(raw) >> 24) & 0xFF)
    display = f"{hour:02d}:{minute:02d}:{second:02d}"
    return ({"hour": hour, "minute": minute, "second": second, "display": display}, "")


def _maveric_bcd_date(raw: int) -> tuple[dict, str]:
    """uint32 LE BCD date -> {year, month, day, weekday, display}."""
    weekday = _bcd_byte(int(raw) & 0xFF)
    day = _bcd_byte((int(raw) >> 8) & 0xFF)
    month = _bcd_byte((int(raw) >> 16) & 0xFF)
    year = _bcd_byte((int(raw) >> 24) & 0xFF)
    display = f"{year:02d}-{month:02d}-{day:02d}"
    return (
        {"year": year, "month": month, "day": day,
         "weekday": weekday, "display": display},
        "",
    )


def _to_signed_16(value: int) -> int:
    value &= 0xFFFF
    return value if value < 0x8000 else value - 0x10000


def _maveric_adcs_tmp(raw: int) -> tuple[dict, str]:
    """uint32 LE encoding int16[2] -> {brdtmp, celsius, comm_fault}."""
    raw_word0 = int(raw) & 0xFFFF
    if raw_word0 == 0xFFFF:
        return ({"brdtmp": 0xFFFF, "celsius": None, "comm_fault": True}, "")
    brdtmp = _to_signed_16(raw_word0)
    celsius = brdtmp * 150.0 / 32768.0
    return ({"brdtmp": brdtmp, "celsius": celsius, "comm_fault": False}, "°C")


def _maveric_fss_tmp(raw: int) -> tuple[dict, str]:
    """uint32 LE encoding int16[2] -> per-FSS temperature dict (Eq. 6-3)."""
    fss0 = _to_signed_16(int(raw) & 0xFFFF)
    fss1 = _to_signed_16((int(raw) >> 16) & 0xFFFF)
    return (
        {
            "fss0_raw": fss0,
            "fss1_raw": fss1,
            "fss0_celsius": fss0 * 0.03125,
            "fss1_celsius": fss1 * 0.03125,
        },
        "°C",
    )


_GNC_PLANNER_MODE_NAMES = {0: "Safe", 1: "Auto", 2: "Manual"}


def _maveric_gnc_planner_mode(raw: int) -> tuple[dict, str]:
    mode = int(raw)
    return ({"mode": mode, "mode_name": _GNC_PLANNER_MODE_NAMES.get(mode, "Unknown")}, "")


CALIBRATORS: dict[str, CalibratorCallable] = {
    "maveric.bcd_time": _maveric_bcd_time,
    "maveric.bcd_date": _maveric_bcd_date,
    "maveric.adcs_tmp": _maveric_adcs_tmp,
    "maveric.fss_tmp": _maveric_fss_tmp,
    "maveric.gnc_planner_mode": _maveric_gnc_planner_mode,
}
