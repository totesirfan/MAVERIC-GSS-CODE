"""CalibratorRuntime — applies polynomial / python calibrators at decode.

Plugins are validated at construction: every PythonCalibrator's
`callable_ref` must resolve to a key in the supplied `plugins` map;
unresolved keys raise MissingPluginError. Belt-and-suspenders for the
parser's own check, so out-of-band Mission objects can't slip a missing
plugin through.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .calibrators import PolynomialCalibrator, PythonCalibrator
from .errors import MissingPluginError
from .parameter_types import (
    AggregateParameterType,
    ArrayParameterType,
    FloatParameterType,
    IntegerParameterType,
    ParameterType,
)

PluginCallable = Callable[..., tuple[Any, str]]


class CalibratorRuntime:
    __slots__ = ("_types", "_plugins")

    def __init__(
        self,
        *,
        types: Mapping[str, ParameterType],
        plugins: Mapping[str, PluginCallable],
    ) -> None:
        self._types = types
        self._plugins = plugins
        self._validate_plugins()

    def _validate_plugins(self) -> None:
        for t in self._types.values():
            cal = getattr(t, "calibrator", None)
            if isinstance(cal, PythonCalibrator) and cal.callable_ref not in self._plugins:
                raise MissingPluginError(cal.callable_ref)

    def apply(self, type_ref: str, raw: Any) -> tuple[Any, str]:
        t = self._types[type_ref]
        cal = getattr(t, "calibrator", None)
        type_unit = getattr(t, "unit", "")
        if cal is None:
            return raw, type_unit
        if isinstance(cal, PolynomialCalibrator):
            value = 0.0
            for power, coef in enumerate(cal.coefficients):
                value += coef * (raw ** power)
            return value, cal.unit or type_unit
        if isinstance(cal, PythonCalibrator):
            fn = self._plugins[cal.callable_ref]
            value, unit_from_plugin = fn(raw)
            # If the type is a calibrator-backed aggregate, the calibrator's
            # dict output IS the parameter's emitted shape — so it must match
            # the declared MemberList exactly. Mismatch is a contract bug
            # between the type declaration and the calibrator implementation;
            # surface it loudly rather than silently emitting a malformed dict.
            if isinstance(t, AggregateParameterType) and t.size_bits is not None:
                _validate_aggregate_calibrator_output(t, value, cal.callable_ref)
            return value, unit_from_plugin or cal.unit or type_unit
        raise TypeError(f"Unknown calibrator type {type(cal).__name__}")


def _validate_aggregate_calibrator_output(
    t: AggregateParameterType, value: Any, callable_ref: str,
) -> None:
    """Enforce the MemberList contract on calibrator-backed aggregates.

    Raises ValueError if the calibrator's output is not a dict, is missing
    declared members, or carries members that aren't declared. The set must
    match exactly — this is the type's honest contract.
    """
    if not isinstance(value, dict):
        raise ValueError(
            f"calibrator {callable_ref!r} for aggregate {t.name!r} returned "
            f"{type(value).__name__}, expected dict matching MemberList "
            f"{[m.name for m in t.member_list]}"
        )
    declared = {m.name for m in t.member_list}
    got = set(value.keys())
    missing = declared - got
    extra = got - declared
    if missing or extra:
        raise ValueError(
            f"calibrator {callable_ref!r} for aggregate {t.name!r} produced "
            f"keys {sorted(got)}, declared MemberList {sorted(declared)}"
            + (f"; missing {sorted(missing)}" if missing else "")
            + (f"; extra {sorted(extra)}" if extra else "")
        )


__all__ = ["CalibratorRuntime", "PluginCallable"]
