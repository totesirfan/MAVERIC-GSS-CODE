from mav_gss_lib.platform.loader import load_mission_spec


def test_echo_v2_loads_without_maveric_concepts(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    assert spec.id == "echo_v2"
    assert not hasattr(spec.packets, "node_name")
    assert not hasattr(spec.packets, "ptype_name")
    assert spec.spec_root is None

    normalized = spec.packets.normalize({"transmitter": "test"}, b"\xde\xad")
    mission_packet = spec.packets.parse(normalized)
    flags = spec.packets.classify(mission_packet)

    assert mission_packet.payload["hex"] == "dead"
    assert flags.is_unknown is False


def test_balloon_v2_loads_silent_telemetry(tmp_path):
    """balloon_v2 has no declarative spec post-Task-4 — packets parse but
    the walker won't emit parameters."""
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )

    assert spec.id == "balloon_v2"
    assert spec.commands is None
    assert spec.spec_root is None

    raw = b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}'
    normalized = spec.packets.normalize({}, raw)
    mission_packet = spec.packets.parse(normalized)
    flags = spec.packets.classify(mission_packet)

    assert mission_packet.payload["type"] == "beacon"
    assert mission_packet.payload["alt_m"] == 1200
    assert flags.is_unknown is False


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
