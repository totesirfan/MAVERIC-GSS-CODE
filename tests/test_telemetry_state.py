from mav_gss_lib.web_runtime.telemetry import TelemetryFragment


def test_fragment_fields():
    f = TelemetryFragment(
        domain="eps", key="V_BAT", value=12.34,
        ts_ms=1_700_000_000_000, unit="V",
    )
    assert (f.domain, f.key, f.value, f.ts_ms, f.unit) == (
        "eps", "V_BAT", 12.34, 1_700_000_000_000, "V",
    )


def test_fragment_unit_defaults_to_empty():
    f = TelemetryFragment(domain="platform", key="ops_stage", value=3, ts_ms=1)
    assert f.unit == ""


def test_fragment_to_dict_is_stable():
    f = TelemetryFragment("eps", "V_BAT", 7.622, 1_700_000_000_000, unit="V")
    assert f.to_dict() == {
        "domain": "eps", "key": "V_BAT", "value": 7.622,
        "ts_ms": 1_700_000_000_000, "unit": "V",
    }
