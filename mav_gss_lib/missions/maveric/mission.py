"""MAVERIC MissionSpec entry point for platform v2.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import os
from pathlib import Path

from mav_gss_lib.missions.maveric.commands.ops import MavericCommandOps
from mav_gss_lib.missions.maveric.defaults import seed_mission_cfg
from mav_gss_lib.missions.maveric.imaging.events import MavericImagingEvents
from mav_gss_lib.missions.maveric.imaging import ImageAssembler, get_imaging_router
from mav_gss_lib.missions.maveric.nodes import init_nodes
from mav_gss_lib.missions.maveric.rx.ops import MavericPacketOps
from mav_gss_lib.missions.maveric.preflight import build_preflight
from mav_gss_lib.missions.maveric.schema import load_command_defs
from mav_gss_lib.missions.maveric.config_access import command_defs_name, image_dir, mission_name
from mav_gss_lib.missions.maveric.telemetry.ops import build_telemetry_ops
from mav_gss_lib.missions.maveric.ui.ops import MavericUiOps
from mav_gss_lib.platform import EventOps, MissionConfigSpec, MissionContext, MissionSpec
from mav_gss_lib.platform.contract.mission import HttpOps


def build(ctx: MissionContext) -> MissionSpec:
    mission_cfg = ctx.mission_config
    seed_mission_cfg(mission_cfg, ctx.platform_config)
    nodes = init_nodes(mission_cfg)
    cmd_defs, _ = load_command_defs(command_defs_name(mission_cfg), nodes=nodes)
    image_assembler = ImageAssembler(image_dir(mission_cfg))
    # Accessor closes over the live `ctx.mission_config` reference so
    # /api/config edits to `imaging.thumb_prefix` reach the imaging router
    # without a MissionSpec rebuild.
    routers = [get_imaging_router(image_assembler, config_accessor=lambda: ctx.mission_config)]

    preflight_hook = build_preflight(
        platform_config=ctx.platform_config,
        mission_config=ctx.mission_config,
        mission_dir=Path(os.path.abspath(os.path.dirname(__file__))),
    )

    return MissionSpec(
        id="maveric",
        name=mission_name(mission_cfg),
        packets=MavericPacketOps(cmd_defs=cmd_defs, nodes=nodes),
        commands=MavericCommandOps(
            cmd_defs=cmd_defs,
            nodes=nodes,
            mission_config=ctx.mission_config,
            platform_config=ctx.platform_config,
        ),
        ui=MavericUiOps(nodes=nodes),
        telemetry=build_telemetry_ops(nodes),
        events=EventOps(sources=[MavericImagingEvents(nodes=nodes, image_assembler=image_assembler)]),
        http=HttpOps(routers=routers),
        config=MissionConfigSpec(
            editable_paths={"ax25.*", "csp.*", "imaging.thumb_prefix"},
            protected_paths={
                "nodes",
                "ptypes",
                "node_descriptions",
                "gs_node",
                "mission_name",
                "command_defs",
                "command_defs_resolved",
                "command_defs_warning",
                "rx_title",
                "tx_title",
                "splash_subtitle",
            },
        ),
        preflight=preflight_hook,
    )


