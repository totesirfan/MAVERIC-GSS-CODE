# Mission-Agnostic Ground Station Platform Spec

This document is the implementation spec for evolving this repository from a MAVERIC-first ground station into a mission-agnostic CubeSat ground station platform.

It is written for:

- future SERC teams adapting the software for new missions
- maintainers keeping the platform healthy over time
- AI editors making architectural changes

This is not a maintainer handoff guide. It is the platform design and migration reference.

## Platform Goal

The target is a CubeSat-focused ground station platform with these properties:

- GNU Radio / gr-satellites transport remains supported
- common CubeSat protocol families are supported in core
- the overall UI shell remains consistent across missions
- the overall workflow remains consistent across missions
- missions provide their own parsing and command semantics
- MAVERIC remains the default built-in mission during migration
- one mission is active at a time for now

This is not a universal mission-control framework. It is a practical CubeSat platform for SERC-style missions.

## Spec Status

This document is intended to be the implementation reference used during migration.

That means the codebase inventory and interface definitions here must stay current enough to guide real refactors. Phase 2 is therefore a required maintenance step for this document, not a purely optional discovery exercise.

## Platform Decisions

These decisions are fixed for version 1 of the platform.

### 1. Scope

The platform is CubeSat-focused for now.

It should be possible to support more later, but version 1 should optimize for:

- AX.25
- ASM+Golay
- CSP
- CRC-based integrity checks
- GNU Radio / gr-satellites style transport integration

### 2. Active Mission Model

Only one mission is active at a time.

Multi-mission runtime support is explicitly out of scope for now.

### 3. Workflow

The platform owns and enforces the operator workflow.

For now that includes:

- RX monitoring
- packet list and packet detail views
- TX queueing
- delays
- guard confirmations
- logging and replay

Missions do not redefine the workflow in version 1.

### 4. UI

The platform owns and enforces the UI shell.

Missions do not ship custom frontend modules in version 1.

What missions do control:

- packet list column headers
- packet list row content
- semantic packet detail content

What the platform keeps stable:

- overall layout
- protocol/wrapper section
- integrity section
- raw/hex section
- TX workflow shell
- logs/replay shell

### 5. Parsing And Commands

The platform does not standardize mission parsing or mission command semantics.

This is deliberate.

Reason:

- MAVERIC and previous SERC missions already differ in internal command structure
- similar wrappers do not imply similar payload semantics
- standardizing mission semantics too early would make the platform MAVERIC-shaped

Therefore:

- missions provide exact parsing
- missions provide exact command syntax/meaning
- core only supports common outer protocols and rendering shells

### 6. MAVERIC Status

MAVERIC remains the default built-in mission implementation during migration.

The platform should be designed so MAVERIC is one mission implementation, not the platform itself.

### 7. Mission Selection

Version 1 uses one active mission selected from runtime config.

The intended selection mechanism is:

- `general.mission` in the active config

If absent during migration, MAVERIC remains the implicit default.

## Core Architectural Principle

The platform should strongly standardize:

- transport
- supported protocol-family support
- protocol presentation
- integrity presentation
- workflow shell
- UI shell
- mission integration interfaces

The platform should not strongly standardize:

- mission packet semantics
- mission command grammar
- mission-specific routing semantics
- mission-specific display semantics

In plain terms:

- platform owns wrappers, transport, workflow, and shell
- missions own packet meaning

## Layering Model

The platform is split into five conceptual layers.

### 1. Transport Layer

Owns:

- ZMQ sockets
- PMT serialization/deserialization
- transport status monitoring
- raw send and receive

Must not own:

- packet semantics
- AX.25 meaning
- CSP meaning
- mission parsing

### 2. Protocol Support Layer

Owns reusable support for common protocol families.

Version 1 target support:

- AX.25
- ASM+Golay
- CSP
- CRC helpers

This layer owns:

- wrapping and unwrapping
- header extraction
- protocol detail generation
- protocol-layer integrity checks

This layer must not own:

- MAVERIC command semantics
- any mission-specific command model
- mission-specific duplicate heuristics

### 3. Mission Layer

Owns:

- exact mission parsing
- exact command build/validation
- mission-specific heuristics
- mission-specific packet list content
- mission-specific packet detail content

This layer may use protocol support helpers, but it owns payload meaning.

### 4. Runtime Layer

Owns:

- orchestration
- counters
- queue control
- persistence
- logging
- replay
- API/websocket projection

The runtime should coordinate flow, not interpret packet meaning.

### 5. UI Layer

Owns:

- fixed shell
- packet list shell
- packet detail shell
- TX workflow shell
- logs/replay shell
- protocol section rendering
- integrity section rendering
- raw/hex section rendering

The UI should render mission-provided semantic content inside fixed slots.

## What Is Standardized In Core

The platform standardizes four kinds of things.

### 1. Transport Interface

Transport returns raw bytes plus metadata.

Example:

```python
@dataclass
class RawFrame:
    meta: dict
    raw: bytes
    received_at: float
```

This is raw only.

Version 1 metadata guarantees are intentionally minimal:

- `received_at` is always platform-provided
- transport metadata is passed through from the underlying source

The platform should not promise a mission-specific metadata schema here.

Later phases may document a "known transport metadata keys" subset once the platform has enough real mission coverage to justify standardizing it.

### 2. Protocol Block Contract

The platform standardizes how wrapper/protocol information is represented and rendered.

This is used in the packet detail protocol section.

Example:

```python
@dataclass
class ProtocolField:
    name: str
    value: str


@dataclass
class ProtocolBlock:
    kind: str
    label: str
    fields: list[ProtocolField]
```

Examples:

- AX.25 header block
- CSP header block
- other wrapper blocks later

The platform owns how these are rendered.

Illustrative JSON shape:

```json
{
  "kind": "csp",
  "label": "CSP V1",
  "fields": [
    {"name": "Src", "value": "2"},
    {"name": "Dest", "value": "6"}
  ]
}
```

### 3. Integrity Block Contract

The platform standardizes how integrity checks are represented and rendered.

This is used in the packet detail integrity section.

Example:

```python
@dataclass
class IntegrityBlock:
    kind: str
    label: str
    scope: str
    ok: bool | None
    received: str | None = None
    computed: str | None = None
```

Examples:

- CSP CRC-32C
- mission payload CRC-16

The platform owns how these are rendered.

Illustrative JSON shape:

```json
{
  "kind": "crc32c",
  "label": "CRC-32C",
  "scope": "csp",
  "ok": true,
  "received": "0x12345678",
  "computed": "0x12345678"
}
```

### 4. Rendering Slots

The platform standardizes where mission content goes in the UI, not what the content means.

Version 1 rendering slots are:

- packet list columns
- packet list row values
- packet semantic detail area
- protocol section
- integrity section
- raw/hex section
- warnings section

This is the main platform/UI contract.

## What Missions Must Provide

The mission does not need to fit a universal semantic packet schema.

Instead, the mission must provide implementations for the platform rendering slots and command/parsing hooks.

Version 1 mission package should contain:

- `adapter.py`
- `mission.yml`
- `commands.yml`

Optional later:

- telemetry schema files
- capability declarations
- alternate workflow declarations

Not required in version 1.

## Mission Package Contract

### 1. Mission Metadata YAML

`mission.yml` should hold:

- mission name
- node names and descriptions if applicable
- packet type labels if applicable
- titles and UI branding labels
- supported transport/protocol modes
- mission-local paths such as command schema path

This replaces the idea that platform defaults should carry MAVERIC-specific values.

### 2. Command Schema YAML

`commands.yml` should hold whatever command schema the mission uses.

The platform should not assume all missions express commands the same way, but it may provide helpers for missions that do.

### 3. Mission Adapter

The mission adapter is the mission integration point.

It should provide:

- RX parsing
- TX command build/validation
- packet list columns
- packet list row values
- packet semantic detail output
- protocol blocks
- integrity blocks

The adapter may call mission-specific helper modules and reusable protocol-family helpers.

Version 1 mission packages should also expose an adapter contract version marker.

Illustrative example:

```python
ADAPTER_API_VERSION = 1
```

## Adapter Contract

The platform should standardize mission interfaces, not mission semantics.

Version 1 adapter contract should focus on behavior and rendering payloads.

Illustrative target:

```python
class MissionAdapter(Protocol):
    def detect_frame_type(self, meta: dict) -> str: ...
    def normalize_frame(self, frame_type: str, raw: bytes) -> tuple[bytes, str | None, list[str]]: ...

    def parse_rx_packet(self, meta: dict, raw: bytes, inner_payload: bytes, warnings: list[str]) -> dict: ...

    def packet_list_columns(self) -> list[dict]: ...
    def packet_list_row(self, parsed_packet: dict) -> list[str]: ...
    def packet_detail_blocks(self, parsed_packet: dict) -> list[dict]: ...

    def protocol_blocks(self, parsed_packet: dict) -> list[ProtocolBlock]: ...
    def integrity_blocks(self, parsed_packet: dict) -> list[IntegrityBlock]: ...

    def build_tx_command(self, command_input: dict) -> bytes: ...
    def validate_tx_command(self, command_input: dict) -> tuple[bool, list[str]]: ...
```

Notes:

- The exact return types may evolve.
- The important thing is that missions provide data, not UI code.
- Core renders those data structures in a fixed shell.
- The platform should reject mission packages whose declared adapter API version is unsupported.
- The runtime owns adapter error handling. If adapter parse/build logic fails, the runtime should log the failure, surface a warning to operators where appropriate, and avoid crashing the platform shell.

## Packet Detail Model

The packet detail view should be split into two categories:

### Mission-Defined Semantic Area

This is where the mission controls what the packet means.

The mission provides:

- summary text or summary fields
- semantic detail rows or blocks
- mission-specific parsed output

This area may differ substantially between missions.

### Platform-Defined Detail Areas

These sections remain stable across missions:

- warnings
- protocol/wrapper section
- integrity section
- raw/hex section

This is how the UI remains consistent even when packet semantics differ.

## Packet List Model

The packet list shell remains platform-owned.

The mission provides:

- column headers
- row values for each parsed packet

This lets the list adapt to mission semantics without requiring custom UI modules.

The mission should provide data only.

The platform retains:

- list behavior
- selection behavior
- focus behavior
- sorting/filter hooks if those are present
- styling and layout

## No Required Semantic Packet Fields

The platform must not require all missions to emit fields like:

- `src`
- `dest`
- `echo`
- `ptype`
- `cmd`
- `args`

Reason:

- previous SERC missions already differ in internal command styles
- wrapper similarity does not imply semantic similarity

Those fields may still be used by missions that have them, but they are not core platform requirements.

## Nested Integrity Support

The platform must support integrity checks at multiple layers.

Example for MAVERIC:

- CSP CRC-32C at the protocol layer
- CRC-16 embedded in the mission payload

This is why integrity must be rendered through standardized integrity blocks rather than one flat checksum field.

## Target Module Layout

This is the target conceptual layout. It does not need to appear all at once.

```text
mav_gss_lib/
  transport.py
  config.py
  mission_adapter.py

  protocols/
    __init__.py
    ax25.py
    golay.py
    csp.py
    crc.py
    frame_detect.py

  missions/
    __init__.py
    maveric/
      __init__.py
      adapter.py
      mission.yml
      commands.yml
      wire_format.py
      imaging.py

  runtime/
    parsing.py
    logging.py
    tx_runtime.py
    rx_runtime.py

  web_runtime/
    app.py
    runtime.py
    security.py
    state.py
    services.py
    api.py
    rx.py
    tx.py

  tui/
    common.py
    rx.py
    tx.py
```

Notes:

- `protocol.py` in the repo may temporarily remain as a compatibility facade.
- exact file names can vary during migration.
- the important split is core protocol support vs mission implementation.

## Current Repo Mapping

Current main modules:

- `mav_gss_lib/transport.py`
  Already close to platform core.
- `mav_gss_lib/config.py`
  Core configuration loading and runtime settings application.
- `mav_gss_lib/protocol.py`
  Currently mixes reusable protocol-family support with MAVERIC-specific semantics.
- `mav_gss_lib/ax25.py`
  Standalone AX.25 encoder path that should map into protocol-family core support.
- `mav_gss_lib/golay.py`
  Standalone ASM+Golay encoder path that should map into protocol-family core support.
- `mav_gss_lib/mission_adapter.py`
  Current mission seam and likely foundation for the mission package contract.
- `mav_gss_lib/parsing.py`
  RX packet processing pipeline and packet-state tracking.
- `mav_gss_lib/imaging.py`
  Mission-specific image reassembly logic, likely MAVERIC mission-layer code.
- `mav_gss_lib/logging.py`
  Shared logging infrastructure with formatting responsibilities that may need clearer core/mission boundaries later.
- `mav_gss_lib/web_runtime/`
  Platform shell and backend services.
- `mav_gss_lib/web_runtime/app.py`
  App assembly and lifecycle.
- `mav_gss_lib/web_runtime/runtime.py`
  Shared backend runtime helpers.
- `mav_gss_lib/web_runtime/security.py`
  Session-token/origin checks and related security plumbing.
- `mav_gss_lib/web/`
  Platform UI shell.
- `mav_gss_lib/tui_rx.py`, `mav_gss_lib/tui_tx.py`, `mav_gss_lib/tui_common.py`
  Current Textual fallback UI path.

Current main problem:

- core and MAVERIC semantics are still too interleaved
- the UI still assumes more shared semantic structure than the new platform target wants
- some reusable core paths are not yet organized as reusable core modules
- some legacy or fallback paths exist and must be explicitly classified rather than ignored

## TUI Status

Version 1 platform position:

- the web UI is the primary platform shell
- the current Textual path is treated as a fallback/legacy shell
- the TUI must either consume the same platform/mission contracts over time or be explicitly deprecated later

The migration must not leave the TUI status ambiguous.

Expected timing:

- TUI classification happens in Phase 2
- if the TUI remains supported, it must start consuming the same mission/platform contracts in Phase 4 or Phase 5
- otherwise, deprecation must be explicit before platform assumptions diverge further

## Logging Status

Current `logging.py` should be treated as shared infrastructure first.

However, later phases may need to separate:

- platform logging infrastructure
- mission-provided semantic formatting content, if any

Version 1 does not require a full logging split, but this distinction should be kept in mind during refactors.

Expected timing:

- logging classification happens in Phase 2
- if mission-specific formatting is found to block platform migration, logging split work must be pulled into Phase 4 rather than deferred

## Migration Phases

Each phase must be independently deployable.

At the end of every phase:

- MAVERIC must still work
- the software must remain usable
- tests must still pass
- the next phase must not be immediately required

### Phase 1: Platform Decisions And Spec

Goal:

- define the platform target before structural edits

Deliverables:

- this platform spec
- explicit core vs mission ownership
- explicit adapter/rendering contracts

Validation:

- documentation review only

### Phase 2: Core vs Mission Inventory

Goal:

- identify current files/functions as platform core or MAVERIC mission implementation

Deliverables:

- mapping of existing modules to target layers
- list of logic that must move out of core
- explicit classification of TUI and imaging paths
- explicit classification of config and logging responsibilities

Validation:

- no behavior changes required

### Phase 3: Separate Protocol-Family Support Into Core

Goal:

- isolate AX.25 / ASM+Golay / CSP / CRC support from mission semantics

Deliverables:

- `protocols/` modules or equivalent
- compatibility re-exports if needed

Validation:

- full test suite
- targeted AX.25 / Golay / CSP tests

### Phase 4: Make MAVERIC A Mission Implementation

Goal:

- move MAVERIC parsing and command semantics behind a mission package

Deliverables:

- `missions/maveric/` or equivalent
- adapter using mission-local parsing/build logic

Validation:

- full test suite
- current MAVERIC runtime still works

### Phase 5: UI Rendering Slot Migration

Goal:

- make packet list columns and semantic packet detail data mission-provided
- keep protocol/integrity/raw areas platform-defined

Deliverables:

- mission-provided list column/row contracts
- mission-provided semantic detail data
- fixed platform rendering of protocol/integrity/raw sections

Validation:

- frontend build
- manual runtime verification
- current test suite

### Phase 6: Hardening

Goal:

- make mission loading and adaptation safe

Deliverables:

- mission config validation
- mission self-check/startup validation
- clearer runtime reporting of active mission
- required fake second mission fixture for tests

Validation:

- test suite
- config validation tests

## Follow-On Phases

Phase 6 is the end of the initial migration track, not the end of platform work.

The next migration track is defined in:

- [phase7_11_platform_spec.md](phase7_11_platform_spec.md)

That document covers:

- Phase 7: runtime mission loading
- Phase 8: config and mission package cleanup
- Phase 9: transitional semantics cleanup
- Phase 10: legacy surface decision
- Phase 11: facade removal and final cleanup

## Acceptance Criteria

The migration is successful when:

- MAVERIC is a mission implementation, not the platform identity
- core owns transport, protocol-family support, workflow shell, and UI shell
- missions own parsing, command semantics, columns, and semantic detail content
- protocol and integrity sections are rendered through platform-standard contracts
- no core code assumes all missions expose MAVERIC-like fields
- a non-MAVERIC test mission exists and passes through the platform boundary

## Guidance For AI Editors

If you are an AI editor changing this repository, follow these rules:

1. Do not standardize mission semantics prematurely.
2. Do not move mission parsing into transport or UI code.
3. Keep protocol-family support reusable and mission-independent.
4. Prefer data-driven mission rendering payloads over mission-specific frontend code.
5. Preserve MAVERIC behavior during migration unless explicitly asked otherwise.
6. Use compatibility facades during structural moves when practical.

## Guidance For Future Mission Teams

If you are adapting this platform for a new mission:

1. Confirm the mission still fits the current platform scope:
   - CubeSat-focused
   - supported wrappers/protocol families
   - shared operator workflow shell
2. Provide a mission package:
   - `adapter.py`
   - `mission.yml`
   - `commands.yml`
3. Implement the mission-specific parsing and command logic there.
4. Map mission packet meaning into:
   - packet list columns/rows
   - packet semantic detail blocks
   - protocol blocks
   - integrity blocks
5. Leave transport, protocol-family support, workflow shell, and UI shell alone unless the platform itself needs to evolve.
