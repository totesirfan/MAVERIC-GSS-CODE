"""Exception hierarchy for the spec runtime.

Two roots:
  - ParseError: anything raised by yaml_parse / parser-time validation.
  - SpecRuntimeError: anything raised by the walker, codec, or factories
    at runtime (post-parse).

Concrete subclasses carry structured fields the caller can introspect
(error message includes the field values for human readability).
"""

from __future__ import annotations


class SpecError(Exception):
    """Root for all spec-runtime exceptions."""


class ParseError(SpecError):
    """Raised at parse time (yaml_parse, schema validation, graph checks)."""


class SpecRuntimeError(SpecError):
    """Raised at runtime by walker / codec / factories."""


# ---- ParseError family ----


class UnknownTypeRef(ParseError):
    def __init__(self, name: str, *, source: str = ""):
        self.name = name
        self.source = source
        super().__init__(f"Unknown type reference {name!r} at {source!r}")


class DuplicateTypeName(ParseError):
    def __init__(self, name: str, *, namespaces: tuple[str, ...] = ()):
        self.name = name
        self.namespaces = namespaces
        super().__init__(
            f"Duplicate type name {name!r} across namespaces {namespaces!r}"
        )


class ContainerConflict(ParseError):
    def __init__(self, name_a: str, name_b: str, *, signature: dict | None = None):
        self.name_a = name_a
        self.name_b = name_b
        self.signature = signature or {}
        super().__init__(
            f"Container equality-signature collision: {name_a!r} vs {name_b!r}"
            + (f" (signature={signature})" if signature else "")
        )


class IncompatibleSchemaVersion(ParseError):
    def __init__(self, found: int, supported: int):
        self.found = found
        self.supported = supported
        super().__init__(
            f"mission.yml schema_version={found} not supported (this parser handles v{supported})"
        )


class InvalidDynamicRef(ParseError):
    def __init__(self, binary_entry_name: str, ref_name: str, reason: str):
        self.binary_entry_name = binary_entry_name
        self.ref_name = ref_name
        self.reason = reason
        super().__init__(
            f"Invalid dynamic_ref on binary entry {binary_entry_name!r}: "
            f"references {ref_name!r} — {reason}"
        )


class PagedFrameTargetEmpty(ParseError):
    def __init__(self, entry_owner: str, base_container_ref: str):
        self.entry_owner = entry_owner
        self.base_container_ref = base_container_ref
        super().__init__(
            f"paged_frame_entry on {entry_owner!r} targets parent "
            f"{base_container_ref!r} which has no concrete children declared"
        )


class MissingPluginError(ParseError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"PythonCalibrator references unresolved plugin {name!r}")


class UnknownVerifierId(ParseError):
    def __init__(self, ref: str, *, source: str = ""):
        self.ref = ref
        self.source = source
        super().__init__(
            f"Unknown verifier_id {ref!r} referenced"
            + (f" in {source!r}" if source else "")
            + " — declare it under verifier_specs"
        )


# ---- Codec / runtime family ----


class MissingRequiredHeaderField(SpecRuntimeError):
    def __init__(self, cmd_id: str, field: str):
        self.cmd_id = cmd_id
        self.field = field
        super().__init__(
            f"command {cmd_id!r} is missing required header field {field!r}"
        )


class HeaderFieldNotOverridable(SpecRuntimeError):
    def __init__(self, cmd_id: str, field: str):
        self.cmd_id = cmd_id
        self.field = field
        super().__init__(
            f"command {cmd_id!r} does not allow operator override of header field {field!r}"
        )


class HeaderValueNotAllowed(SpecRuntimeError):
    def __init__(self, cmd_id: str, field: str, value: object, allowed: tuple):
        self.cmd_id = cmd_id
        self.field = field
        self.value = value
        self.allowed = allowed
        super().__init__(
            f"command {cmd_id!r} header field {field!r} value {value!r} "
            f"not in allowed set {allowed!r}"
        )


class UnknownHeaderValue(SpecRuntimeError):
    def __init__(self, cmd_id: str, field: str, value: object, *, allowed: tuple = ()):
        self.cmd_id = cmd_id
        self.field = field
        self.value = value
        self.allowed = allowed
        super().__init__(
            f"command {cmd_id!r} field {field!r} value {value!r} "
            f"not resolvable; allowed={allowed!r}"
        )


class ArgsTooLong(SpecRuntimeError):
    def __init__(self, cmd_id: str, length: int, *, ceiling: int = 255):
        self.cmd_id = cmd_id
        self.length = length
        self.ceiling = ceiling
        super().__init__(
            f"command {cmd_id!r} args length {length} exceeds ceiling {ceiling}"
        )


class CmdIdTooLong(SpecRuntimeError):
    def __init__(self, cmd_id: str, length: int, *, ceiling: int = 255):
        self.cmd_id = cmd_id
        self.length = length
        self.ceiling = ceiling
        super().__init__(
            f"command id {cmd_id!r} ASCII-encoded length {length} exceeds ceiling {ceiling}"
        )


class CrcMismatch(SpecRuntimeError):
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(f"CRC mismatch: expected={expected:#06x} actual={actual:#06x}")


class NonJsonSafeArg(SpecRuntimeError):
    def __init__(self, cmd_id: str, arg_name: str, value_type: type):
        self.cmd_id = cmd_id
        self.arg_name = arg_name
        self.value_type = value_type
        super().__init__(
            f"command {cmd_id!r} argument {arg_name!r} value type "
            f"{value_type.__name__} is not JSON-serialisable; encode in the calibrator"
        )
