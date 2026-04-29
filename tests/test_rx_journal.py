import json
import struct

from mav_gss_lib.platform.rx.records import make_ingest_record
from mav_gss_lib.server.rx.journal import RxIngestJournal


def test_rx_ingest_journal_writes_length_prefixed_records(tmp_path):
    path = tmp_path / "session.rxj"
    journal = RxIngestJournal(path)
    record = make_ingest_record(
        2,
        {"transmitter": "fixture"},
        b"\x01\x02\x03",
        event_id="a" * 32,
        received_at_ms=1_700_000_000_000,
        received_mono_ns=99,
    )

    journal.append(record)
    journal.close()

    data = path.read_bytes()
    assert data[:4] == b"RXJ1"
    meta_len, raw_len = struct.unpack("<II", data[4:12])
    meta = json.loads(data[12:12 + meta_len])
    raw = data[12 + meta_len:12 + meta_len + raw_len]
    assert meta["event_id"] == "a" * 32
    assert meta["received_at_ms"] == 1_700_000_000_000
    assert meta["transport_meta"]["transmitter"] == "fixture"
    assert raw == b"\x01\x02\x03"


def test_rx_ingest_journal_rename_preserves_stream_and_continues(tmp_path):
    first = tmp_path / "session.rxj"
    second = tmp_path / "session_renamed.rxj"
    journal = RxIngestJournal(first)
    journal.append(make_ingest_record(
        1,
        {"transmitter": "before"},
        b"\x01",
        event_id="b" * 32,
        received_at_ms=1,
        received_mono_ns=10,
    ))

    journal.rename(second)
    journal.append(make_ingest_record(
        1,
        {"transmitter": "after"},
        b"\x02",
        event_id="c" * 32,
        received_at_ms=2,
        received_mono_ns=20,
    ))
    journal.close()

    assert not first.exists()
    data = second.read_bytes()
    assert data[:4] == b"RXJ1"
    offset = 4
    metas = []
    raws = []
    while offset < len(data):
        meta_len, raw_len = struct.unpack("<II", data[offset:offset + 8])
        offset += 8
        metas.append(json.loads(data[offset:offset + meta_len]))
        offset += meta_len
        raws.append(data[offset:offset + raw_len])
        offset += raw_len

    assert [m["event_id"] for m in metas] == ["b" * 32, "c" * 32]
    assert [m["transport_meta"]["transmitter"] for m in metas] == ["before", "after"]
    assert raws == [b"\x01", b"\x02"]
