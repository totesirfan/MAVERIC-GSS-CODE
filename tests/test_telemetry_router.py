from mav_gss_lib.platform.telemetry import TelemetryFragment
from mav_gss_lib.platform.telemetry.router import TelemetryRouter


def test_register_and_ingest(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("eps")
    r.register_domain("gnc")
    frags = [
        TelemetryFragment("eps", "V_BAT", 12.0, 100),
        TelemetryFragment("gnc", "STAT", 0, 100),
    ]
    msgs = r.ingest(frags)
    assert {m["domain"] for m in msgs} == {"eps", "gnc"}
    assert all(m["type"] == "telemetry" for m in msgs)


def test_ingest_unknown_domain_is_dropped(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("eps")
    msgs = r.ingest([TelemetryFragment("unknown", "X", 1, 100)])
    assert msgs == []


def test_ingest_emits_only_changed_domains(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("eps"); r.register_domain("gnc")
    r.ingest([TelemetryFragment("eps", "V_BAT", 12.0, 100)])
    msgs = r.ingest([TelemetryFragment("eps", "V_BAT", 11.0, 90)])  # stale
    assert msgs == []


def test_replay_yields_one_msg_per_nonempty_domain(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("eps"); r.register_domain("gnc")
    r.ingest([TelemetryFragment("eps", "V_BAT", 12.0, 100)])
    msgs = r.replay()
    assert len(msgs) == 1
    assert msgs[0]["domain"] == "eps" and msgs[0]["replay"] is True
    assert msgs[0]["changes"]["V_BAT"]["v"] == 12.0


def test_clear_builds_cleared_message(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("eps")
    r.ingest([TelemetryFragment("eps", "V_BAT", 12.0, 100)])
    msg = r.clear("eps")
    assert msg == {"type": "telemetry", "domain": "eps", "cleared": True}
    assert r.replay() == []


def test_clear_unknown_domain_returns_none(tmp_path):
    assert TelemetryRouter(tmp_path).clear("nope") is None


def test_router_honors_domain_merge_policy(tmp_path):
    always_reject = lambda prev, frag: None
    r = TelemetryRouter(tmp_path)
    r.register_domain("d", merge=always_reject)
    msgs = r.ingest([TelemetryFragment("d", "K", 1, 100)])
    assert msgs == []


def test_router_exposes_mission_catalog(tmp_path):
    r = TelemetryRouter(tmp_path)
    r.register_domain("gnc", catalog=lambda: [{"name": "STAT", "unit": ""}])
    r.register_domain("eps")
    assert r.get_catalog("gnc") == [{"name": "STAT", "unit": ""}]
    assert r.get_catalog("eps") is None  # registered without catalog
    assert r.get_catalog("nope") is None  # unregistered
