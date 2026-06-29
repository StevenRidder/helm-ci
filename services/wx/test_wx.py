#!/usr/bin/env python3
"""
helm-wx self-test — OFFLINE (no network; runs even while rate-limited).
Validates the full bake -> PNG -> decode -> value round-trip, the manifest contract, and caching.

    python3 test_wx.py
"""
import asyncio
import json
from pathlib import Path
import struct
import sys
import zlib

import app
from fastapi.testclient import TestClient


def decode_png_rgba(png: bytes):
    """Minimal decoder for the filter-0 RGBA PNGs write_png_bytes() emits. Returns (w, h, pixels[])."""
    assert png[:8] == b'\x89PNG\r\n\x1a\n', "not a PNG"
    i, idat = 8, bytearray()
    w = h = 0
    while i < len(png):
        ln = struct.unpack('>I', png[i:i + 4])[0]
        tag = png[i + 4:i + 8]
        data = png[i + 8:i + 8 + ln]
        if tag == b'IHDR':
            w, h = struct.unpack('>II', data[:8])
        elif tag == b'IDAT':
            idat.extend(data)
        i += 12 + ln
    raw = zlib.decompress(bytes(idat))
    stride = w * 4
    px = []
    for row in range(h):
        base = row * (stride + 1) + 1                 # skip the per-row filter byte (0 = None)
        line = raw[base:base + stride]
        for c in range(w):
            o = c * 4
            px.append((line[o], line[o + 1], line[o + 2], line[o + 3]))
    return w, h, px


def decode_value(r, g, b, a, scale, offset):
    if a < 128:
        return None
    return offset + ((r << 16) | (g << 8) | b) * scale


fails = 0


def check(cond, msg):
    global fails
    if cond:
        print("  ok   " + msg)
    else:
        fails += 1
        print("  FAIL " + msg)


def main():
    # isolate from any prior on-disk cache so the test is deterministic
    import tempfile
    app.CACHE_DIR = tempfile.mkdtemp(prefix="helmwx-test-")
    app._tiles = app.OrderedTileCache(app.TILE_MEM_MAX)

    # 1) encode/decode round-trip at the value level for every layer's fixed scale/offset
    for layer, cfg in app.LAYERS.items():
        scale, offset = app.layer_scale_offset(cfg)
        mid = (cfg["vmin"] + cfg["vmax"]) / 2.0
        r, g, b = app.encode_value(mid, scale, offset)
        back = decode_value(r, g, b, 255, scale, offset)
        check(abs(back - mid) <= 2 * scale + 1e-6, "%s: value round-trips (%.2f ~ %.2f)" % (layer, back, mid))

    # 2) bake a real tile from a SYNTHETIC grid (no network) and decode it back through the PNG.
    # The fake mirrors _fetch_grid's geometry (a grid over the coarse-cell bounds + margin) so it
    # always covers the requested tile — exactly like the real fetch, minus the network.
    UNIFORM = 23.5  # kn

    async def fake_fetch(layer, cz, cx, cy):
        w, s, e, n = app.tile_bounds(cz, cx, cy)
        mw, mh = (e - w) * 0.08, (n - s) * 0.08
        w, e, s, n = w - mw, e + mw, s - mh, n + mh
        return app.Grid(app.GRID_N, app.GRID_N, w, s, e, n, [UNIFORM] * (app.GRID_N * app.GRID_N))
    app._fetch_grid = fake_fetch                       # monkeypatch the only network call

    z, x = 6, app.lonlat_to_tile(177.4, -17.6, 6)[0]
    y = app.lonlat_to_tile(177.4, -17.6, 6)[1]
    xt, yt = int(x), int(y)
    calls0 = app._stats["openmeteo_calls"]
    png = asyncio.run(app.bake_tile("wind", z, xt, yt))
    check(png[:8] == b'\x89PNG\r\n\x1a\n', "bake_tile returns a PNG")
    w, h, px = decode_png_rgba(png)
    check((w, h) == (256, 256), "tile is 256x256 (%dx%d)" % (w, h))

    scale, offset = app.layer_scale_offset(app.LAYERS["wind"])
    cr, cg, cb, ca = px[128 * 256 + 128]               # centre pixel
    val = decode_value(cr, cg, cb, ca, scale, offset)
    check(val is not None and abs(val - UNIFORM) <= 2 * scale + 1e-6,
          "centre pixel decodes to the baked value (%.2f ~ %.2f kn)" % (val or -1, UNIFORM))
    check(app._stats["openmeteo_calls"] == calls0, "bake used the SYNTHETIC grid (no network call)")

    # 3) caching: re-baking the same tile is a cache hit (no re-bake)
    bakes0 = app._stats["bakes"]
    asyncio.run(app.bake_tile("wind", z, xt, yt))
    check(app._stats["bakes"] == bakes0, "second request is a cache hit (no re-bake)")

    # 4) manifest contract
    m = app.manifest_for("wind")
    check(m["encoding"] == "helm-wxv1", "manifest encoding is helm-wxv1")
    check(m["tiles_template"] == "{z}/{x}/{y}.png", "manifest tiles_template matches the client contract")
    check("scale" in m and "offset" in m and "ramp" in m, "manifest carries scale/offset/ramp")
    check("NOT FOR NAVIGATION" in m["disclaimer"], "manifest is honestly not-for-navigation")

    # 5) environmental bundle contract: the root fix for Windy-parity cache/render work.
    b = app.environment_bundle_manifest()
    check(b["schema"] == "helm.env.bundle.v1", "bundle manifest uses helm.env.bundle.v1")
    check(b["cachePolicy"]["upstreamFetchesAllowedDuringGesture"] is False,
          "bundle contract forbids upstream API fetches during pan/zoom/scrub")
    check(b["lod"]["parentFallback"] is True and "overzoom" in b["lod"],
          "bundle contract defines all-zoom parent fallback/overzoom behaviour")
    check(set(app.BUNDLE_LAYER_ORDER).issubset(set(b["layers"].keys())),
          "bundle advertises the full met-ocean layer catalog")
    wind = b["layers"]["wind"]
    current = b["layers"]["current"]
    check(wind["fieldTiles"]["urlTemplate"] == "/wind/{z}/{x}/{y}.png",
          "wind scalar colour field remains a numeric field-tile contract")
    check(wind["vectorField"]["type"] == "bbox-json-compatibility" and wind["vectorField"]["urlTemplate"].startswith("/velocity/wind"),
          "wind particles use an explicit vector-field endpoint")
    check(wind["vectorField"]["preparedComponentTiles"]["type"] == "component-tiles",
          "wind bundle advertises the prepared vector component-tile target")
    check(current["s100"]["productIdentifier"] == "S-111" and current["s100"]["officialProduct"] is False,
          "surface currents align to S-111 metadata without claiming official S-100 authority")
    check(b["layers"]["waves"]["s100"]["productIdentifier"] == "S-413",
          "wave layers align to the S-413 weather/wave family")
    idx = app.bundle_index()
    check(idx["bundles"][0]["manifest"] == "/bundles/open-meteo/latest/manifest.json",
          "bundle index points at the live Open-Meteo bundle manifest")
    client = TestClient(app.app)
    route_manifest = client.get("/bundles/open-meteo/latest/manifest.json")
    route_index = client.get("/index.json")
    check(route_manifest.status_code == 200 and route_manifest.json()["schema"] == "helm.env.bundle.v1",
          "bundle manifest endpoint returns the bundle contract")
    check(route_index.status_code == 200 and "bundles" in route_index.json(),
          "legacy index advertises bundle discovery without breaking layer discovery")
    fixture = json.loads((Path(__file__).parent / "fixtures" / "fiji-env-bundle-v1.json").read_text())
    check(fixture["schema"] == "helm.env.bundle.v1" and fixture["coverage"]["bbox"]["crossesAntimeridian"] is True,
          "Fiji/South Pacific fixture carries the bundle schema and antimeridian coverage")
    check(set(app.BUNDLE_LAYER_ORDER).issubset(set(fixture["layers"].keys())),
          "Fiji/South Pacific fixture includes the full met-ocean layer catalog")

    # 6) NODATA honesty: a grid that samples None must emit a transparent pixel, never a fake value
    empty = app.Grid(2, 2, 0, 0, 1, 1, [None, None, None, None])
    check(empty.sample(0.5, 0.5) is None, "fully-missing grid samples to None (NODATA, not faked)")

    print("\nHELM-WX TESTS: " + ("all passed" if not fails else ("%d FAILED" % fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
