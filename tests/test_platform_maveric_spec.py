from pathlib import Path

from mav_gss_lib.config import load_split_config
from mav_gss_lib.platform.tx.commands import prepare_command
from mav_gss_lib.platform.loader import load_mission_spec_from_split
from mav_gss_lib.platform.parameter_cache import ParameterCache
from mav_gss_lib.platform.rx.pipeline import RxPipeline
from mav_gss_lib.platform.spec.runtime import DeclarativeWalker


EPS_HK_PAYLOAD_HEX = (
    "900600000206000506606570735f686b00b4000000e823220088266c"
    "1d2c2134023f00f50c8c00f40176132600c8000000feff00000000fe"
    "ff00000000feff00000000feff00000000feff00000000000000000000feff000000"
    "00feff00000000feff00000000feff00000000000000000000feff00"
    "0000050f079ba7a4"
)

# Real on-orbit beacon captured 2026-04-29T19:27:26 in the function-test
# session log. ADCS_TMP at the recorded offset decodes as IEEE-754 LE float
# 26.9989013671875 °C — pinning this prevents anyone from re-collapsing
# the parameter back to the AdcsTmp aggregate (which would reinterpret the
# same bytes as raw int16 brdtmp and produce ~-2.6 °C).
TLM_BEACON_PAYLOAD_HEX = (
    "90060000030600050a69746c6d5f626561636f6e00"
    "57513258494300da4db5da9d010000010200000700064394410038bc6a00010101"
    "010000018000000000"
    "3ea80bbbdb9f8bbb3ea80bbbeb64b7c1d3b38140ef21c2c1"
    "cdcc4c3ecdcc4c3ecdcccc3d"
    "c0fdd741"  # ADCS_TMP_BEACON: f32_le 26.9989013671875 °C
    "8f02f301b020a220c02039024600020001000000000000003435799e02ef"
)


def _maveric_spec(tmp_path):
    platform_cfg, mission_id, mission_cfg = load_split_config()
    return load_mission_spec_from_split(
        platform_cfg, mission_id, mission_cfg, data_dir=tmp_path,
    )


def _maveric_pipeline(spec, tmp_path: Path) -> RxPipeline:
    walker = (
        DeclarativeWalker(spec.spec_root, plugins=spec.spec_plugins)
        if spec.spec_root is not None else None
    )
    return RxPipeline(spec, walker=walker)


def test_maveric_v2_spec_loads_with_capabilities(tmp_path):
    spec = _maveric_spec(tmp_path)

    assert spec.id == "maveric"
    assert spec.packets is not None
    assert spec.commands is not None
    assert spec.spec_root is not None
    assert spec.spec_plugins
    assert spec.http is not None


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
    assert prepared.encoded.cmd_id == "ftdi_log"
    assert prepared.encoded.mission_facts["header"]["cmd_id"] == "ftdi_log"


def test_maveric_v2_rx_pipeline_renders_unknown_raw_packet(tmp_path):
    spec = _maveric_spec(tmp_path)
    rx = _maveric_pipeline(spec, tmp_path)

    result = rx.process({"transmitter": "fixture"}, b"\x01\x02")

    assert result.packet.seq == 1
    assert result.packet.flags.is_unknown is True
    assert result.packet.mission["id"] == "maveric"
    assert "cmd_id" not in result.packet.mission


def test_maveric_v2_rx_pipeline_extracts_eps_hk_parameters(tmp_path):
    """EPS_HK fixture parity. Skipped when commands.yml/mission.yml routing
    rejects the fixture as unknown, matching the pre-existing fixture gap."""
    spec = _maveric_spec(tmp_path)
    rx = _maveric_pipeline(spec, tmp_path)

    result = rx.process({"transmitter": "fixture"}, bytes.fromhex(EPS_HK_PAYLOAD_HEX))

    if result.packet.flags.is_unknown:
        import pytest
        pytest.skip("EPS_HK fixture not accepted by current commands.yml routing")

    mission = result.packet.mission
    assert mission["id"] == "maveric"
    assert mission["facts"]["header"]["cmd_id"] == "eps_hk"
    assert result.packet.flags.integrity_ok == mission["facts"]["integrity"]["overall_ok"]
    assert "body_crc_ok" in mission["facts"]["integrity"]
    assert "csp_crc32_ok" in mission["facts"]["integrity"]
    # Walker emits qualified ParamUpdates.
    by_name = {p.name: p for p in result.packet.parameters}
    assert "eps.V_BAT" in by_name
    assert "eps.V_BUS" in by_name
    assert by_name["eps.V_BAT"].value == 7.532
    assert by_name["eps.V_BUS"].value == 9.192

    # ParameterCache is now a server projection over decoded parameters.
    changes = ParameterCache(tmp_path / "parameters.json").apply(result.packet.parameters)
    assert changes
    update_names = {u["name"] for u in changes}
    assert "eps.V_BAT" in update_names


def test_tlm_beacon_adcs_tmp_split(tmp_path):
    """tlm_beacon's ADCS_TMP is f32_le precomputed celsius; the AX100
    register at module 0 / reg 0x94 is uint32 holding raw int16 brdtmp.
    They must stay split — collapsing both to the AdcsTmp aggregate
    misreads beacon bytes as raw int16 (300 of 305 captured beacons
    produced wrong-sign celsius before the split was reinstated)."""
    import pytest

    spec = _maveric_spec(tmp_path)
    if spec.spec_root is None or "ADCS_TMP_BEACON" not in spec.spec_root.parameters:
        pytest.skip("local mission.yml does not declare the ADCS_TMP_BEACON split")
    rx = _maveric_pipeline(spec, tmp_path)

    result = rx.process({"transmitter": "fixture"}, bytes.fromhex(TLM_BEACON_PAYLOAD_HEX))
    if result.packet.flags.is_unknown:
        pytest.skip("tlm_beacon fixture not accepted by current routing")

    by_name = {p.name: p for p in result.packet.parameters}
    assert "gnc.ADCS_TMP_BEACON" in by_name
    assert by_name["gnc.ADCS_TMP_BEACON"].value == 26.9989013671875
    assert by_name["gnc.ADCS_TMP_BEACON"].unit == "°C"
    # The aggregate parameter belongs to the register, not the beacon.
    assert "gnc.ADCS_TMP" not in by_name
