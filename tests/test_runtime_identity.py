from unittest import mock

from mav_gss_lib.config import load_gss_config
from mav_gss_lib.web_runtime.state import create_runtime


def _cfg_without_stations_catalog():
    """Return the merged config with the `stations` catalog emptied — simulates
    an install where the mocked hostname isn't catalogued, so station falls
    back to host. Robust against any real `gss.yml` catalog entries."""
    cfg = load_gss_config()
    cfg["stations"] = {}
    return cfg


def test_runtime_captures_identity_on_construction(tmp_path, monkeypatch):
    monkeypatch.delenv("SUDO_USER", raising=False)
    with mock.patch("mav_gss_lib.identity.getpass.getuser", return_value="irfan"), \
         mock.patch("mav_gss_lib.identity.socket.gethostname", return_value="host-under-test"), \
         mock.patch("mav_gss_lib.web_runtime.state.load_gss_config",
                    return_value=_cfg_without_stations_catalog()):
        runtime = create_runtime()
        assert runtime.operator == "irfan"
        assert runtime.host == "host-under-test"
        # Mocked hostname isn't catalogued → station falls back to host
        assert runtime.station == "host-under-test"
        assert runtime.session.operator == "irfan"
        assert runtime.session.host == "host-under-test"
        assert runtime.session.station == "host-under-test"
