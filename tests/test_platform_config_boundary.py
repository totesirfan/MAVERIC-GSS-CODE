from mav_gss_lib.platform.config import (
    apply_mission_config_update,
    persist_mission_config,
)
from mav_gss_lib.platform import MissionConfigSpec


def test_mission_config_update_is_opaque_by_default():
    current = {"nodes": {"1": "A"}, "imaging": {"dir": "images"}}
    update = {"nodes": {"1": "B"}, "imaging": {"dir": "other"}}

    result = apply_mission_config_update(current, update, MissionConfigSpec())

    assert result == current


def test_mission_config_update_allows_declared_editable_paths():
    current = {"imaging": {"dir": "images", "thumb_prefix": "thumb_"}}
    update = {"imaging": {"dir": "other", "thumb_prefix": "small_"}}
    spec = MissionConfigSpec(editable_paths={"imaging.thumb_prefix"})

    result = apply_mission_config_update(current, update, spec)

    assert result["imaging"]["dir"] == "images"
    assert result["imaging"]["thumb_prefix"] == "small_"


def test_mission_config_protected_paths_win_over_editable_paths():
    current = {"nodes": {"1": "A"}, "imaging": {"thumb_prefix": "thumb_"}}
    update = {"nodes": {"1": "B"}, "imaging": {"thumb_prefix": "small_"}}
    spec = MissionConfigSpec(
        editable_paths={"nodes.1", "imaging.thumb_prefix"},
        protected_paths={"nodes"},
    )

    result = apply_mission_config_update(current, update, spec)

    assert result["nodes"] == {"1": "A"}
    assert result["imaging"]["thumb_prefix"] == "small_"


def test_mission_config_update_does_not_create_undeclared_paths():
    current = {"imaging": {}}
    update = {"imaging": {"thumb_prefix": "small_"}, "new": {"field": 1}}
    spec = MissionConfigSpec(editable_paths={"imaging.thumb_prefix"})

    result = apply_mission_config_update(current, update, spec)

    assert result == {"imaging": {"thumb_prefix": "small_"}}


def test_editable_paths_glob_allows_all_subkeys_under_prefix():
    current = {"ax25": {"src_call": "OLD", "src_ssid": 0}}
    update = {"ax25": {"src_call": "NEW", "src_ssid": 7, "dest_call": "DST"}}
    spec = MissionConfigSpec(editable_paths={"ax25.*"})

    result = apply_mission_config_update(current, update, spec)

    assert result["ax25"]["src_call"] == "NEW"
    assert result["ax25"]["src_ssid"] == 7
    assert result["ax25"]["dest_call"] == "DST"


def test_editable_paths_glob_is_subtree_matched():
    current = {"csp": {"priority": 0, "ports": {"dest": 0}}}
    update = {"csp": {"priority": 3, "ports": {"dest": 9, "src": 1}}}
    spec = MissionConfigSpec(editable_paths={"csp.*"})

    result = apply_mission_config_update(current, update, spec)

    assert result["csp"]["priority"] == 3
    assert result["csp"]["ports"]["dest"] == 9
    assert result["csp"]["ports"]["src"] == 1


def test_protected_path_wins_over_glob_editable():
    current = {"ax25": {"src_call": "OLD"}, "nodes": {"1": "A"}}
    update = {"ax25": {"src_call": "NEW"}, "nodes": {"1": "B"}}
    spec = MissionConfigSpec(
        editable_paths={"ax25.*", "nodes.*"},
        protected_paths={"nodes"},
    )

    result = apply_mission_config_update(current, update, spec)

    assert result["ax25"]["src_call"] == "NEW"
    assert result["nodes"] == {"1": "A"}


def test_persist_mission_config_keeps_only_editable_paths():
    """Seeded mission constants (nodes, ptypes, mission_name, ui titles) must
    not leak onto disk — they live in code. Only editable paths persist."""
    mission_cfg = {
        "ax25": {"src_call": "WM2XBB", "dest_call": "WS9XSW"},
        "csp": {"priority": 2, "destination": 8},
        "imaging": {"thumb_prefix": "tn_"},
        "nodes": {0: "NONE", 1: "LPPM"},
        "ptypes": {1: "CMD"},
        "mission_name": "MAVERIC",
        "gs_node": "GS",
        "rx_title": "RX DOWNLINK",
    }
    spec = MissionConfigSpec(
        editable_paths={"ax25.*", "csp.*", "imaging.thumb_prefix"},
        protected_paths={"nodes", "ptypes", "mission_name", "gs_node", "rx_title"},
    )

    out = persist_mission_config(mission_cfg, spec)

    assert set(out.keys()) == {"ax25", "csp", "imaging"}
    assert out["ax25"]["src_call"] == "WM2XBB"
    assert out["csp"]["destination"] == 8
    assert out["imaging"] == {"thumb_prefix": "tn_"}


def test_persist_mission_config_leaf_path_persists_only_declared_key():
    """A non-glob editable path under a dict copies only that leaf, not
    sibling keys left in mission_cfg from earlier seeding."""
    mission_cfg = {
        "imaging": {"thumb_prefix": "tn_", "seeded_sibling": "constant"},
    }
    spec = MissionConfigSpec(editable_paths={"imaging.thumb_prefix"})

    out = persist_mission_config(mission_cfg, spec)

    assert out == {"imaging": {"thumb_prefix": "tn_"}}


def test_persist_mission_config_skips_missing_paths():
    spec = MissionConfigSpec(editable_paths={"ax25.*", "imaging.thumb_prefix"})

    out = persist_mission_config({}, spec)

    assert out == {}
