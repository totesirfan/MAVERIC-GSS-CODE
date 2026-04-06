# Phase 2: Core vs Mission Inventory

This document maps every module, class, and function in the codebase to its target layer per the architecture migration spec. It is the reference for Phases 3–6.

## Module-Level Summary

| Current Module | Target Layer | Status |
|---|---|---|
| `transport.py` | Platform Core — Transport | Ready (no mission code) |
| `ax25.py` | Platform Core — Protocol Support | Ready (no mission code) |
| `golay.py` | Platform Core — Protocol Support | Ready (no mission code) |
| `config.py` | Platform Core + Mission Defaults | Needs split: `_DEFAULTS` + config schema review |
| `protocol.py` | Mixed — must be split | ~31 core, ~24 MAVERIC |
| `mission_adapter.py` | Mixed — interface is core, impl is mission | ~4 core, ~7 MAVERIC |
| `parsing.py` | Platform Core (pipeline) + light MAVERIC fields | ~17 core, ~5 MAVERIC |
| `logging.py` | Platform Core (`_BaseLog`) + MAVERIC (`SessionLog`, `TXLog`) | ~18 core, ~7 MAVERIC |
| `imaging.py` | MAVERIC Mission | Entire module is mission-specific |
| `tui_common.py` | Mixed — framework is core, screens/colors are mission | ~14 core, ~8 MAVERIC |
| `tui_rx.py` | MAVERIC Mission | Entire module is mission-specific |
| `tui_tx.py` | MAVERIC Mission | Entire module is mission-specific |
| `web_runtime/app.py` | Platform Core — Runtime | Ready (no mission code) |
| `web_runtime/runtime.py` | Mixed | ~5 core, ~3 MAVERIC |
| `web_runtime/state.py` | Mixed — wires in `MavericMissionAdapter` | ~7 core, ~2 MAVERIC |
| `web_runtime/security.py` | Platform Core — Runtime | Ready (no mission code) |
| `web_runtime/services.py` | Mixed | ~20 core, ~6 MAVERIC |
| `web_runtime/api.py` | Mixed | ~8 core, ~6 MAVERIC |
| `web_runtime/rx.py` | Platform Core — Runtime | Ready (no mission code) |
| `web_runtime/tx.py` | Mixed — queue ops are core, command parsing is mission | ~9 core, ~2 MAVERIC |

## Detailed Inventory

### `protocol.py` — The Main Split Target

**Platform Core (stays in `protocols/`):**

| Item | Lines | Target File |
|---|---|---|
| `FEND`, `FESC`, `TFEND`, `TFESC` | 96–99 | `protocols/crc.py` or `protocols/__init__.py` |
| `kiss_wrap()` | 102–108 | `protocols/kiss.py` or `protocols/csp.py` |
| `_crc16_fn`, `_crc32c_fn`, `crc16()`, `crc32c()` | 131–142 | `protocols/crc.py` |
| `verify_csp_crc32()` | 145–157 | `protocols/csp.py` |
| `try_parse_csp_v1()` | 306–322 | `protocols/csp.py` |
| `AX25Config` | 337–397 | `protocols/ax25.py` |
| `CSPConfig` | 400–451 | `protocols/csp.py` |
| `CommandFrame` | 178–268 | `missions/maveric/wire_format.py` (MAVERIC inner payload layout + CRC-16; not a generic protocol primitive) |
| `_LazyEpochMs`, `_parse_epoch_ms` | 465–513 | `protocols/types.py` or stay in core utils |
| `_TYPE_PARSERS`, `_parse_arg_list` | 516–537 | stays with schema parsing |
| `detect_frame_type()` | 730–736 | `protocols/frame_detect.py` |
| `normalize_frame()` | 739–750 | `protocols/frame_detect.py` |
| `format_arg_value()` | 802–809 | utils or stays with schema |
| `_CLEAN_TABLE`, `clean_text()` | 812–820 | utils |

**MAVERIC Mission (moves to `missions/maveric/`):**

| Item | Lines | Target File |
|---|---|---|
| `NODE_NAMES`, `NODE_IDS`, `PTYPE_NAMES`, `PTYPE_IDS`, `GS_NODE` | 35–39 | `missions/maveric/wire_format.py` — **wide dependency impact** (see note below) |
| `init_nodes()` | 43–58 | `missions/maveric/wire_format.py` |
| `node_name()`, `ptype_name()`, `node_label()`, `ptype_label()` | 81–84 | `missions/maveric/wire_format.py` — **wide dependency impact** (see note below) |
| `resolve_node()`, `resolve_ptype()` | 85–86 | `missions/maveric/wire_format.py` — **wide dependency impact** (see note below) |
| `_lookup_name()`, `_format_label()`, `_resolve_id()` | 61–79 | `missions/maveric/wire_format.py` |

**Dependency note:** `node_name`, `ptype_name`, `resolve_node`, `resolve_ptype` and the global lookup tables are currently used as shared labeling helpers across `logging.py`, `tui_common.py`, `tui_rx.py`, `tui_tx.py`, `web_runtime/services.py`, `web_runtime/api.py`, and `web_runtime/tx.py`. Moving these to mission-local code will require either compatibility re-exports from `protocol.py` during migration or an adapter-provided labeling interface that the platform calls instead. The dependency surface is large enough that this should be planned explicitly, not treated as a simple file move.
| `build_cmd_raw()`, `build_kiss_cmd()` | 271–284 | `missions/maveric/wire_format.py` |
| `try_parse_command()` | 287–295 | `missions/maveric/wire_format.py` |
| `load_command_defs()` | 540–607 | `missions/maveric/wire_format.py` |
| `apply_schema()` | 610–679 | `missions/maveric/wire_format.py` |
| `validate_args()` | 682–720 | `missions/maveric/wire_format.py` |
| `parse_cmd_line()` | 760–795 | `missions/maveric/wire_format.py` |

### `config.py`

**Platform Core:**

All loading/merge/sync infrastructure: `_deep_merge`, `load_gss_config`, `resolve_project_path`, `get_command_defs_path`, `get_decoder_yml_path`, `get_generated_commands_dir`, `save_gss_config`, `_apply_map`, `_sync_to_cfg`, `apply_ax25`, `apply_csp`, `update_cfg_from_state`, `ax25_handle_msg`, `csp_handle_msg`.

**MAVERIC Mission:**

| Item | Description |
|---|---|
| `_DEFAULTS` | Contains MAVERIC-specific values: node IDs/names, callsigns WM2XBB/WS9XSW, CSP defaults, mission name "MAVERIC", frequency "437.6 MHz" |
| `_AX25_MAP` | AX.25 config-to-object mapping — structurally generic, values come from config not hardcoded MAVERIC constants. Stays in core. |
| `_CSP_MAP` | CSP config-to-object mapping — structurally generic, values come from config not hardcoded MAVERIC constants. Stays in core. |

**Migration path:** Extract `_DEFAULTS` content into `missions/maveric/mission.yml`. The mapping tables (`_AX25_MAP`, `_CSP_MAP`) are structurally generic — the values come from config, not hardcoded MAVERIC constants. They can stay in core; the mission-specific part is only the default values.

**Design note:** The split is bigger than just `_DEFAULTS`. The current config schema itself mixes platform settings (ZMQ addresses, log paths, general runtime), mission metadata (mission name, node definitions, packet types), and protocol defaults (AX.25 callsigns, CSP routing, frequencies) into one flat structure. A future phase will need to define which config keys are platform-owned vs mission-provided, and how mission config merges into the platform config at load time. This does not block Phase 3 or 4, but should not be forgotten.

### `mission_adapter.py`

**Platform Core:**

| Item | Description |
|---|---|
| `ParsedPacket` dataclass | Generic normalized parse result — any mission adapter returns this |
| `detect_frame_type()` | Delegates to `protocol.detect_frame_type` (generic) |
| `normalize_frame()` | Delegates to `protocol.normalize_frame` (generic) |
| Class structure of `MavericMissionAdapter` | Will become the `MissionAdapter` Protocol definition |

**MAVERIC Mission:**

| Item | Description |
|---|---|
| `parse_packet()` | MAVERIC CSP + command parsing + schema application |
| `parse_command()` | Backward-compat MAVERIC wrapper |
| `verify_crc()` | MAVERIC CRC validation |
| `duplicate_fingerprint()` | MAVERIC-specific fingerprint (crc + csp_crc32) |
| `is_uplink_echo()` | Checks src == GS_NODE (MAVERIC constant) |
| `build_raw_command()` | MAVERIC command wire format building |
| `validate_tx_args()` | MAVERIC schema validation |

**Migration path:** `ParsedPacket` + a formal `MissionAdapter` Protocol stay in core. `MavericMissionAdapter` moves to `missions/maveric/adapter.py`.

### `parsing.py`

**Platform Core (most of it):**

`Packet` dataclass (pipeline record), `RxPipeline` class (orchestration, duplicate detection framework, rate tracking, counters).

**MAVERIC Mission (embedded in core structures):**

| Item | Description |
|---|---|
| `Packet.cmd` / `Packet.cmd_tail` | Assumes MAVERIC command structure |
| `Packet.is_uplink_echo` | Assumes MAVERIC GS_NODE echo semantics |
| `RxPipeline.uplink_echo_count` | Counter for MAVERIC echo classification |
| `build_rx_log_record()` cmd dict handling | Assumes MAVERIC cmd field names |

**Transitional status:** The current `Packet` dataclass and `build_rx_log_record()` are centered on MAVERIC command semantics — fields like `cmd`, `cmd_tail`, `is_uplink_echo`, and the log record's cmd dict extraction all reflect MAVERIC's specific payload model. Short-term, these can remain as optional fields that missions populate via the adapter. But they should be treated as **transitional compatibility fields**, not as the likely final generic model. The platform's eventual packet record should carry mission-opaque semantic data (via adapter-provided rendering payloads) rather than baking in any one mission's field names.

### `logging.py`

**Platform Core:**

`_BaseLog` class — all file I/O, background writer thread, session lifecycle, JSONL writing, generic text formatting (`_separator`, `_field`, `_hex_lines`, `_format_csp`, `_write_summary_block`), session management (`new_session`, `rename`, `close`).

**MAVERIC Mission:**

| Item | Description |
|---|---|
| `_route_line()` | Uses `node_label()` / `ptype_label()` from MAVERIC protocol |
| `SessionLog` (entire class) | RX logging with MAVERIC packet fields (cmd, args, is_uplink_echo, unknown_num) |
| `TXLog` (entire class) | TX logging with MAVERIC command fields (src/dest/echo/ptype, uplink_mode) |

**Migration path:** `_BaseLog` stays in platform core. `SessionLog` and `TXLog` either:
- Move to `missions/maveric/` and use `_BaseLog` as their parent, or
- Stay in core but accept mission-provided formatting callbacks instead of hardcoding MAVERIC fields.

The second approach is cleaner for v1 — the logging infrastructure calls an adapter method like `format_rx_log_entry(pkt)` instead of directly reading MAVERIC fields. This avoids splitting the file while still decoupling. **Adapter-provided formatting callbacks are the preferred direction** unless proven too awkward during Phase 4 implementation.

**Assessment:** Logging does NOT block Phase 3 or Phase 4. The coupling is in the subclass formatting, not in the base infrastructure. Phase 4 can defer the full split.

### `imaging.py`

**Classification: MAVERIC Mission (entire module)**

Image chunk reassembly for MAVERIC's `img_get_chunk` command. While the `ImageAssembler` class is generically written, image reassembly is a mission-specific feature — other missions may not have image downlink at all.

**Migration path:** Moves to `missions/maveric/imaging.py`. No changes needed — the module has no imports from other mission-specific code.

### TUI Modules

**`tui_common.py` — Mixed:**

| Category | Items |
|---|---|
| Platform Core | Style constants, `title_style/fill`, status durations, datetime formats, `compute_col_widths`, `build_header`, `lr_line`, `flash_phase`, `scrollbar_styles`, `append_wrapped_args`, `ScrollableWidget`, `MavAppBase`, `Hints`, `HelpScreen`, `ConfirmScreen`, `StatusMessage` |
| MAVERIC Mission | `_FRAME_COLORS`, `_PTYPE_COLORS`, `frame_color()`, `ptype_color()`, `node_color()`, `build_col_hdr()`, `build_cmd_columns()`, `dispatch_common()`, `ConfigScreen`, `ImportScreen`, `SplashScreen` |

**`tui_rx.py` — MAVERIC Mission (entire module)**

RX monitor widgets: `RxHeader`, `_FilteredCache`, `PacketList`, `_build_detail_lines`, `PacketDetail`, `rx_config_get_values`, `rx_help_info`. All assume MAVERIC packet structure.

**`tui_tx.py` — MAVERIC Mission (entire module)**

TX dashboard widgets: `TxHeader`, `TxQueue`, `SentHistory`, `TxStatusBar`, config helpers, `build_guard_content`. All assume MAVERIC command structure.

**TUI classification decision:** The TUI is a fallback shell. Its framework pieces (`tui_common.py` core items) are platform-generic. Its content (`tui_rx.py`, `tui_tx.py`, mission-specific `tui_common.py` items) is entirely MAVERIC.

**Migration path:** If TUI remains supported, it needs the same adapter-driven rendering as the web UI. For Phase 4, the minimum viable approach is to leave TUI files where they are but have them import from `missions/maveric/` instead of `protocol.py` directly. **Phase 4 must explicitly decide: align the TUI with the adapter contract, or deprecate it.** That decision should not be deferred past Phase 4.

### `web_runtime/` Modules

**`runtime.py` — MAVERIC items to extract:**

| Item | Description |
|---|---|
| `make_cmd()` | Builds queue items with MAVERIC src/dest/echo/ptype/cmd/args fields |
| `validate_cmd_item()` | Validates against MAVERIC schema and uplink framing |
| `sanitize_queue_items()` | Uses `validate_cmd_item()` |

**`state.py` — MAVERIC coupling:**

`WebRuntime.__init__()` directly instantiates `MavericMissionAdapter`. Migration: make the adapter a parameter (injected from mission config).

**`services.py` — MAVERIC items to extract:**

| Item | Description |
|---|---|
| `RxService.packet_to_json()` | Maps MAVERIC cmd fields to JSON (src/dest/echo/ptype/cmd/args) |
| `TxService.json_to_item()` | Deserializes MAVERIC command items |
| `TxService.match_tx_args()` | MAVERIC schema argument matching |
| `TxService.tx_extra_args()` | MAVERIC schema overflow args |
| `TxService.queue_items_json()` | Projects MAVERIC node/ptype names |
| `TxService.run_send()` | MAVERIC-specific log fields and history entry construction |

**`api.py` — MAVERIC items to extract:**

| Item | Description |
|---|---|
| `api_status()` | Returns MAVERIC mission name, command defs metadata — see design note below |
| `api_schema()` | Returns MAVERIC command definitions — see design note below |
| `parse_import_file()` | Parses import files using `make_cmd()` (MAVERIC fields) |
| `preview_import()` / `import_file()` | Use `parse_import_file()` |
| `api_log_entries()` | Normalizes log records with MAVERIC field names |

**`tx.py` — MAVERIC items:**

`ws_tx()` actions `"queue"` and `"queue_built"` parse MAVERIC command lines and resolve MAVERIC node/ptype names.

**Design note on `api_status()` and `/api/schema`:** These endpoints currently assume command-schema-centric semantics — the platform exposes a command definitions dict and the UI builds around it. For the new platform direction, the replacement is not just "adapter-provided schema." It is more likely a mission metadata/capabilities interface (mission name, supported modes, node labels, packet type labels) plus optional command schema support for missions that have it. Not all missions will express TX through a command schema at all.

## Logic That Must Move Out of Core

Ordered by migration phase dependency:

### Phase 3 (Protocol Split)

From `protocol.py`, extract to `protocols/`:
- `crc.py`: CRC-16, CRC-32C functions
- `csp.py`: `try_parse_csp_v1`, `verify_csp_crc32`, `CSPConfig`, KISS wrapping
- `ax25.py`: `AX25Config` (merge with existing `ax25.py` encoder)
- `frame_detect.py`: `detect_frame_type`, `normalize_frame`

Existing standalone modules move as-is:
- `ax25.py` → `protocols/ax25.py`
- `golay.py` → `protocols/golay.py`

`CommandFrame` moves to `missions/maveric/wire_format.py` in Phase 4. It encodes MAVERIC's specific inner command payload layout plus CRC-16 — not a generic protocol-family primitive.

### Phase 4 (MAVERIC Mission Package)

From `protocol.py`, extract to `missions/maveric/wire_format.py`:
- Node/ptype tables and lookup functions
- `init_nodes()`, `GS_NODE`
- `build_cmd_raw()`, `build_kiss_cmd()`, `try_parse_command()`
- `load_command_defs()`, `apply_schema()`, `validate_args()`, `parse_cmd_line()`

From `config.py`, extract to `missions/maveric/mission.yml`:
- `_DEFAULTS` MAVERIC-specific values (node names, callsigns, frequencies)

From `mission_adapter.py`:
- `MavericMissionAdapter` implementation → `missions/maveric/adapter.py`
- `ParsedPacket` + formal `MissionAdapter` Protocol remain in core

From `logging.py`:
- `SessionLog` and `TXLog` formatting logic needs adapter indirection (not necessarily a file move)

Move entirely to `missions/maveric/`:
- `imaging.py`

### Phase 5 (UI Rendering Slots)

From `web_runtime/services.py`:
- `packet_to_json()` field mapping must come from adapter
- `queue_items_json()` node/ptype name resolution must come from adapter

From `web_runtime/api.py`:
- `api_log_entries()` normalization must use adapter
- `api_status()` mission name/schema must come from mission config

From `web_runtime/tx.py`:
- `"queue"` / `"queue_built"` actions must delegate command parsing to adapter

From `web_runtime/runtime.py`:
- `make_cmd()` must use adapter for field construction
- `validate_cmd_item()` must delegate to adapter

## Modules Ready As-Is (No Changes Needed)

| Module | Layer | Notes |
|---|---|---|
| `transport.py` | Transport | Zero mission code |
| `ax25.py` | Protocol Support | Move to `protocols/`, no content changes |
| `golay.py` | Protocol Support | Move to `protocols/`, no content changes |
| `web_runtime/app.py` | Runtime | Zero mission code |
| `web_runtime/security.py` | Runtime | Zero mission code |
| `web_runtime/rx.py` | Runtime | Zero mission code |

## Phase 3 Readiness Assessment

Phase 3 (protocol split) can begin immediately. The work is:

1. Create `protocols/` package
2. Move CRC functions → `protocols/crc.py`
3. Move CSP functions + `CSPConfig` + KISS → `protocols/csp.py`
4. Move `AX25Config` into existing `ax25.py`, move to `protocols/ax25.py`
5. Move `detect_frame_type` + `normalize_frame` → `protocols/frame_detect.py`
6. Move `golay.py` → `protocols/golay.py`
7. Leave `protocol.py` as compatibility facade with re-exports
8. Update all imports across codebase
9. Run test suite

No MAVERIC behavior changes. No mission-layer work. Mechanical refactor with a few design decisions to resolve first.

**Open decisions before Phase 3 starts:**

1. **Where does KISS belong?** `kiss_wrap()` is used by CSP wrapping. It could live in `protocols/csp.py` (since KISS is the CSP transport framing) or in its own `protocols/kiss.py` (if other protocol families might use KISS independently). Recommend `protocols/csp.py` for v1 since KISS is only used in the CSP path today.

2. **Does `AX25Config` merge with `ax25.py`?** The existing `ax25.py` is a standalone encoder (HDLC + G3RUH + NRZI). `AX25Config` in `protocol.py` is a higher-level TX framing wrapper. They serve different purposes but both live in the AX.25 protocol family. Recommend merging into one `protocols/ax25.py` since they are complementary (config + encoder), but the merge should be reviewed.

3. **`CommandFrame` stays out of `protocols/`.** It is MAVERIC's inner payload format, not a protocol-family primitive. It remains in `protocol.py` during Phase 3 and moves to `missions/maveric/wire_format.py` in Phase 4.
