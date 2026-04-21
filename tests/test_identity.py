import os
from unittest import mock

import pytest

from mav_gss_lib.identity import capture_host, capture_operator, capture_station


def test_capture_operator_returns_getpass_user(monkeypatch):
    monkeypatch.delenv("SUDO_USER", raising=False)
    with mock.patch("mav_gss_lib.identity.getpass.getuser", return_value="irfan"):
        assert capture_operator() == "irfan"


def test_capture_operator_prefers_sudo_user(monkeypatch):
    monkeypatch.setenv("SUDO_USER", "alice")
    with mock.patch("mav_gss_lib.identity.getpass.getuser", return_value="root"):
        assert capture_operator() == "alice"


def test_capture_host_returns_socket_hostname():
    with mock.patch("mav_gss_lib.identity.socket.gethostname", return_value="d23ll-barnhart"):
        assert capture_host() == "d23ll-barnhart"


def test_capture_station_returns_config_override_when_set():
    cfg = {"general": {"station_id": "GS-1"}}
    assert capture_station(cfg, host="d23ll-barnhart") == "GS-1"


def test_capture_station_falls_back_to_host_when_override_missing():
    cfg = {"general": {}}
    assert capture_station(cfg, host="d23ll-barnhart") == "d23ll-barnhart"


def test_capture_station_falls_back_to_host_when_override_blank():
    cfg = {"general": {"station_id": ""}}
    assert capture_station(cfg, host="d23ll-barnhart") == "d23ll-barnhart"


def test_capture_station_handles_missing_general_section():
    cfg = {}
    assert capture_station(cfg, host="host1") == "host1"
