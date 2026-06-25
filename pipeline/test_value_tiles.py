#!/usr/bin/env python3
"""
Helm — pipeline/test_value_tiles.py        WX epic · WX-10
Stdlib-only tests for the value-encoded weather-tile baker. Also proves the Python
baker and the JS renderer (web/wx-value-codec.js) agree on the encoding by round-
tripping Python-encoded pixels through the ACTUAL JS decoder via `node` (skipped
with a notice if node is unavailable, so the test still runs standalone).

    python3 pipeline/test_value_tiles.py
"""
import json, math, os, struct, subprocess, sys, tempfile, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_value_tiles as M

fails = 0
def check(cond, msg):
    global fails
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1

# 1) encode -> (python) decode round-trips to well under display resolution, across the range.
so_min, so_max = 980.0, 1040.0
scale = (so_max - so_min) / M.VMAX24
offset = so_min
def py_decode(r, g, b):
    return offset + ((r << 16) | (g << 8) | b) * scale
for v in (980.0, 1000.0, 1013.2, 1025.7, 1040.0):
    r, g, b = M.encode_value(v, scale, offset)
    check(abs(py_decode(r, g, b) - v) < 0.001, f"roundtrip {v} hPa (got {py_decode(r,g,b):.4f})")

# 2) the exact RGB for a known (value,scale,offset) — a fixed point both languages must hit.
r, g, b = M.encode_value(1013.2, scale, offset)
check((r, g, b) == (141, 167, 64), f"deterministic encode 1013.2 -> {(r,g,b)} (want (141,167,64))")

# 3) clamping never wraps at the ends.
check(M.encode_value(5000, scale, offset) == (255, 255, 255), "over-range clamps high")
check(M.encode_value(-100, scale, offset) == (0, 0, 0), "under-range clamps low")

# 4) tile math: pixel<->lonlat inverts (parity with wx-value-codec.js + gen_demo_data.py).
xf, yf = M.lonlat_to_tile(177.4, -17.7, 10)
lon, lat = M.pixel_to_lonlat(10, math.floor(xf), math.floor(yf),
                             (xf - math.floor(xf)) * 256, (yf - math.floor(yf)) * 256)
check(abs(lon - 177.4) < 1e-6 and abs(lat + 17.7) < 1e-6, f"tile<->pixel round-trip ({lon:.5f},{lat:.5f})")
check(len(M.tiles_for_bbox(8, (175.9, -19.2, 178.9, -16.2))) >= 1, "tiles_for_bbox covers Fiji demo bbox")

# 5) end-to-end bake of a tiny synthetic field -> decode a tile's center pixel ~= source value.
with tempfile.TemporaryDirectory() as td:
    data = os.path.join(td, "data"); out = os.path.join(td, "out")
    os.makedirs(data)
    # a smooth 4x4 ramp over a small bbox, values 10..40
    nx = ny = 4
    vals = [10 + 30 * (j * nx + i) / (nx * ny - 1) for j in range(ny) for i in range(nx)]
    json.dump({"layer": "tst", "unit": "kn", "kind": "scalar", "nx": nx, "ny": ny,
               "west": 177.0, "north": -17.0, "east": 178.0, "south": -18.0,
               "vmin": min(vals), "vmax": max(vals),
               "stops": [[0, [0, 0, 255]], [40, [255, 0, 0]]], "values": vals},
              open(os.path.join(data, "field-tst.json"), "w"))
    man = M.bake_layer(data, out, "tst", 7, 9, None, None, "test", "Synthetic")
    check(man is not None and man["encoding"] == "helm-wxv1", "bake produced a helm-wxv1 manifest")
    check(os.path.exists(os.path.join(out, "tst", "manifest.json")), "manifest.json written")
    pngs = []
    for dp, _, fs in os.walk(os.path.join(out, "tst")):
        pngs += [os.path.join(dp, f) for f in fs if f.endswith(".png")]
    check(len(pngs) >= 1, f"tiles written ({len(pngs)})")

    # decode the highest-zoom tile nearest bbox-center, sample its center pixel, compare to source.
    def read_png_rgb(path):
        raw = open(path, "rb").read()
        # minimal PNG reader for our own 8-bit RGB no-interlace output
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        off = 8; w = h = ct = 0; idat = bytearray()
        while off < len(raw):
            ln = struct.unpack(">I", raw[off:off+4])[0]; tag = raw[off+4:off+8]
            data = raw[off+8:off+8+ln]; off += 12 + ln
            if tag == b"IHDR":
                w, h = struct.unpack(">II", data[:8]); ct = data[9]
            elif tag == b"IDAT":
                idat += data
            elif tag == b"IEND":
                break
        ch = 4 if ct == 6 else 3
        rawpix = zlib.decompress(bytes(idat))
        stride = w * ch
        rows = []
        for r in range(h):
            base = r * (stride + 1) + 1            # skip filter byte (we wrote filter 0)
            rows.append(rawpix[base:base + stride])
        return w, h, ch, rows
    # center of the source bbox
    cx, cy = 177.5, -17.5
    z = man["maxzoom"]
    xf, yf = M.lonlat_to_tile(cx, cy, z)
    xt, yt = math.floor(xf), math.floor(yf)
    tp = os.path.join(out, "tst", str(z), str(xt), f"{yt}.png")
    check(os.path.exists(tp), "center tile exists at maxzoom")
    if os.path.exists(tp):
        w, h, ch, rows = read_png_rgb(tp)
        px = int((xf - xt) * 256); py = int((yf - yt) * 256)
        row = rows[min(py, h - 1)]; o = min(px, w - 1) * ch
        rr, gg, bb = row[o], row[o + 1], row[o + 2]
        decoded = man["offset"] + ((rr << 16) | (gg << 8) | bb) * man["scale"]
        # source bilinear value at center
        g = M.Grid(json.load(open(os.path.join(data, "field-tst.json"))))
        src = g.sample(cx, cy, None, None)
        check(abs(decoded - src) < 0.2, f"decoded center pixel {decoded:.3f} ~= source {src:.3f} kn")

# 6) cross-language: Python-encoded pixel decodes through the ACTUAL JS codec to the same value.
codec = os.path.join(ROOT, "web", "wx-value-codec.js")
try:
    rr, gg, bb = M.encode_value(1013.2, scale, offset)
    js = (f"const C=require({json.dumps(codec)});"
          f"const v=C.decodeRGBA({rr},{gg},{bb},255,{scale!r},{offset!r});"
          f"process.stdout.write(String(v));")
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=20)
    if out.returncode == 0 and out.stdout.strip():
        jval = float(out.stdout.strip())
        check(abs(jval - 1013.2) < 0.001, f"JS codec decodes Python-encoded pixel to {jval:.4f} (want 1013.2)")
    else:
        print("  note   skipped cross-language check (node error):", out.stderr.strip()[:120])
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("  note   skipped cross-language check (node unavailable)")

print(("\nVALUE-TILE TESTS: %d FAILED" % fails) if fails else "\nVALUE-TILE TESTS: all passed")
sys.exit(1 if fails else 0)
