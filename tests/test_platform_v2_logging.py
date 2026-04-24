from mav_gss_lib.platform.loader import load_mission_spec
from mav_gss_lib.platform.logging import build_rx_log_record, format_rx_text_lines
from mav_gss_lib.platform.rx_pipeline import RxPipelineV2
from mav_gss_lib.web_runtime.telemetry.router import TelemetryRouter


def _router_for(spec, tmp_path):
    router = TelemetryRouter(tmp_path)
    if spec.telemetry is not None:
        for name, domain in spec.telemetry.domains.items():
            router.register_domain(name, **domain.router_kwargs())
    return router


def test_build_rx_log_record_wraps_echo_packet_in_platform_envelope(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    result = RxPipelineV2(spec, _router_for(spec, tmp_path)).process(
        {"transmitter": "fixture"},
        b"\xde\xad",
    )

    record = build_rx_log_record(spec, result.packet, "1.2.3", operator="op", station="gs")

    assert record["v"] == "1.2.3"
    assert record["mission"] == "echo_v2"
    assert record["operator"] == "op"
    assert record["station"] == "gs"
    assert record["raw_hex"] == "dead"
    assert record["payload_hex"] == "dead"
    assert record["telemetry"] == []
    assert record["_rendering"]["row"]["hex"]["value"] == "dead"
    assert record["mission_log"] == {"hex": "dead"}


def test_build_rx_log_record_contains_balloon_telemetry_under_generic_key(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    result = RxPipelineV2(spec, _router_for(spec, tmp_path)).process(
        {},
        b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}',
    )

    record = build_rx_log_record(spec, result.packet, "1.2.3")

    telemetry_keys = {(f["domain"], f["key"]) for f in record["telemetry"]}
    assert ("environment", "altitude_m") in telemetry_keys
    assert ("position", "gps") in telemetry_keys
    assert record["mission_log"]["type"] == "beacon"
    assert "nodes" not in record
    assert "ptypes" not in record
    assert "gs_node" not in record


def test_format_rx_text_lines_uses_mission_ui_safely(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    result = RxPipelineV2(spec, _router_for(spec, tmp_path)).process({}, b"\xca\xfe")

    assert format_rx_text_lines(spec, result.packet) == ["  RAW         cafe"]
