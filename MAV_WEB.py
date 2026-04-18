#!/usr/bin/env python3
"""MAV_WEB — Web dashboard entrypoint for MAVERIC GSS."""

from __future__ import annotations

import socket
import threading
import time

# Bootstrap runtime dependencies BEFORE any non-stdlib import.
# If any critical dep is missing, this call self-installs and os.execv's.
from mav_gss_lib.updater import bootstrap_dependencies
bootstrap_dependencies()

# Safe — all critical deps guaranteed importable past this line.
import uvicorn

from mav_gss_lib.constants import DEFAULT_MISSION
from mav_gss_lib.web_runtime.app import create_app
from mav_gss_lib.web_runtime.state import HOST, PORT

app = create_app()


def _wait_for_server_and_open(url: str, host: str, port: int, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                import webbrowser
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.1)


if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}"
    mission_name = app.state.runtime.cfg.get("general", {}).get("mission_name", "Mission")
    mission = app.state.runtime.cfg.get("general", {}).get("mission", DEFAULT_MISSION)
    print(f"{mission_name} GSS Web -> {url}")
    threading.Thread(
        target=_wait_for_server_and_open,
        args=(url, HOST, PORT),
        daemon=True,
        name=f"{mission}-web-open",
    ).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning", ws_max_size=65536)
