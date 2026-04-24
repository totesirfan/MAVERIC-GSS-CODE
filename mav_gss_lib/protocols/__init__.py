"""
mav_gss_lib.protocols -- Reusable CubeSat Protocol-Family Support

Wire-format primitives consumed only by missions (see
``tests/test_mission_owned_framing.py`` for the guardrail that the server
does not import these directly):
    crc   -- CRC-16 XMODEM, CRC-32C Castagnoli
    csp   -- CSP v1 header, KISS framing, CSPConfig
    ax25  -- AX.25 encoder, AX25Config
    golay -- ASM+Golay encoder (AX100 Mode 5)

Transport-metadata framing heuristics live on the platform side at
``mav_gss_lib.platform.rx.frame_detect`` (they don't decode wire bytes, they
inspect gr-satellites metadata strings).
"""

from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32
from mav_gss_lib.protocols.csp import (
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig,
)
from mav_gss_lib.protocols.ax25 import (
    AX25Config, ax25_decode_header, build_ax25_gfsk_frame,
)
from mav_gss_lib.protocols.golay import (
    ASM, PREAMBLE, build_asm_golay_frame, ccsds_scrambler_sequence, golay_encode, rs_encode,
)
