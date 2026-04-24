"""MAVERIC RX packet pipeline — inbound bytes to structured packet.

The platform calls `MavericPacketOps` with the raw ZMQ frame and the RX
metadata; this subpackage turns that into a fully parsed, classified
`PacketEnvelope` with a MAVERIC-local RX view attached.

Modules
-------
- `ops.py`       — `MavericPacketOps`, the platform-v2 boundary.
  Drives `normalize` → `parse` → `classify` and stamps duplicate /
  uplink-echo / unknown-packet flags.
- `parser.py`    — frame detection (CSP / AX.25 / ASM+Golay), outer-
  framing strip, command-wire decode, field extraction, and
  duplicate-fingerprint derivation.
- `packet.py`    — `MavericRxPacket`, the mission-local RX view built
  from `PacketEnvelope`. Rendering, log formatting, and telemetry
  extractors all consume this type natively instead of poking at raw
  envelope data.

The byte-level command frame (`wire_format.py`) and the commands.yml
loader/validator (`schema.py`) live at the package top level because
both the RX parser and the TX builder consume them.
"""

from mav_gss_lib.missions.maveric.rx.ops import MavericPacketOps

__all__ = ["MavericPacketOps"]
