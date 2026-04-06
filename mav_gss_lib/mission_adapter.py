"""
mav_gss_lib.mission_adapter -- Mission Adapter Interface + Facade

Platform core:
  - ParsedPacket: normalized packet parse result
  - MissionAdapter: formal Protocol defining the mission boundary

Facade:
  - MavericMissionAdapter: re-exported from missions.maveric.adapter

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# =============================================================================
#  PLATFORM CORE -- ParsedPacket
# =============================================================================

@dataclass
class ParsedPacket:
    """Normalized packet parse result returned by a mission adapter.

    Transitional compatibility note: the csp, cmd, cmd_tail, and
    ts_result fields reflect MAVERIC's packet model and are kept for
    backward compatibility during migration.  The platform's eventual
    packet record should carry mission-opaque semantic data via
    adapter-provided rendering payloads rather than baking in any
    one mission's field names.  These fields may be replaced or
    generalized in a future phase.
    """

    csp: dict | None = None          # transitional -- MAVERIC CSP parse result
    csp_plausible: bool = False
    cmd: dict | None = None          # transitional -- MAVERIC command dict
    cmd_tail: bytes | None = None    # transitional -- unparsed tail bytes
    ts_result: tuple | None = None   # transitional -- satellite timestamp
    warnings: list[str] = field(default_factory=list)
    crc_status: dict = field(default_factory=lambda: {
        "csp_crc32_valid": None,
        "csp_crc32_rx": None,
        "csp_crc32_comp": None,
    })


# =============================================================================
#  PLATFORM CORE -- Rendering Contracts
# =============================================================================

@dataclass
class ProtocolBlock:
    """Standardized protocol/wrapper information for the detail view.

    The platform owns how these are rendered. Missions provide the data.
    """
    kind: str        # e.g. "csp", "ax25"
    label: str       # e.g. "CSP V1", "AX.25"
    fields: list     # list of {"name": str, "value": str}


@dataclass
class IntegrityBlock:
    """Standardized integrity check result for the detail view.

    The platform owns how these are rendered. Missions provide the data.
    """
    kind: str                    # e.g. "crc16", "crc32c"
    label: str                   # e.g. "CRC-16", "CRC-32C"
    scope: str                   # e.g. "command", "csp"
    ok: bool | None              # True/False/None (unknown)
    received: str | None = None  # e.g. "0x1234"
    computed: str | None = None  # e.g. "0x1234"


# =============================================================================
#  PLATFORM CORE -- MissionAdapter Protocol
# =============================================================================

@runtime_checkable
class MissionAdapter(Protocol):
    """Formal interface for mission adapter implementations.

    Missions provide an adapter that satisfies this protocol.
    The platform runtime calls these methods without knowing
    which mission is active.
    """

    def detect_frame_type(self, meta: dict) -> str: ...
    def normalize_frame(self, frame_type: str, raw: bytes) -> tuple: ...

    def parse_packet(self, inner_payload: bytes, warnings: list[str] | None = None) -> ParsedPacket: ...

    def duplicate_fingerprint(self, parsed: ParsedPacket) -> tuple | None: ...
    def is_uplink_echo(self, cmd) -> bool: ...

    def build_raw_command(self, src: int, dest: int, echo: int, ptype: int,
                          cmd_id: str, args: str) -> bytes: ...
    def validate_tx_args(self, cmd_id: str, args: str) -> tuple[bool, list[str]]: ...

    # -- Rendering-slot contract (architecture spec §4) --
    def packet_list_columns(self) -> list[dict]: ...
    def packet_list_row(self, pkt) -> dict: ...
    def packet_detail_blocks(self, pkt) -> list[dict]: ...
    def protocol_blocks(self, pkt) -> list: ...
    def integrity_blocks(self, pkt) -> list: ...


# =============================================================================
#  FACADE -- re-export MAVERIC adapter
# =============================================================================

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter  # noqa: F401
