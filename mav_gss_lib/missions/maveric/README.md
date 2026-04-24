# MAVERIC Mission Package

The MAVERIC mission implementation — one pluggable mission package within the
broader ground station platform. The platform loads it by convention at startup
when mission id `maveric` is active and calls `mission.py::build(ctx)` to obtain
a `MissionSpec`.

## Layout

Organized into five domain subpackages plus shared top-level modules. Every
subpackage `__init__.py` is self-documenting — open it for the intra-package
overview.

```
maveric/
├── __init__.py
├── mission.py             MissionSpec builder (build(ctx) entry point)
├── defaults.py            Seed constants + seed_mission_cfg
├── config_access.py       mission_cfg read helpers
├── nodes.py               NodeTable + init_nodes
├── preflight.py           Mission preflight-check factory
├── wire_format.py         CommandFrame encode/decode     — SHARED (RX + TX)
├── schema.py              commands.yml load/validate     — SHARED (RX + TX)
├── commands.yml           Operational schema (gitignored)
├── commands.example.yml   Public-safe schema template
│
├── rx/                    RX pipeline — boundary: MavericPacketOps
│   ├── ops.py             normalize → parse → classify
│   ├── parser.py          frame detect + CSP/AX.25/Golay strip + command decode
│   └── packet.py          MavericRxPacket (mission-local RX view)
│
├── commands/              TX pipeline — boundary: MavericCommandOps
│   ├── ops.py             parse_input → validate → encode → frame → render
│   ├── parser.py          raw CLI grammar (cmd_line_to_payload)
│   ├── builder.py         routing + arg validate + inner-frame encode
│   └── framing.py         MavericFramer (CSP + AX.25 / ASM+Golay)
│
├── ui/                    Presentation — boundary: MavericUiOps
│   ├── ops.py             UiOps implementation
│   ├── rendering.py       row / detail_blocks / protocol_blocks / integrity_blocks
│   ├── formatters.py      atom-level helpers (ptype, hex, timestamps)
│   └── log_format.py      JSONL mission-data + text log lines
│
├── telemetry/             Fragments + catalogs — boundary: build_telemetry_ops
│   ├── __init__.py        TELEMETRY_MANIFEST + per-domain catalog builders
│   ├── ops.py             MavericTelemetryExtractor
│   ├── extractors/        per-packet fragment producers (tlm_beacon, eps_hk, gnc_res)
│   └── semantics/         canonical shapes (eps, gnc_schema, gnc_handlers, ...)
│
└── imaging/               Imaging plugin
    ├── assembler.py       ImageAssembler (chunk reassembly, restart recovery)
    ├── router.py          /api/plugins/imaging FastAPI router
    └── events.py          MavericImagingEvents (EventOps source)
```

## What this package owns

- **Packet parsing** (`rx/`) — command wire decode, CSP v1 header extraction,
  CRC-16 and CRC-32C integrity checks, frame detection, duplicate
  fingerprinting.
- **Command building** (`commands/`) — CLI parse, argument validation,
  routing resolution, inner frame encoding, and outer uplink framing
  (CSP + AX.25 or ASM+Golay). `frame()` returns wire bytes plus structured
  `log_fields` / `log_text` for the platform TX log.
- **Operator rendering** (`ui/`) — `Cell` / `DetailBlock` / `IntegrityBlock`
  / `PacketRendering` values for the platform's generic UI containers.
- **Log formatting** (`ui/log_format.py`) — mission-specific JSONL mission-data
  shape and human-readable text log lines.
- **Telemetry decoders** (`telemetry/`) — per-packet `TelemetryFragment`s
  for `eps`, `gnc`, and `spacecraft` domains, backed by semantic decoders
  (`semantics/`). The platform telemetry router persists latest-value state
  per domain and serves catalogs at `/api/telemetry/{domain}/catalog`.
- **Imaging plugin** (`imaging/`) — chunk reassembly, REST endpoints, and the
  packet event source that drives the assembler from inbound imaging commands.
- **Node / ptype tables** (`nodes.py` + seed data in `defaults.py`).
- **Command schema** (`schema.py`, `wire_format.py`, `commands.yml`).
- **Mission identity + defaults** (`defaults.py`) — mission name, nodes,
  ptypes, GS node, UI titles, placeholder AX.25/CSP/imaging, mission-declared
  TX defaults. Seeded into `mission_cfg` / `platform_cfg.tx` by
  `mission.py::build(ctx)`; operator values in `gss.yml` win.
- **Mission config access** (`config_access.py`) — read helpers with
  legacy-flat-config fallback.
- **Frontend plugin surface** — TX builder + imaging page + GNC page under
  `mav_gss_lib/web/src/plugins/maveric/`.

## MAVERIC-specific behavior (not platform-level)

- **AX.25 + CSP v1 + Command Wire Format** — MAVERIC's three-layer framing.
  Other missions may use different or no protocol wrappers.
- **CRC-16 per command + CRC-32C over CSP** — dual integrity scheme is
  MAVERIC's wire format, not a platform requirement.
- **Node / ptype integer IDs** — MAVERIC maps integers (LPPM=1, EPS=2, …) to
  names. The platform has no opinion on how missions resolve nodes.
- **Uplink modes — Mode 5 (ASM+Golay) and Mode 6 (AX.25)** — MAVERIC radio
  parameters. The platform surfaces `tx.uplink_mode` but the modes themselves
  are mission-specific.
- **Satellite time decoding** — MAVERIC commands embed `epoch_ms` timestamps.
  Other missions may not.

## Config shape

At runtime MAVERIC's `mission_cfg` carries these keys under `mission.config`
in the native v2 split shape:

| Key | Source | Operator-editable? |
|-----|--------|---------------------|
| `mission_name`, `nodes`, `ptypes`, `node_descriptions`, `gs_node`, `command_defs`, `rx_title`, `tx_title`, `splash_subtitle` | `defaults.py`, seeded by `build(ctx)` | No — `MissionConfigSpec.protected_paths` |
| `ax25.*`, `csp.*`, `imaging.thumb_prefix` | `defaults.py` placeholders overlaid by `gss.yml:mission.config.*` | Yes — `MissionConfigSpec.editable_paths` |

Mission-declared TX defaults (`tx.frequency`, `tx.uplink_mode`) are seeded on
`platform_cfg["tx"]` at build time and can be overridden in `gss.yml`.

Mission code reads through `config_access.py` helpers; reaching through ad hoc
`general.*` fields is not supported.

## Warning: do not copy as-is

The MAVERIC MissionSpec implementation is tailored to MAVERIC's wire format,
node topology, and command schema. New missions should implement their own
MissionSpec using `mav_gss_lib.platform` contracts and may omit commands,
telemetry, events, or HTTP extensions if they do not need them. See
`mav_gss_lib/missions/echo_v2/` and `mav_gss_lib/missions/balloon_v2/` for
minimal reference implementations.
