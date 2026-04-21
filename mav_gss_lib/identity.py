"""
mav_gss_lib.identity -- Operator & Station Identity Capture

Captures the OS-level operator, the hostname, and a display-label
station ID. Used by WebRuntime at startup and threaded through every
log record, session event, and preflight row.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import getpass
import os
import socket


def capture_operator() -> str:
    """Return the real human OS account.

    Prefers SUDO_USER when GSS is launched with sudo (otherwise
    getpass.getuser() reports 'root'). Safe on headless Ubuntu where
    os.getlogin() can fail without a controlling TTY.
    """
    return os.getenv("SUDO_USER") or getpass.getuser()


def capture_host() -> str:
    """Return the machine hostname."""
    return socket.gethostname()


def capture_station(cfg: dict, host: str) -> str:
    """Return the display-label station ID.

    Uses cfg.general.station_id if set (e.g. "GS-0" / "GS-1" / "GS-2"),
    otherwise falls back to the raw hostname.
    """
    general = cfg.get("general") or {}
    override = general.get("station_id") or ""
    return override.strip() or host
