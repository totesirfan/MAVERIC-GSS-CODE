"""Platform v2 runtime container used by the production web runtime.

Loads the active MissionSpec, registers mission telemetry domains, processes
RX through RxPipelineV2, and prepares TX commands through CommandOps.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mav_gss_lib.web_runtime.telemetry.router import TelemetryRouter

from .command_pipeline import PreparedCommand, frame_command, prepare_command
from .commands import EncodedCommand, FramedCommand
from .loader import load_mission_spec_from_split
from .mission_api import MissionSpec
from .rx_pipeline import RxPipelineV2, RxResult


def _resolve_log_dir(platform_cfg: dict[str, Any]) -> str:
    general = platform_cfg.get("general") or {}
    log_dir = general.get("log_dir")
    if log_dir:
        return str(log_dir)
    logs_block = platform_cfg.get("logs") or {}
    return str(logs_block.get("dir", "logs"))


@dataclass(slots=True)
class PlatformRuntimeV2:
    mission: MissionSpec
    telemetry: TelemetryRouter
    rx: RxPipelineV2

    @classmethod
    def from_split(
        cls,
        platform_cfg: dict[str, Any],
        mission_id: str,
        mission_cfg: dict[str, Any],
    ) -> "PlatformRuntimeV2":
        """Build the platform v2 runtime from split operator state."""
        log_dir = _resolve_log_dir(platform_cfg)
        mission = load_mission_spec_from_split(
            platform_cfg, mission_id, mission_cfg, data_dir=Path(log_dir),
        )
        telemetry = TelemetryRouter(Path(log_dir) / ".telemetry")
        if mission.telemetry is not None:
            for name, domain in mission.telemetry.domains.items():
                telemetry.register_domain(name, **domain.router_kwargs())
        return cls(
            mission=mission,
            telemetry=telemetry,
            rx=RxPipelineV2(mission, telemetry),
        )

    def process_rx(self, meta: dict[str, Any], raw: bytes) -> RxResult:
        return self.rx.process(meta, raw)

    def prepare_tx(self, value: str | dict[str, Any]) -> PreparedCommand:
        return prepare_command(self.mission, value)

    def frame_tx(self, encoded: EncodedCommand) -> FramedCommand:
        return frame_command(self.mission, encoded)
