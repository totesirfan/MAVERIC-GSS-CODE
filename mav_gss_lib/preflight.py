"""
mav_gss_lib.preflight -- Shared Preflight Check Library

Defines structured preflight checks as a generator yielding CheckResult
events. Used by both the CLI script and the web backend.

Author:  Irfan Annuar - USC ISI SERC
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from mav_gss_lib.config import get_rx_zmq_addr, get_tx_zmq_addr
from mav_gss_lib.constants import DEFAULT_MISSION

_LIB_DIR = Path(__file__).resolve().parent


@dataclass
class CheckResult:
    group: str
    label: str
    status: str        # "ok" | "fail" | "warn" | "skip"
    fix: str = ""
    detail: str = ""


@dataclass
class PreflightSummary:
    total: int
    passed: int
    failed: int
    warnings: int
    ready: bool


def summarize(results: list[CheckResult]) -> PreflightSummary:
    passed = sum(1 for r in results if r.status == "ok")
    failed = sum(1 for r in results if r.status == "fail")
    warnings = sum(1 for r in results if r.status == "warn")
    return PreflightSummary(
        total=len(results),
        passed=passed,
        failed=failed,
        warnings=warnings,
        ready=failed == 0,
    )


def run_preflight(cfg: dict | None = None,
                  lib_dir: Path | None = None) -> Iterator[CheckResult]:
    """Yield check results as each check executes.

    Args:
        cfg: Pre-loaded config dict. If None, loads from gss.yml.
        lib_dir: Library directory for path resolution. Defaults to mav_gss_lib/.
    """
    if lib_dir is None:
        lib_dir = _LIB_DIR

    # ── Python Dependencies ──
    for mod, pkg, install in [
        ("fastapi", "fastapi", "pip install fastapi"),
        ("uvicorn", "uvicorn", "pip install uvicorn"),
        ("websockets", "websockets", "pip install websockets"),
        ("yaml", "PyYAML", "pip install PyYAML"),
        ("zmq", "pyzmq", "pip install pyzmq"),
        ("crcmod", "crcmod", "pip install crcmod"),
    ]:
        try:
            importlib.import_module(mod)
            yield CheckResult("python_deps", pkg, "ok")
        except ImportError:
            yield CheckResult("python_deps", pkg, "fail", fix=install)

    # ── GNU Radio / PMT ──
    try:
        importlib.import_module("pmt")
        yield CheckResult("gnuradio", "pmt (GNU Radio)", "ok")
    except ImportError:
        yield CheckResult("gnuradio", "pmt (GNU Radio)", "fail",
                          fix="Activate radioconda: conda activate radioconda")

    # ── Config Files ──
    gss_yml = lib_dir / "gss.yml"
    gss_example = lib_dir / "gss.example.yml"
    if gss_yml.is_file():
        yield CheckResult("config", "gss.yml exists", "ok")
    else:
        yield CheckResult("config", "gss.yml exists", "fail",
                          fix=f"Copy from example: cp {gss_example} {gss_yml}")

    # Load config for remaining checks
    if cfg is None:
        from mav_gss_lib.config import load_gss_config
        cfg = load_gss_config(str(gss_yml)) if gss_yml.is_file() else {}

    mission = cfg.get("general", {}).get("mission", DEFAULT_MISSION)
    mission_dir = lib_dir / "missions" / mission
    if mission_dir.is_dir():
        yield CheckResult("config", f"Mission: {mission}", "ok")
    else:
        yield CheckResult("config", f"Mission: {mission}", "fail",
                          fix=f"Set general.mission in gss.yml or create {mission_dir}")

    # Command schema
    cmd_defs_name = cfg.get("general", {}).get("command_defs", "commands.yml")
    if Path(cmd_defs_name).is_absolute():
        cmd_schema = Path(cmd_defs_name)
    else:
        cmd_schema = mission_dir / cmd_defs_name
    cmd_example = mission_dir / (Path(cmd_defs_name).stem + ".example" + Path(cmd_defs_name).suffix)
    if cmd_schema.is_file():
        yield CheckResult("config", f"Command schema: {cmd_schema.name}", "ok")
    elif cmd_example.is_file():
        yield CheckResult("config", f"Command schema: {cmd_schema.name}", "warn",
                          fix=f"Copy from example: cp {cmd_example} {cmd_schema}")
    else:
        yield CheckResult("config", f"Command schema: {cmd_schema.name}", "warn",
                          fix="System starts but cannot validate or send commands")

    # ── Web Build ──
    dist = lib_dir / "web" / "dist"
    index = dist / "index.html"
    if index.is_file():
        yield CheckResult("web_build", "Web build (dist/index.html)", "ok")
    else:
        yield CheckResult("web_build", "Web build (dist/index.html)", "fail",
                          fix="Run: cd mav_gss_lib/web && npm install && npm run build")

    # ── ZMQ Addresses ──
    rx_addr = get_rx_zmq_addr(cfg)
    tx_addr = get_tx_zmq_addr(cfg)
    yield CheckResult("zmq", "RX SUB", "ok", detail=rx_addr)
    yield CheckResult("zmq", "TX PUB", "ok", detail=tx_addr)
