"""MAVERIC TX command pipeline — operator input to on-air bytes.

The platform calls `MavericCommandOps` with a `CommandDraft` produced
either from the web UI command builder or from the raw-CLI text input.
This subpackage turns that into a fully validated, encoded, and framed
set of wire bytes plus the structured TX-log metadata the platform
records alongside every send.

Modules
-------
- `ops.py`     — `MavericCommandOps`, the platform boundary.
  Captures live references to `mission_config` and `platform_config`
  so `/api/config` edits (e.g. AX.25 callsigns, CSP routing, uplink
  mode) apply without a MissionSpec rebuild. Coordinates
  `parse_input` → `validate` → `encode` → `frame` → `render`.
- `parser.py`  — raw-CLI grammar. Turns a `command arg=value …` line
  into a typed payload matched against `commands.yml`.
- `builder.py` — resolves routing (src/dest/echo/ptype) against the
  node table, validates argument types, and encodes the inner MAVERIC
  command frame (`CommandFrame` bytes).
- `framing.py` — `MavericFramer`. Wraps the encoded command in CSP v1
  and then either HDLC/G3RUH/GFSK AX.25 or ASM + Golay(24,12) length +
  RS(255,223) + CCSDS scrambler, depending on
  `platform.tx.uplink_mode`. Returns the exact bytes for ZMQ plus
  `log_fields`/`log_text` for the TX log, and raises `ValueError` when
  the frame exceeds the mode-specific MTU.
"""

from mav_gss_lib.missions.maveric.commands.ops import MavericCommandOps

__all__ = ["MavericCommandOps"]
