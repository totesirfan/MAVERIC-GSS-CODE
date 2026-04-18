"""
mav_gss_lib.web_runtime.tx_context -- TX send-context helper.

Small helper that snapshots the current TX send context (uplink mode + protocol
state) from the runtime. Extracted from the legacy runtime.py module. Kept in
a leaf module to avoid circular imports — specifically, the lazy import in
tx_queue.validate_mission_cmd (which imports build_send_context) must NOT
promote to a module-top import.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import copy

from .state import WebRuntime, ensure_runtime


def build_send_context(runtime: WebRuntime | None = None):
    """Copy the current send-mode protocol context from the runtime."""
    runtime = ensure_runtime(runtime)
    with runtime.cfg_lock:
        return (
            runtime.cfg.get("tx", {}).get("uplink_mode", "AX.25"),
            copy.copy(runtime.csp),
            copy.copy(runtime.ax25),
        )
