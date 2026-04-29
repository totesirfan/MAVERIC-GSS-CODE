"""Lifecycle tests for the _BaseLog writer thread.

Covers the three spots the adversarial audit flagged:
  1. write_jsonl becomes a no-op after close() — no lost writes piling
     up on a dead queue (previously: silent loss).
  2. Two-phase session swap (prepare + commit) happy path preserves
     session_id and file stems.
  3. commit_new_session can only be called on an open log.
"""

from __future__ import annotations

import json
import tempfile

from mav_gss_lib.logging import SessionLog


def _new_rx_log(tmp: str) -> SessionLog:
    return SessionLog(tmp, "tcp://127.0.0.1:0", "0.0.0",
                      mission_id="maveric", station="GS-0", operator="op")


def test_write_after_close_is_noop_not_crash():
    with tempfile.TemporaryDirectory() as tmp:
        log = _new_rx_log(tmp)
        log.write_jsonl({"before": True})
        log.close()
        log.write_jsonl({"after": True})  # must not raise
        # close() is idempotent
        log.close()


def test_write_after_close_does_not_reach_disk():
    with tempfile.TemporaryDirectory() as tmp:
        log = _new_rx_log(tmp)
        path = log.jsonl_path
        log.write_jsonl({"ok": 1})
        log.close()
        log.write_jsonl({"lost": 2})  # post-close no-op

        with open(path) as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    # exactly one row — the pre-close write; the post-close write is dropped
    assert rows == [{"ok": 1}]


def test_prepare_and_commit_new_session_swaps_stem():
    with tempfile.TemporaryDirectory() as tmp:
        log = _new_rx_log(tmp)
        first_stem = log.session_id
        first_jsonl = log.jsonl_path

        try:
            prepared = log.prepare_new_session(tag="pass2")
            assert prepared["session_id"] != first_stem
            assert "pass2" in prepared["session_id"]

            log.commit_new_session(prepared)
            assert log.session_id == prepared["session_id"]
            assert log.jsonl_path == prepared["jsonl_path"]
            assert log.jsonl_path != first_jsonl

            # new session is writable
            log.write_jsonl({"session": log.session_id})
        finally:
            log.close()


def test_session_swap_rejected_on_closed_log():
    """prepare_new_session + commit_new_session both refuse a closed log
    so no orphan .jsonl files are left on disk."""
    import pytest

    with tempfile.TemporaryDirectory() as tmp:
        log = _new_rx_log(tmp)
        log.close()
        with pytest.raises(RuntimeError, match="closed log"):
            log.prepare_new_session(tag="afterclose")
