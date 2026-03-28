"""
mav_gss_lib.golay -- ASM+Golay Uplink Encoder (AX100 Mode 5)

Self-contained encoder for the ASM+Golay over-the-air frame format
used by the GomSpace AX100 radio in Mode 5, matching gr-satellites
u482c_decode exactly.

Frame layout:
    [preamble 50B] [ASM 4B] [golay 3B] [scrambled RS codeword]

The Golay 12-bit field encodes flags + frame length:
    bit 11:   unused
    bit 10:   RS flag
    bit 9:    scrambler flag
    bit 8:    viterbi flag
    bits 7-0: frame_len (= payload_len + 32 RS parity)

The RS codeword is dynamically shortened: RS(frame_len, payload_len)
using conventional (non-CCSDS-dual-basis) RS with pad = 255 - frame_len.

Encoding: NRZ, MSB first.
ASM sync word: 0x930B51DE (gr-satellites ax100_deframer convention).

Author:  Irfan Annuar - USC ISI SERC
"""

try:
    from gnuradio import gr
    from satellites import encode_rs as _encode_rs_block
    import pmt as _pmt
    import time as _time
    _GR_RS_OK = True
except ImportError:
    _GR_RS_OK = False


# -- Constants ----------------------------------------------------------------

PREAMBLE   = b'\xAA' * 50
ASM        = bytes([0x93, 0x0B, 0x51, 0xDE])
RS_PARITY  = 32
MAX_PAYLOAD = 223       # max RS data capacity (255 - 32)


def rs_encode(payload):
    """RS encode matching gr-satellites encode_rs_8 (Phil Karn FEC).

    Uses gr-satellites' encode_rs block directly for exact compatibility.
    Returns: payload + 32 parity bytes."""
    if not _GR_RS_OK:
        raise RuntimeError("gr-satellites not installed — cannot encode RS")
    plen = len(payload)
    if plen > MAX_PAYLOAD:
        raise ValueError(f"payload {plen}B exceeds RS capacity {MAX_PAYLOAD}B")

    enc = _encode_rs_block(False)  # conventional (not dual-basis)
    result = [None]

    class _Sink(gr.basic_block):
        def __init__(self):
            gr.basic_block.__init__(self, '_rs_sink', [], [])
            self.message_port_register_in(_pmt.intern('in'))
            self.set_msg_handler(_pmt.intern('in'), self._h)
        def _h(self, msg):
            result[0] = bytes(_pmt.u8vector_elements(_pmt.cdr(msg)))

    sink = _Sink()
    tb = gr.top_block()
    tb.msg_connect(enc, 'out', sink, 'in')
    tb.start()
    enc.to_basic_block()._post(
        _pmt.intern('in'),
        _pmt.cons(_pmt.PMT_NIL, _pmt.init_u8vector(plen, list(payload))))
    _time.sleep(0.1)
    tb.stop(); tb.wait()

    if result[0] is None:
        raise RuntimeError("encode_rs produced no output")
    return result[0]


# -- CCSDS Synchronous Scrambler (matching gr-satellites randomizer.c) ---------

def ccsds_scrambler_sequence(length):
    """Generate CCSDS PN sequence matching gr-satellites ccsds_generate_sequence().

    Uses h(x) = x^8+x^7+x^5+x^3+1 with all-ones initial state.
    Generates one BIT per LFSR clock, packs 8 bits per output byte (MSB first)."""
    x = [1, 1, 1, 1, 1, 1, 1, 1, 1]  # 9-element shift register, all 1s
    seq = bytearray(length)
    for i in range(length * 8):
        seq[i >> 3] |= x[1] << (7 - (i & 7))     # output bit = x[1], pack MSB first
        x[0] = (x[8] ^ x[6] ^ x[4] ^ x[1]) & 1   # feedback taps
        x[1], x[2], x[3], x[4] = x[2], x[3], x[4], x[5]
        x[5], x[6], x[7], x[8] = x[6], x[7], x[8], x[0]
    return bytes(seq)

# Pre-compute max PN sequence (255 bytes, slice as needed).
_PN_MAX = ccsds_scrambler_sequence(255)


# -- Golay(24,12) Encoder (matching gr-satellites golay24.c) -------------------

# Generator matrix rows from gr-satellites (Morelos-Zaragoza construction).
# Each row is a 24-bit value; lower 12 bits are the B(i) parity sub-matrix.
_GOLAY_H = [
    0x8008ed, 0x4001db, 0x2003b5, 0x100769, 0x80ed1, 0x40da3,
    0x20b47,  0x1068f,  0x8d1d,   0x4a3b,   0x2477,  0x1ffe,
]


def golay_encode(value_12bit):
    """Encode a 12-bit value into a 24-bit Golay(24,12) codeword.

    Matches gr-satellites golay24.c encode_golay24() exactly.
    Format: [12 parity bits][12 data bits] (MSB first, 3 bytes)."""
    r = value_12bit & 0xFFF
    s = 0
    for i in range(12):
        s <<= 1
        s |= bin(_GOLAY_H[i] & r).count('1') % 2
    codeword = ((s & 0xFFF) << 12) | r
    return codeword.to_bytes(3, 'big')


# -- Frame Assembly -----------------------------------------------------------

def build_asm_golay_frame(csp_packet):
    """Build complete ASM+Golay over-the-air frame from a CSP packet.

    Matches gr-satellites u482c_decode exactly:
      - Golay 12-bit field: RS flag | scrambler flag | frame_len
      - RS: conventional (decode_rs_8), dynamically shortened
      - CCSDS scrambler on the RS codeword
      - No dual-basis conversion

    Input:  CSP packet (max 223B).
    Output: Frame bytes ready for GFSK modulation."""
    if not _GR_RS_OK:
        raise RuntimeError("reedsolo not installed — cannot build ASM+Golay frame")
    plen = len(csp_packet)
    if plen > MAX_PAYLOAD:
        raise ValueError(f"CSP packet {plen}B exceeds RS capacity {MAX_PAYLOAD}B")

    # RS encode (conventional, shortened)
    rs_codeword = rs_encode(csp_packet)     # plen + 32 bytes
    frame_len = len(rs_codeword)            # = plen + 32

    # CCSDS scrambler (only frame_len bytes)
    pn = _PN_MAX[:frame_len]
    scrambled = bytes(a ^ b for a, b in zip(rs_codeword, pn))

    # Golay field: [unused 1][rs 1][scrambler 1][viterbi 1][frame_len 8]
    golay_value = (1 << 10) | (1 << 9) | (frame_len & 0xFF)
    golay_field = golay_encode(golay_value)

    # Pad to 255 bytes after ASM (packlen=255 in gr-satellites deframer)
    after_asm = golay_field + scrambled
    after_asm = after_asm.ljust(255, b'\x00')

    return PREAMBLE + ASM + after_asm
