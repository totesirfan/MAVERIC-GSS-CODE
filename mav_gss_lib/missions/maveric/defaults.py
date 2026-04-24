"""MAVERIC mission seeding defaults.

Non-operational placeholder defaults that seed a bare mission_cfg /
platform_cfg.tx at mission-build time. Operator-specific real values
(callsigns, CSP routing, frequency) live in gss.yml — platform.tx for
TX parameters and mission.config.* for mission overrides — and win over
these defaults via gap-fill merging.

Read helpers for already-seeded mission config live in `config_access.py`.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from typing import Any

MISSION_NAME: str = "MAVERIC"
GS_NODE: str = "GS"
COMMAND_DEFS_FILE: str = "commands.yml"

NODES: dict[int, str] = {
    0: "NONE",
    1: "LPPM",
    2: "EPS",
    3: "UPPM",
    4: "HLNV",
    5: "ASTR",
    6: "GS",
    7: "FTDI",
}

PTYPES: dict[int, str] = {
    1: "CMD",
    2: "RES",
    3: "ACK",
    4: "NACK",
    5: "TLM",
    6: "FILE",
}

NODE_DESCRIPTIONS: dict[str, str] = {
    "LPPM": "Lower Pluggable Processor Module",
    "UPPM": "Upper Pluggable Processor Module",
    "EPS":  "Electrical Power System",
    "GS":   "Ground Station",
    "HLNV": "Holonav Payload",
    "ASTR": "ASTR Payload",
    "FTDI": "FTDI Debug Interface",
}

# Non-operational placeholders. Real callsigns/SSIDs/CSP routing are
# supplied by the operator in gss.yml:mission.config.{ax25,csp}.
AX25_DEFAULTS: dict[str, Any] = {
    "src_call":  "NOCALL",
    "src_ssid":  0,
    "dest_call": "NOCALL",
    "dest_ssid": 0,
}

CSP_DEFAULTS: dict[str, Any] = {
    "priority":    2,
    "source":      0,
    "destination": 0,
    "dest_port":   0,
    "src_port":    0,
    "flags":       0,
    "csp_crc":     True,
}

IMAGING_DEFAULTS: dict[str, Any] = {
    "thumb_prefix": "tn_",
}

UI_DEFAULTS: dict[str, str] = {
    "rx_title":        "RX DOWNLINK",
    "tx_title":        "TX UPLINK",
    "splash_subtitle": "Mission Ground Station",
}

# Mission-declared TX defaults. Platform owns the tx section, so these
# seed platform_cfg["tx"] — operator values win.
TX_DEFAULTS: dict[str, str] = {
    "frequency":   "XXX.XX MHz",
    "uplink_mode": "ASM+Golay",
}


def seed_mission_cfg(mission_cfg: dict[str, Any], platform_cfg: dict[str, Any] | None = None) -> None:
    """Seed mission_cfg (and platform_cfg.tx) with MAVERIC defaults in place.

    Operator values win at every level; defaults only fill gaps. Per-key
    one-deep merge is used for dict-of-leaves so an operator can override
    a single ax25/csp field without having to repeat the rest.
    """
    for key, defaults in (
        ("nodes", NODES),
        ("ptypes", PTYPES),
        ("node_descriptions", NODE_DESCRIPTIONS),
        ("ax25", AX25_DEFAULTS),
        ("csp", CSP_DEFAULTS),
        ("imaging", IMAGING_DEFAULTS),
    ):
        existing = mission_cfg.get(key)
        if isinstance(existing, dict) and existing:
            merged = dict(defaults)
            merged.update(existing)
            mission_cfg[key] = merged
        elif key not in mission_cfg:
            mission_cfg[key] = dict(defaults)

    for key, value in (
        ("mission_name",    MISSION_NAME),
        ("gs_node",         GS_NODE),
        ("command_defs",    COMMAND_DEFS_FILE),
        ("rx_title",        UI_DEFAULTS["rx_title"]),
        ("tx_title",        UI_DEFAULTS["tx_title"]),
        ("splash_subtitle", UI_DEFAULTS["splash_subtitle"]),
    ):
        mission_cfg.setdefault(key, value)

    if isinstance(platform_cfg, dict):
        tx_cfg = platform_cfg.setdefault("tx", {})
        if isinstance(tx_cfg, dict):
            for key, value in TX_DEFAULTS.items():
                tx_cfg.setdefault(key, value)
