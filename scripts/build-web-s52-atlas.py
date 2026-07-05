#!/usr/bin/env python3
"""Build web-consumable S-52 atlas PNG sheets + helm.s52.atlas.web.v2 manifest.

Reads web/data/s52-atlas-fixture.json, packs recognizable symbol/pattern/line/glyph
sprites per palette, writes PNGs under web/data/s52-atlas-web/.

Run from repo root: python3 scripts/build-web-s52-atlas.py
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "data" / "s52-atlas-web"
FIXTURE = ROOT / "web" / "data" / "s52-atlas-fixture.json"

PALETTES = ["day", "dusk", "night"]
PAD = 1


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    n = int(h, 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def write_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    raw = b""
    stride = width * 4
    for y in range(height):
        raw += b"\x00" + rgba[y * stride : (y + 1) * stride]
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def fill_rect(rgba: bytearray, atlas_w: int, x: int, y: int, w: int, h: int, rgb: tuple[int, int, int], a: int = 255) -> None:
    for py in range(y, y + h):
        for px in range(x, x + w):
            i = (py * atlas_w + px) * 4
            rgba[i : i + 3] = bytes(rgb)
            rgba[i + 3] = a


def draw_symbol_shape(name: str, w: int, h: int, rgb: tuple[int, int, int]) -> bytearray:
    buf = bytearray(w * h * 4)
    cx, cy = w // 2, h // 2
    if name in ("BOYSPP", "sym.boyspp"):
        # Paper-chart buoy: yellow diamond + stem
        for y in range(h):
            for x in range(w):
                dx, dy = abs(x - cx), abs(y - cy)
                if dx + dy <= cx and dy >= cy - 2:
                    i = (y * w + x) * 4
                    buf[i : i + 3] = bytes(rgb)
                    buf[i + 3] = 255
        fill_rect(buf, w, cx - 1, 0, 2, cy, (40, 40, 40))
    elif name in ("sym.hazard",):
        for y in range(h):
            for x in range(w):
                if abs(x - cx) + max(0, (y - 1) * 2) <= cx:
                    i = (y * w + x) * 4
                    buf[i : i + 3] = bytes(rgb)
                    buf[i + 3] = 255
    elif name in ("sym.sounding",):
        for y in range(h):
            for x in range(w):
                if (x - cx) ** 2 + (y - cy) ** 2 <= (min(w, h) // 2) ** 2:
                    i = (y * w + x) * 4
                    buf[i : i + 3] = bytes(rgb)
                    buf[i + 3] = 220
    else:
        fill_rect(buf, w, 0, 0, w, h, rgb)
    return buf


def draw_pattern_tile(name: str, w: int, h: int, rgb: tuple[int, int, int]) -> bytearray:
    buf = bytearray(w * h * 4)
    fill_rect(buf, w, 0, 0, w, h, rgb, 255)
    if "depare" in name or name == "DEPARE01":
        for y in range(0, h, 2):
            for x in range(y % 2, w, 2):
                i = (y * w + x) * 4
                buf[i : i + 3] = bytes(min(255, c + 20) for c in rgb)
    elif "land" in name:
        for y in range(h):
            if y % 3 == 0:
                fill_rect(buf, w, 0, y, w, 1, tuple(min(255, c + 15) for c in rgb))
    elif "dredged" in name:
        for x in range(0, w, 2):
            fill_rect(buf, w, x, 0, 1, h, tuple(max(0, c - 15) for c in rgb))
    return buf


def draw_line_stamp(w: int, h: int, rgb: tuple[int, int, int], dash: list[int]) -> bytearray:
    buf = bytearray(w * h * 4)
    cy = h // 2
    x = 0
    di = 0
    on = True
    while x < w:
        seg = dash[di % len(dash)] if dash else w
        seg = max(1, seg)
        if on:
            fill_rect(buf, w, x, cy - 1, min(seg, w - x), 2, rgb)
        x += seg
        di += 1
        on = not on
        if not dash:
            break
    return buf


GLYPHS = "0123456789.-+SYNTHEIUCBOV "


def draw_glyph(ch: str, w: int, h: int, rgb: tuple[int, int, int]) -> bytearray:
    """Minimal bitmap font cell (recognizable block glyphs)."""
    buf = bytearray(w * h * 4)
    patterns = {
        "0": ["111", "101", "101", "111"],
        "1": ["010", "110", "010", "111"],
        "2": ["111", "001", "111", "100", "111"],
        "3": ["111", "011", "001", "011", "111"],
        "4": ["101", "101", "111", "001", "001"],
        "5": ["111", "100", "111", "001", "111"],
        "6": ["111", "100", "111", "101", "111"],
        "7": ["111", "001", "010", "010", "010"],
        "8": ["111", "101", "111", "101", "111"],
        "9": ["111", "101", "111", "001", "111"],
        ".": ["0", "0", "0", "0", "010"],
        "-": ["0", "0", "111", "0", "0"],
        "+": ["0", "010", "111", "010", "0"],
    }
    pat = patterns.get(ch, patterns.get("8"))
    if not pat:
        fill_rect(buf, w, 2, 2, w - 4, h - 4, rgb, 200)
        return buf
    gh = len(pat)
    gw = max(len(row) for row in pat)
    scale_x = max(1, (w - 2) // gw)
    scale_y = max(1, (h - 2) // gh)
    for gy, row in enumerate(pat):
        for gx, c in enumerate(row):
            if c != "1":
                continue
            px = 1 + gx * scale_x
            py = 1 + gy * scale_y
            fill_rect(buf, w, px, py, scale_x, scale_y, rgb)
    return buf


def pack_sheet(entries: list[dict], draw_fn, atlas_w: int = 256) -> tuple[bytearray, int, list[dict]]:
    x = y = row_h = 0
    out_entries: list[dict] = []
    atlas = bytearray(atlas_w * 256 * 4)  # grow height as needed
    max_y = 0
    for e in entries:
        w, h = e["width"], e["height"]
        if x + w + PAD > atlas_w:
            x = 0
            y += row_h + PAD
            row_h = 0
        row_h = max(row_h, h)
        max_y = max(max_y, y + h)
        sprite = draw_fn(e)
        for sy in range(h):
            for sx in range(w):
                si = (sy * w + sx) * 4
                di = ((y + sy) * atlas_w + (x + sx)) * 4
                if di + 3 < len(atlas):
                    atlas[di : di + 4] = sprite[si : si + 4]
        uv = [
            x / atlas_w,
            y / max(max_y, 1),
            (x + w) / atlas_w,
            (y + h) / max(max_y, 1),
        ]
        out_entries.append({**e, "pixel_rect": [x, y, w, h], "uv": uv})
        x += w + PAD
    height = max(1, max_y)
    trimmed = bytearray(atlas_w * height * 4)
    for row in range(height):
        src = row * atlas_w * 4
        trimmed[row * atlas_w * 4 : (row + 1) * atlas_w * 4] = atlas[src : src + atlas_w * 4]
    # Recompute UV with final height
    for ent in out_entries:
        pr = ent["pixel_rect"]
        ent["uv"] = [pr[0] / atlas_w, pr[1] / height, (pr[0] + pr[2]) / atlas_w, (pr[1] + pr[3]) / height]
    return trimmed, height, out_entries


def main() -> None:
    spec = json.loads(FIXTURE.read_text())
    entries = spec.get("entries", [])
    # Add font atlas entries (glyph cells)
    glyph_entries = []
    for ch in GLYPHS:
        if ch == " ":
            continue
        glyph_entries.append(
            {
                "name": f"glyph.{ch}",
                "kind": "glyph",
                "width": 8,
                "height": 12,
                "anchor": [0, 10],
                "char": ch,
                "colors": {"day": "#1b2a36", "dusk": "#8fa2ad", "night": "#9fb6c4"},
            }
        )
    font_entry = {
        "name": "font.chart-label",
        "kind": "font",
        "width": 8,
        "height": 12,
        "anchor": [0, 10],
        "glyph_prefix": "glyph.",
        "colors": {"day": "#1b2a36", "dusk": "#8fa2ad", "night": "#9fb6c4"},
    }

    manifest = {
        "schema_version": "helm.s52.atlas.web.v2",
        "generator": "scripts/build-web-s52-atlas.py",
        "palettes": PALETTES,
        "atlases": [],
        "entries": [],
        "ref_aliases": {
            "sym.boyspp": "BOYSPP",
            "line.depth-contour": "DEPCNT02",
            "area.depare": "DEPARE01",
            "pattern.depare": "DEPARE01",
        },
    }

    for palette in PALETTES:
        for kind in ("symbol", "pattern", "line", "glyph"):
            kind_entries = [e for e in entries if e.get("kind") == kind]
            if kind == "glyph":
                kind_entries = glyph_entries
            if not kind_entries:
                continue

            def make_draw_fn(palette_name: str, kind_name: str):
                def draw_one(ent: dict) -> bytearray:
                    rgb = hex_rgb((ent.get("colors") or {}).get(palette_name, "#888888"))
                    w, h = ent["width"], ent["height"]
                    if kind_name == "symbol":
                        return draw_symbol_shape(ent["name"], w, h, rgb)
                    if kind_name == "pattern":
                        return draw_pattern_tile(ent["name"], w, h, rgb)
                    if kind_name == "line":
                        return draw_line_stamp(w, h, rgb, ent.get("dash") or [])
                    ch = ent.get("char", "?")
                    return draw_glyph(ch, w, h, rgb)

                return draw_one

            rgba, height, packed = pack_sheet(kind_entries, make_draw_fn(palette, kind))
            image_name = f"s52_{kind}s_{palette}.png"
            image_path = OUT / image_name
            write_png(image_path, 256, height, bytes(rgba))
            atlas_id = f"atlas.{kind}.{palette}"
            manifest["atlases"].append(
                {
                    "atlas_id": atlas_id,
                    "kind": kind,
                    "palette": palette,
                    "image": f"data/s52-atlas-web/{image_name}",
                    "format": "png-rgba",
                    "width": 256,
                    "height": height,
                }
            )
            for ent in packed:
                manifest["entries"].append(
                    {
                        "name": ent["name"],
                        "kind": kind if kind != "glyph" else "glyph",
                        "palette": palette,
                        "atlas_id": atlas_id,
                        "pixel_rect": ent["pixel_rect"],
                        "uv": ent["uv"],
                        "anchor": ent.get("anchor", [0, 0]),
                        "repeat": ent.get("repeat", [0, 0]),
                        "dash": ent.get("dash", []),
                        "char": ent.get("char"),
                    }
                )

    manifest["entries"].append(
        {
            "name": "font.chart-label",
            "kind": "font",
            "palette": "day",
            "atlas_id": "atlas.glyph.day",
            "glyph_prefix": "glyph.",
            "anchor": font_entry["anchor"],
        }
    )
    for palette in ("dusk", "night"):
        manifest["entries"].append(
            {
                "name": "font.chart-label",
                "kind": "font",
                "palette": palette,
                "atlas_id": f"atlas.glyph.{palette}",
                "glyph_prefix": "glyph.",
                "anchor": font_entry["anchor"],
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"ok wrote {OUT / 'manifest.json'} ({len(manifest['entries'])} entries, {len(manifest['atlases'])} atlases)")


if __name__ == "__main__":
    main()
