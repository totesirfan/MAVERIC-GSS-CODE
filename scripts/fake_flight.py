#!/usr/bin/env python3
"""Fake flight-side responder for MAVERIC commands.

Listens on the GSS /ws/tx event stream and emits the canonical
UPPM-gateway-ACK + destination-ACK + destination-RES sequence on the
RX ZMQ socket. Synthetic RES args are derived from `commands.yml`
rx_args, with hand-tuned overrides for commands where a realistic
value matters (com_ping → "pong", ppm_get_time → live RTC, etc).

Lets an operator drive the GSS UI through almost the entire MAVERIC
command schema without flight hardware.

Per-dest flow (mirrors fake_flight_com_ping.py):
    LPPM/HLNV/ASTR :  UPPM ACK (~0.4s) → dest ACK (~1.2s) → dest RES (~2.5s)
    UPPM           :  UPPM ACK (~0.4s) →                  → UPPM RES (~2.5s)
    EPS            :  UPPM ACK (~0.4s) →                  → EPS  RES (~2.5s)

Skip rules:
    * `rx_only` commands (tlm_beacon, tlm_get_data) — never originated by GSS.
    * Commands listed in SILENT_CMDS (rpi_shutdown, ftdi_log) — flight emits
      no response.
    * Destinations not in FLOWS (e.g. FTDI) — silently dropped.

Run BEFORE issuing a command from the UI:

    conda activate
    python3 scripts/fake_flight.py

Options:
    --only LPPM            respond only when dest matches
    --skip cfg_get         skip a specific cmd_id (repeatable)
    --beacon-period 60     seconds between tlm_beacon emits (0 disables)
    --http URL             non-default GSS URL (default http://127.0.0.1:8080)
    --rx-addr ADDR         non-default RX PUB bind (default reads gss.yml)

Outgoing PDUs are tagged transmitter=AX100 in the PMT metadata so the
GSS frame detector classifies them as ASM+GOLAY rather than UNKNOWN —
this silences the "Unknown frame type — returning raw" warning that
the original com_ping responder script generated.

Beacons are TLM-typed tlm_beacon packets (97-byte unified struct)
sourced from UPPM. The mission's tlm_beacon extractor decodes them
into spacecraft/gnc/eps telemetry fragments, populating the live
state, GNC dashboard, and EPS bench views.

eps_hk responses are TLM-typed (not RES), carrying a 96-byte EPS HK
binary struct that the eps_hk extractor decodes into 48 engineering-
unit fragments. This makes the eps_hk command's `value_change`
verifier fire correctly.

Stops on Ctrl-C.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pmt
import zmq

from mav_gss_lib.config import load_split_config
from mav_gss_lib.protocols.crc import crc16
from mav_gss_lib.protocols.csp import CSPConfig
from mav_gss_lib.missions.maveric.defaults import NODES, PTYPES
from mav_gss_lib.missions.maveric.schema import load_command_defs
from mav_gss_lib.missions.maveric.wire_format import build_cmd_raw
from mav_gss_lib.transport import init_zmq_pub

NODE_ID = {name: nid for nid, name in NODES.items()}
PTYPE_ID = {name: pid for pid, name in PTYPES.items()}

GS   = NODE_ID["GS"]
UPPM = NODE_ID["UPPM"]
LPPM = NODE_ID["LPPM"]
EPS  = NODE_ID["EPS"]
HLNV = NODE_ID["HLNV"]
ASTR = NODE_ID["ASTR"]
ACK  = PTYPE_ID["ACK"]
RES  = PTYPE_ID["RES"]
TLM  = PTYPE_ID["TLM"]


# Layout from `missions/maveric/telemetry/extractors/tlm_beacon.py`. 97 bytes.
BEACON_STRUCT = struct.Struct("<7sQBHBHBBBBBBBIBB3f3f3ffHHHHHHHHBHHH")
assert BEACON_STRUCT.size == 97

# Layout from `missions/maveric/telemetry/semantics/eps.py`. 48 int16 = 96 bytes.
EPS_HK_STRUCT = struct.Struct("<48h")
assert EPS_HK_STRUCT.size == 96


# Per-dest flow: (second_ack_source_or_None, res_source).
# UPPM is always the gateway-ack source for nodes behind it.
FLOWS: dict[str, tuple[int | None, int]] = {
    "LPPM": (LPPM, LPPM),
    "UPPM": (None, UPPM),   # UPPM is both gateway and responder
    "HLNV": (HLNV, HLNV),
    "ASTR": (ASTR, ASTR),
    "EPS":  (None, EPS),    # EPS only emits RES, no ACK
}

# Commands the flight side never replies to (per GNC Command List CSV).
SILENT_CMDS: set[str] = {"rpi_shutdown", "ftdi_log"}


def _now_ms() -> str:
    return str(int(time.time() * 1000))


# Default token by rx_arg type — used when no override is registered.
DEFAULTS_BY_TYPE: dict[str, Callable[[], str]] = {
    "int":      lambda: "0",
    "float":    lambda: "0.0",
    "str":      lambda: "ok",
    "bool":     lambda: "1",
    "epoch_ms": _now_ms,
    "blob":     lambda: "",
}

# Default token by rx_arg *name* (lowercased). Beats DEFAULTS_BY_TYPE.
# Reflects real on-orbit conventions observed in `logs/json/` — flight
# returns Status="1" for SUCCESS, not "0", so a naive int default would
# render every reply as a failure in the GSS UI.
NAME_DEFAULTS: dict[str, str] = {
    "status":          "1",
    "mode":            "1",
    "module":          "0",
    "register":        "0",
    "reg data":        "0x0000",
    "address":         "0x0",
    "length":          "0",
    "filename":        "img.jpg",
    "thumb filename":  "thumb_img.jpg",
    "num chunks":      "10",
    "thumb num chunks": "2",
    "page":            "0",
    "sensor":          "0",
    "rate":            "1",
    "sched id":        "0",
    "active":          "1",
    "type":            "1",
    "period (ms)":     "1000",
    "remaining reps":  "10",
    "next release":    None,   # filled at call time → _now_ms()
    "weekday":         "1",
    "month":           "1",
    "day":             "1",
    "year":            "2026",
    "hour":            "0",
    "minute":          "0",
    "second":          "0",
    "power level":     "30",
    "beacon period":   "60",
    "log level":       "2",
    "ops stage":       "2",
    "burn port":       "0",
    "burn res":        "0",
    "time":            "0",
    "counter":         "0",
    "port":            "0",
    "io":              "1",
    "tle":             "ok",
    "config":          "log_level=INFO,ops_stage=NOMINAL",
    "response":        "pong",
    "x":               "0.0",
    "y":               "0.0",
    "z":               "0.0",
    "mag x":           "100",
    "mag y":           "-20",
    "mag z":           "50",
    "unexpected safe count":     "0",
    "unexpected detumble count": "0",
    "sunspin count":   "0",
    "gyro rate source": "1",
    "mag source":       "1",
}


# ── Per-cmd response overrides ─────────────────────────────────────────────
# Each builder receives the inbound args_str and returns the args_str to
# place in the synthetic RES frame. Status fields default to "0" (success).

def _ov_com_ping(_a: str) -> str:
    return "pong"

def _ov_ppm_get_time(_a: str) -> str:
    t = time.gmtime()
    # weekday: 1=Mon..7=Sun; tm_wday is 0=Mon..6=Sun.
    return f"{t.tm_wday + 1} {t.tm_mon} {t.tm_mday} {t.tm_year} {t.tm_hour} {t.tm_min} {t.tm_sec}"

def _ov_cfg_get(_a: str) -> str:
    return "log_level=INFO,ops_stage=NOMINAL,beacon_period=60,gyro_src=NVG,mag_src=NVG"

def _ov_gnc_get_mode(_a: str) -> str:
    return "1"  # observed in logs/json/ on 2026-04-24

def _ov_gnc_get_cnts(_a: str) -> str:
    return "0 0 0"  # counts — not status fields, real zeros are fine

def _ov_ax100_get_power(_a: str) -> str:
    return "1 30"

def _ov_mag_read(_a: str) -> str:
    return "100 -20 50"

def _ov_mtq_heartbeat(_a: str) -> str:
    return "1"

def _ov_nvg_heartbeat(_a: str) -> str:
    return "1"

def _ov_ppm_get_sched(args_in: str) -> str:
    sid = (args_in.split() or ["0"])[0]
    # status, sched_id, active, type, period_ms, remaining_reps, next_release
    return f"1 {sid} 1 2 1000 65535 {_now_ms()}"

def _ov_ppm_get_all_scheds(_a: str) -> str:
    # repeated slot_idx:id,active,type
    return "0:1,1,1 1:2,1,2 6:6,1,3"

def _ov_ppm_sched_cmd(args_in: str) -> str:
    parts = args_in.split()
    sid = parts[0] if parts else "0"
    return f"1 {sid} {_now_ms()}"

def _ov_ppm_desched(args_in: str) -> str:
    sid = (args_in.split() or ["0"])[0]
    return f"1 {sid}"

def _ov_ppm_resched(args_in: str) -> str:
    sid = (args_in.split() or ["0"])[0]
    return f"1 {sid} {_now_ms()}"

def _ov_ppm_clear_sched(args_in: str) -> str:
    sid = (args_in.split() or ["0"])[0]
    return f"1 {sid}"

def _ov_ppm_update_sched(args_in: str) -> str:
    parts = args_in.split()
    sid    = parts[0] if len(parts) > 0 else "0"
    period = parts[1] if len(parts) > 1 else "1000"
    reps   = parts[2] if len(parts) > 2 else "10"
    return f"1 {sid} {period} {reps}"

def _ov_flash_read(args_in: str) -> str:
    parts = args_in.split()
    addr   = parts[0] if len(parts) > 0 else "0x0"
    length = parts[1] if len(parts) > 1 else "0"
    # status, address, length, payload (blob — empty in synth)
    return f"1 {addr} {length}"

def _ov_flash_write(args_in: str) -> str:
    parts = args_in.split()
    addr   = parts[0] if len(parts) > 0 else "0x0"
    length = parts[1] if len(parts) > 1 else "0"
    return f"1 {addr} {length}"

def _ov_flash_erase(args_in: str) -> str:
    parts = args_in.split()
    addr   = parts[0] if len(parts) > 0 else "0x0"
    nblk   = parts[1] if len(parts) > 1 else "1"
    return f"1 {addr} 0 {nblk}"

def _ov_flash_unprot(args_in: str) -> str:
    addr = (args_in.split() or ["0x0"])[0]
    return f"1 {addr}"

def _ov_flash_read_prot(args_in: str) -> str:
    addr = (args_in.split() or ["0x0"])[0]
    return f"1 {addr} 1"

def _ov_mtq_read_1(args_in: str) -> str:
    parts = args_in.split()
    midx = parts[0] if len(parts) > 0 else "0"
    ridx = parts[1] if len(parts) > 1 else "0"
    return f"1 {midx} {ridx}"

def _ov_mtq_get_1(args_in: str) -> str:
    # rx_args = [Module, Register, Reg Data] — no leading status (per real
    # 2026-04-24 sample: Module=0, Register=136, Reg Data="NaN").
    parts = args_in.split()
    midx = parts[0] if len(parts) > 0 else "0"
    ridx = parts[1] if len(parts) > 1 else "0"
    return f"{midx} {ridx} 0x0000"

def _ov_mtq_set_1(args_in: str) -> str:
    parts = args_in.split()
    midx = parts[0] if len(parts) > 0 else "0"
    ridx = parts[1] if len(parts) > 1 else "0"
    return f"1 {midx} {ridx}"

def _ov_mtq_get_active(args_in: str) -> str:
    # Real on-orbit shape: "1 <page> midx,ridx" (e.g. "1 0 0,5").
    page = (args_in.split() or ["0"])[0]
    return f"1 {page} 0,0"

def _ov_mtq_get_hk(args_in: str) -> str:
    page = (args_in.split() or ["0"])[0]
    return f"1 {page} 0,0"

def _ov_mtq_get_param(args_in: str) -> str:
    page = (args_in.split() or ["0"])[0]
    return f"1 {page} 0,0"

def _ov_nvg_get_1(args_in: str) -> str:
    sid = (args_in.split() or ["0"])[0]
    return f"1 {sid} {_now_ms()} 0.0,0.0,0.0"

def _ov_nvg_set_1(args_in: str) -> str:
    parts = args_in.split()
    sid  = parts[0] if len(parts) > 0 else "0"
    rate = parts[1] if len(parts) > 1 else "1"
    return f"1 {sid} {rate}"

def _ov_cam_capture(args_in: str) -> str:
    parts = args_in.split()
    fname = parts[0] if parts else "img.jpg"
    qty = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    qty = max(1, min(qty, 4))
    stem = fname[:-4] if fname.lower().endswith(".jpg") else fname
    chunks = []
    for i in range(qty):
        chunks.append(f"1 {stem}_{i}.jpg 10 thumb_{stem}_{i}.jpg 2")
    return " ".join(chunks)

def _ov_img_cnt_chunks(args_in: str) -> str:
    parts = args_in.split()
    fname = parts[0] if parts else "img.jpg"
    return f"1 {fname} 10 thumb_{fname} 2"

def _ov_img_get_chunks(args_in: str) -> str:
    parts = args_in.split()
    fname = parts[0] if parts else "img.jpg"
    start = parts[1] if len(parts) > 1 else "0"
    return f"{fname} {start} 0"

def _ov_cfg_set_bcnprd(args_in: str) -> str:
    period = (args_in.split() or ["60"])[0]
    return f"1 {period}"


OVERRIDES: dict[str, Callable[[str], str]] = {
    "com_ping":           _ov_com_ping,
    "ppm_get_time":       _ov_ppm_get_time,
    "cfg_get":            _ov_cfg_get,
    "cfg_set_bcnprd":     _ov_cfg_set_bcnprd,
    "gnc_get_mode":       _ov_gnc_get_mode,
    "gnc_get_cnts":       _ov_gnc_get_cnts,
    "ax100_get_power":    _ov_ax100_get_power,
    "mag_read":           _ov_mag_read,
    "mtq_heartbeat":      _ov_mtq_heartbeat,
    "nvg_heartbeat":      _ov_nvg_heartbeat,
    "ppm_get_sched":      _ov_ppm_get_sched,
    "ppm_get_all_scheds": _ov_ppm_get_all_scheds,
    "ppm_sched_cmd":      _ov_ppm_sched_cmd,
    "ppm_desched":        _ov_ppm_desched,
    "ppm_resched":        _ov_ppm_resched,
    "ppm_clear_sched":    _ov_ppm_clear_sched,
    "ppm_update_sched":   _ov_ppm_update_sched,
    "flash_read":         _ov_flash_read,
    "flash_write":        _ov_flash_write,
    "flash_erase":        _ov_flash_erase,
    "flash_unprot":       _ov_flash_unprot,
    "flash_read_prot":    _ov_flash_read_prot,
    "mtq_read_1":         _ov_mtq_read_1,
    "mtq_get_1":          _ov_mtq_get_1,
    "mtq_set_1":          _ov_mtq_set_1,
    "mtq_get_active":     _ov_mtq_get_active,
    "mtq_get_hk":         _ov_mtq_get_hk,
    "mtq_get_param":      _ov_mtq_get_param,
    "nvg_get_1":          _ov_nvg_get_1,
    "nvg_set_1":          _ov_nvg_set_1,
    "cam_capture":        _ov_cam_capture,
    "img_cnt_chunks":     _ov_img_cnt_chunks,
    "img_get_chunks":     _ov_img_get_chunks,
}


def _default_for(arg_def: dict) -> str:
    """Pick the synth default for a single rx_arg. Name-keyed beats type-keyed."""
    name_key = (arg_def.get("name") or "").strip().lower()
    if name_key in NAME_DEFAULTS:
        v = NAME_DEFAULTS[name_key]
        return _now_ms() if v is None else v
    gen = DEFAULTS_BY_TYPE.get(arg_def.get("type", "str"), DEFAULTS_BY_TYPE["str"])
    return gen()


def synth_args(cmd_id: str, args_in: str, cmd_defs: dict) -> str:
    """Build the args_str for a synthetic RES frame."""
    ov = OVERRIDES.get(cmd_id)
    if ov is not None:
        return ov(args_in)
    defn = cmd_defs.get(cmd_id)
    if not defn:
        return "1"
    rx_args = defn.get("rx_args") or []
    if not rx_args:
        return "1"
    return " ".join(_default_for(a) for a in rx_args)


def _build_response(src: int, ptype: int, cmd_id: str, args: str = "") -> bytes:
    """CSP-wrapped text-arg CommandFrame from flight → GS."""
    csp = CSPConfig()
    csp.src = 8; csp.dest = 0; csp.dport = 24; csp.sport = 0
    frame = build_cmd_raw(src=src, dest=GS, cmd=cmd_id, args=args, echo=0, ptype=ptype)
    return csp.wrap(bytes(frame))


def _build_binary_response(src: int, ptype: int, cmd_id: str, args_raw: bytes) -> bytes:
    """CSP-wrapped CommandFrame carrying *binary* args_raw.

    `wire_format.CommandFrame.to_bytes()` ASCII-encodes args_str, which
    cannot represent 0x00–0xFF blobs. This helper builds the inner
    frame bytes directly so tlm_beacon (97 B) and eps_hk TLM (96 B)
    blobs survive the trip.
    """
    cmd_bytes = cmd_id.encode("ascii")
    header = bytes([src & 0xFF, GS & 0xFF, 0, ptype & 0xFF,
                    len(cmd_bytes) & 0xFF, len(args_raw) & 0xFF])
    packet = bytearray(header)
    packet.extend(cmd_bytes)
    packet.append(0x00)
    packet.extend(args_raw)
    packet.append(0x00)
    crc_val = crc16(packet)
    packet.extend(crc_val.to_bytes(2, byteorder="little"))

    csp = CSPConfig()
    csp.src = 8; csp.dest = 0; csp.dport = 24; csp.sport = 0
    return csp.wrap(bytes(packet))


def _make_meta_ax100() -> "pmt.pmt_t":
    """PMT metadata dict that mimics gr-satellites' AX100 demodulator
    output. `frame_detect.detect_frame_type` looks for "AX100" in the
    `transmitter` field and classifies as ASM+GOLAY — silences the
    "Unknown frame type — returning raw" warning the GSS otherwise
    stamps on every synthetic packet."""
    meta = pmt.make_dict()
    meta = pmt.dict_add(meta, pmt.intern("transmitter"), pmt.intern("AX100"))
    return meta


def _send_pdu_ax100(sock, payload: bytes) -> bool:
    """Replacement for `transport.send_pdu` that tags transmitter=AX100."""
    meta = _make_meta_ax100()
    vec = pmt.init_u8vector(len(payload), list(payload))
    try:
        sock.send(pmt.serialize_str(pmt.cons(meta, vec)))
        return True
    except zmq.ZMQError:
        return False


def _publish(sock, payload: bytes, label: str) -> None:
    ts = time.strftime("%H:%M:%S")
    ok = _send_pdu_ax100(sock, payload)
    print(f"  [{ts}] → {label} ({len(payload)}B) {'ok' if ok else 'FAIL'}")


# ── Binary telemetry packers ──────────────────────────────────────────────

def _pack_beacon() -> bytes:
    """Build a 97-byte tlm_beacon struct with realistic values."""
    return BEACON_STRUCT.pack(
        b"MAVERIC",                      # callsign[7]
        int(time.time() * 1000),         # time (ms since epoch)
        2,                                # ops_stage (NOMINAL)
        0, 0,                             # lppm_rbt_cnt, lppm_rbt_cause
        0, 0,                             # uppm_rbt_cnt, uppm_rbt_cause
        1, 1, 1, 1,                       # ertc/mtq/nvg/eps heartbeats
        0, 0,                             # hn_state, ab_state
        0x80,                             # mtq_stat (STAT bitfield)
        1, 1,                             # gyro_rate_src, mag_src (NVG)
        0.0, 0.0, 0.0,                    # gyro_rate[3] (rad/s)
        10000.0, -5000.0, 30000.0,        # mag[3] (nT)
        0.0, 0.0, 0.0,                    # mtq_dipole[3] (A.m^2)
        22.5,                             # temp_adcs (°C)
        350,                              # i_bus (mA → 0.350 A)
        100,                              # i_bat (mA → 0.100 A)
        7400,                             # v_bus (mV → 7.4 V)
        7400,                             # v_bat (mV → 7.4 V)
        5000,                             # v_sys (mV → 5.0 V)
        307,                              # temp_adc (raw, ~30 % via 0.0976563)
        50,                               # temp_die (raw, 25 °C via 0.5)
        1,                                # eps_mode
        1,                                # gnc_mode
        0, 0, 0,                          # unexpected_safe/detumble/sunspin
    )


def _pack_eps_hk() -> bytes:
    """Build a 96-byte EPS HK struct (48 int16 LE) with realistic values.

    Field order matches `_EPS_HK_NAMES` in semantics/eps.py. Voltages
    in mV, currents in mA, powers in mW. TS_ADC and T_DIE are raw
    (BQ25672 register LSBs scaled by 0.0976563 %/LSB and 0.5 °C/LSB).
    """
    return EPS_HK_STRUCT.pack(
        # I_BUS  I_BAT  V_BUS  V_AC1  V_AC2  V_BAT  V_SYS
        350,   100,   7400,  0,     0,     7400,  5000,
        # TS_ADC  T_DIE  V3V3  I3V3  P3V3
        307,    50,    3300, 50,   165,
        # V5V0  I5V0  P5V0
        5000,  100,  500,
        # VOUT1..6 / IOUT1..6 / POUT1..6 grouped per-channel
        3300, 0, 0,    3300, 0, 0,
        3300, 0, 0,    3300, 0, 0,
        3300, 0, 0,    3300, 0, 0,
        # VBRN1..2 / IBRN1..2 / PBRN1..2
        0, 0, 0,       0, 0, 0,
        # VSIN1..3 / ISIN1..3 / PSIN1..3
        0, 0, 0,       0, 0, 0,       0, 0, 0,
    )


async def respond(pub_sock, cmd_id: str, dest: str, args_in: str,
                  cmd_defs: dict, skips: set[str]) -> None:
    """Fire the canonical ACK/RES sequence for one (cmd_id, dest)."""
    if cmd_id in SILENT_CMDS or cmd_id in skips:
        return
    defn = cmd_defs.get(cmd_id)
    if defn and defn.get("rx_only"):
        return
    dest_u = (dest or "").upper()
    if dest_u not in FLOWS:
        return
    second_ack_src, res_src = FLOWS[dest_u]

    await asyncio.sleep(0.4)
    _publish(pub_sock, _build_response(UPPM, ACK, cmd_id),
             f"UPPM ACK  ({cmd_id} → {dest_u})")

    if second_ack_src is not None:
        await asyncio.sleep(0.8)
        _publish(pub_sock, _build_response(second_ack_src, ACK, cmd_id),
                 f"{dest_u} ACK")

    # eps_hk is a TLM-typed packet carrying a 96-byte binary HK struct, NOT a
    # text-arg RES. The eps_hk extractor in the mission only fires when both
    # cmd_id=="eps_hk" and ptype==TLM, so the operator's `complete` verifier
    # (watching eps.hk for value_change) only sees motion if we send TLM here.
    if cmd_id == "eps_hk":
        await asyncio.sleep(1.3)
        _publish(pub_sock,
                 _build_binary_response(res_src, TLM, "eps_hk", _pack_eps_hk()),
                 f"{dest_u} TLM eps_hk (96B)")
        return

    res_args = synth_args(cmd_id, args_in, cmd_defs)
    await asyncio.sleep(1.3)
    preview = res_args if len(res_args) <= 60 else res_args[:57] + "..."
    _publish(pub_sock, _build_response(res_src, RES, cmd_id, res_args),
             f"{dest_u} RES '{preview}'")


async def beacon_loop(pub_sock, period_s: float) -> None:
    """Emit a tlm_beacon TLM packet from UPPM every `period_s` seconds.

    The beacon is the unified 97-byte struct decoded by the mission's
    tlm_beacon extractor — drives spacecraft/gnc/eps telemetry fragments
    so the GSS Live State, GNC dashboard, and EPS bench views all
    populate without flight hardware.
    """
    if period_s <= 0:
        return
    # First beacon goes out almost immediately so the operator sees life
    # without waiting a full period.
    await asyncio.sleep(2.0)
    while True:
        try:
            payload = _build_binary_response(UPPM, TLM, "tlm_beacon", _pack_beacon())
            _publish(pub_sock, payload, "UPPM TLM tlm_beacon (97B)")
        except Exception as exc:
            print(f"  beacon error: {exc}", file=sys.stderr)
        await asyncio.sleep(period_s)


def _coerce_args(payload_args) -> str:
    """Normalize the WS payload args field into a single space-joined string."""
    if payload_args is None:
        return ""
    if isinstance(payload_args, str):
        return payload_args
    if isinstance(payload_args, list):
        return " ".join(str(a) for a in payload_args)
    return str(payload_args)


async def run(http_base: str, ws_base: str, rx_addr: str, only: str,
              skips: set[str], cmd_defs: dict, beacon_period_s: float) -> int:
    try:
        with urlopen(f"{http_base}/api/status", timeout=5) as resp:
            status = json.loads(resp.read())
        token = status.get("auth_token")
    except Exception as exc:
        print(f"ERROR: cannot reach {http_base}/api/status — is MAV_WEB.py running?\n  {exc}",
              file=sys.stderr)
        return 1
    if not token:
        print("ERROR: /api/status returned no auth_token", file=sys.stderr)
        return 1

    try:
        import websockets
    except ImportError:
        print("ERROR: 'websockets' package is required (it ships with uvicorn[standard])",
              file=sys.stderr)
        return 1

    pub_ctx, pub_sock, pub_mon = init_zmq_pub(rx_addr)
    uri = f"{ws_base}/ws/tx?token={token}"
    txable = sum(1 for c, d in cmd_defs.items()
                 if not d.get("rx_only") and c not in SILENT_CMDS)
    print(f"fake_flight  ({txable} responsive cmds, {len(OVERRIDES)} overrides)")
    print(f"  /ws/tx  ← {uri}")
    print(f"  downlink → {rx_addr}")
    print(f"  only: {only}   skipping: {sorted(skips) or '(none)'}")
    if beacon_period_s > 0:
        print(f"  beacon: every {beacon_period_s:.0f}s (UPPM TLM tlm_beacon, 97B)")
    else:
        print(f"  beacon: disabled")
    print(f"  Ctrl-C to stop.\n")

    beacon_task = asyncio.create_task(beacon_loop(pub_sock, beacon_period_s))

    try:
        async with websockets.connect(uri, max_size=2**24) as ws:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if msg.get("type") != "sent":
                    continue
                data = msg.get("data") or {}
                payload = data.get("payload") or {}
                cmd_id = (payload.get("cmd_id") or "").lower()
                dest = (payload.get("dest") or "").upper()
                args_in = _coerce_args(payload.get("args"))
                if only != "ANY" and dest != only:
                    print(f"[{time.strftime('%H:%M:%S')}] skip {cmd_id} → {dest} (only={only})")
                    continue
                args_preview = args_in if len(args_in) <= 40 else args_in[:37] + "..."
                print(f"[{time.strftime('%H:%M:%S')}] ↑ sent {cmd_id} → {dest}  args={args_preview!r}")
                asyncio.create_task(respond(pub_sock, cmd_id, dest, args_in, cmd_defs, skips))
    except KeyboardInterrupt:
        print("\nstopped.")
    except Exception as exc:
        print(f"\nWS error: {exc}", file=sys.stderr)
    finally:
        beacon_task.cancel()
        try:
            await beacon_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            pub_mon.close(); pub_sock.close(); pub_ctx.term()
        except Exception:
            pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fake flight-side responder for MAVERIC commands.",
    )
    parser.add_argument("--http", default="http://127.0.0.1:8080",
                        help="GSS HTTP base URL (default: http://127.0.0.1:8080)")
    parser.add_argument("--rx-addr", default=None,
                        help="RX PUB address (default: read from gss.yml)")
    parser.add_argument("--only", default="any",
                        choices=["any", "LPPM", "UPPM", "HLNV", "ASTR", "EPS",
                                 "lppm", "uppm", "hlnv", "astr", "eps"],
                        help="Respond only to sends targeting this dest (default: any)")
    parser.add_argument("--skip", action="append", default=None,
                        help="cmd_id to skip when responding (repeatable)")
    parser.add_argument("--beacon-period", type=float, default=60.0,
                        help="seconds between tlm_beacon emits (default: 60; "
                             "set 0 to disable)")
    args = parser.parse_args()

    cmd_defs, warn = load_command_defs(nodes=None)
    if warn or not cmd_defs:
        print(f"ERROR: commands.yml not loaded: {warn or '(empty)'}", file=sys.stderr)
        return 1

    skips: set[str] = {s.lower() for s in (args.skip or [])}

    platform_cfg, _mid, _mcfg = load_split_config()
    rx_addr = args.rx_addr or platform_cfg["rx"]["zmq_addr"]
    http_base = args.http.rstrip("/")
    ws_base = http_base.replace("http://", "ws://").replace("https://", "wss://")

    return asyncio.run(run(http_base, ws_base, rx_addr, args.only.upper(),
                           skips, cmd_defs, args.beacon_period))


if __name__ == "__main__":
    sys.exit(main())
