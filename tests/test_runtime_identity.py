from unittest import mock

from mav_gss_lib.web_runtime.state import create_runtime


def test_runtime_captures_identity_on_construction(tmp_path, monkeypatch):
    monkeypatch.delenv("SUDO_USER", raising=False)
    monkeypatch.chdir(tmp_path)
    with mock.patch("mav_gss_lib.identity.getpass.getuser", return_value="irfan"), \
         mock.patch("mav_gss_lib.identity.socket.gethostname", return_value="host-under-test"):
        runtime = create_runtime()
        assert runtime.operator == "irfan"
        assert runtime.host == "host-under-test"
        # No station_id override in default config → falls back to host
        assert runtime.station == "host-under-test"
        assert runtime.session.operator == "irfan"
        assert runtime.session.host == "host-under-test"
        assert runtime.session.station == "host-under-test"
