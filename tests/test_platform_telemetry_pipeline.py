"""Legacy TelemetryOps pipeline tests — retired post-Task-4.

The platform no longer drives a TelemetryFragment pipeline. The
DeclarativeWalker emits ParamUpdate; ParameterCache holds canonical
state. See test_platform_rx_pipeline.py for the live shape.

Task 5 will delete the orphan ``platform/telemetry/`` package and the
matching ``rx/telemetry.py`` runner. This file is intentionally empty.
"""
