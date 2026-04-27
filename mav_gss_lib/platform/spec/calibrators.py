"""Calibrators — engineering-unit transforms applied at fragment emission.

Two flavours; absence (`None`) means identity:
  - PolynomialCalibrator : engineering = sum(c_i * raw^i). Scalar only.
  - PythonCalibrator     : callable resolved from the mission's plugin
                           registry passed to ``parse_yaml(..., plugins=)``.

When a calibrator is present, its `unit` overrides the bound ParameterType's
`unit` at fragment emission time and in catalog projection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolynomialCalibrator:
    """YAML: calibrator: {polynomial: [c0, c1, c2, ...]}

    Engineering value = sum(c_i * raw^i). Scalar (int/float) types only —
    parser rejects on enum/string/binary/aggregate/array/absolute_time."""

    coefficients: tuple[float, ...]
    unit: str = ""


@dataclass(frozen=True, slots=True)
class PythonCalibrator:
    """YAML: calibrator: {python: 'module.function'}

    `callable_ref` resolves at MissionSpec wiring time against the
    mission's plugin registry (a ``dict[str, Callable]`` passed to
    ``parse_yaml`` as the ``plugins=`` argument). Scalar (int/float)
    types only in v1. Callable signature is fixed to:
        (raw: int | float) -> tuple[Any, str]    # (value, unit)
    """

    callable_ref: str
    unit: str = ""


Calibrator = PolynomialCalibrator | PythonCalibrator | None
