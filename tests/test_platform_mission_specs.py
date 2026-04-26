from mav_gss_lib.platform import PacketEnvelope
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


def test_balloon_v2_loads_silent_telemetry(tmp_path):
    """balloon_v2 has no declarative spec post-Task-4 — UI still works,
    but spec_root is None and the walker won't emit parameters."""
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
