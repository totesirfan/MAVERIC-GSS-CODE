"""MAVERIC mission telemetry — extractors, semantic decoders, catalogs.

Turns inbound MAVERIC packets into canonical, per-domain telemetry
values (EPS, GNC, spacecraft). The platform `TelemetryRouter` reads
`TELEMETRY_MANIFEST` at startup to discover domains and their catalog
endpoints; `MavericTelemetryExtractor` (in `ops.py`) walks `EXTRACTORS`
per packet and produces `TelemetryFragment`s that feed the platform's
live-state store.

Submodules
----------
- `ops.py`         — `MavericTelemetryExtractor` and
  `build_telemetry_ops(nodes)`. Back-fills `mission_data["ts_result"]`
  from the beacon spacecraft-time fragment so renderers/log formatters
  don't each need to peek at fragments.
- `extractors/`    — per-packet fragment producers:
  `tlm_beacon`, `eps_hk`, `gnc_res`. Tuple order in
  `extractors/__init__.py` is load-bearing (first-match wins for
  shared keys).
- `semantics/`     — canonical value shapes: bitfield layouts,
  enum tables, engineering-unit scalings. `eps.py`, `gnc_schema.py`,
  `gnc_handlers.py`, `nvg_sensors.py`, `types.py`. Extractors call
  these directly and pass the result through as fragment values.

`TELEMETRY_MANIFEST` below also defines the per-domain HTTP catalog
(`/api/telemetry/<domain>/catalog`) so the frontend and canonical-key
tests share a single source of truth for "what keys exist + metadata".
"""

from __future__ import annotations

# Relocated schema path — Task 7a moved the register catalog out of the
# legacy gnc_registers/ package. Do NOT re-introduce a
# `from ...telemetry.gnc_registers` import here; that package is deleted
# in Task 16.
from mav_gss_lib.missions.maveric.telemetry.semantics.gnc_schema import REGISTERS


# Canonical `gnc` keys that do NOT correspond to addressable spacecraft
# registers — RES handler output (GNC_MODE, GNC_COUNTERS) and beacon
# shared-prefix / tail fields (GYRO_RATE_SRC, MAG_SRC, heartbeats).
# module and register are null because they have no (module, register)
# address on the wire.
#
# Listed here so the catalog is the single source of truth for "what
# canonical gnc keys exist + their metadata", matching the platform
# contract where consumers discover keys through
# `useTelemetryCatalog('gnc')` rather than through extractor source.
_GNC_NON_REGISTER_ENTRIES = [
    {"module": None, "register": None, "name": "GNC_MODE",
     "type": "gnc_mode", "unit": "",
     "notes": "Planner mode (Safe/Auto/Manual) from gnc_get_mode RES or tlm_beacon."},
    {"module": None, "register": None, "name": "GNC_COUNTERS",
     "type": "gnc_counters", "unit": "",
     "notes": "Reboot / De-Tumble / Sunspin counters from gnc_get_cnts RES or tlm_beacon."},
    {"module": None, "register": None, "name": "GYRO_RATE_SRC",
     "type": "uint8", "unit": "",
     "notes": "Active gyro-rate source selector, from tlm_beacon. Raw int."},
    {"module": None, "register": None, "name": "MAG_SRC",
     "type": "uint8", "unit": "",
     "notes": "Active magnetometer source selector, from tlm_beacon. Raw int."},
    {"module": None, "register": None, "name": "mtq_heartbeat",
     "type": "uint8", "unit": "",
     "notes": "MTQ subsystem heartbeat byte from tlm_beacon."},
    {"module": None, "register": None, "name": "nvg_heartbeat",
     "type": "uint8", "unit": "",
     "notes": "NVG subsystem heartbeat byte from tlm_beacon."},
]


def _gnc_catalog():
    """Serve the GNC register catalog at /api/telemetry/gnc/catalog.

    The platform does not interpret the shape — it passes the body
    through verbatim. The frontend's GncProvider consumes it as
    `CatalogEntry[]` keyed by register name.

    Includes both addressable spacecraft registers (from REGISTERS)
    and non-register canonical keys (handler-emitted + beacon-only).
    Non-register entries carry `module: null, register: null` so
    consumers that care about the distinction (e.g. the Registers
    table) can filter by `module !== null`.
    """
    register_entries = [
        {"module": m, "register": r,
         "name": REGISTERS[(m, r)].name,
         "type": REGISTERS[(m, r)].type,
         "unit": REGISTERS[(m, r)].unit,
         "notes": REGISTERS[(m, r)].notes}
        for (m, r) in sorted(REGISTERS.keys())
    ]
    return register_entries + list(_GNC_NON_REGISTER_ENTRIES)


# Spacecraft domain catalog. Unlike `gnc`, these keys don't come from
# addressable registers — they're all emitted by tlm_beacon. The
# catalog gives the frontend + any future consumer a single source of
# truth for key→metadata mapping, matching the gnc pattern.
#
# type values:
#   string  — the callsign
#   unix_ms — integer unix milliseconds (decoded to display-ready dict
#             by to_spacecraft_time; renders via is_bcd_display)
#   uint{8,16} — raw scalars
_SPACECRAFT_CATALOG = [
    {"name": "callsign",       "type": "string",
     "unit": "", "notes": "Spacecraft callsign transmitted on every beacon."},
    {"name": "time",           "type": "unix_ms",
     "unit": "", "notes": "Spacecraft onboard wall-clock time (unix ms)."},
    {"name": "ops_stage",      "type": "uint8",
     "unit": "", "notes": "Operational stage (raw enum; see FSW)."},
    {"name": "lppm_rbt_cnt",   "type": "uint16",
     "unit": "", "notes": "LPPM reboot count."},
    {"name": "lppm_rbt_cause", "type": "uint8",
     "unit": "", "notes": "LPPM last reboot cause code."},
    {"name": "uppm_rbt_cnt",   "type": "uint16",
     "unit": "", "notes": "UPPM reboot count."},
    {"name": "uppm_rbt_cause", "type": "uint8",
     "unit": "", "notes": "UPPM last reboot cause code."},
    {"name": "ertc_heartbeat", "type": "uint8",
     "unit": "", "notes": "ERTC (real-time clock) heartbeat byte."},
    {"name": "hn_state",       "type": "uint8",
     "unit": "", "notes": "HN state byte."},
    {"name": "ab_state",       "type": "uint8",
     "unit": "", "notes": "AB state byte."},
]


def _spacecraft_catalog():
    """Serve the spacecraft catalog at /api/telemetry/spacecraft/catalog.

    Matches the gnc catalog contract shape (name/type/unit/notes per entry).
    Module/register are absent — spacecraft keys are wire-only, not
    addressable registers.
    """
    return list(_SPACECRAFT_CATALOG)


# EPS domain catalog. The 48-field eps_hk engineering vector is covered
# by `_EPS_HK_NAMES` + `_scale_and_unit` in semantics/eps.py and is
# discoverable by observation; the catalog here explicitly lists the
# beacon-only canonical keys that don't appear in eps_hk so the
# frontend + canonical-key tests have a single source of truth for
# "what non-eps_hk canonical EPS keys exist".
_EPS_CATALOG = [
    {"name": "eps_heartbeat", "type": "uint8", "unit": "",
     "notes": "EPS subsystem heartbeat byte from tlm_beacon."},
    {"name": "eps_mode", "type": "uint8", "unit": "",
     "notes": "EPS operating mode (raw enum) from tlm_beacon. "
              "Promote to a structured {mode, mode_name} once FSW enum is documented."},
]


def _eps_catalog():
    """Serve the eps catalog at /api/telemetry/eps/catalog.

    Lists canonical EPS keys that aren't part of the eps_hk 48-field
    vector (which is self-describing via _EPS_HK_NAMES). Beacon-only
    canonical keys go here.
    """
    from mav_gss_lib.missions.maveric.telemetry.semantics.eps import (
        _EPS_HK_NAMES, _scale_and_unit,
    )
    hk_entries = [
        {"name": n, "type": "int16", "unit": _scale_and_unit(n)[1],
         "notes": "From eps_hk / tlm_beacon. Engineering units via semantics/eps.py _scale_and_unit."}
        for n in _EPS_HK_NAMES
    ]
    return hk_entries + list(_EPS_CATALOG)


TELEMETRY_MANIFEST: dict[str, dict] = {
    # eps_hk 48 engineering fields + beacon-only canonical keys
    # (eps_heartbeat, eps_mode). Default LWW merge.
    "eps":      {"catalog": _eps_catalog},
    # GNC register catalog served via the platform route; live values
    # come in through the extractor + router.
    "gnc":      {"catalog": _gnc_catalog},
    # Spacecraft-wide state: callsign + time + ops_stage + reboot
    # counters + heartbeats + hn/ab states. Populated on every beacon.
    "spacecraft": {"catalog": _spacecraft_catalog},
    # Future-domain examples showing every extension point:
    #   "thermal": {
    #       "merge": sequence_monotonic("seq"),         # custom merge
    #       "load_entries": drop_entries_without_seq,   # paired loader
    #       "catalog": _thermal_catalog,
    #   }
}

__all__ = ["TELEMETRY_MANIFEST"]
