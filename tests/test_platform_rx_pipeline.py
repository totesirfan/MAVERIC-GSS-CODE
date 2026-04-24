from mav_gss_lib.platform.loader import load_mission_spec
from mav_gss_lib.platform.rx.pipeline import RxPipeline
from mav_gss_lib.platform.telemetry.router import TelemetryRouter


def _router_for(spec, tmp_path):
    router = TelemetryRouter(tmp_path)
    if spec.telemetry is not None:
        for name, domain in spec.telemetry.domains.items():
            router.register_domain(name, **domain.router_kwargs())
    return router


def test_rx_pipeline_v2_processes_echo_packet_without_telemetry(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    rx = RxPipeline(spec, _router_for(spec, tmp_path))

    result = rx.process({"transmitter": "fixture"}, b"\x01\x02")

    assert result.packet.seq == 1
    assert result.packet.telemetry == []
    assert result.telemetry_messages == []
    assert result.packet_message["type"] == "packet"
    assert result.packet_message["data"]["raw_hex"] == "0102"
    assert result.packet_message["data"]["_rendering"]["row"]["hex"]["value"] == "0102"


def test_rx_pipeline_v2_processes_balloon_packet_with_telemetry(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    rx = RxPipeline(spec, _router_for(spec, tmp_path))

    result = rx.process(
        {},
        b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}',
    )

    assert result.packet.flags.is_unknown is False
    assert {f.domain for f in result.packet.telemetry} == {"environment", "position"}
    assert {m["domain"] for m in result.telemetry_messages} == {"environment", "position"}
    assert result.packet_message["data"]["_rendering"]["row"]["kind"]["value"] == "beacon"
    assert result.packet_message["data"]["_rendering"]["row"]["alt"]["value"] == 1200


def test_rx_pipeline_v2_marks_unknown_balloon_packet(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    rx = RxPipeline(spec, _router_for(spec, tmp_path))

    result = rx.process({}, b'{"type":"status"}')

    assert result.packet.flags.is_unknown is True
    assert result.packet_message["data"]["is_unknown"] is True
    assert result.telemetry_messages == []
