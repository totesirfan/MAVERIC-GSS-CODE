from queue import Empty

import pytest

from mav_gss_lib.platform.contract.packets import PacketEnvelope, PacketFlags
from mav_gss_lib.server.rx.detail_store import RxDetailStore
from mav_gss_lib.server.rx.queueing import DropOldestQueue


def _packet(event_id: str, seq: int = 1) -> PacketEnvelope:
    return PacketEnvelope(
        seq=seq,
        received_at_ms=1_700_000_000_000 + seq,
        raw=b"\x01\x02",
        payload=b"\x01\x02",
        frame_type="raw",
        transport_meta={"transmitter": "fixture"},
        warnings=[],
        mission_payload=None,
        flags=PacketFlags(),
        mission={"id": "test"},
        parameters=(),
        event_id=event_id,
    )


def test_drop_oldest_queue_makes_overload_policy_explicit():
    q = DropOldestQueue[int](maxlen=2)
    q.put(1)
    q.put(2)
    q.put(3)

    assert q.dropped_oldest == 1
    assert q.get_nowait() == 2
    assert q.get_nowait() == 3
    with pytest.raises(Empty):
        q.get_nowait()


def test_rx_detail_store_serializes_domain_packets_at_boundary():
    store = RxDetailStore(maxlen=2)
    store.append_packet(_packet("e1", 1))
    store.append_packet(_packet("e2", 2))

    replay = store.replay(replay=True)
    assert [event["packet"]["event_id"] for event in replay] == ["e1", "e2"]
    assert all(event["replay"] is True for event in replay)
    assert store.get("e1")["packet"]["raw_hex"] == "0102"


def test_rx_detail_store_eviction_updates_event_index():
    store = RxDetailStore(maxlen=1)
    store.append_packet(_packet("old", 1))
    store.append_packet(_packet("new", 2))

    assert store.get("old") is None
    assert store.get("new")["packet"]["event_id"] == "new"
