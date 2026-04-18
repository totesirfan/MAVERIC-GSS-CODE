"""Platform-level string constants shared across modules.

Author: Irfan
"""
from __future__ import annotations

DEFAULT_MISSION: str = "maveric"
DEFAULT_MISSION_NAME: str = "MAVERIC"

# Default socket addresses used only when gss.yml is absent / missing the key.
# Operator-editable at runtime via /api/config.
DEFAULT_RX_ZMQ_ADDR: str = "tcp://127.0.0.1:52001"
DEFAULT_TX_ZMQ_ADDR: str = "tcp://127.0.0.1:52002"
