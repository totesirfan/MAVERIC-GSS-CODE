#!/usr/bin/env python3
"""Preflight check for MAVERIC GSS startup prerequisites.

Run before launching MAV_WEB.py to verify the environment is ready.

Usage:
    python3 scripts/preflight.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mav_gss_lib.preflight import run_preflight, summarize

OK = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m!\033[0m"

_STATUS_ICON = {"ok": OK, "fail": FAIL, "warn": WARN, "skip": "  "}
_GROUP_LABELS = {
    "python_deps": "Python Dependencies",
    "gnuradio": "GNU Radio / PMT",
    "config": "Config Files",
    "web_build": "Web Build",
    "zmq": "ZMQ Addresses",
}

current_group = None
results = []

for check in run_preflight():
    if check.group != current_group:
        current_group = check.group
        print(f"\n── {_GROUP_LABELS.get(check.group, check.group)} ──")
    icon = _STATUS_ICON.get(check.status, "  ")
    line = f"  {icon} {check.label}"
    if check.detail:
        line += f": {check.detail}"
    print(line)
    if check.fix and check.status != "ok":
        print(f"      → {check.fix}")
    results.append(check)

summary = summarize(results)
print()
if summary.ready:
    print(f"  All checks passed. Ready to run: python3 MAV_WEB.py\n")
else:
    print(f"  {summary.failed} issue(s) found. Fix before launching MAV_WEB.py.\n")
    sys.exit(1)
