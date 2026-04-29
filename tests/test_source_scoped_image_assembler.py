from mav_gss_lib.missions.maveric.imaging import ImageAssembler


def test_same_filename_is_scoped_by_imaging_source(tmp_path):
    asm = ImageAssembler(output_dir=str(tmp_path))
    asm.set_total("capture.jpg", 84, source="HLNV")
    asm.set_total("capture.jpg", 120, source="ASTR")

    pairs = sorted(
        asm.paired_status(prefix="thumb_")["files"],
        key=lambda p: p["source"],
    )

    assert len(pairs) == 2
    assert [(p["source"], p["id"], p["full"]["total"]) for p in pairs] == [
        ("ASTR", "ASTR/capture.jpg", 120),
        ("HLNV", "HLNV/capture.jpg", 84),
    ]
    assert pairs[0]["stem"] == pairs[1]["stem"] == "capture.jpg"


def test_chunks_and_outputs_are_scoped_by_imaging_source(tmp_path):
    asm = ImageAssembler(output_dir=str(tmp_path))
    asm.set_total("capture.jpg", 1, source="HLNV")
    asm.set_total("capture.jpg", 1, source="ASTR")

    asm.feed_chunk("capture.jpg", 0, b"\xff\xd8hlnv", chunk_size=6, source="HLNV")
    asm.feed_chunk("capture.jpg", 0, b"\xff\xd8astr", chunk_size=6, source="ASTR")

    assert (tmp_path / "HLNV" / "capture.jpg").read_bytes() == b"\xff\xd8hlnv\xff\xd9"
    assert (tmp_path / "ASTR" / "capture.jpg").read_bytes() == b"\xff\xd8astr\xff\xd9"
    assert asm.progress("capture.jpg", source="HLNV") == (1, 1)
    assert asm.progress("capture.jpg", source="ASTR") == (1, 1)
