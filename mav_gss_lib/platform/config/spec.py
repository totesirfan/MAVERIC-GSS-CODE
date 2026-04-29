"""Platform-level config-update allowlist.

`apply_platform_config_update` uses a `PlatformConfigSpec` to decide
which parts of an incoming update it will actually write. Sections and
general keys not listed here (install-time state like `stations`,
runtime-derived fields like `version` / `build_sha`, stray mission-only
keys that shouldn't have made it into the platform bucket) are silently
dropped.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PlatformConfigSpec:
    editable_sections: frozenset[str] = field(default_factory=frozenset)
    editable_general_keys: frozenset[str] = field(default_factory=frozenset)


DEFAULT_PLATFORM_CONFIG_SPEC = PlatformConfigSpec(
    editable_sections=frozenset({"tx", "rx", "radio"}),
    editable_general_keys=frozenset({"log_dir", "generated_commands_dir"}),
)
