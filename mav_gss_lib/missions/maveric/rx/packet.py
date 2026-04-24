"""Native MAVERIC v2 RX packet view.

`MavericRxPacket` is the internal view MAVERIC rendering / log formatting /
telemetry extraction operate on. It wraps a platform `PacketEnvelope` and
exposes the attribute surface the MAVERIC-internal helpers read:

- `pkt_num`, `gs_ts`, `gs_ts_short`, `frame_type`, `raw`, `inner_payload`
  — platform-owned packet metadata.
- `mission_data`, `stripped_hdr` — mission-owned parse output produced by
  `packet_ops.parse`.
- `is_dup`, `is_uplink_echo`, `is_unknown` — classification flags set by
  `packet_ops.classify`.
- `fragments` — decoded telemetry fragments attached to the envelope by
  `telemetry_ops.MavericTelemetryExtractor.extract`. First-class on the
  view so rendering / log formatting never reach into `mission_data` for
  them.

The view performs no mutation of the underlying envelope. Fragments are
copied as dicts at construction so callers downstream can rely on the
shape they used to read from `mission_data["fragments"]`.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

from dataclasses import dataclass

from mav_gss_lib.platform import PacketEnvelope


@dataclass(frozen=True, slots=True)
class MavericRxPacket:
    envelope: PacketEnvelope
    fragments: tuple[dict, ...] = ()

    @classmethod
    def from_envelope(cls, envelope: PacketEnvelope) -> MavericRxPacket:
        frags = tuple(fragment.to_dict() for fragment in envelope.telemetry)
        return cls(envelope=envelope, fragments=frags)

    @property
    def pkt_num(self) -> int:
        return self.envelope.seq

    @property
    def gs_ts(self) -> str:
        return self.envelope.received_at_text

    @property
    def gs_ts_short(self) -> str:
        return self.envelope.received_at_short

    @property
    def frame_type(self) -> str:
        return self.envelope.frame_type

    @property
    def raw(self) -> bytes:
        return self.envelope.raw

    @property
    def inner_payload(self) -> bytes:
        return self.envelope.payload

    @property
    def mission_data(self) -> dict:
        payload = self.envelope.mission_payload
        return payload if isinstance(payload, dict) else {}

    @property
    def stripped_hdr(self) -> str | None:
        return self.mission_data.get("stripped_hdr")

    @property
    def is_dup(self) -> bool:
        return self.envelope.flags.is_duplicate

    @property
    def is_uplink_echo(self) -> bool:
        return self.envelope.flags.is_uplink_echo

    @property
    def is_unknown(self) -> bool:
        return self.envelope.flags.is_unknown
