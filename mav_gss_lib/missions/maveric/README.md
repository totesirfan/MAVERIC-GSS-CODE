# MAVERIC Mission Package

This directory contains the MAVERIC-specific mission implementation. It is one
pluggable mission package within the broader ground station platform. The platform
loads it by convention at startup when `general.mission: maveric` is set in `gss.yml`.

## What This Package Owns

- **Packet parsing** — MAVERIC command wire format decoding, CSP v1 header extraction,
  CRC-16 and CRC-32C integrity checks (`adapter.py`, `wire_format.py`)
- **Command building** — TX command construction from operator input, argument validation,
  AX.25/CSP routing field assembly (`adapter.py` → `build_tx_command`)
- **Operator rendering** — structured data (column values, detail blocks, protocol blocks)
  for the platform's generic UI containers (`adapter.py` rendering-slot methods)
- **Wire format** — node/ptype definitions, `CommandFrame` encode/decode, schema-based
  argument parsing (`wire_format.py`)
- **TX builder UI** — MAVERIC command picker React component
  (`mav_gss_lib/web/src/missions/maveric/TxBuilder.tsx`)
- **Mission metadata** — node names, ptypes, AX.25/CSP defaults (`mission.example.yml`)
- **Command schema** — `commands.yml` (gitignored; not in public repo)

## Files

| File | Tracked | Purpose |
|------|---------|---------|
| `__init__.py` | Yes | Package entry point: `ADAPTER_API_VERSION`, `ADAPTER_CLASS`, `init_mission` |
| `adapter.py` | Yes | `MavericMissionAdapter` — implements the `MissionAdapter` protocol |
| `wire_format.py` | Yes | Node/ptype tables, `CommandFrame`, argument parsing |
| `imaging.py` | Yes | MAVERIC imaging subsystem command helpers |
| `mission.example.yml` | Yes | Public-safe mission metadata (nodes, ptypes, AX.25/CSP defaults) |
| `commands.example.yml` | Yes | Annotated command schema example — safe structure, redacted content |
| `mission.yml` | No | Local private mission metadata override (gitignored) |
| `commands.yml` | No | Operational command schema (gitignored for security) |

## MAVERIC-Specific Behavior

The following behaviors are specific to MAVERIC and should not be mistaken
for platform-level behavior:

- **AX.25 + CSP v1 framing** — MAVERIC uses AX.25 outer framing and CSP v1 headers.
  Other missions may use different or no protocol wrappers.
- **CRC-16 per command + CRC-32C over CSP** — dual integrity check scheme is
  MAVERIC's wire format, not a platform requirement.
- **Node/ptype integer IDs** — MAVERIC maps integer IDs (LPPM=1, EPS=2, etc.) to
  names. The platform has no opinion on how missions resolve nodes.
- **`GS_NODE` constant** — MAVERIC's ground station node ID. Platform only knows
  about it via `adapter.gs_node`.
- **Golay and AX.25 uplink modes** — MAVERIC supports Mode 5 (ASM+Golay) and
  Mode 6 (AX.25). Uplink mode selection is in `gss.yml`, applied by the platform
  protocol framing — but the modes themselves are MAVERIC radio hardware parameters.
- **Satellite time decoding** — MAVERIC commands embed `epoch_ms` timestamps
  decoded from the wire format. Other missions may not have embedded timestamps.

## Warning: Do Not Copy As-Is

The MAVERIC adapter is tailored to MAVERIC's specific wire format, node topology,
and command schema. Do not copy `adapter.py` wholesale for a new mission —
start from `mav_gss_lib/missions/template/adapter.py` instead, which contains
stub implementations and docstrings explaining each method's contract.

See `docs/adding-a-mission.md` for the full mission authoring guide.
