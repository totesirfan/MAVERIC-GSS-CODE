# Mission-Decoupled Ground Station Platform Spec

## 1. Purpose

This platform shall support multiple CubeSat missions without embedding one mission's packet semantics, command model, or workflow assumptions into platform core.

The platform shall provide:

- runtime and transport infrastructure
- reusable protocol and integrity utilities
- generic RX/TX/replay/logging UI infrastructure
- mission loading
- generic queueing and byte transmission

Each mission package shall provide:

- mission-specific framing composition
- mission-specific packet semantics
- mission-specific command semantics
- mission-specific operator presentation data

This spec assumes mission packages live under `mav_gss_lib/missions/<mission_name>/`.

## 1.1 Current State

This document is not a greenfield design. The codebase already implements a substantial part of this architecture.

Already true in the current codebase:

- convention-based mission loading exists
- a reusable protocol toolkit already exists for common mechanisms
- RX packet rendering is primarily driven by `_rendering`
- the mission adapter boundary already exists
- the MAVERIC adapter already implements RX rendering hooks
- platform auth/runtime naming has largely been neutralized

The remaining work is concentrated in:

- finishing replay/RX cleanup
- redesigning TX around an optional mission plugin model
- migrating queue/history away from MAVERIC-shaped command fields
- removing transitional parsed-packet semantics
- tightening config and replay contracts

## 2. Core Design Rule

The platform owns reusable mechanics.

The mission owns meaning.

Examples:

- CRC algorithm support belongs in platform.
- "This CRC applies to the command body and failing it means packet invalid" belongs in mission.
- AX.25 encode/decode belongs in platform.
- "This AX.25 payload contains CSP for this spacecraft" belongs in mission.
- Generic queue execution belongs in platform.
- "This mission has a reboot command with these fields" belongs in mission.

## 3. Non-Goals

This spec does not require:

- a plugin marketplace
- arbitrary external mission loading
- a universal telemetry ontology
- a workflow DSL
- arbitrary mission-injected frontend code in Phase 1

## 4. Platform Responsibilities

The platform shall own:

- mission loading and validation
- transport interfaces such as ZMQ ingress/egress
- raw frame receive/send plumbing
- session logging and replay storage
- generic RX list/detail containers
- generic TX queue/history containers
- generic form rendering for mission-defined command inputs
- raw transmit support
- auth, config, persistence, and runtime lifecycle
- reusable protocol libraries
- reusable integrity libraries

## 5. Mission Responsibilities

The mission package shall own:

- how wrappers are composed
- how packets are parsed semantically
- how commands are defined semantically
- how operator input maps to encoded bytes
- how parsed packets are rendered for operators
- how queued and sent commands are rendered for operators
- mission labels, node naming, packet-type naming, and workflow wording
- mission-specific replay semantics

## 6. Platform Protocol Toolkit

Reusable mechanisms that may be used by any mission shall live in platform support modules.

Suggested modules:

- `mav_gss_lib/protocols/crc.py`
- `mav_gss_lib/protocols/ax25.py`
- `mav_gss_lib/protocols/csp.py`
- `mav_gss_lib/protocols/golay.py`
- `mav_gss_lib/protocols/frame_detect.py`

These modules shall expose reusable primitives such as:

- encode/build
- decode/parse
- check/validate
- helper serializers/deserializers

Examples:

```python
crc16_compute(data: bytes) -> int
crc16_check(data: bytes, expected: int) -> bool

ax25_encode(payload: bytes, ...) -> bytes
ax25_decode(frame: bytes) -> tuple[dict, bytes]

csp_build_header(...) -> bytes
csp_parse_header(data: bytes) -> tuple[dict, bytes]

golay_encode(data: bytes) -> bytes
golay_decode(data: bytes) -> bytes
```

The platform shall not assume:

- a protocol is always present
- a protocol appears only once
- a protocol has fixed semantic meaning across missions

## 7. Protocol And Integrity Representation

The platform shall support arbitrary protocol layers and arbitrary integrity checks per packet.

It must not hardcode assumptions like:

- one CRC16 per packet
- one CRC32 per packet
- one CSP header per packet

Instead, mission adapters shall provide protocol and integrity records as lists.

See the `ProtocolBlock` and `IntegrityBlock` dataclasses in `mav_gss_lib/mission_adapter.py` for the canonical typed contract used by the current implementation.

Example protocol block:

```python
{
  "kind": "csp",
  "label": "CSP",
  "fields": [
    {"name": "Src", "value": "OBC"},
    {"name": "Dest", "value": "EPS"},
  ],
}
```

Example integrity block:

```python
{
  "kind": "crc32",
  "label": "CRC-32",
  "scope": "payload",
  "ok": True,
  "received": "0x12345678",
  "computed": "0x12345678",
}
```

This allows:

- multiple CRCs per packet
- the same integrity type multiple times
- nested wrapper stacks
- no wrappers at all

## 8. Core Packet Contract

The platform RX packet model shall contain only platform-owned envelope data plus mission-rendered presentation data.

Example:

```ts
interface RxPacket {
  num: number
  time: string
  time_utc: string
  frame: string
  size: number
  raw_hex: string
  warnings: string[]
  is_echo: boolean
  is_dup: boolean
  is_unknown: boolean
  _rendering: RenderingData
}
```

The frontend shall not depend on fields like:

- `cmd`
- `src`
- `dest`
- `echo`
- `ptype`
- `csp_header`
- `crc16_ok`
- `crc32_ok`

unless they are encoded inside mission-provided rendering structures.

In the current implementation, this RX contract is largely already in place. Remaining work is mostly replay-path cleanup and removal of compatibility fallbacks.

## 9. Parsed Packet Contract

The backend parse result shall be mission-opaque and composable.

Illustrative end-state example:

```python
@dataclass
class ParsedPacket:
    mission_data: dict
    protocol_data: list[dict] = field(default_factory=list)
    integrity_data: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_unknown: bool = False
    is_echo: bool = False
    duplicate_key: tuple | None = None
```

Current implementation note:

The current `ParsedPacket` already exists, but still carries transitional MAVERIC-shaped fields. This section describes the intended end-state after those compatibility fields are removed.

Clarification:

This example does not require Phase 7 to collapse all mission semantics into a single `mission_data` dict if a better typed or structured end-state emerges. The requirement is mission opacity at the platform boundary, not one exact internal container shape.

The platform shall remove transitional mission-shaped fields such as:

- `csp`
- `cmd`
- `cmd_tail`
- `ts_result`

once compatibility is no longer needed.

## 10. RX Rendering Contract

Mission adapters shall provide complete operator rendering for RX.

Required outputs:

- packet list columns
- packet list row values
- detail blocks
- protocol blocks
- integrity blocks

Current adapter contract:

```python
def packet_list_columns(self) -> list[dict]: ...
def packet_list_row(self, pkt: ParsedPacket) -> dict: ...
def packet_detail_blocks(self, pkt: ParsedPacket) -> list[dict]: ...
def protocol_blocks(self, pkt: ParsedPacket) -> list[dict]: ...
def integrity_blocks(self, pkt: ParsedPacket) -> list[dict]: ...
```

The platform UI shall only render these generic structures.

Current implementation note:

This RX rendering contract is already implemented in practice by the MAVERIC mission adapter, though replay and a few operator convenience paths still need cleanup.

## 11. TX Model

The platform shall support two TX layers:

### 11.1 Platform TX Core

The platform shall provide:

- raw byte send
- queueing
- guard confirmations
- send scheduling
- TX history storage
- generic queue/history UI containers

### 11.2 Optional Mission TX Plugin

A mission may provide command-building support.

If a mission does not provide it:

- the command-builder UI shall be hidden
- raw transmit shall still work

This avoids forcing all missions into one fixed command model.

Current implementation note:

The current codebase does not yet implement this optional TX plugin model. TX still uses a platform-shaped command path with mission participation via existing adapter methods. Sections 12-13 describe the intended future direction, not the current implementation.

## 12. Mission TX Plugin Contract

Mission command-building shall be data-driven by default.

Future mission adapter extensions may expose:

```python
def tx_capabilities(self) -> dict: ...
def command_templates(self) -> list[dict]: ...
def validate_command(self, template_id: str, values: dict) -> tuple[bool, list[str]]: ...
def build_command(self, template_id: str, values: dict) -> bytes: ...
def render_queued_command(self, template_id: str, values: dict, raw: bytes) -> dict: ...
def render_history_command(self, record: dict) -> dict: ...
```

Example capability response:

```python
{
  "raw_send": True,
  "command_builder": True,
}
```

Current implementation note:

Today the adapter exposes TX-oriented methods such as:

- `build_raw_command()`
- `validate_tx_args()`
- `parse_cmd_line()`

The plugin-style TX contract in this section is planned future work for Phases 3-5.

Example template:

```python
{
  "id": "reboot",
  "label": "Reboot",
  "category": "OBC",
  "guard": True,
  "fields": [
    {"id": "target", "label": "Target", "type": "select", "required": True, "options": [...]},
    {"id": "mode", "label": "Mode", "type": "select", "required": True, "options": [...]},
  ],
}
```

## 13. TX Queue And History Contract

Queue and history shall store:

- mission template identity
- mission input values
- encoded raw bytes
- display metadata

They shall not require platform-standard fields like:

- `src`
- `dest`
- `echo`
- `ptype`
- `cmd`
- `args`

Example:

```ts
interface QueuedMissionCommand {
  type: 'mission_cmd'
  num: number
  template_id: string
  values: Record<string, string | number | boolean>
  raw_hex: string
  size: number
  display: {
    title: string
    subtitle?: string
    fields: { name: string; value: string }[]
    guard?: boolean
  }
}
```

This allows future missions to define different command semantics without changing platform code.

Clarification:

This section does not mean missions may never use routing fields such as `src`, `dest`, `echo`, or `ptype`. It means the platform must not require those fields as universal queue/history primitives. A mission may still include such routing information inside mission-owned values and display metadata.

## 14. Replay Contract

Replay shall be mission-rendered.

Replay entries shall be displayable from one of:

- stored rendering payload
- stored mission semantic record plus adapter replay renderer

The mission adapter currently exposes required logging hooks:

```python
def build_log_mission_data(self, pkt: ParsedPacket) -> dict: ...
def format_log_lines(self, pkt: ParsedPacket) -> list[str]: ...
```

These are part of the current required adapter protocol, not optional.

The platform shall not reconstruct replay semantics from legacy flat fields in the long-term end state.

Current implementation note:

The current log writer stores `protocol_blocks`, `integrity_blocks`, and mission data in the JSONL record, but does not persist the full `_rendering` payload (notably `detail_blocks` and `row`). The replay path in `api.py` still reconstructs detail rendering from flat semantic fields in the log entry. This means replay is not yet rendering-payload-driven — it still depends on legacy flat field reconstruction for detail and row display. Phase 1 addresses this by adding a temporary adapter-based reconstruction fallback plus a migration tool to backfill full `_rendering` into legacy logs, converging replay to pure passthrough.

## 15. Logging Contract

The log format shall contain:

- platform envelope
- timestamps
- raw data or hex
- warnings and flags
- mission record and/or rendering payload

Logs should preserve enough data to:

- replay visually
- inspect mission semantics later
- avoid platform-specific semantic reconstruction hacks

## 16. Mission Loading Contract

Every mission package shall expose:

- `ADAPTER_API_VERSION`
- `ADAPTER_CLASS`
- `init_mission(cfg) -> dict`

The platform shall load missions by convention from:

- `mav_gss_lib.missions.<mission_name>`

Future expansion to external modules may be added later, but is not required by this spec.

### 16.1 Adapter API Versioning Policy

- `ADAPTER_API_VERSION` shall be incremented on breaking adapter interface changes.
- The platform shall validate the declared adapter API version at startup.
- Unknown adapter API versions shall be rejected with a clear startup error.
- Backward-compatible additive changes should prefer optional methods or clearly versioned rollout phases rather than silent contract drift.

## 17. Generic UI Principle

The platform UI shall render:

- generic rows
- generic blocks
- generic forms
- generic queue/history cards

Mission packages should provide structured data, not arbitrary frontend code, in the default design.

Custom mission UI injection should be deferred until a real mission requires it.

## 17.1 Error Handling Policy

The platform should degrade gracefully when mission adapter behavior fails.

Expected behavior:

- startup-time adapter contract/version failures should fail fast with explicit errors
- per-packet parse/render failures should preserve raw packet visibility when possible
- UI surfaces should prefer warning/error states over blank or misleading semantic data
- replay and log inspection should remain possible even when mission semantic rendering is incomplete

## 18. Migration Phases

### Phase 1: Finish RX Decouple

- remove remaining frontend dependence on mission-shaped packet fields
- ensure replay and live RX both render from mission-provided structures
- eliminate replay/operator actions that assume live-only row data

Status:

- mostly complete
- remaining work is concentrated in replay/operator cleanup and compatibility removal

### Phase 2: Introduce Platform Protocol Toolkit

- move reusable CRC, AX.25, CSP, Golay, and framing helpers into explicit platform modules
- have mission adapters compose these utilities instead of carrying ad hoc copies or mission-bound assumptions

Status:

- largely complete
- remaining work is mostly cleanup, normalization, and clearer documentation of supported primitives

### Phase 3: Introduce Optional Mission TX Plugin Contract

- add `tx_capabilities`, `command_templates`, validation, encode, and render hooks
- implement generic frontend form renderer for mission-defined commands
- keep raw TX available regardless of mission plugin presence

Status:

- not yet implemented
- this is the main architectural frontier

Open design questions to resolve during implementation:

- whether `command_templates()` is purely static or may be computed dynamically from mission/runtime context
- how validation should be split between frontend affordances and backend authority
- which field types the generic form renderer must support in the first usable version

### Phase 4: Migrate MAVERIC TX To Mission Plugin

- make MAVERIC command building use the new optional mission TX contract
- preserve current operator behavior
- prove the abstraction with one real mission

Status:

- not yet started

### Phase 5: Migrate Queue And History

- replace platform-owned command semantics with mission-owned display/data records
- update import/export/history UI accordingly

Status:

- complete
- all queue items are now mission_cmd type
- raw CLI routes through cmd_line_to_payload → build_tx_command
- explicit source-node CLI semantics preserved via payload.src
- legacy cmd items migrated on queue restore and import
- frontend renders from CmdDisplay without interpreting field semantics
- dedicated dest/ptype columns dropped from queue UI
- duplicate/requeue faithfully re-submit original payload via queueTemplate
- guard confirm renders from opaque CmdDisplay

### Phase 6: Migrate Replay And Logs

- replay from mission records or stored rendering
- remove legacy flat semantic replay reconstruction

Status:

- complete
- RX logs persist _rendering and pass through directly
- TX logs persist display with row + detail_blocks
- TX log-view consumes entry.display directly, no flat-field reconstruction
- log cmd filter unified to _rendering.row.values.cmd for both RX and TX
- old TX logs migrated via scripts/migrate_tx_logs.py
- LogViewer uses TX columns for TX sessions, RX columns for RX sessions
- ReplayPanel works with rendering-backed entries

### Phase 7: Remove Transitional Parsed Fields

- remove `csp`, `cmd`, `cmd_tail`, `ts_result`
- convert platform internals to fully mission-opaque parse records

Status:

- complete
- ParsedPacket is mission-opaque: only mission_data + warnings
- Packet carries mission_data as opaque passthrough
- MAVERIC adapter reads/writes mission_data internally via _md() helper
- platform never accesses mission-specific parse fields
- transitional csp/cmd/cmd_tail/ts_result/crc_status/csp_plausible removed
- RxPipeline.process() passes mission_data through without unpacking
- all 133 tests updated and passing

### Phase 8: Config Boundary Cleanup

- retain runtime settings in platform config
- move mission defaults and mission semantics into mission metadata/config

Status:

- complete
- mission placeholders removed from platform _DEFAULTS
- mission keys populated exclusively by load_mission_metadata()
- apply_ax25/apply_csp guarded against missing sections
- config ownership documented in CLAUDE.md
- platform defaults contain only platform-owned keys

## 19. Acceptance Criteria

The platform is fully decoupled when:

- a new mission can be added under `mav_gss_lib/missions/<name>/` without platform core edits
- the platform provides reusable protocol support but does not assign mission meaning to protocol fields
- RX is rendered entirely from mission-provided structures
- command building is optional and mission-provided
- queue/history do not require MAVERIC-shaped command fields
- replay does not depend on legacy flat semantic fields
- `ParsedPacket` is mission-opaque
- MAVERIC is only one mission package using the platform

## 19.1 Ownership Clarification For Derived Flags

Fields such as:

- `is_echo`
- `is_dup`
- `is_unknown`
- duplicate fingerprints

should be treated as mission-derived but platform-consumed.

That is:

- the mission adapter determines how they are computed
- the platform may use them for generic UI/logging behavior

They are not universal protocol truths owned purely by the platform.

## 20. What Not To Build Yet

Do not build:

- a plugin marketplace
- external package discovery
- dynamic arbitrary UI injection
- a universal packet ontology
- a workflow scripting engine

## 21. Guiding Principle For Future Work

If something is reusable across missions, put it in platform support.

If something explains what data means for one mission, keep it in the mission package.

## 22. Conformance Expectations

Any mission adapter intended for platform use should be covered by a lightweight conformance test set.

At minimum, the conformance expectations should verify:

- mission package exports the required symbols
- adapter API version is supported
- adapter initialization succeeds with valid config
- RX rendering methods return structurally valid data
- parse and render paths do not throw on valid mission packets
- TX plugin hooks, if implemented, validate and build deterministically for valid inputs
- replay/log data can be rendered without requiring legacy flat semantic fields
