"""Platform RX runners — the inbound packet flow.

    packet_pipeline.py — PacketPipeline (dedup window, sequence, rate counters)
    events.py       — collect_connect_events + collect_packet_events
    frame_detect.py — detect_frame_type + normalize_frame + is_noise_frame
                      (transport-metadata heuristics; mission- and server-safe)
    pipeline.py     — RxPipeline + RxResult (decode-only domain pipeline)
    records.py      — immutable ingest and decoded RX record contracts

Author:  Irfan Annuar - USC ISI SERC
"""

from .events import collect_connect_events, collect_packet_events
from .frame_detect import detect_frame_type, is_noise_frame, normalize_frame
from .packet_pipeline import PacketPipeline
from .pipeline import RxPipeline, RxResult
from .records import RxDecodedRecord, RxIngestRecord, make_ingest_record

__all__ = [
    "PacketPipeline",
    "RxDecodedRecord",
    "RxIngestRecord",
    "RxPipeline",
    "RxResult",
    "collect_connect_events",
    "collect_packet_events",
    "detect_frame_type",
    "is_noise_frame",
    "make_ingest_record",
    "normalize_frame",
]
