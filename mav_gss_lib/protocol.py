"""
mav_gss_lib.protocol -- Compatibility Facade

STATUS: Phase 11 removal candidate. Re-exports from canonical locations
for backward compatibility with TUI modules, backup_control/, external
tests, and logging.py. New code should import directly from:
  - mav_gss_lib.protocols.*          (CRC, CSP, KISS, AX.25, frame detect)
  - mav_gss_lib.missions.maveric.*   (node tables, command wire format, schema)

Author:  Irfan Annuar - USC ISI SERC
"""

# -- Protocol-family support (Phase 3) ----------------------------------------

from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32  # noqa: F401

from mav_gss_lib.protocols.csp import (  # noqa: F401
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig,
)

from mav_gss_lib.protocols.ax25 import AX25Config  # noqa: F401

from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame  # noqa: F401


# -- MAVERIC mission wire format (Phase 4) ------------------------------------

from mav_gss_lib.missions.maveric.wire_format import (  # noqa: F401
    # Node/ptype tables and lookup helpers
    NODE_NAMES, NODE_IDS, PTYPE_NAMES, PTYPE_IDS, GS_NODE,
    init_nodes, node_name, ptype_name, node_label, ptype_label,
    resolve_node, resolve_ptype,
    # Command wire format
    CommandFrame,
    build_cmd_raw, build_kiss_cmd, try_parse_command,
    # Command schema
    TS_MIN_MS, TS_MAX_MS,
    load_command_defs, apply_schema, validate_args,
    # TX and display
    parse_cmd_line, format_arg_value,
)


# -- Generic utilities (remain here) ------------------------------------------

_CLEAN_TABLE = bytearray(0xB7 for _ in range(256))  # middle dot
for _b in range(32, 127):
    _CLEAN_TABLE[_b] = _b
_CLEAN_TABLE = bytes(_CLEAN_TABLE)


def clean_text(data: bytes) -> str:
    """Printable ASCII representation with non-printable bytes as middle dot."""
    return data.translate(_CLEAN_TABLE).decode('latin-1')
