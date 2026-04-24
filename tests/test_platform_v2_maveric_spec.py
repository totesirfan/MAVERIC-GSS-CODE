from mav_gss_lib.config import load_split_config
from mav_gss_lib.platform.command_pipeline import prepare_command
from mav_gss_lib.platform.loader import load_mission_spec_from_split
from mav_gss_lib.platform.packets import PacketEnvelope, PacketFlags
from mav_gss_lib.platform.rx_pipeline import RxPipelineV2
from mav_gss_lib.web_runtime.telemetry.router import TelemetryRouter


EPS_HK_PAYLOAD_HEX = (
    "900600000206000506606570735f686b00b4000000e823220088266c"
    "1d2c2134023f00f50c8c00f40176132600c8000000feff00000000fe"
    "ff00000000feff00000000feff00000000feff00000000000000000000feff000000"
    "00feff00000000feff00000000feff00000000000000000000feff00"
    "0000050f079ba7a4"
)


def _maveric_spec(tmp_path):
    platform_cfg, mission_id, mission_cfg = load_split_config()
    # Mission defaults are seeded inside build(ctx) by load_mission_spec_from_split.
    return load_mission_spec_from_split(
        platform_cfg, mission_id, mission_cfg, data_dir=tmp_path,
    )


def _router_for(spec, tmp_path):
    router = TelemetryRouter(tmp_path)
    if spec.telemetry is not None:
        for name, domain in spec.telemetry.domains.items():
            router.register_domain(name, **domain.router_kwargs())
    return router


def test_maveric_v2_spec_loads_with_capabilities(tmp_path):
    spec = _maveric_spec(tmp_path)

    assert spec.id == "maveric"
    assert spec.packets is not None
    assert spec.commands is not None
    assert spec.telemetry is not None
    assert spec.ui is not None
    assert spec.http is not None
    assert {"eps", "gnc", "spacecraft"}.issubset(spec.telemetry.domains.keys())


def test_maveric_v2_spec_loads_from_native_mission_config_shape(tmp_path):
    # Prove the spec loads from native split state starting empty — build(ctx)
    # seeds MAVERIC defaults, no external metadata file required.
    spec = load_mission_spec_from_split({}, "maveric", {}, data_dir=tmp_path)

    assert spec.id == "maveric"
    assert spec.name == "MAVERIC"
    assert spec.commands is not None
    assert spec.http is not None


def test_maveric_v2_command_ops_prepare_schema_command(tmp_path):
    spec = _maveric_spec(tmp_path)

    prepared = prepare_command(spec, "ftdi_log hello")

    assert prepared.encoded.raw
    assert prepared.rendering.title == "ftdi_log"
    assert "cmd" in prepared.rendering.row


def test_maveric_v2_rx_pipeline_renders_unknown_raw_packet(tmp_path):
    spec = _maveric_spec(tmp_path)
    rx = RxPipelineV2(spec, _router_for(spec, tmp_path))

    result = rx.process({"transmitter": "fixture"}, b"\x01\x02")

    assert result.packet.seq == 1
    assert result.packet.flags.is_unknown is True
    assert result.packet_message["data"]["is_unknown"] is True
    assert result.packet_message["data"]["_rendering"]["row"]["num"]["value"] == 1


def test_maveric_v2_rx_pipeline_extracts_eps_hk_telemetry(tmp_path):
    spec = _maveric_spec(tmp_path)
    rx = RxPipelineV2(spec, _router_for(spec, tmp_path))

    result = rx.process({"transmitter": "fixture"}, bytes.fromhex(EPS_HK_PAYLOAD_HEX))

    assert result.packet.flags.is_unknown is False
    assert result.packet_message["data"]["_rendering"]["row"]["cmd"]["value"] == "eps_hk"
    assert len(result.packet.telemetry) == 48
    # Native v2: fragments live on the envelope only. No `mission_payload["fragments"]`.
    assert "fragments" not in result.packet.mission_payload

    by_key = {fragment.key: fragment for fragment in result.packet.telemetry}
    assert by_key["V_BAT"].domain == "eps"
    assert by_key["V_BUS"].domain == "eps"
    assert by_key["V_BAT"].value == 7.532
    assert by_key["V_BUS"].value == 9.192

    assert [msg["domain"] for msg in result.telemetry_messages] == ["eps"]
    assert result.telemetry_messages[0]["changes"]["V_BAT"]["v"] == 7.532

    details = result.packet_message["data"]["_rendering"]["detail_blocks"]
    eps_block = next(block for block in details if block["label"] == "EPS")
    rendered = {field["name"]: field["value"] for field in eps_block["fields"]}
    assert rendered["Battery Voltage"] == "7.532 V"
    assert rendered["Bus Voltage"] == "9.192 V"


def test_maveric_v2_imaging_events_are_mission_owned(tmp_path):
    spec = _maveric_spec(tmp_path)
    source = spec.events.sources[0]
    packet = PacketEnvelope(
        seq=1,
        received_at_ms=0,
        received_at_text="2026-04-14 18:21:09 PDT",
        received_at_short="18:21:09",
        raw=b"",
        payload=b"",
        frame_type="fixture",
        transport_meta={},
        warnings=[],
        flags=PacketFlags(),
        mission_payload={
            "ptype": source.nodes.ptype_ids["RES"],
            "cmd": {
                "cmd_id": "img_cnt_chunks",
                "schema_match": True,
                "typed_args": [
                    {"name": "Filename", "value": "capture.jpg"},
                    {"name": "Num Chunks", "value": "3"},
                    {"name": "Thumb Filename", "value": "capture_thumb.jpg"},
                    {"name": "Thumb Num Chunks", "value": "1"},
                ],
            },
        },
    )

    messages = list(source.on_packet(packet))

    assert messages == [
        {
            "type": "imaging_progress",
            "filename": "capture.jpg",
            "received": 0,
            "total": 3,
            "complete": False,
        },
        {
            "type": "imaging_progress",
            "filename": "capture_thumb.jpg",
            "received": 0,
            "total": 1,
            "complete": False,
        },
    ]
