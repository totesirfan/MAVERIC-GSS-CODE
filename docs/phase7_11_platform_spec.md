# Phase 7-11 Platform Completion Spec

This document defines the next migration phases after Phase 6.

Current state after Phase 6:

- the platform/core vs mission boundary is substantially in place
- MAVERIC is implemented as a mission package
- protocol-family support is split into core modules
- the web frontend renders from mission-provided rendering slots
- adapter validation and a fake second mission fixture exist

The remaining work is no longer about proving the architecture direction.
It is about making the platform operationally complete, reducing transitional
compatibility layers, and finishing the move away from MAVERIC-shaped runtime
assumptions.

This document is written for:

- maintainers planning the next migration track
- future SERC teams extending the platform
- AI editors implementing the remaining phases

## Overall Strategy

The remaining phases should happen in this order:

1. Phase 7: Runtime Mission Loading
2. Phase 8: Config And Mission Package Cleanup
3. Phase 9: Transitional Semantics Cleanup
4. Phase 10: Legacy Surface Decision
5. Phase 11: Facade Removal And Final Cleanup

This order is deliberate.

Do not remove facades first.
Do not delete transitional packet fields first.
Do not generalize config first.

The runtime must load missions cleanly before the older MAVERIC-oriented
compatibility paths can be retired safely.

## Phase 7: Runtime Mission Loading

### Goal

Replace hardcoded MAVERIC adapter construction in runtime paths with one shared
mission-loading mechanism based on `general.mission`.

### Why This Phase Exists

After Phase 6, the adapter boundary is real, but runtime construction still is
not. The following still depend on MAVERIC directly:

- `mav_gss_lib/parsing.py`
- compatibility imports that assume MAVERIC is the only runtime mission

`WebRuntime` already selects MAVERIC by `general.mission`, and Phase 6 already
validates that startup path. The remaining gap is that the mission-loading
logic is still inline there and is not yet the shared runtime path used by
other construction flows such as `RxPipeline`.

That means the platform is architecturally cleaner, but not yet mission-selectable
through one shared runtime loading mechanism.

### Scope

This phase should:

- introduce a single mission loader/factory used by runtime code
- keep MAVERIC as the default mission
- make unknown or invalid mission selection fail clearly
- keep mission selection startup-only unless reload support is explicitly added

This phase should not:

- add multi-mission runtime support
- add hot-swappable live mission changes
- redesign mission config structure yet

### Deliverables

- one mission-loading function or module in core
- `WebRuntime` switches from its inline mission selection logic to that shared loader
- `RxPipeline` uses the same mission-loading path when constructed from config or
  command definitions are not explicitly provided
- tests for:
  - valid MAVERIC mission load
  - echo mission load through the shared loader
  - invalid mission name
  - invalid adapter API version
  - missing mission adapter entry point

### Design Rules

- the mission loader must be data-driven by `general.mission`
- MAVERIC remains the default if the config key is missing during migration
- startup error messages must name the bad mission and the supported mission ids
- no frontend changes are required in this phase

### Validation

- `pytest -q`
- startup tests for valid and invalid mission selection
- web runtime still boots with MAVERIC unchanged

## Phase 8: Config And Mission Package Cleanup

### Goal

Make mission selection and mission package configuration explicit and safe.

### Why This Phase Exists

The code can now separate core from mission behavior, but config still mixes:

- platform settings
- mission selection
- mission metadata
- protocol defaults
- command schema location

That is manageable for MAVERIC, but fragile for future missions.

### Scope

This phase should:

- define the version-1 mission package shape clearly
- clarify platform config vs mission config responsibilities
- improve validation and startup diagnostics
- make restart-required behavior explicit for mission-level changes

This phase should not:

- implement hot mission reload unless it is clearly justified
- introduce a large config framework or plugin registry

### Version-1 Mission Package Contract

Version 1 should stay small:

- `adapter.py`
- `mission.yml`
- `commands.yml`

Optional later additions can exist, but they should not be required in this phase.

`mission.yml` does not exist yet in the current repo. Creating it from the
current mission metadata/config surface is part of this phase, not a preexisting
assumption.

### Deliverables

- explicit handling of `general.mission`
- creation of a version-1 `mission.yml` for MAVERIC and a documented rule for
  where future missions put their metadata
- clearer config validation errors for:
  - missing mission metadata
  - missing command schema
  - unsupported mission id
  - invalid adapter API version
- documented restart-required behavior for mission selection changes, extending
  the current startup-only handling already present in the web config path
- startup or self-check output that names:
  - active mission id
  - display mission name
  - adapter API version
  - command schema path

### Design Rules

- keep mission selection startup-only unless a later phase proves reload is worth it
- validation errors should be user-facing and concrete
- do not split config into many files unless there is clear operational payoff

### Validation

- tests for invalid mission config combinations
- tests for clear startup failure messages
- docs updated to reflect real mission package layout

## Phase 9: Transitional Semantics Cleanup

### Goal

Reduce dependence on flat MAVERIC-era packet semantics outside the rendering path.

### Why This Phase Exists

After Phase 5b-ii, the UI rendering path is adapter-driven, but several
non-rendering paths still depend on flat fields shaped around MAVERIC:

- stats
- filtering
- text export
- copy actions
- some logging assumptions

In addition, platform-core still carries explicitly transitional MAVERIC-shaped
fields in `ParsedPacket`:

- `csp`
- `cmd`
- `cmd_tail`
- `ts_result`

Those are useful compatibility paths, but they should no longer define the
platform long-term.

### Scope

This phase should:

- identify which flat fields are still truly needed
- move obvious platform behavior to mission-driven or generic concepts where useful
- keep only the compatibility fields that still earn their complexity

This phase should not:

- force a universal mission semantic schema
- delete all flat fields blindly
- make TX semantics generic before there is evidence they should be

### Deliverables

- inventory of remaining flat RX packet field consumers
- explicit review of `ParsedPacket` transitional fields and whether each one
  should be removed, generalized, or retained longer with documentation
- adapter-driven or generic replacements where justified
- updated logging/summary rules if any MAVERIC-specific formatting still lives in core
- narrowed transitional field set, or at minimum clearer documentation of why the
  remaining ones still exist

### Design Rules

- prefer removing dependencies on flat fields in helper paths first
- preserve current user-visible behavior unless the new behavior is clearly better
- if a field has no general meaning across missions, keep it mission-local

### Validation

- `pytest -q`
- frontend build
- replay/log export behavior still works
- no regression in packet stats/filtering behavior

## Phase 10: Legacy Surface Decision

### Goal

Resolve the status of remaining legacy paths, especially the TUI and any older
compatibility-only interfaces.

### Why This Phase Exists

The repo now has a coherent web-platform story, but some older surfaces still
exist outside that architecture. Leaving them ambiguous indefinitely creates
two different maintenance stories.

### Scope

This phase should explicitly choose one of these for each legacy surface:

- migrate to platform/mission contracts
- freeze as legacy/MAVERIC-only
- deprecate and remove later

### TUI Decision

The TUI is the main remaining legacy surface.

Phase 4 already treated the TUI as a closed MAVERIC-only legacy decision.
This phase should not reopen that by default. It should only revisit the TUI if
there is a concrete operational reason to migrate it after the web path is stable.

Version-1 acceptable outcomes for this phase:

- keep it as explicitly MAVERIC-only legacy tooling and document that status
- revisit migration only if there is a documented need and an explicit decision
  to supersede the Phase 4 legacy stance

The wrong outcome is leaving it architecturally ambiguous.

### Deliverables

- explicit TUI status documented in code and docs
- explicit decision for any remaining compatibility-only helper APIs
- reduced ambiguity for future maintainers about what is platform-core vs legacy

### Design Rules

- do not start a second frontend migration unless there is a real operational need
- prefer explicit legacy status over partial migration
- keep user-facing behavior stable where legacy tools are still in use

### Validation

- if TUI is retained: verify it still works and its status is documented
- if TUI is deprecated: document it and ensure main supported path remains clean

## Phase 11: Facade Removal And Final Cleanup

### Goal

Remove migration scaffolding only after the new architecture is the sole real path.

### Why This Phase Exists

Facades and compatibility shims were the right migration tool, but they should
not remain forever once their job is done.

### Facade Removal Rule

A facade or compatibility shim may be removed only when all of the following
are true:

1. no core code depends on it
2. no supported runtime path depends on it
3. tests cover the replacement path directly
4. at least one non-MAVERIC mission fixture still passes through the new path

### Likely Cleanup Targets

- old compatibility re-exports in `protocol.py`
- old compatibility re-exports in `imaging.py`
- Phase 5A transitional adapter methods:
  - `packet_to_json`
  - `queue_item_to_json`
  - `history_entry`
- older facade imports that exist only to preserve migration-time call sites
- redundant frontend fallback paths, if replay/older-data strategy no longer needs them

### This Phase Should Not Do

- premature deletion of working compatibility paths before runtime loading is complete
- architectural redesign
- another major semantic refactor

### Deliverables

- list of removable facades and shims
- direct imports/use sites updated to final paths
- docs updated from “migration state” to “current architecture”

### Validation

- `pytest -q`
- frontend build
- no remaining core imports of deprecated facades
- second-mission fixture still passes

## Acceptance Criteria For The Next Track

The next phases are successful when:

- runtime mission loading no longer hardcodes MAVERIC construction in the main paths
- mission selection is explicit, validated, and operationally safe
- the most important non-rendering MAVERIC-shaped compatibility paths are either
  removed, reduced, or clearly justified
- TUI/legacy surfaces have explicit status
- facades are removed only after their replacements are the real runtime path

## Guidance For AI Editors

If you are implementing these phases:

1. Do not remove facades before runtime mission loading is complete.
2. Do not treat startup validation as a substitute for true mission loading.
3. Do not force a universal semantic schema where the platform has intentionally
   left missions free to define semantics.
4. Keep MAVERIC behavior stable while the runtime path is generalized.
5. Prefer one central mission-loader seam over ad hoc mission imports in multiple modules.
