import pytest

from mav_gss_lib.config import load_split_config
from mav_gss_lib.platform.command_pipeline import CommandRejected
from mav_gss_lib.platform.runtime import PlatformRuntimeV2


def test_runtime_v2_loads_echo_and_processes_rx_and_tx(tmp_path):
    runtime = PlatformRuntimeV2.from_split(
        {"logs": {"dir": str(tmp_path)}},
        "echo_v2",
        {},
    )

    rx = runtime.process_rx({"transmitter": "fixture"}, b"\x01\x02")
    tx = runtime.prepare_tx("ping hello")

    assert runtime.mission.id == "echo_v2"
    assert rx.packet_message["data"]["raw_hex"] == "0102"
    assert rx.telemetry_messages == []
    assert tx.encoded.raw == b"ping hello"


def test_runtime_v2_loads_balloon_and_registers_telemetry_domains(tmp_path):
    runtime = PlatformRuntimeV2.from_split(
        {"logs": {"dir": str(tmp_path)}},
        "balloon_v2",
        {},
    )

    result = runtime.process_rx(
        {},
        b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}',
    )

    assert runtime.mission.id == "balloon_v2"
    assert runtime.telemetry.has_domain("environment")
    assert runtime.telemetry.has_domain("position")
    assert {m["domain"] for m in result.telemetry_messages} == {"environment", "position"}


def test_runtime_v2_rejects_tx_for_non_commandable_mission(tmp_path):
    runtime = PlatformRuntimeV2.from_split(
        {"logs": {"dir": str(tmp_path)}},
        "balloon_v2",
        {},
    )

    with pytest.raises(CommandRejected):
        runtime.prepare_tx("anything")


def test_runtime_v2_loads_maveric_and_prepares_command(tmp_path):
    platform_cfg, mission_id, mission_cfg = load_split_config()
    platform_cfg["logs"] = {"dir": str(tmp_path)}

    runtime = PlatformRuntimeV2.from_split(platform_cfg, mission_id, mission_cfg)

    rx = runtime.process_rx({"transmitter": "fixture"}, b"\x01\x02")
    tx = runtime.prepare_tx("ftdi_log hello")

    assert runtime.mission.id == "maveric"
    assert runtime.telemetry.has_domain("eps")
    assert runtime.telemetry.has_domain("gnc")
    assert runtime.telemetry.has_domain("spacecraft")
    assert rx.packet.flags.is_unknown is True
    assert rx.packet_message["data"]["is_unknown"] is True
    assert tx.encoded.raw
    assert tx.rendering.title == "ftdi_log"
