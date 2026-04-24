"""GNC command-handler dispatch: parsed cmd dict → decoded register dict.

Each handler returns `{register_name: decoded_dict}` or `None`. The
snapshot store does not care which command produced a value; last
write wins for any shared register slot.
"""

from __future__ import annotations

from typing import Callable, Iterator

from mav_gss_lib.missions.maveric.telemetry.semantics.nvg_sensors import (
    _handle_nvg_get_1,
    _handle_nvg_heartbeat,
)

from .gnc_schema import decode_register


def _handle_mtq_get_1(cmd: dict) -> dict[str, dict] | None:
    """Decode an `mtq_get_1` RES (or echo/ACK) into a one-entry dict."""
    typed = cmd.get("typed_args") or []
    extras = cmd.get("extra_args") or []

    if len(typed) < 2:
        return None

    try:
        module = int(typed[0]["value"])
        register = int(typed[1]["value"])
    except (ValueError, TypeError, KeyError):
        return None

    # typed_args[2] is the first token that fell into the "Reg Data"
    # slot from the schema; the rest of the data tokens are in extras.
    reg_data_tokens: list[str] = []
    if len(typed) > 2:
        reg_data_tokens.append(str(typed[2]["value"]))
    reg_data_tokens.extend(str(t) for t in extras)

    decoded = decode_register(module, register, reg_data_tokens)
    return {decoded.name: decoded.to_dict()}


# GNC Planner mode enum — separate from the MTQ STAT.MODE enum.
# Per MAVERIC flight software: 0=Safe, 1=Auto, 2=Manual.
GNC_PLANNER_MODE_NAMES: dict[int, str] = {
    0: "Safe",
    1: "Auto",
    2: "Manual",
}


def _handle_gnc_get_mode(cmd: dict) -> dict[str, dict] | None:
    """Decode `gnc_get_mode` RES → `GNC_MODE` snapshot."""
    typed = cmd.get("typed_args") or []
    if len(typed) < 1:
        return None
    try:
        mode = int(typed[0]["value"])
    except (ValueError, TypeError, KeyError):
        return None
    return {
        "GNC_MODE": {
            "name": "GNC_MODE",
            "module": None,
            "register": None,
            "type": "gnc_mode",
            "unit": "",
            "value": {
                "mode": mode,
                "mode_name": GNC_PLANNER_MODE_NAMES.get(mode, f"UNKNOWN_{mode}"),
            },
            "raw_tokens": [str(mode)],
            "decode_ok": True,
            "decode_error": None,
        }
    }


def _handle_gnc_get_cnts(cmd: dict) -> dict[str, dict] | None:
    """Decode `gnc_get_cnts` RES → `GNC_COUNTERS` snapshot.

    Wire fields per commands.yml: Unexpected Safe Count,
    Unexpected Detumble Count, Sunspin Count. Maps to the dashboard's
    Reboot / De-Tumble / Sunspin counters respectively — "Reboot" on
    the mockup = unexpected safe-mode entries (which are the GNC-side
    recovery events; true power-cycle reboot count lives on
    `tlm_beacon`).
    """
    typed = cmd.get("typed_args") or []
    if len(typed) < 3:
        return None
    try:
        safe     = int(typed[0]["value"])
        detumble = int(typed[1]["value"])
        sunspin  = int(typed[2]["value"])
    except (ValueError, TypeError, KeyError):
        return None
    return {
        "GNC_COUNTERS": {
            "name": "GNC_COUNTERS",
            "module": None,
            "register": None,
            "type": "gnc_counters",
            "unit": "",
            "value": {
                "reboot": safe,       # unexpected-safe count — mockup label
                "detumble": detumble,
                "sunspin": sunspin,
                "unexpected_safe": safe,  # kept under its wire name for clarity
            },
            "raw_tokens": [str(safe), str(detumble), str(sunspin)],
            "decode_ok": True,
            "decode_error": None,
        }
    }


def _walk_paged_frame(tokens: list[str]) -> "Iterator[tuple[str, str, list[str]]]":
    """Yield `(module, register, values)` tuples from a paged-frame stream.

    Shared wire format across mtq_get_active / mtq_get_hk / mtq_get_param:
    the stream alternates `<module>,<register>` marker tokens and raw
    value tokens. Each marker starts a new register; collect subsequent
    non-marker tokens until the next marker or end of stream.
    """
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if "," not in token:
            i += 1
            continue
        try:
            module_s, reg_s = token.split(",", 1)
            module = int(module_s)
            register = int(reg_s)
        except ValueError:
            i += 1
            continue
        j = i + 1
        values: list[str] = []
        while j < len(tokens) and "," not in tokens[j]:
            values.append(tokens[j])
            j += 1
        yield module, register, values
        i = j


def _handle_mtq_paged_regs(cmd: dict) -> dict[str, dict] | None:
    """Decode a paged MTQ register-frame RES into a register snapshot.

    Shared by three frame-type commands:

      mtq_get_active (22 regs / pages 0-4) — flight-operations downlink
        page 0: TIME, DATE, MTQ_USER, ACT_ERR, SEN_ERR
        page 1: Q, LLA, FSS_TMP1, RATE, MAG
        page 2: SV, MAG0_S, FSS0_SV, IMU0_S, IMU1_S
        page 3: PWR_VOL_5V, PWR_CUR_5V, PWR_VOL_3V, PWR_CUR_3V, CONF
        page 4: FSS0_PDSUM, MEAS_MAG_B, MEAS_IMU_B

      mtq_get_hk (7 regs / pages 0-1) — LPPM 5 s housekeeping, beacon
        page 0: STAT, MTQ, ADCS_TMP, CAL_MAG_B, CAL_IMU_B
        page 1: RATE, MAG

      mtq_get_param (18 regs / pages 0-3) — configuration parameters
        page 0: POINTING_AXIS, TLE, MAG_MAT, MAG_VEC, MAG_INFO
        page 1: MAG_STAT, FSS_STAT, IMU_STAT, FSS_INFO, IMU_INFO
        page 2: MASS, INE_TEN, MAG0_ORIEN_BS, FSS0_ORIEN_BS, IMU0_ORIEN_BS
        page 3: IMU1_ORIEN_BS, IMU_BIAS, NVM

    Wire per MAVERIC flight software: Status, Page, then a sequence of
    `<module>,<register>` markers each followed by that register's
    payload values. Last write wins for any register slot, so the GNC
    snapshot stays coherent across frame types.
    """
    typed = cmd.get("typed_args") or []
    extras = cmd.get("extra_args") or []

    if len(typed) < 3:
        return None

    # typed_args[0]=Status, [1]=Page, [2]=Reg Data (first marker token);
    # extras carry the rest of the stream.
    tokens: list[str] = [str(typed[2]["value"])]
    tokens.extend(str(t) for t in extras)

    out: dict[str, dict] = {}
    for module, register, values in _walk_paged_frame(tokens):
        decoded = decode_register(module, register, values)
        out[decoded.name] = decoded.to_dict()
    return out or None


# Command → handler dispatch. Each handler returns
#   {register_name: decoded_dict}  or  None.
# To have a new command feed the dashboard, add its handler here.
# The handler can write into any register-name slot — the snapshot
# store does not care which command produced the value, so if multiple
# commands expose the same logical field they simply overwrite each
# other (last write wins).
COMMAND_HANDLERS: dict[str, Callable[[dict], dict[str, dict] | None]] = {
    "mtq_get_1":      _handle_mtq_get_1,
    "mtq_get_active": _handle_mtq_paged_regs,
    "mtq_get_hk":     _handle_mtq_paged_regs,
    "mtq_get_param":  _handle_mtq_paged_regs,
    "nvg_get_1":      _handle_nvg_get_1,
    "nvg_heartbeat":  _handle_nvg_heartbeat,
    "gnc_get_mode":   _handle_gnc_get_mode,
    "gnc_get_cnts":   _handle_gnc_get_cnts,
}


def decode_from_cmd(cmd: dict) -> dict[str, dict] | None:
    """Dispatch a parsed cmd dict through the command handler table.

    Called by the mission's `extractors/gnc_res.py` extractor. Returns
    `{register_name: decoded}` or `None` if no handler is registered for
    this command. The extractor projects each `decode_ok` entry into a
    TelemetryFragment targeting the `gnc` domain.
    """
    if cmd is None:
        return None
    handler = COMMAND_HANDLERS.get(cmd.get("cmd_id"))
    if handler is None:
        return None
    return handler(cmd)
