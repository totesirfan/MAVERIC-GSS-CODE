"""Unit tests for mav_gss_lib.updater — self-updater + bootstrap.

Mocks subprocess.run / Popen, os.execv, and importlib.util.find_spec
so these tests do not touch the real filesystem, network, or git.
"""

from __future__ import annotations

import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

# Ensure mav_gss_lib is importable when run from the tests directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib import updater  # noqa: E402
from mav_gss_lib.updater import (  # noqa: E402
    Commit,
    DirtyTreeError,
    PipBlockedError,
    PreflightError,
    SubprocessFailed,
    UpdateStatus,
    VenvUnavailableError,
    _detect_pip_blocked,
    apply_update,
    bootstrap_dependencies,
    check_for_updates,
)


def _cp(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeProc:
    """Minimal subprocess.Popen stand-in for _stream_subprocess tests."""

    def __init__(self, lines: list[str], returncode: int = 0):
        self._lines = iter(lines)
        self.returncode = returncode
        self.stdout = self
        self._killed = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._lines) + "\n"

    def close(self):
        pass

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self._killed = True


# =============================================================================
#  check_for_updates
# =============================================================================

class TestCheckForUpdates(unittest.TestCase):

    def setUp(self):
        # Canonical responses for each git call, keyed by the first arg after "git".
        self.responses = {
            "rev-parse --abbrev-ref HEAD": _cp(0, "main\n"),
            "rev-parse HEAD": _cp(0, "abcdef1234567890\n"),
            "status --porcelain": _cp(0, ""),
            "fetch --quiet origin main": _cp(0, ""),
            "rev-list --count HEAD..origin/main": _cp(0, "0\n"),
            "log HEAD..origin/main --pretty=format:%h|%s": _cp(0, ""),
            "diff --name-only HEAD..origin/main": _cp(0, ""),
        }

    def _fake_run_git(self, args, timeout):
        key = " ".join(args)
        if key in self.responses:
            return self.responses[key]
        raise AssertionError(f"unexpected git invocation: {key}")

    def _patched_check(self, **overrides):
        self.responses.update(overrides)
        with mock.patch.object(updater, "_run_git", side_effect=self._fake_run_git), \
             mock.patch.object(updater, "_scan_missing_pip_deps", return_value=[]), \
             mock.patch.object(updater, "_compute_requirements_hash", return_value="h"), \
             mock.patch.object(updater, "_read_persisted_hash", return_value="h"):
            return check_for_updates()

    def test_up_to_date_skips_log_and_diff(self):
        # rev-list returns 0 → no log or diff calls. We enforce this by dropping
        # them from the response dict and asserting no AssertionError fires.
        self.responses.pop("log HEAD..origin/main --pretty=format:%h|%s")
        self.responses.pop("diff --name-only HEAD..origin/main")
        status = self._patched_check()
        self.assertEqual(status.behind_count, 0)
        self.assertFalse(status.fetch_failed)
        self.assertEqual(status.branch, "main")

    def test_behind_parses_commits_and_changed_files(self):
        status = self._patched_check(**{
            "rev-list --count HEAD..origin/main": _cp(0, "2\n"),
            "log HEAD..origin/main --pretty=format:%h|%s": _cp(0, "abc1234|first\ndef5678|second\n"),
            "diff --name-only HEAD..origin/main": _cp(0, "requirements.txt\nMAV_WEB.py\n"),
        })
        self.assertEqual(status.behind_count, 2)
        self.assertEqual(len(status.commits), 2)
        self.assertEqual(status.commits[0], Commit(sha="abc1234", subject="first"))
        self.assertIn("requirements.txt", status.changed_files)
        self.assertTrue(status.requirements_changed)

    def test_dirty_tree(self):
        status = self._patched_check(**{
            "status --porcelain": _cp(0, " M some_file.py\n"),
        })
        self.assertTrue(status.working_tree_dirty)

    def test_fetch_timeout(self):
        def _raise_timeout(args, timeout):
            key = " ".join(args)
            if key.startswith("fetch"):
                raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)
            return self.responses[key]
        with mock.patch.object(updater, "_run_git", side_effect=_raise_timeout), \
             mock.patch.object(updater, "_scan_missing_pip_deps", return_value=[]), \
             mock.patch.object(updater, "_compute_requirements_hash", return_value="h"), \
             mock.patch.object(updater, "_read_persisted_hash", return_value="h"):
            status = check_for_updates()
        self.assertTrue(status.fetch_failed)
        self.assertEqual(status.fetch_error, "fetch timeout")

    def test_fetch_network_error_marks_failed(self):
        status = self._patched_check(**{
            "fetch --quiet origin main": _cp(1, "", "unable to resolve host"),
        })
        self.assertTrue(status.fetch_failed)

    def test_detached_head(self):
        status = self._patched_check(**{
            "rev-parse --abbrev-ref HEAD": _cp(0, "HEAD\n"),
        })
        self.assertTrue(status.fetch_failed)
        self.assertEqual(status.fetch_error, "detached HEAD — not on a branch")

    def test_missing_requirements_hash_triggers_out_of_sync(self):
        with mock.patch.object(updater, "_run_git", side_effect=self._fake_run_git), \
             mock.patch.object(updater, "_scan_missing_pip_deps", return_value=[]), \
             mock.patch.object(updater, "_compute_requirements_hash", return_value="h"), \
             mock.patch.object(updater, "_read_persisted_hash", return_value=None):
            status = check_for_updates()
        self.assertTrue(status.requirements_out_of_sync)

    def test_stale_requirements_hash_triggers_out_of_sync(self):
        with mock.patch.object(updater, "_run_git", side_effect=self._fake_run_git), \
             mock.patch.object(updater, "_scan_missing_pip_deps", return_value=[]), \
             mock.patch.object(updater, "_compute_requirements_hash", return_value="new"), \
             mock.patch.object(updater, "_read_persisted_hash", return_value="old"):
            status = check_for_updates()
        self.assertTrue(status.requirements_out_of_sync)

    def test_matching_hash_in_sync(self):
        with mock.patch.object(updater, "_run_git", side_effect=self._fake_run_git), \
             mock.patch.object(updater, "_scan_missing_pip_deps", return_value=[]), \
             mock.patch.object(updater, "_compute_requirements_hash", return_value="same"), \
             mock.patch.object(updater, "_read_persisted_hash", return_value="same"):
            status = check_for_updates()
        self.assertFalse(status.requirements_out_of_sync)


# =============================================================================
#  bootstrap_dependencies
# =============================================================================

class TestBootstrapDependencies(unittest.TestCase):

    def setUp(self):
        os.environ.pop("MAV_BOOTSTRAP_ATTEMPTED", None)
        os.environ.pop("MAV_UPDATE_APPLIED", None)

    def tearDown(self):
        os.environ.pop("MAV_BOOTSTRAP_ATTEMPTED", None)

    def test_hard_prereq_missing_exits_3(self):
        def fake_find_spec(name):
            if name == "pmt":
                return None
            return types.SimpleNamespace()
        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec):
            with self.assertRaises(SystemExit) as ctx:
                bootstrap_dependencies()
        self.assertEqual(ctx.exception.code, 3)

    def test_all_deps_present_is_noop(self):
        with mock.patch("importlib.util.find_spec", return_value=types.SimpleNamespace()), \
             mock.patch.object(updater, "_run_pip_install_terminal") as pip, \
             mock.patch.object(updater, "_reexec") as reexec_mock:
            bootstrap_dependencies()
        pip.assert_not_called()
        reexec_mock.assert_not_called()
        self.assertNotIn("MAV_BOOTSTRAP_ATTEMPTED", os.environ)

    def test_missing_deps_first_try_triggers_pip_and_reexec(self):
        def fake_find_spec(name):
            # pmt present, fastapi missing, others present
            if name == "pmt":
                return types.SimpleNamespace()
            if name == "fastapi":
                return None
            return types.SimpleNamespace()
        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec), \
             mock.patch.object(updater, "_run_pip_install_terminal") as pip, \
             mock.patch.object(updater, "_reexec") as reexec_mock:
            bootstrap_dependencies()
        pip.assert_called_once()
        reexec_mock.assert_called_once()
        self.assertEqual(os.environ.get("MAV_BOOTSTRAP_ATTEMPTED"), "1")

    def test_missing_deps_retry_guard_exits_2(self):
        os.environ["MAV_BOOTSTRAP_ATTEMPTED"] = "1"
        def fake_find_spec(name):
            if name == "pmt":
                return types.SimpleNamespace()
            if name == "fastapi":
                return None
            return types.SimpleNamespace()
        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec):
            with self.assertRaises(SystemExit) as ctx:
                bootstrap_dependencies()
        self.assertEqual(ctx.exception.code, 2)

    def test_pip_blocked_triggers_venv_and_reexec(self):
        def fake_find_spec(name):
            if name == "pmt":
                return types.SimpleNamespace()
            if name == "fastapi":
                return None
            return types.SimpleNamespace()
        cleared_flag_before_reexec = {"ok": False}

        def fake_reexec(python=None, extra_env=None):
            # Capture state at the moment of the first re-exec call. In real
            # life os.execv never returns, so our mock simulates that by
            # raising to short-circuit the fall-through.
            cleared_flag_before_reexec["ok"] = (
                "MAV_BOOTSTRAP_ATTEMPTED" not in os.environ
                and str(python).endswith("/fake/.venv/bin/python")
            )
            raise SystemExit(0)

        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec), \
             mock.patch.object(updater, "_run_pip_install_terminal", side_effect=PipBlockedError("blocked")), \
             mock.patch.object(updater, "_ensure_venv", return_value=Path("/fake/.venv/bin/python")) as ev, \
             mock.patch.object(updater, "_reexec", side_effect=fake_reexec):
            with self.assertRaises(SystemExit):
                bootstrap_dependencies()
        ev.assert_called_once()
        # MAV_BOOTSTRAP_ATTEMPTED must be cleared before the venv re-exec so
        # the new interpreter gets its own fresh attempt.
        self.assertTrue(cleared_flag_before_reexec["ok"])

    def test_pip_blocked_and_venv_unavailable_exits_3(self):
        def fake_find_spec(name):
            if name == "pmt":
                return types.SimpleNamespace()
            if name == "fastapi":
                return None
            return types.SimpleNamespace()
        with mock.patch("importlib.util.find_spec", side_effect=fake_find_spec), \
             mock.patch.object(updater, "_run_pip_install_terminal", side_effect=PipBlockedError("blocked")), \
             mock.patch.object(updater, "_ensure_venv", side_effect=VenvUnavailableError("no ensurepip")):
            with self.assertRaises(SystemExit) as ctx:
                bootstrap_dependencies()
        self.assertEqual(ctx.exception.code, 3)


# =============================================================================
#  _detect_pip_blocked
# =============================================================================

class TestDetectPipBlocked(unittest.TestCase):

    def test_pep668(self):
        self.assertTrue(_detect_pip_blocked(
            "error: externally-managed-environment"
        ))

    def test_externally_managed_marker(self):
        self.assertTrue(_detect_pip_blocked("EXTERNALLY-MANAGED"))

    def test_permission_denied(self):
        self.assertTrue(_detect_pip_blocked("Permission denied: /usr/lib/python3"))

    def test_errno_13(self):
        self.assertTrue(_detect_pip_blocked("[Errno 13] Permission denied"))

    def test_normal_conflict_is_not_blocked(self):
        self.assertFalse(_detect_pip_blocked(
            "ERROR: Cannot install foo==1.0 and bar==2.0 because these package versions have conflicting dependencies"
        ))


# =============================================================================
#  _ensure_venv
# =============================================================================

class TestEnsureVenv(unittest.TestCase):

    def test_success_path(self):
        with mock.patch.object(Path, "exists", return_value=True):
            # Already-exists path: no subprocess call at all.
            p = updater._ensure_venv()
        self.assertTrue(str(p).endswith("bin/python"))

    def test_ensurepip_missing_raises_venv_unavailable(self):
        with mock.patch.object(Path, "exists", side_effect=[False, True]), \
             mock.patch("subprocess.run", return_value=_cp(
                 1, "", "ensurepip is not available\n"
             )):
            with self.assertRaises(VenvUnavailableError):
                updater._ensure_venv()

    def test_other_failure_raises_runtime_error(self):
        with mock.patch.object(Path, "exists", side_effect=[False, True]), \
             mock.patch("subprocess.run", return_value=_cp(
                 1, "", "unexpected error\n"
             )):
            with self.assertRaises(RuntimeError):
                updater._ensure_venv()


# =============================================================================
#  _reexec
# =============================================================================

class TestReexec(unittest.TestCase):

    def test_applies_env_before_exec(self):
        seen_env = {}

        def fake_execv(path, argv):
            seen_env["MAV_UPDATE_APPLIED"] = os.environ.get("MAV_UPDATE_APPLIED")

        with mock.patch("os.execv", side_effect=fake_execv):
            os.environ.pop("MAV_UPDATE_APPLIED", None)
            updater._reexec(extra_env={"MAV_UPDATE_APPLIED": "abc123"})

        self.assertEqual(seen_env["MAV_UPDATE_APPLIED"], "abc123")
        os.environ.pop("MAV_UPDATE_APPLIED", None)


# =============================================================================
#  _run_pip_install hash-write behavior
# =============================================================================

class TestPipInstallHashWrite(unittest.TestCase):

    def setUp(self):
        self.events: list[dict] = []

    def _broadcast(self, event: dict) -> None:
        self.events.append(event)

    def test_success_writes_hash(self):
        with mock.patch.object(updater, "_stream_subprocess"), \
             mock.patch.object(updater, "_write_persisted_hash") as write:
            updater._run_pip_install(self._broadcast)
        write.assert_called_once()

    def test_failure_does_not_write_hash(self):
        with mock.patch.object(updater, "_stream_subprocess",
                               side_effect=SubprocessFailed("boom")), \
             mock.patch.object(updater, "_write_persisted_hash") as write:
            with self.assertRaises(SubprocessFailed):
                updater._run_pip_install(self._broadcast)
        write.assert_not_called()

    def test_timeout_does_not_write_hash(self):
        with mock.patch.object(updater, "_stream_subprocess",
                               side_effect=subprocess.TimeoutExpired(cmd=[], timeout=1)), \
             mock.patch.object(updater, "_write_persisted_hash") as write:
            with self.assertRaises(subprocess.TimeoutExpired):
                updater._run_pip_install(self._broadcast)
        write.assert_not_called()

    def test_pip_blocked_triggers_venv_and_reexec(self):
        with mock.patch.object(updater, "_stream_subprocess",
                               side_effect=PipBlockedError("blocked")), \
             mock.patch.object(updater, "_ensure_venv",
                               return_value=Path("/fake/.venv/bin/python")) as ev, \
             mock.patch.object(updater, "_reexec") as reexec_mock, \
             mock.patch.object(updater, "_write_persisted_hash") as write:
            updater._run_pip_install(self._broadcast)
        ev.assert_called_once()
        reexec_mock.assert_called_once()
        write.assert_not_called()


# =============================================================================
#  apply_update
# =============================================================================

class TestApplyUpdate(unittest.TestCase):

    def setUp(self):
        self.events: list[dict] = []

    def _broadcast(self, event: dict) -> None:
        self.events.append(event)

    def _status(self, **kw):
        defaults = dict(
            current_sha="old_sha",
            branch="main",
            behind_count=1,
            commits=[Commit("abc1234", "msg")],
            changed_files=["requirements.txt"],
            working_tree_dirty=False,
            missing_pip_deps=[],
            requirements_changed=True,
            requirements_out_of_sync=False,
            fetch_failed=False,
            fetch_error=None,
            update_applied_sha=None,
        )
        defaults.update(kw)
        return UpdateStatus(**defaults)

    def test_happy_path_runs_phases_and_reexecs_with_new_sha(self):
        status = self._status()
        git_calls = {
            "status --porcelain": _cp(0, ""),
            "rev-parse HEAD": _cp(0, "new_sha_after_pull\n"),
        }
        def fake_run_git(args, timeout):
            return git_calls[" ".join(args)]
        with mock.patch.object(updater, "_run_git", side_effect=fake_run_git), \
             mock.patch.object(updater, "_stream_subprocess") as stream, \
             mock.patch.object(updater, "_run_pip_install") as pip, \
             mock.patch.object(updater, "_reexec") as reexec_mock:
            apply_update(self._broadcast, status)
        stream.assert_called()  # git_pull
        pip.assert_called_once()
        reexec_mock.assert_called_once()
        _, kwargs = reexec_mock.call_args
        self.assertEqual(kwargs["extra_env"]["MAV_UPDATE_APPLIED"], "new_sha_after_pull")

    def test_dirty_tree_gate_blocks_all_phases(self):
        status = self._status()
        def fake_run_git(args, timeout):
            return _cp(0, " M file.py\n")
        with mock.patch.object(updater, "_run_git", side_effect=fake_run_git), \
             mock.patch.object(updater, "_stream_subprocess") as stream, \
             mock.patch.object(updater, "_run_pip_install") as pip, \
             mock.patch.object(updater, "_reexec") as reexec_mock:
            with self.assertRaises(DirtyTreeError):
                apply_update(self._broadcast, status)
        stream.assert_not_called()
        pip.assert_not_called()
        reexec_mock.assert_not_called()

    def test_nothing_to_do_raises_preflight_error(self):
        status = self._status(behind_count=0, missing_pip_deps=[],
                              requirements_changed=False,
                              requirements_out_of_sync=False,
                              changed_files=[])
        def fake_run_git(args, timeout):
            return _cp(0, "")
        with mock.patch.object(updater, "_run_git", side_effect=fake_run_git), \
             mock.patch.object(updater, "_reexec") as reexec_mock:
            with self.assertRaises(PreflightError):
                apply_update(self._broadcast, status)
        reexec_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
