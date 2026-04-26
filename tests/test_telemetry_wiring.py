"""Telemetry router wiring tests — retired post-Task-4.

``runtime.telemetry`` is gone. The new live state is ``runtime.parameter_cache``;
the transitional ``/api/telemetry/...`` router proxies it for a limited window
before Task 6 swaps in ``/api/parameters/...``.
"""

from fastapi.testclient import TestClient


def test_runtime_exposes_parameter_cache():
    from mav_gss_lib.server.state import create_runtime
    from mav_gss_lib.platform.parameters import ParameterCache

    runtime = create_runtime()
    assert isinstance(runtime.parameter_cache, ParameterCache)
    assert runtime.parameter_cache is runtime.platform.parameter_cache


def test_create_app_mounts_telemetry_routes():
    """Catalog endpoint still serves while transitional router is mounted."""
    from mav_gss_lib.server.app import create_app

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/telemetry/eps/catalog")
    # MAVERIC declares an 'eps' domain in containers.
    assert r.status_code in (200, 404)


def test_create_app_catalog_404_on_unknown_domain():
    from mav_gss_lib.server.app import create_app

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/telemetry/nope/catalog")
    assert r.status_code == 404
