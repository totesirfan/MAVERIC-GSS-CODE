# Phase 3: Protocol-Family Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract reusable protocol-family support (CRC, CSP, AX.25, Golay, frame detection) from `protocol.py` into a `protocols/` package while keeping all existing imports working.

**Architecture:** This is a compatibility refactor, not an architecture rewrite. New `protocols/` modules are the canonical home for protocol-family code. The old `protocol.py`, `ax25.py`, and `golay.py` become thin facades that re-export everything from the new locations. Zero behavior changes. All 68 existing tests must pass after each task.

**Tech Stack:** Python 3.10+, crcmod, PyYAML (optional)

---

## Resolved Design Decisions

These were listed as open in the Phase 2 inventory. They are now resolved:

1. **KISS goes in `protocols/csp.py`.** KISS framing is only used in the CSP TX path today. If another protocol family needs KISS independently later, it can be extracted then.

2. **`AX25Config` merges into `protocols/ax25.py`.** The encoder (HDLC + G3RUH + NRZI) and the TX config wrapper (`AX25Config`) are complementary AX.25 protocol support. They stay in one file. `AX25Config` is appended below the encoder with a section separator. No cross-dependencies between them.

3. **`CommandFrame` stays in `protocol.py`.** It is MAVERIC's inner command payload format, not a protocol-family primitive. It moves to `missions/maveric/wire_format.py` in Phase 4.

## File Plan

| Action | File | Responsibility |
|---|---|---|
| Create | `mav_gss_lib/protocols/__init__.py` | Package marker, re-exports key symbols |
| Create | `mav_gss_lib/protocols/crc.py` | CRC-16 XMODEM, CRC-32C Castagnoli, CSP CRC verification |
| Create | `mav_gss_lib/protocols/csp.py` | KISS constants + wrapping, CSP v1 header parse, CSPConfig TX wrapper |
| Create | `mav_gss_lib/protocols/ax25.py` | AX.25 encoder (HDLC/G3RUH/NRZI) + AX25Config TX wrapper |
| Create | `mav_gss_lib/protocols/frame_detect.py` | Frame type detection + normalization (RX direction) |
| Move | `mav_gss_lib/golay.py` content → `mav_gss_lib/protocols/golay.py` | ASM+Golay encoder (unchanged) |
| Modify | `mav_gss_lib/protocol.py` | Compatibility facade: re-exports moved symbols from `protocols/` |
| Modify | `mav_gss_lib/ax25.py` | Compatibility facade: re-exports from `protocols.ax25` |
| Modify | `mav_gss_lib/golay.py` | Compatibility facade: re-exports from `protocols.golay` |

## Test Commands

Two test suites must pass after every task:

```bash
# In-repo tests (44 tests)
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

# Parent-dir tests (24 tests)
cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

## Compatibility Rules

1. **No downstream import changes.** Every existing `from mav_gss_lib.protocol import X` and `import mav_gss_lib.protocol as protocol` must continue to work.
2. **No downstream import changes for ax25/golay.** Every existing `from mav_gss_lib.ax25 import X` and `from mav_gss_lib.golay import X` must continue to work.
3. **`protocol.py` keeps all MAVERIC-specific code in place.** Node tables, `CommandFrame`, command schema, `parse_cmd_line`, and all lookup helpers stay in `protocol.py` for Phase 3. They move in Phase 4.
4. **New `protocols/` modules must not import from `protocol.py`.** Dependency flows one way: `protocol.py` imports from `protocols/`, never the reverse.
5. **`__init__.py` in `mav_gss_lib/` is not changed.** It imports from `protocol.py` which remains the facade.

---

## Task 1: Create `protocols/` Package

**Files:**
- Create: `mav_gss_lib/protocols/__init__.py`

- [ ] **Step 1: Create the package file**

```python
"""
mav_gss_lib.protocols -- Reusable CubeSat Protocol-Family Support

Protocol-family primitives shared across missions:
    crc          -- CRC-16 XMODEM, CRC-32C Castagnoli
    csp          -- CSP v1 header, KISS framing, CSPConfig
    ax25         -- AX.25 encoder, AX25Config
    golay        -- ASM+Golay encoder (AX100 Mode 5)
    frame_detect -- Frame type detection and normalization
"""

from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32
from mav_gss_lib.protocols.csp import (
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig,
)
from mav_gss_lib.protocols.ax25 import (
    AX25Config, build_ax25_gfsk_frame,
)
from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame
```

Note: This file will fail to import until Tasks 2–5 create the modules it references. That is expected. Do not run tests until Task 7.

- [ ] **Step 2: Commit**

```bash
git add mav_gss_lib/protocols/__init__.py
git commit -m "Add protocols/ package skeleton for protocol-family split"
```

---

## Task 2: Create `protocols/crc.py`

**Files:**
- Create: `mav_gss_lib/protocols/crc.py`

- [ ] **Step 1: Create the CRC module**

```python
"""
mav_gss_lib.protocols.crc -- CRC-16 XMODEM & CRC-32C (Castagnoli)

CRC-16 XMODEM: used in MAVERIC command wire format integrity.
CRC-32C (Castagnoli): used in CSP v1 packet integrity.

Both use C-accelerated crcmod for performance.
"""

try:
    import crcmod.predefined as _crcmod
except ImportError:
    raise ImportError(
        "crcmod is required for CRC computation but not installed. "
        "Install with: pip install crcmod   (or: conda install crcmod)"
    ) from None

_crc16_fn = _crcmod.mkCrcFun('xmodem')
_crc32c_fn = _crcmod.mkCrcFun('crc-32c')


def crc16(data):
    """CRC-16 XMODEM checksum (C-accelerated via crcmod)."""
    return _crc16_fn(data)


def crc32c(data):
    """CRC-32C (Castagnoli) checksum for CSP v1 packet integrity (C-accelerated via crcmod)."""
    return _crc32c_fn(data)


def verify_csp_crc32(inner_payload):
    """Verify CRC-32C over a complete CSP packet (header + data + CRC-32C).

    Last 4 bytes are the received CRC-32C (big-endian); computed over
    everything preceding them.

    Returns (is_valid, received_crc, computed_crc).
    Returns (None, None, None) if payload is too short to contain a CRC."""
    if len(inner_payload) < 8:  # need at least 4B CSP header + 4B CRC
        return None, None, None
    received = int.from_bytes(inner_payload[-4:], 'big')
    computed = crc32c(inner_payload[:-4])
    return received == computed, received, computed
```

- [ ] **Step 2: Smoke test the module in isolation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32; print('crc16:', hex(crc16(b'hello'))); print('crc32c:', hex(crc32c(b'hello'))); print('OK')"
```

Expected: prints hex values and `OK` with no errors.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/protocols/crc.py
git commit -m "Add protocols/crc.py with CRC-16 and CRC-32C"
```

---

## Task 3: Create `protocols/csp.py`

**Files:**
- Create: `mav_gss_lib/protocols/csp.py`

- [ ] **Step 1: Create the CSP + KISS module**

```python
"""
mav_gss_lib.protocols.csp -- CSP v1 Header & KISS Framing

CSP v1 header parse/build for the Cubesat Space Protocol.
KISS framing for CSP transport.
CSPConfig for TX-direction CSP wrapping with optional CRC-32C.
"""

from mav_gss_lib.protocols.crc import crc32c


# =============================================================================
#  KISS FRAMING
# =============================================================================

FEND  = 0xC0
FESC  = 0xDB
TFEND = 0xDC
TFESC = 0xDD


def kiss_wrap(raw_cmd):
    """KISS-wrap a raw command payload.
    Output: C0 00 [kiss-escaped data] C0
    DB must be escaped before C0 to avoid double-escaping."""
    escaped = raw_cmd.replace(b'\xDB', b'\xDB\xDD').replace(b'\xC0', b'\xDB\xDC')
    return b'\xC0\x00' + escaped + b'\xC0'


# =============================================================================
#  CSP V1 HEADER
#
#  32-bit big-endian word:
#    [31:30] priority  [29:25] source  [24:20] destination
#    [19:14] dest_port [13:8]  src_port [7:0] flags
# =============================================================================

def try_parse_csp_v1(payload):
    """Parse first 4 bytes as CSP v1 header (RX direction).
    Returns (parsed_dict, is_plausible) or (None, False)."""
    if len(payload) < 4:
        return None, False

    h = int.from_bytes(payload[0:4], "big")
    csp = {
        "prio":  (h >> 30) & 0x03,
        "src":   (h >> 25) & 0x1F,
        "dest":  (h >> 20) & 0x1F,
        "dport": (h >> 14) & 0x3F,
        "sport": (h >> 8)  & 0x3F,
        "flags": h & 0xFF,
    }
    plausible = csp["src"] <= 20 and csp["dest"] <= 20
    return csp, plausible


class CSPConfig:
    """Configurable CSP v1 header for uplink (TX direction).

    When enabled, wrap() prepends the 4-byte CSP header and appends
    a 4-byte CRC-32C (Castagnoli) over the entire CSP packet."""

    def __init__(self):
        self.enabled = True
        self.prio    = 2
        self.src     = 0
        self.dest    = 8
        self.dport   = 0
        self.sport   = 24
        self.flags   = 0x00
        self.csp_crc = True

    def build_header(self):
        """Pack CSP fields into 4-byte big-endian header."""
        h = ((self.prio  & 0x03) << 30 |
             (self.src   & 0x1F) << 25 |
             (self.dest  & 0x1F) << 20 |
             (self.dport & 0x3F) << 14 |
             (self.sport & 0x3F) << 8  |
             (self.flags & 0xFF))
        return h.to_bytes(4, 'big')

    def overhead(self):
        """Number of bytes the CSP header + optional CRC-32C add to a payload."""
        if not self.enabled:
            return 0
        return 8 if self.csp_crc else 4

    def wrap(self, payload):
        """Prepend CSP header and optionally append CRC-32C.

        Output: [CSP header 4B] [payload] [CRC-32C 4B BE] (if csp_crc)
                [CSP header 4B] [payload]                  (if not csp_crc)"""
        if self.enabled:
            packet = self.build_header() + payload
            if self.csp_crc:
                checksum = crc32c(packet).to_bytes(4, 'big')
                return packet + checksum
            return packet
        return payload
```

- [ ] **Step 2: Smoke test the module in isolation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.protocols.csp import kiss_wrap, try_parse_csp_v1, CSPConfig
print('kiss:', kiss_wrap(b'\\xC0test').hex())
csp = CSPConfig()
wrapped = csp.wrap(b'payload')
print('csp wrap len:', len(wrapped))
parsed, ok = try_parse_csp_v1(wrapped)
print('parsed src:', parsed['src'], 'plausible:', ok)
print('OK')
"
```

Expected: prints values and `OK` with no errors.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/protocols/csp.py
git commit -m "Add protocols/csp.py with CSP v1 header, KISS, and CSPConfig"
```

---

## Task 4: Create `protocols/ax25.py`

**Files:**
- Create: `mav_gss_lib/protocols/ax25.py`
- Source: `mav_gss_lib/ax25.py` (encoder, copied verbatim) + `AX25Config` from `mav_gss_lib/protocol.py:337-397`

- [ ] **Step 1: Create the merged AX.25 module**

The file has two sections: the existing encoder (copied verbatim from `mav_gss_lib/ax25.py`) followed by `AX25Config` (copied from `mav_gss_lib/protocol.py`). No cross-dependencies between them.

```python
"""
mav_gss_lib.protocols.ax25 -- AX.25 Protocol Support (AX100 Mode 6)

Two complementary pieces:
  1. AX25Config   -- TX-direction AX.25 UI frame header wrapper
  2. Encoder      -- HDLC framer + G3RUH scrambler + NRZI encoder + bit packing

AX25Config.wrap() produces an AX.25 packet (header + payload).
build_ax25_gfsk_frame() takes that packet and produces the over-the-air
encoded bitstream ready for GFSK modulation.

Author:  Irfan Annuar - USC ISI SERC
"""


# =============================================================================
#  AX.25 UI FRAME HEADER (TX direction)
# =============================================================================

class AX25Config:
    """Configurable AX.25 header for uplink (TX direction).

    Wraps a payload with a 16-byte AX.25 UI frame header so the PDU
    is ready for an HDLC framer with no custom GRC blocks needed.
    """

    HEADER_LEN = 16  # 7 dest + 7 src + 1 control + 1 PID

    def __init__(self):
        self.enabled   = True
        self.dest_call = "WS9XSW"
        self.dest_ssid = 0
        self.src_call  = "WM2XBB"
        self.src_ssid  = 0

    @staticmethod
    def _encode_callsign(call, ssid, last=False):
        """Encode callsign + SSID into 7 AX.25 address bytes.

        Each character is shifted left 1 bit. Callsign is space-padded
        to 6 characters. SSID byte: 0b0RR_SSSS_E (E=1 if last address).

        *ssid* accepts either a 0-15 SSID value (standard) or a raw
        SSID byte (> 0x0F, e.g. 0x60 from GomSpace AX100 config).
        The extension bit is always managed automatically."""
        call = call.upper().ljust(6)[:6]
        addr = bytearray(ord(c) << 1 for c in call)
        if ssid > 0x0F:
            ssid_byte = ssid & 0xFE
            if last:
                ssid_byte |= 0x01
        else:
            ssid_byte = 0x60 | ((ssid & 0x0F) << 1)
            if last:
                ssid_byte |= 0x01
        addr.append(ssid_byte)
        return bytes(addr)

    def overhead(self):
        """Number of bytes the AX.25 header adds to a payload."""
        return self.HEADER_LEN if self.enabled else 0

    def wrap(self, payload):
        """Prepend 16-byte AX.25 UI frame header if enabled.

        Output: [dest 7B][src 7B][0x03][0xF0][payload]"""
        if self.enabled:
            header = (
                self._encode_callsign(self.dest_call, self.dest_ssid, last=False)
                + self._encode_callsign(self.src_call, self.src_ssid, last=True)
                + b'\x03\xF0'
            )
            return header + payload
        return payload


# =============================================================================
#  AX.25 OVER-THE-AIR ENCODER
#
#  Replicates the GNU Radio AX.25 TX chain:
#    HDLC framer -> G3RUH scrambler -> NRZI encoder -> bit packing
# =============================================================================

# -- Tunables ----------------------------------------------------------------

PREAMBLE_FLAGS  = 20       # Number of 0x7E flag bytes before frame
POSTAMBLE_FLAGS = 20       # Number of 0x7E flag bytes after frame

G3RUH_MASK      = 0x21    # Feedback tap mask (x^17 + x^12 + 1)
G3RUH_REG_LEN   = 16      # Shift register length (17 effective bits: 0-16)
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
        HDLC framer -> G3RUH scrambler -> NRZI encoder -> MSB bit packing

    G3RUH scrambler: polynomial x^17 + x^12 + 1 (GNU Radio Fibonacci LFSR).
    NRZI encoder: 0 -> toggle, 1 -> hold.
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
```

- [ ] **Step 2: Smoke test the module in isolation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.protocols.ax25 import AX25Config, build_ax25_gfsk_frame
ax = AX25Config()
pkt = ax.wrap(b'test_payload')
print('wrapped len:', len(pkt))
frame = build_ax25_gfsk_frame(pkt)
print('frame len:', len(frame))
print('OK')
"
```

Expected: prints lengths and `OK` with no errors.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/protocols/ax25.py
git commit -m "Add protocols/ax25.py with AX25Config and encoder"
```

---

## Task 5: Create `protocols/frame_detect.py`

**Files:**
- Create: `mav_gss_lib/protocols/frame_detect.py`

- [ ] **Step 1: Create the frame detection module**

```python
"""
mav_gss_lib.protocols.frame_detect -- Frame Type Detection & Normalization

RX-direction utilities: detect outer framing type from gr-satellites
metadata and strip it to expose the inner CSP+payload.
"""


def detect_frame_type(meta):
    """Determine frame type from gr-satellites metadata."""
    tx_info = str(meta.get("transmitter", ""))
    for keyword, label in (("AX.25", "AX.25"), ("AX100", "ASM+GOLAY")):
        if keyword in tx_info:
            return label
    return "UNKNOWN"


def normalize_frame(frame_type, raw):
    """Strip outer framing, return (inner_payload, stripped_header_hex, warnings)."""
    warnings = []
    if frame_type == "AX.25":
        idx = raw.find(b"\x03\xf0")
        if idx == -1:
            warnings.append("AX.25 frame but no 03 f0 delimiter found")
            return raw, None, warnings
        return raw[idx + 2:], raw[:idx + 2].hex(" "), warnings
    if frame_type != "ASM+GOLAY":
        warnings.append("Unknown frame type -- returning raw")
    return raw, None, warnings
```

- [ ] **Step 2: Smoke test the module in isolation**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame
ft = detect_frame_type({'transmitter': 'AX.25 9k6'})
print('type:', ft)
inner, hdr, warns = normalize_frame('AX.25', b'\\x00' * 14 + b'\\x03\\xf0PAYLOAD')
print('inner:', inner)
print('OK')
"
```

Expected: prints `type: AX.25`, inner payload, and `OK`.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/protocols/frame_detect.py
git commit -m "Add protocols/frame_detect.py with frame type detection"
```

---

## Task 6: Copy Golay Encoder to `protocols/golay.py`

**Files:**
- Create: `mav_gss_lib/protocols/golay.py` (copy of `mav_gss_lib/golay.py`, unchanged)

- [ ] **Step 1: Copy the golay module**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
cp mav_gss_lib/golay.py mav_gss_lib/protocols/golay.py
```

No content changes. The file is self-contained with no imports from other `mav_gss_lib` modules.

- [ ] **Step 2: Smoke test the module from the new path**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.protocols.golay import MAX_PAYLOAD, golay_encode
print('MAX_PAYLOAD:', MAX_PAYLOAD)
cw = golay_encode(42)
print('golay(42):', hex(cw))
print('OK')
"
```

Expected: prints values and `OK`.

- [ ] **Step 3: Commit**

```bash
git add mav_gss_lib/protocols/golay.py
git commit -m "Copy golay.py to protocols/golay.py"
```

---

## Task 7: Convert `protocol.py` to Compatibility Facade

This is the critical task. `protocol.py` keeps all its MAVERIC-specific code but replaces the protocol-family definitions with imports from `protocols/`.

**Files:**
- Modify: `mav_gss_lib/protocol.py`

- [ ] **Step 1: Replace CRC section with imports from `protocols.crc`**

Replace lines 111–142 (the CRC section from the `try: import crcmod` block through the `crc32c` function) with:

```python
# =============================================================================
#  CRC — re-exported from protocols.crc
# =============================================================================

from mav_gss_lib.protocols.crc import crc16, crc32c, verify_csp_crc32  # noqa: F401
```

Remove lines 145–157 (the `verify_csp_crc32` function definition) since it is now imported above.

- [ ] **Step 2: Replace KISS section with imports from `protocols.csp`**

Replace lines 89–108 (KISS constants and `kiss_wrap`) with:

```python
# =============================================================================
#  KISS & CSP — re-exported from protocols.csp
# =============================================================================

from mav_gss_lib.protocols.csp import (  # noqa: F401
    FEND, FESC, TFEND, TFESC, kiss_wrap,
    try_parse_csp_v1, CSPConfig,
)
```

Remove the original `try_parse_csp_v1` function (lines 306–322) and `CSPConfig` class (lines 400–451) since they are now imported above.

- [ ] **Step 3: Replace AX25Config with import from `protocols.ax25`**

Replace the `AX25Config` class (lines 337–397) with:

```python
# =============================================================================
#  AX.25 — re-exported from protocols.ax25
# =============================================================================

from mav_gss_lib.protocols.ax25 import AX25Config  # noqa: F401
```

- [ ] **Step 4: Replace frame detection with imports from `protocols.frame_detect`**

Replace `detect_frame_type` and `normalize_frame` (lines 730–750) with:

```python
# =============================================================================
#  FRAME DETECTION — re-exported from protocols.frame_detect
# =============================================================================

from mav_gss_lib.protocols.frame_detect import detect_frame_type, normalize_frame  # noqa: F401
```

- [ ] **Step 5: Run the full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass. Zero failures.

- [ ] **Step 6: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/protocol.py
git commit -m "Convert protocol.py CRC/CSP/AX25/frame functions to facade re-exports from protocols/"
```

---

## Task 8: Convert Old `ax25.py` and `golay.py` to Compatibility Facades

**Files:**
- Modify: `mav_gss_lib/ax25.py`
- Modify: `mav_gss_lib/golay.py`

- [ ] **Step 1: Replace `ax25.py` with facade**

Replace the entire content of `mav_gss_lib/ax25.py` with:

```python
"""
mav_gss_lib.ax25 -- Compatibility facade

Canonical location: mav_gss_lib.protocols.ax25
This module re-exports all public symbols for backward compatibility.
"""

from mav_gss_lib.protocols.ax25 import *  # noqa: F401,F403
from mav_gss_lib.protocols.ax25 import (
    AX25Config,
    PREAMBLE_FLAGS,
    POSTAMBLE_FLAGS,
    G3RUH_MASK,
    G3RUH_REG_LEN,
    G3RUH_SEED,
    NRZI_INIT,
    build_ax25_gfsk_frame,
)
```

- [ ] **Step 2: Replace `golay.py` with facade**

Replace the entire content of `mav_gss_lib/golay.py` with:

```python
"""
mav_gss_lib.golay -- Compatibility facade

Canonical location: mav_gss_lib.protocols.golay
This module re-exports all public symbols for backward compatibility.
"""

from mav_gss_lib.protocols.golay import *  # noqa: F401,F403
from mav_gss_lib.protocols.golay import (
    MAX_PAYLOAD,
    build_asm_golay_frame,
    rs_encode,
    golay_encode,
    ccsds_scrambler_sequence,
    _GR_RS_OK,
)
```

- [ ] **Step 3: Verify old import paths still work**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
# Test old ax25 imports
from mav_gss_lib.ax25 import build_ax25_gfsk_frame
print('ax25 old path: OK')

# Test old golay imports
from mav_gss_lib.golay import MAX_PAYLOAD, build_asm_golay_frame, _GR_RS_OK
print('golay old path: OK')

# Test new canonical paths
from mav_gss_lib.protocols.ax25 import build_ax25_gfsk_frame as f1
from mav_gss_lib.protocols.golay import MAX_PAYLOAD as m1
print('new paths: OK')

# Test protocol.py facade
from mav_gss_lib.protocol import AX25Config, CSPConfig, crc16, crc32c
print('protocol facade: OK')
"
```

Expected: all four `OK` lines print.

- [ ] **Step 4: Run the full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass. Zero failures.

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add mav_gss_lib/ax25.py mav_gss_lib/golay.py
git commit -m "Convert ax25.py and golay.py to compatibility facades over protocols/"
```

---

## Task 9: Final Verification and Cleanup

- [ ] **Step 1: Verify the `protocols/` package import works end-to-end**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
import mav_gss_lib.protocols as p

# CRC
assert callable(p.crc16)
assert callable(p.crc32c)

# CSP
assert callable(p.kiss_wrap)
assert callable(p.try_parse_csp_v1)
csp = p.CSPConfig()
assert csp.wrap(b'x') is not None

# AX.25
ax = p.AX25Config()
assert ax.wrap(b'x') is not None
assert callable(p.build_ax25_gfsk_frame)

# Frame detect
assert p.detect_frame_type({'transmitter': 'AX100 9k6'}) == 'ASM+GOLAY'

print('All protocols/ imports verified')
"
```

- [ ] **Step 2: Verify `mav_gss_lib.__init__` still works**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib import (
    crc16, crc32c, verify_csp_crc32,
    CSPConfig, detect_frame_type, normalize_frame,
    init_nodes, build_cmd_raw, try_parse_csp_v1,
)
print('__init__ re-exports: OK')
"
```

- [ ] **Step 3: Run both test suites one final time**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

Expected: All 68 tests pass.

- [ ] **Step 4: Verify no circular imports**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
# Import everything in dependency order to check for cycles
import mav_gss_lib.protocols.crc
import mav_gss_lib.protocols.csp
import mav_gss_lib.protocols.ax25
import mav_gss_lib.protocols.frame_detect
import mav_gss_lib.protocols.golay
import mav_gss_lib.protocols
import mav_gss_lib.protocol
import mav_gss_lib.ax25
import mav_gss_lib.golay
import mav_gss_lib
print('No circular imports')
"
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add -A
git commit -m "Phase 3 complete: protocol-family support extracted to protocols/"
```

---

## Post-Phase 3 State

After all tasks complete:

```
mav_gss_lib/
  protocols/              # NEW — canonical home for protocol-family support
    __init__.py
    crc.py                # CRC-16 XMODEM, CRC-32C Castagnoli
    csp.py                # CSP v1 header, KISS, CSPConfig
    ax25.py               # AX25Config + encoder (HDLC/G3RUH/NRZI)
    frame_detect.py       # Frame type detection + normalization
    golay.py              # ASM+Golay encoder (AX100 Mode 5)

  protocol.py             # FACADE — re-exports from protocols/, keeps MAVERIC code
  ax25.py                 # FACADE — re-exports from protocols.ax25
  golay.py                # FACADE — re-exports from protocols.golay

  # Unchanged:
  transport.py
  config.py
  mission_adapter.py
  parsing.py
  logging.py
  imaging.py
  tui_common.py
  tui_rx.py
  tui_tx.py
  web_runtime/
  web/
```

**What moved:** CRC, CSP, KISS, AX25Config, AX.25 encoder, Golay encoder, frame detection.

**What stayed in `protocol.py`:** Node tables, `CommandFrame`, command schema, `parse_cmd_line`, all MAVERIC-specific code. These move in Phase 4.

**What did NOT change:** Every downstream import. Every test. Every behavior.
