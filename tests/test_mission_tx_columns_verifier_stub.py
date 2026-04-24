"""Every mission whose MissionSpec has a CommandOps must declare a
`verifiers` column in `CommandOps.tx_columns()` (the API-consumed path).

The column is empty today — auto-hidden via `hide_if_all=[""]`. Reserves
the slot so the command-verification feature can populate per-command
verifier ticks without frontend layout churn.

Balloon_v2 has no CommandOps, so `/api/tx-columns` returns [] for it
regardless; the UiOps edit there is defensive/forward-compat only and is
validated separately.

MavericCommandOps.tx_columns() reads neither `cmd_defs` nor `nodes`, so
we construct it with an empty `cmd_defs` dict and a default NodeTable —
no YAML load, no mission-config dependency.
"""
import unittest

from mav_gss_lib.missions.maveric.commands.ops import MavericCommandOps
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.missions.echo_v2.mission import EchoCommandOps, EchoUiOps
from mav_gss_lib.missions.balloon_v2.mission import BalloonUiOps


def _find(cols, col_id):
    for c in cols:
        if c.id == col_id:
            return c
    return None


def _assert_verifier_stub(test_case, cols, mission_name):
    v = _find(cols, "verifiers")
    test_case.assertIsNotNone(v, f"{mission_name}: missing 'verifiers' column")
    test_case.assertEqual(v.label, "verify")
    test_case.assertEqual(
        v.hide_if_all, [""],
        f"{mission_name}: verifiers column must auto-hide on empty cells today"
    )
    test_case.assertEqual(v.align, "right")


class AuthoritativeCommandOpsSurface(unittest.TestCase):
    """Columns that /api/tx-columns actually serves."""

    def test_maveric_command_ops(self):
        ops = MavericCommandOps(
            cmd_defs={}, nodes=NodeTable(),
            mission_config={}, platform_config={},
        )
        _assert_verifier_stub(self, ops.tx_columns(), "maveric/commands")

    def test_echo_v2_command_ops(self):
        _assert_verifier_stub(self, EchoCommandOps().tx_columns(), "echo_v2/commands")


class DefensiveUiOpsSurface(unittest.TestCase):
    """Columns on UiOps — not API-consumed, but kept in sync defensively."""

    def test_echo_v2_ui_ops(self):
        _assert_verifier_stub(self, EchoUiOps().tx_columns(), "echo_v2/ui")

    def test_balloon_v2_ui_ops(self):
        # Balloon has no CommandOps, so /api/tx-columns returns [] for it.
        # The UiOps stub is forward-compat only: when Balloon grows a
        # CommandOps, it will want the verifier slot ready.
        _assert_verifier_stub(self, BalloonUiOps().tx_columns(), "balloon_v2/ui")


if __name__ == "__main__":
    unittest.main()
