from dataclasses import dataclass
from typing import Iterable

from mav_gss_lib.platform import MissionConfigSpec, MissionSpec, TelemetryDomainSpec, TelemetryOps
from mav_gss_lib.platform.loader import load_mission_spec
from mav_gss_lib.platform.packet_pipeline import PacketPipeline
from mav_gss_lib.platform.telemetry_pipeline import extract_telemetry_fragments, ingest_packet_telemetry
from mav_gss_lib.platform.telemetry import TelemetryFragment
from mav_gss_lib.platform.telemetry.router import TelemetryRouter
from mav_gss_lib.missions.echo_v2.mission import EchoPacketOps, EchoUiOps


def test_telemetry_pipeline_extracts_and_ingests_balloon_fragments(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "balloon_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    router = TelemetryRouter(tmp_path)
    assert spec.telemetry is not None
    for name, domain in spec.telemetry.domains.items():
        router.register_domain(name, **domain.router_kwargs())

    packet = PacketPipeline(spec).process(
        {},
        b'{"type":"beacon","alt_m":1200,"lat":34.0,"lon":-118.2,"temp_c":18.4}',
    )
    fragments = extract_telemetry_fragments(spec, packet)
    messages = ingest_packet_telemetry(router, packet)

    assert packet.telemetry == fragments
    assert {f.domain for f in fragments} == {"environment", "position"}
    assert {m["domain"] for m in messages} == {"environment", "position"}
    env_msg = next(m for m in messages if m["domain"] == "environment")
    assert env_msg["changes"]["altitude_m"]["v"] == 1200


def test_telemetry_pipeline_noops_when_mission_has_no_telemetry(tmp_path):
    spec = load_mission_spec(
        {"mission": {"id": "echo_v2", "config": {}}, "platform": {}},
        data_dir=tmp_path,
    )
    packet = PacketPipeline(spec).process({}, b"hello")

    fragments = extract_telemetry_fragments(spec, packet)

    assert fragments == []
    assert packet.telemetry == []


@dataclass(frozen=True, slots=True)
class ExplodingExtractor:
    def extract(self, packet) -> Iterable[TelemetryFragment]:
        raise RuntimeError("boom")


@dataclass(frozen=True, slots=True)
class GoodExtractor:
    def extract(self, packet) -> Iterable[TelemetryFragment]:
        return [TelemetryFragment("health", "ok", True, packet.received_at_ms)]


def test_telemetry_pipeline_isolates_extractor_failures(tmp_path, caplog):
    spec = MissionSpec(
        id="mixed_telemetry",
        name="Mixed Telemetry",
        packets=EchoPacketOps(),
        ui=EchoUiOps(),
        config=MissionConfigSpec(),
        telemetry=TelemetryOps(
            domains={"health": TelemetryDomainSpec()},
            extractors=[ExplodingExtractor(), GoodExtractor()],
        ),
    )
    packet = PacketPipeline(spec).process({}, b"x")

    fragments = extract_telemetry_fragments(spec, packet)

    assert fragments == [TelemetryFragment("health", "ok", True, packet.received_at_ms)]
    assert "Telemetry extractor failed" in caplog.text
