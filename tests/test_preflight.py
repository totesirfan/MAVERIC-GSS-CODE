import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mav_gss_lib.preflight import CheckResult, run_preflight, summarize


def _find(results, label):
    return next((r for r in results if r.label == label), None)

def test_check_result_fields():
    c = CheckResult(group="test", label="thing", status="ok")
    assert c.group == "test"
    assert c.status == "ok"
    assert c.fix == ""
    assert c.detail == ""

def test_run_preflight_yields_check_results():
    results = list(run_preflight())
    assert len(results) > 0
    assert all(isinstance(r, CheckResult) for r in results)
    for r in results:
        assert r.status in ("ok", "fail", "warn", "skip")

def test_summarize():
    results = [
        CheckResult("a", "x", "ok"),
        CheckResult("a", "y", "fail", fix="do this"),
        CheckResult("b", "z", "warn"),
    ]
    s = summarize(results)
    assert s.total == 3
    assert s.passed == 1
    assert s.failed == 1
    assert s.warnings == 1
    assert s.ready is False

def test_summarize_all_pass():
    results = [CheckResult("a", "x", "ok"), CheckResult("b", "y", "ok")]
    s = summarize(results)
    assert s.ready is True


def test_run_preflight_fails_on_missing_gss_yml():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        results = list(run_preflight(cfg={}, lib_dir=tmp_dir))

        gss_check = _find(results, "gss.yml exists")
        assert gss_check is not None
        assert gss_check.group == "config"
        assert gss_check.status == "fail"

        web_check = _find(results, "Web build (dist/index.html)")
        assert web_check is not None
        assert web_check.status == "fail"

        s = summarize(results)
        assert s.ready is False


def test_run_preflight_ok_when_gss_yml_present():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "gss.yml").touch()
        (tmp_dir / "missions" / "maveric").mkdir(parents=True)
        (tmp_dir / "web" / "dist").mkdir(parents=True)
        (tmp_dir / "web" / "dist" / "index.html").touch()

        cfg = {
            "rx": {"zmq_addr": "tcp://1.2.3.4:1111"},
            "tx": {"zmq_addr": "tcp://5.6.7.8:2222"},
        }
        results = list(run_preflight(cfg=cfg, mission_id="maveric", lib_dir=tmp_dir))

        gss_check = _find(results, "gss.yml exists")
        assert gss_check is not None
        assert gss_check.status == "ok"

        mission_check = _find(results, "Mission: maveric")
        assert mission_check is not None
        assert mission_check.status == "ok"

        web_check = _find(results, "Web build (dist/index.html)")
        assert web_check is not None
        assert web_check.status == "ok"

        rx_check = _find(results, "RX SUB")
        assert rx_check is not None
        assert rx_check.status == "ok"
        assert rx_check.detail == "tcp://1.2.3.4:1111"

        tx_check = _find(results, "TX PUB")
        assert tx_check is not None
        assert tx_check.status == "ok"
        assert tx_check.detail == "tcp://5.6.7.8:2222"


def test_run_preflight_fails_on_unknown_mission():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "gss.yml").touch()

        cfg = {}
        results = list(run_preflight(cfg=cfg, mission_id="nonexistent", lib_dir=tmp_dir))

        mission_check = _find(results, "Mission: nonexistent")
        assert mission_check is not None
        assert mission_check.status == "fail"


if __name__ == "__main__":
    test_check_result_fields()
    test_run_preflight_yields_check_results()
    test_summarize()
    test_summarize_all_pass()
    test_run_preflight_fails_on_missing_gss_yml()
    test_run_preflight_ok_when_gss_yml_present()
    test_run_preflight_fails_on_unknown_mission()
    print("All preflight tests passed.")
