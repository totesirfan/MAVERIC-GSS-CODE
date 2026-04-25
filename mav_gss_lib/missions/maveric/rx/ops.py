"""MAVERIC PacketOps implementation.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mav_gss_lib.missions.maveric.rx import parser as rx_ops
from mav_gss_lib.missions.maveric.ui import log_format
from mav_gss_lib.missions.maveric.nodes import NodeTable
from mav_gss_lib.platform import MissionPacket, NormalizedPacket, PacketFlags, PacketOps


@dataclass(frozen=True, slots=True)
class MavericPacketOps(PacketOps):
    cmd_defs: dict
    nodes: NodeTable

    def normalize(self, meta: dict[str, Any], raw: bytes) -> NormalizedPacket:
        frame_type = rx_ops.detect(meta)
        payload, stripped_hdr, warnings = rx_ops.normalize(frame_type, raw)
        return NormalizedPacket(
            raw=raw,
            payload=payload,
            frame_type=frame_type,
            stripped_header=stripped_hdr,
            warnings=list(warnings),
        )

    def parse(self, normalized: NormalizedPacket) -> MissionPacket:
        parsed = rx_ops.parse_packet(normalized.payload, self.cmd_defs, list(normalized.warnings))
        mission_data = dict(parsed.mission_data)
        mission_data["stripped_hdr"] = normalized.stripped_header
        return MissionPacket(payload=mission_data, warnings=list(parsed.warnings))

    def classify(self, packet: MissionPacket) -> PacketFlags:
        mission_data = packet.payload if isinstance(packet.payload, dict) else {}
        return PacketFlags(
            duplicate_key=rx_ops.duplicate_fingerprint(mission_data),
            is_unknown=log_format.is_unknown_packet(mission_data),
            is_uplink_echo=rx_ops.is_uplink_echo(mission_data, self.nodes.gs_node),
        )

    def match_verifiers(
        self,
        envelope,                # PacketEnvelope (duck-typed — only .mission_payload is read)
        open_instances,          # list[CommandInstance]
        *,
        now_ms: int,
        rx_event_id: str = "",
    ):
        from mav_gss_lib.platform.tx.verifiers import VerifierOutcome

        mp = getattr(envelope, "mission_payload", None)
        if not isinstance(mp, dict):
            return []
        cmd = mp.get("cmd") or {}
        cmd_id = cmd.get("cmd_id")
        src_id = cmd.get("src")
        ptype_id = cmd.get("pkt_type")
        if not cmd_id or src_id is None or ptype_id is None:
            return []

        # NodeTable API (missions/maveric/nodes.py):
        #   .node_names: dict[int, str]     (int -> str)
        #   .ptype_names: dict[int, str]    (int -> str)
        #   .node_name(id:int) -> str       (accessor; falls back to str(id))
        #   .ptype_name(id:int) -> str      (accessor; falls back to str(id))
        # Use the dict membership check to reject unknown ids (the accessors'
        # string-fallback would turn "5" into a pseudo-ptype and mismatch).
        src_name = self.nodes.node_name(src_id) if src_id in self.nodes.node_names else None
        ptype_name = self.nodes.ptype_name(ptype_id) if ptype_id in self.nodes.ptype_names else None
        if not src_name or not ptype_name:
            return []
        src_lower = src_name.lower()

        # Filter candidates by cmd_id, sort newest-first.
        candidates = [i for i in open_instances if i.correlation_key and i.correlation_key[0] == cmd_id]
        candidates.sort(key=lambda i: i.t0_ms, reverse=True)
        if not candidates:
            return []

        # Map (ptype_name, src_name) → expected verifier_id.
        if ptype_name == "ACK":
            expected = f"{src_lower}_ack"
        elif ptype_name == "RES":
            expected = f"res_from_{src_lower}"
        elif ptype_name == "NACK":
            expected = f"nack_{src_lower}"
        elif ptype_name == "TLM":
            # The TLM-as-completion override (e.g. eps_hk) registers a
            # verifier_id of the form `tlm_<cmd_id>` via apply_override —
            # match by cmd_id directly rather than by telemetry-fragment
            # bridge.
            expected = f"tlm_{cmd_id}"
        else:
            # CMD/FILE/other types produce no verifier transition.
            return []

        # Claim in the newest matching instance that carries this verifier_id.
        for inst in candidates:
            if any(v.verifier_id == expected for v in inst.verifier_set.verifiers):
                return [(
                    inst.instance_id, expected,
                    VerifierOutcome.passed(matched_at_ms=now_ms, match_event_id=rx_event_id),
                )]
        return []
