# Phase 7: Runtime Mission Loading

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the inline mission-loading logic from `WebRuntime._load_adapter()` into a shared `load_mission_adapter()` function in platform core, and make `RxPipeline` use it instead of importing `MavericMissionAdapter` directly.

**Architecture:** Add `load_mission_adapter(cfg, cmd_defs)` to `mission_adapter.py`. It reads `general.mission` from config, imports the corresponding mission package, instantiates and validates the adapter, and returns it. `WebRuntime._load_adapter()` becomes a one-liner calling this function. `parsing.py` replaces its `MavericMissionAdapter` import with a call to the shared loader for its fallback path. Tests verify both MAVERIC and echo missions load through the same function.

**Tech Stack:** Python 3.10+, pytest

---

## Design Decisions

1. **The shared loader lives in `mission_adapter.py`.** It's platform core — right next to `validate_adapter()` and the `MissionAdapter` Protocol.

2. **The loader uses a registry dict, not dynamic imports.** For v1, the registry is `{"maveric": "mav_gss_lib.missions.maveric"}`. This is explicit and auditable. Dynamic plugin discovery can come later if needed.

3. **Adapter class discovery uses an explicit entry point.** Each mission package's `__init__.py` must export `ADAPTER_CLASS` — the adapter class itself (not an instance). The loader imports the package, reads `ADAPTER_CLASS`, and instantiates it. No name-scanning or heuristic class discovery.

4. **`cmd_defs` is a loader parameter.** The loader receives pre-loaded command definitions. It does not load them itself — that's the caller's responsibility. This keeps the loader focused on adapter construction and validation.

4. **`RxPipeline`'s fallback path changes from `MavericMissionAdapter(cmd_defs)` to `load_mission_adapter(cfg, cmd_defs)`.** As a compatibility compromise, the fallback branch calls `load_gss_config()` internally to get the config dict. This avoids changing the `RxPipeline` constructor signature. The primary path (passing an adapter directly) is unchanged and is what `WebRuntime` uses.

5. **No frontend changes.** This is entirely backend.

## File Plan

| Action | File | Change |
|---|---|---|
| Modify | `mav_gss_lib/mission_adapter.py` | Add `load_mission_adapter()` function |
| Modify | `mav_gss_lib/missions/maveric/__init__.py` | Export `ADAPTER_CLASS` |
| Modify | `mav_gss_lib/web_runtime/state.py` | Replace inline `_load_adapter()` with call to shared loader |
| Modify | `mav_gss_lib/parsing.py` | Replace `MavericMissionAdapter` import with shared loader fallback |
| Modify | `tests/echo_mission.py` | Export `ADAPTER_CLASS` |
| Modify | `tests/test_ops_mission_boundary.py` | Add tests for shared loader (MAVERIC + echo positive path) |

## Test Commands

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v
```

---

## Task 1: Add `load_mission_adapter()` to Platform Core

**Files:**
- Modify: `mav_gss_lib/mission_adapter.py`

- [ ] **Step 1: Add the mission registry and loader function**

In `mav_gss_lib/mission_adapter.py`, add this after `validate_adapter()` and before the facade re-export section:

```python
# =============================================================================
#  PLATFORM CORE -- Mission Loader
# =============================================================================

# Registry of known mission packages: mission_id -> module path
_MISSION_REGISTRY = {
    "maveric": "mav_gss_lib.missions.maveric",
}


def load_mission_adapter(cfg: dict, cmd_defs: dict):
    """Load, instantiate, and validate a mission adapter from config.

    Reads general.mission from cfg (default: "maveric"), imports the
    corresponding mission package, and returns a validated adapter.

    This is the single shared mission-loading path used by all runtime
    construction flows.

    Raises ValueError with a clear message if:
      - mission ID is not in the registry
      - mission package has no ADAPTER_API_VERSION
      - adapter does not satisfy MissionAdapter interface
      - ADAPTER_API_VERSION is unsupported
    """
    import importlib
    import logging

    mission = cfg.get("general", {}).get("mission", "maveric")
    mission_name = cfg.get("general", {}).get("mission_name", mission.upper())

    module_path = _MISSION_REGISTRY.get(mission)
    if module_path is None:
        raise ValueError(
            f"Unknown mission '{mission}' in general.mission config. "
            f"Supported: {', '.join(sorted(_MISSION_REGISTRY))}"
        )

    try:
        mission_pkg = importlib.import_module(module_path)
    except ImportError as exc:
        raise ValueError(
            f"Mission '{mission}' package '{module_path}' could not be imported: {exc}"
        ) from exc

    api_version = getattr(mission_pkg, "ADAPTER_API_VERSION", None)
    if api_version is None:
        raise ValueError(
            f"Mission '{mission}' package '{module_path}' has no ADAPTER_API_VERSION"
        )

    adapter_cls = getattr(mission_pkg, "ADAPTER_CLASS", None)
    if adapter_cls is None:
        raise ValueError(
            f"Mission '{mission}' package '{module_path}' has no ADAPTER_CLASS"
        )

    adapter = adapter_cls(cmd_defs=cmd_defs)
    validate_adapter(adapter, api_version, mission_name)
    logging.info("Mission loaded: %s (adapter API v%d)", mission_name, api_version)
    return adapter
```

- [ ] **Step 2: Export ADAPTER_CLASS from MAVERIC mission package**

In `mav_gss_lib/missions/maveric/__init__.py`, add after `ADAPTER_API_VERSION`:

```python
from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter as ADAPTER_CLASS  # noqa: F401
```

The file should now contain:
```python
"""
mav_gss_lib.missions.maveric -- MAVERIC CubeSat Mission Implementation

Wire format, command schema, adapter, and imaging for the MAVERIC mission.
"""

ADAPTER_API_VERSION = 1

from mav_gss_lib.missions.maveric.adapter import MavericMissionAdapter as ADAPTER_CLASS  # noqa: F401
```

- [ ] **Step 3: Export ADAPTER_CLASS from echo mission test fixture**

In `tests/echo_mission.py`, add after `ADAPTER_API_VERSION = 1`:

```python
# Explicit entry point for shared mission loader
ADAPTER_CLASS = EchoMissionAdapter
```

Note: Since `ADAPTER_CLASS = EchoMissionAdapter` references the class defined later in the file, add it at the bottom of the file instead:

```python
# At the end of tests/echo_mission.py:
ADAPTER_CLASS = EchoMissionAdapter
```

- [ ] **Step 4: Smoke test**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.config import load_gss_config, get_command_defs_path
from mav_gss_lib.protocol import init_nodes, load_command_defs
from mav_gss_lib.mission_adapter import load_mission_adapter, MissionAdapter

cfg = load_gss_config()
init_nodes(cfg)
cmd_defs, _ = load_command_defs(get_command_defs_path(cfg))

adapter = load_mission_adapter(cfg, cmd_defs)
print('type:', type(adapter).__name__)
print('isinstance:', isinstance(adapter, MissionAdapter))

# Test bad mission
try:
    bad_cfg = dict(cfg)
    bad_cfg['general'] = dict(cfg.get('general', {}))
    bad_cfg['general']['mission'] = 'nonexistent'
    load_mission_adapter(bad_cfg, cmd_defs)
except ValueError as e:
    print('Bad mission rejected:', e)

print('OK')
"
```

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q
```

- [ ] **Step 4: Commit**

```bash
git add mav_gss_lib/mission_adapter.py
git commit -m "Add load_mission_adapter() as shared mission-loading function"
```

---

## Task 2: Switch WebRuntime to Shared Loader

**Files:**
- Modify: `mav_gss_lib/web_runtime/state.py`

- [ ] **Step 1: Update imports**

Change:
```python
from mav_gss_lib.mission_adapter import MavericMissionAdapter, validate_adapter
```
to:
```python
from mav_gss_lib.mission_adapter import load_mission_adapter
```

- [ ] **Step 2: Replace `_load_adapter` body**

Replace the entire `_load_adapter` method with:

```python
    def _load_adapter(self):
        """Instantiate and validate the mission adapter via the shared loader."""
        return load_mission_adapter(self.cfg, self.cmd_defs)
```

- [ ] **Step 3: Verify startup**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -c "
from mav_gss_lib.web_runtime.state import WebRuntime
rt = WebRuntime()
print('adapter:', type(rt.adapter).__name__)
print('OK')
"
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add mav_gss_lib/web_runtime/state.py
git commit -m "Switch WebRuntime to shared load_mission_adapter()"
```

---

## Task 3: Switch RxPipeline Fallback to Shared Loader

**Files:**
- Modify: `mav_gss_lib/parsing.py`

- [ ] **Step 1: Update imports**

Change line 17:
```python
from mav_gss_lib.mission_adapter import MavericMissionAdapter
```
to:
```python
from mav_gss_lib.mission_adapter import load_mission_adapter
```

- [ ] **Step 2: Update the fallback constructor path**

In `RxPipeline.__init__()`, change the fallback branch (line 72):

```python
        if hasattr(adapter_or_cmd_defs, "detect_frame_type"):
            self.adapter = adapter_or_cmd_defs
        else:
            self.adapter = MavericMissionAdapter(adapter_or_cmd_defs)
```

to:

```python
        if hasattr(adapter_or_cmd_defs, "detect_frame_type"):
            self.adapter = adapter_or_cmd_defs
        else:
            # Fallback: cmd_defs dict passed directly — load via shared loader
            from mav_gss_lib.config import load_gss_config
            cfg = load_gss_config()
            self.adapter = load_mission_adapter(cfg, adapter_or_cmd_defs)
```

Note: `load_gss_config` is imported inside the fallback branch to avoid a circular import at module level. The primary path (passing an adapter) doesn't need config.

- [ ] **Step 3: Run tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -q

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -q
```

All tests must pass. The main `WebRuntime` path passes an adapter directly (never hits the fallback). Tests that pass `cmd_defs` will now go through the shared loader.

- [ ] **Step 4: Commit**

```bash
git add mav_gss_lib/parsing.py
git commit -m "Switch RxPipeline fallback from MavericMissionAdapter to shared loader"
```

---

## Task 4: Add Shared Loader Tests

**Files:**
- Modify: `tests/test_ops_mission_boundary.py`

- [ ] **Step 1: Add loader tests**

Add these test methods to the existing `TestMissionBoundary` class:

```python
    def test_shared_loader_loads_maveric(self):
        """load_mission_adapter() loads MAVERIC by default config."""
        from mav_gss_lib.mission_adapter import load_mission_adapter
        from mav_gss_lib.config import load_gss_config, get_command_defs_path
        from mav_gss_lib.protocol import init_nodes, load_command_defs

        cfg = load_gss_config()
        init_nodes(cfg)
        cmd_defs, _ = load_command_defs(get_command_defs_path(cfg))
        adapter = load_mission_adapter(cfg, cmd_defs)
        self.assertEqual(type(adapter).__name__, "MavericMissionAdapter")
        self.assertIsInstance(adapter, MissionAdapter)

    def test_shared_loader_rejects_unknown_mission(self):
        """load_mission_adapter() raises ValueError for unknown mission."""
        from mav_gss_lib.mission_adapter import load_mission_adapter
        cfg = {"general": {"mission": "nonexistent"}}
        with self.assertRaises(ValueError) as ctx:
            load_mission_adapter(cfg, {})
        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("Supported", str(ctx.exception))

    def test_shared_loader_loads_echo_mission(self):
        """load_mission_adapter() successfully loads the echo mission fixture."""
        from mav_gss_lib.mission_adapter import load_mission_adapter, _MISSION_REGISTRY

        # Register echo mission temporarily
        _MISSION_REGISTRY["echo_test"] = "tests.echo_mission"
        try:
            cfg = {"general": {"mission": "echo_test"}}
            adapter = load_mission_adapter(cfg, {})
            self.assertEqual(type(adapter).__name__, "EchoMissionAdapter")
            self.assertIsInstance(adapter, MissionAdapter)
        finally:
            del _MISSION_REGISTRY["echo_test"]

    def test_shared_loader_rejects_bad_api_version(self):
        """load_mission_adapter() rejects adapter with unsupported API version."""
        from mav_gss_lib.mission_adapter import load_mission_adapter, _MISSION_REGISTRY

        # Register echo mission temporarily
        _MISSION_REGISTRY["echo_test"] = "tests.echo_mission"

        # Monkey-patch echo mission's ADAPTER_API_VERSION
        from tests import echo_mission
        original_version = echo_mission.ADAPTER_API_VERSION
        echo_mission.ADAPTER_API_VERSION = 99
        try:
            cfg = {"general": {"mission": "echo_test"}}
            with self.assertRaises(ValueError) as ctx:
                load_mission_adapter(cfg, {})
            self.assertIn("ADAPTER_API_VERSION=99", str(ctx.exception))
        finally:
            echo_mission.ADAPTER_API_VERSION = original_version
            del _MISSION_REGISTRY["echo_test"]
```

- [ ] **Step 2: Run the new tests**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/test_ops_mission_boundary.py -v
```

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_ops_mission_boundary.py
git commit -m "Add shared mission loader tests for MAVERIC and error cases"
```

---

## Task 5: Final Verification

- [ ] **Step 1: Verify no direct MavericMissionAdapter imports remain in platform runtime**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
grep -rn "from.*import.*MavericMissionAdapter" mav_gss_lib/ --include="*.py" | grep -v "missions/maveric/" | grep -v "__pycache__"
```

Expected: only `mission_adapter.py` (facade re-export) should match. No direct imports in `state.py`, `parsing.py`, or any other runtime module.

- [ ] **Step 2: Verify shared loader is the only construction path**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
grep -rn "MavericMissionAdapter(" mav_gss_lib/ --include="*.py" | grep -v "missions/maveric/" | grep -v "__pycache__"
```

Expected: no matches in platform runtime code. The only `MavericMissionAdapter(` construction should be inside `missions/maveric/` or tests.

- [ ] **Step 3: Run both test suites**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
python3 -m pytest tests/ -v

cd "/Users/irfan/Documents/MAVERIC GSS"
python3 -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/irfan/Documents/MAVERIC GSS/MAVERIC GSS CODE"
git add -A
git commit -m "Phase 7 complete: runtime mission loading through shared loader"
```

---

## Post-Phase 7 State

**What changed:**
- `load_mission_adapter(cfg, cmd_defs)` in platform core — single shared mission-loading function
- `_MISSION_REGISTRY` maps mission IDs to module paths
- `WebRuntime._load_adapter()` delegates to `load_mission_adapter()`
- `RxPipeline` fallback constructor uses `load_mission_adapter()` instead of importing `MavericMissionAdapter`
- No platform runtime code imports `MavericMissionAdapter` directly anymore (only the facade re-export)
- 3 new tests for the shared loader (MAVERIC load, unknown mission, bad API version)

**What did NOT change:**
- Frontend (no changes)
- `mission_adapter.py` facade re-export (still re-exports `MavericMissionAdapter` for backward compatibility)
- Test fixtures that construct `MavericMissionAdapter` or `EchoMissionAdapter` directly (that's test code, not runtime)
- MAVERIC remains the default when `general.mission` is absent
