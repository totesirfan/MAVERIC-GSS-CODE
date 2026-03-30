"""
mav_gss_lib.ax25 -- AX.25 Uplink Encoder (AX100 Mode 6)

Self-contained encoder that replicates the GNU Radio AX.25 TX chain:
    HDLC framer → G3RUH scrambler → NRZI encoder → bit packing

This allows AX.25 frames to be sent through the same simple flowgraph
used for ASM+Golay (PDU → tagged stream → GFSK mod), eliminating the
need for separate GNU Radio blocks.

HDLC frame layout:
    [preamble flags] [bit-stuffed payload + FCS] [postamble flags]

Flag byte: 0x7E (01111110)
FCS: CRC-16-CCITT (init=0xFFFF, reflected poly=0x8408, final invert)
Bit order: LSB first per byte
Encoding: G3RUH scrambled, NRZI encoded

Zero external imports — hand-rolled for auditability in flight-path code.

Author:  Irfan Annuar - USC ISI SERC
"""

# -- Tunables ----------------------------------------------------------------

PREAMBLE_FLAGS  = 20       # Number of 0x7E flag bytes before frame
POSTAMBLE_FLAGS = 20       # Number of 0x7E flag bytes after frame

G3RUH_MASK      = 0x21    # Feedback tap mask (x^17 + x^12 + 1 → taps at 0, 5)
G3RUH_REG_LEN   = 16      # Shift register length (17 effective bits: 0–16)
G3RUH_SEED      = 0x00000 # Initial register state

NRZI_INIT       = 0       # NRZI encoder initial output state


# -- CRC-16-CCITT (HDLC FCS) -------------------------------------------------

def _crc_ccitt(data):
    """CRC-16-CCITT as used in HDLC/X.25 FCS.

    Init: 0xFFFF, reflected polynomial 0x8408, final XOR 0xFFFF.
    Returns 16-bit CRC value."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return crc ^ 0xFFFF


# -- HDLC Framing -------------------------------------------------------------

_FLAG_BITS = [0, 1, 1, 1, 1, 1, 1, 0]   # 0x7E LSB first


def _bytes_to_bits_lsb(data):
    """Convert bytes to bit list, LSB first per byte."""
    bits = []
    for byte in data:
        for i in range(8):
            bits.append((byte >> i) & 1)
    return bits


def _bit_stuff(bits):
    """Insert a 0 bit after every run of five consecutive 1s."""
    out = []
    ones = 0
    for b in bits:
        out.append(b)
        if b == 1:
            ones += 1
            if ones == 5:
                out.append(0)
                ones = 0
        else:
            ones = 0
    return out


def _hdlc_frame(payload):
    """HDLC-frame a payload, matching gr-satellites hdlc_framer.

    Returns a list of bits (0/1 ints): preamble flags + bit-stuffed
    (payload + FCS) + postamble flags."""
    fcs = _crc_ccitt(payload)
    frame_data = payload + fcs.to_bytes(2, 'little')

    data_bits = _bytes_to_bits_lsb(frame_data)
    stuffed = _bit_stuff(data_bits)

    preamble = _FLAG_BITS * PREAMBLE_FLAGS
    postamble = _FLAG_BITS * POSTAMBLE_FLAGS
    return preamble + stuffed + postamble


# -- Top-Level Builder ---------------------------------------------------------

def build_ax25_gfsk_frame(ax25_packet):
    """Build complete AX.25 over-the-air frame from an AX.25-wrapped CSP packet.

    Replicates the GNU Radio AX.25 TX chain in a single fused pass:
        HDLC framer → G3RUH scrambler → NRZI encoder → MSB bit packing

    G3RUH scrambler: polynomial x^17 + x^12 + 1 (GNU Radio Fibonacci LFSR).
    NRZI encoder: 0 → toggle, 1 → hold.
    Bit packing: MSB first, 8 bits per byte (matches pack_k_bits_bb(8)).

    Input:  AX.25 packet (header + CSP payload) from AX25Config.wrap().
    Output: Frame bytes ready for GFSK mod with do_unpack=True."""
    bits = _hdlc_frame(ax25_packet)

    reg = G3RUH_SEED; mask = G3RUH_MASK; reg_len = G3RUH_REG_LEN
    nrzi_state = NRZI_INIT
    out = bytearray(); byte_acc = 0; bit_count = 0

    for b in bits:
        # G3RUH scrambler
        output = reg & 1
        newbit = ((reg & mask).bit_count() & 1) ^ (b & 1)
        reg = (reg >> 1) | (newbit << reg_len)
        # NRZI encoder
        if output == 0:
            nrzi_state ^= 1
        # MSB-first bit packing
        byte_acc = (byte_acc << 1) | nrzi_state
        bit_count += 1
        if bit_count == 8:
            out.append(byte_acc); byte_acc = 0; bit_count = 0

    return bytes(out)
