"""Platform v2 mission API.

`MissionSpec` is the single mission/platform boundary consumed by
`WebRuntime` and every production code path. Missions live under
`mav_gss_lib.missions.<id>` and are loaded via
`PlatformRuntimeV2.from_split`.

Author:  Irfan Annuar - USC ISI SERC
"""

from .command_pipeline import CommandRejected, PreparedCommand, prepare_command
from .commands import CommandDraft, CommandOps, CommandRendering, EncodedCommand, FramedCommand, ValidationIssue
from .config_boundary import (
    DEFAULT_PLATFORM_CONFIG_SPEC,
    PlatformConfigSpec,
    apply_mission_config_update,
    apply_platform_config_update,
    persist_mission_config,
)
from .events import EventOps, PacketEventSource
from .event_pipeline import collect_connect_events, collect_packet_events
from .loader import load_mission_spec, load_mission_spec_from_split, validate_mission_spec
from .logging import build_rx_log_record, format_rx_text_lines
from .mission_api import MissionConfigSpec, MissionContext, MissionSpec
from .packet_pipeline import PacketPipeline
from .packets import MissionPacket, NormalizedPacket, PacketEnvelope, PacketFlags, PacketOps
from .rendering import Cell, ColumnDef, DetailBlock, IntegrityBlock, PacketRendering
from .runtime import PlatformRuntimeV2
from .rx_pipeline import RxPipelineV2, RxResult
from .telemetry import TelemetryDomainSpec, TelemetryExtractor, TelemetryOps
from .telemetry_pipeline import extract_telemetry_fragments, ingest_packet_telemetry

__all__ = [
    "Cell",
    "ColumnDef",
    "CommandDraft",
    "CommandOps",
    "CommandRejected",
    "CommandRendering",
    "DEFAULT_PLATFORM_CONFIG_SPEC",
    "DetailBlock",
    "EncodedCommand",
    "EventOps",
    "FramedCommand",
    "IntegrityBlock",
    "MissionConfigSpec",
    "MissionContext",
    "MissionPacket",
    "MissionSpec",
    "NormalizedPacket",
    "PacketEnvelope",
    "PacketEventSource",
    "PacketFlags",
    "PacketOps",
    "PacketPipeline",
    "PacketRendering",
    "PlatformConfigSpec",
    "PlatformRuntimeV2",
    "PreparedCommand",
    "RxPipelineV2",
    "RxResult",
    "TelemetryDomainSpec",
    "TelemetryExtractor",
    "TelemetryOps",
    "ValidationIssue",
    "apply_mission_config_update",
    "apply_platform_config_update",
    "persist_mission_config",
    "build_rx_log_record",
    "collect_connect_events",
    "collect_packet_events",
    "extract_telemetry_fragments",
    "format_rx_text_lines",
    "ingest_packet_telemetry",
    "load_mission_spec",
    "load_mission_spec_from_split",
    "prepare_command",
    "validate_mission_spec",
]
