from mav_gss_lib.platform import PacketEnvelope
from mav_gss_lib.platform.loader import load_mission_spec
from mav_gss_lib.web_runtime.telemetry import TelemetryFragment


def test_echo_v2_loads_without_maveric_concepts(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    assert spec.id == "echo_v2"
    assert not hasattr(spec.packets, "node_name")
    assert not hasattr(spec.packets, "ptype_name")
    assert spec.telemetry is None

    normalized = spec.packets.normalize({"transmitter": "test"}, b"\xde\xad")
    mission_packet = spec.packets.parse(normalized)
    flags = spec.packets.classify(mission_packet)
    packet = PacketEnvelope(
        seq=1,
        received_at_ms=1000,
        received_at_text="2026-04-22 12:00:00 PDT",
        received_at_short="12:00:00",
        raw=normalized.raw,
        payload=normalized.payload,
        frame_type=normalized.frame_type,
        transport_meta={},
        warnings=mission_packet.warnings,
        mission_payload=mission_packet.payload,
        flags=flags,
    )
    rendered = spec.ui.render_packet(packet)

    assert rendered.row["hex"].value == "dead"
    assert rendered.row["size"].value == 2


def test_balloon_v2_loads_and_emits_telemetry_without_spacecraft_concepts(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    assert spec.id == "balloon_v2"
    assert spec.commands is None
    assert spec.telemetry is not None

    raw = b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}'
    normalized = spec.packets.normalize({}, raw)
    mission_packet = spec.packets.parse(normalized)
    flags = spec.packets.classify(mission_packet)
    packet = PacketEnvelope(
        seq=7,
        received_at_ms=2000,
        received_at_text="2026-04-22 12:01:00 PDT",
        received_at_short="12:01:00",
        raw=normalized.raw,
        payload=normalized.payload,
        frame_type=normalized.frame_type,
        transport_meta={},
        warnings=mission_packet.warnings,
        mission_payload=mission_packet.payload,
        flags=flags,
    )

    fragments = []
    for extractor in spec.telemetry.extractors:
        fragments.extend(extractor.extract(packet))

    by_key = {(f.domain, f.key): f for f in fragments}
    assert by_key[("environment", "altitude_m")] == TelemetryFragment(
        "environment", "altitude_m", 1200, 2000, unit="m"
    )
    assert by_key[("environment", "temperature_c")].value == 18.4
    assert by_key[("position", "gps")].value == {"lat": 34.0, "lon": -118.2}

    rendered = spec.ui.render_packet(packet)
    assert rendered.row["kind"].value == "beacon"
    assert rendered.row["alt"].value == 1200
    assert rendered.row["gps"].value == "34.0, -118.2"


def test_balloon_v2_unknown_packet_is_classified_without_ptypes(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    normalized = spec.packets.normalize({}, b'{"type":"status"}')
    mission_packet = spec.packets.parse(normalized)
    flags = spec.packets.classify(mission_packet)

    assert flags.is_unknown is True
    assert flags.is_uplink_echo is False
    assert flags.duplicate_key is None
