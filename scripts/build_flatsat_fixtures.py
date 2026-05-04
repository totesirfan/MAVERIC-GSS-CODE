#!/usr/bin/env python3
"""Generate fixture files served by ``fake_flight.py`` for file-chunk tests.

Outputs:
    fake_flight_fixtures/test.jpg     320x240 engineering test card
    fake_flight_fixtures/tn_test.jpg   80x60  thumb of the same card
    fake_flight_fixtures/test.json    small valid JSON for AII flow
    fake_flight_fixtures/test.nvg     small NVG-shaped binary for Mag flow

Run once and commit the outputs alongside this script. Re-run only if you
want to refresh the fixtures.

Author:  Irfan Annuar - USC ISI SERC
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FIXTURE_DIR = Path(__file__).resolve().parent / "fake_flight_fixtures"

# SMPTE-style top-row bars, left to right.
SMPTE_BARS: list[tuple[int, int, int]] = [
    (192, 192, 192),  # 75% white
    (192, 192,   0),  # yellow
    (  0, 192, 192),  # cyan
    (  0, 192,   0),  # green
    (192,   0, 192),  # magenta
    (192,   0,   0),  # red
    (  0,   0, 192),  # blue
    ( 16,  16,  16),  # near-black
]


def _safe_font(size: int) -> ImageFont.ImageFont:
    """Load a TTF if any of a few common system fonts are reachable; else
    fall back to PIL's bitmap default."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def _draw_color_bars(draw: ImageDraw.ImageDraw, x: int, y: int,
                     w: int, h: int) -> None:
    n = len(SMPTE_BARS)
    bar_w = w / n
    for i, color in enumerate(SMPTE_BARS):
        x0 = int(x + i * bar_w)
        x1 = int(x + (i + 1) * bar_w)
        draw.rectangle([x0, y, x1, y + h], fill=color)


def _draw_grayscale_ramp(draw: ImageDraw.ImageDraw, x: int, y: int,
                         w: int, h: int) -> None:
    for px in range(w):
        v = int(round(255 * px / max(1, w - 1)))
        draw.line([(x + px, y), (x + px, y + h)], fill=(v, v, v))


def _draw_resolution_wedge(draw: ImageDraw.ImageDraw, x: int, y: int,
                           w: int, h: int) -> None:
    """Vertical lines that get progressively closer — pseudo-resolution wedge."""
    spacing = max(1, w // 32)
    px = 0
    while px < w:
        sp = max(1, spacing - (px * spacing) // w)
        draw.line([(x + px, y), (x + px, y + h)], fill=(240, 240, 240))
        px += sp + 1


def _draw_corner_brackets(draw: ImageDraw.ImageDraw, w: int, h: int,
                          length: int = 14, color=(255, 255, 0)) -> None:
    pad = 4
    pts = [(pad, pad), (w - pad - 1, pad),
           (pad, h - pad - 1), (w - pad - 1, h - pad - 1)]
    for cx, cy in pts:
        dx = -1 if cx > w / 2 else 1
        dy = -1 if cy > h / 2 else 1
        draw.line([(cx, cy), (cx + dx * length, cy)], fill=color, width=2)
        draw.line([(cx, cy), (cx, cy + dy * length)], fill=color, width=2)


def _draw_crosshair(draw: ImageDraw.ImageDraw, w: int, h: int,
                    span: int = 18, color=(255, 64, 64)) -> None:
    cx, cy = w // 2, h // 2
    draw.line([(cx - span, cy), (cx + span, cy)], fill=color, width=2)
    draw.line([(cx, cy - span), (cx, cy + span)], fill=color, width=2)
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=color, width=1)


def _draw_text(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int],
               font: ImageFont.ImageFont, color=(255, 255, 255),
               shadow=(0, 0, 0)) -> None:
    x, y = xy
    draw.text((x + 1, y + 1), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=color)


def _build_card(width: int, height: int) -> Image.Image:
    """Engineering test card with SMPTE bars, ramp, wedge, crosshair, labels."""
    img = Image.new("RGB", (width, height), (8, 8, 12))
    draw = ImageDraw.Draw(img)

    bars_h = int(height * 0.45)
    _draw_color_bars(draw, 0, 0, width, bars_h)

    ramp_h = max(8, int(height * 0.10))
    _draw_grayscale_ramp(draw, 0, bars_h, width, ramp_h)

    wedge_y = bars_h + ramp_h
    wedge_h = max(10, int(height * 0.18))
    _draw_resolution_wedge(draw, 0, wedge_y, width, wedge_h)
    draw.line([(0, wedge_y - 1), (width, wedge_y - 1)],
              fill=(64, 64, 64), width=1)
    draw.line([(0, wedge_y + wedge_h), (width, wedge_y + wedge_h)],
              fill=(64, 64, 64), width=1)

    label_font = _safe_font(max(10, height // 16))
    small_font = _safe_font(max(8, height // 22))
    title_y = wedge_y + wedge_h + 6
    _draw_text(draw, "MAVERIC TEST CARD", (8, title_y), label_font,
               color=(255, 235, 80))
    _draw_text(draw, "FLATSAT FIXTURE", (8, title_y + label_font.size + 4),
               small_font, color=(220, 220, 220))
    _draw_text(draw, f"{width}x{height} JPEG / Q70",
               (8, title_y + label_font.size + small_font.size + 8),
               small_font, color=(160, 200, 255))
    iso = (_dt.datetime.now(_dt.timezone.utc)
           .replace(microsecond=0, tzinfo=None).isoformat() + "Z")
    _draw_text(draw, iso,
               (8, title_y + label_font.size + 2 * small_font.size + 12),
               small_font, color=(120, 200, 160))

    _draw_corner_brackets(draw, width, height)
    _draw_crosshair(draw, width, height)

    return img


def _save_jpeg(img: Image.Image, path: Path, quality: int = 70) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=quality, optimize=True)
    return path.stat().st_size


def _build_aii_json() -> bytes:
    """Small valid JSON document representative of an AII downlink."""
    payload = {
        "instrument": "AII",
        "fixture": "flatsat",
        "ts_utc": (_dt.datetime.now(_dt.timezone.utc)
                   .replace(microsecond=0, tzinfo=None).isoformat() + "Z"),
        "ops_stage": "SUN_POINT",
        "samples": [
            {"i": i, "v": round(math.sin(i / 3.0) * 0.5 + 0.5, 4)}
            for i in range(24)
        ],
        "status": "ok",
    }
    return json.dumps(payload, indent=2).encode("ascii")


def _build_mag_nvg() -> bytes:
    """Plausible NVG-shaped binary: 16-byte header + N triaxis float vectors.

    Header layout (little-endian):
        magic 'NVG1' (4) | version u16 | sensor_id u16 | nsamp u32 | rate_hz u32
    Body:
        repeat nsamp times: ts_ms u32 | x f32 | y f32 | z f32 | reserved u32
    """
    nsamp = 32
    rate_hz = 10
    body = bytearray()
    for i in range(nsamp):
        ts_ms = i * (1000 // rate_hz)
        ang = i / 6.0
        x = math.cos(ang) * 25.0
        y = math.sin(ang) * 25.0
        z = 8.0 + math.sin(ang / 2.0) * 1.5
        body += struct.pack("<Ifffi", ts_ms, x, y, z, 0)
    header = b"NVG1" + struct.pack("<HHII", 1, 7, nsamp, rate_hz)
    return bytes(header) + bytes(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=320,
                        help="Full-image width (default 320)")
    parser.add_argument("--height", type=int, default=240,
                        help="Full-image height (default 240)")
    parser.add_argument("--thumb-width", type=int, default=80)
    parser.add_argument("--thumb-height", type=int, default=60)
    parser.add_argument("--quality", type=int, default=70)
    parser.add_argument("--thumb-quality", type=int, default=60)
    parser.add_argument("--out", type=Path, default=FIXTURE_DIR)
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    full = _build_card(args.width, args.height)
    full_path = out / "test.jpg"
    full_size = _save_jpeg(full, full_path, quality=args.quality)
    print(f"  test.jpg     {args.width}x{args.height}  q={args.quality}  {full_size:,} B")

    thumb = _build_card(args.thumb_width, args.thumb_height)
    thumb_path = out / "tn_test.jpg"
    thumb_size = _save_jpeg(thumb, thumb_path, quality=args.thumb_quality)
    print(f"  tn_test.jpg  {args.thumb_width}x{args.thumb_height}  q={args.thumb_quality}  {thumb_size:,} B")

    aii_path = out / "test.json"
    aii_bytes = _build_aii_json()
    aii_path.write_bytes(aii_bytes)
    print(f"  test.json        {len(aii_bytes):,} B")

    mag_path = out / "test.nvg"
    mag_bytes = _build_mag_nvg()
    mag_path.write_bytes(mag_bytes)
    print(f"  test.nvg         {len(mag_bytes):,} B")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
