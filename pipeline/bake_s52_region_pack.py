#!/usr/bin/env python3
"""
Bake a Helm S-52 chart region into an offline MBTiles/PMTiles pack.

This is the batch version of the live chart tile path:

  live S-52 tile server /chart/{z}/{x}/{y}.png
    -> bbox/zoom XYZ pyramid
    -> MBTiles intermediate
    -> PMTiles pack with edition/render-date/palette/z-range metadata

Run it against a private helm-tiles or helm-server port. Do not point it at the
live :8080 boat screen while agents are working.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_pmtiles  # noqa: E402

UA = "HelmS52RegionBaker/0.1 (+https://github.com/StevenRidder/Helm)"
DEFAULT_SOURCE = "http://127.0.0.1:8082/chart/{z}/{x}/{y}.png"


def parse_bbox(text: str) -> tuple[float, float, float, float]:
    try:
        w, s, e, n = (float(v.strip()) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("bbox must be W,S,E,N") from None
    if w >= e or s >= n:
        raise argparse.ArgumentTypeError("bbox must satisfy west < east and south < north")
    if not (-180 <= w <= 180 and -180 <= e <= 180 and -85.051129 <= s <= 85.051129 and -85.051129 <= n <= 85.051129):
        raise argparse.ArgumentTypeError("bbox is outside Web Mercator lon/lat bounds")
    return w, s, e, n


def deg2num(lon: float, lat: float, z: int) -> tuple[int, int]:
    lat = max(-85.051129, min(85.051129, lat))
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def iter_tiles(bbox: tuple[float, float, float, float], minzoom: int, maxzoom: int):
    w, s, e, n = bbox
    for z in range(minzoom, maxzoom + 1):
        x0, y0 = deg2num(w, n, z)
        x1, y1 = deg2num(e, s, z)
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                yield z, x, y


def with_display_query(template: str, palette: str, category: str) -> str:
    parsed = urllib.parse.urlsplit(template)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query["p"] = palette
    query["cat"] = category
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )


def fetch_tile(url: str, timeout: float) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 204:
                return None
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 204:
            return None
        raise RuntimeError(f"HTTP {exc.code}") from exc


def metadata_pairs(meta: dict) -> list[tuple[str, str]]:
    rows = []
    for key, value in meta.items():
        if isinstance(value, (dict, list)):
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            encoded = str(value)
        rows.append((key, encoded))
    return rows


def write_mbtiles(path: Path, rows: list[tuple[int, int, int, bytes]], metadata: dict) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
        con.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
        con.execute("CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)")
        con.executemany("INSERT INTO metadata VALUES (?, ?)", metadata_pairs(metadata))
        con.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", rows)
        con.commit()
    finally:
        con.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bake live S-52 chart tiles into an offline region PMTiles pack.")
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="XYZ S-52 tile URL template")
    ap.add_argument("--bbox", required=True, type=parse_bbox, help="W,S,E,N lon/lat")
    ap.add_argument("--minzoom", type=int, required=True)
    ap.add_argument("--maxzoom", type=int, required=True)
    ap.add_argument("--out", required=True, help="Output .pmtiles path")
    ap.add_argument("--mbtiles-out", help="Optional MBTiles intermediate path")
    ap.add_argument("--keep-mbtiles", action="store_true", help="Keep temporary MBTiles intermediate")
    ap.add_argument("--name", default="Helm S-52 region pack")
    ap.add_argument("--palette", choices=("day", "dusk", "night"), default="day")
    ap.add_argument("--display-category", choices=("base", "std", "all", "mariner"), default="std")
    ap.add_argument("--edition", default="unknown", help="Source chart edition/update stamp")
    ap.add_argument("--chart-epoch", default="", help="Optional source chart epoch/checksum/catalog stamp")
    ap.add_argument("--render-date", default="", help="UTC ISO render date; default is now")
    ap.add_argument("--source-label", default="s52-chart-server")
    ap.add_argument("--license", default="local-user-owned")
    ap.add_argument("--attribution", default="Rendered from user-provided S-57/S-52 charts; verify source edition before navigation")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--delay", type=float, default=0.0, help="Seconds between tile requests")
    ap.add_argument("--allow-missing", action="store_true", help="Skip failed tile requests instead of failing")
    args = ap.parse_args(argv)

    if args.minzoom < 0 or args.maxzoom < args.minzoom or args.maxzoom > 24:
        ap.error("zoom range must satisfy 0 <= minzoom <= maxzoom <= 24")

    out = Path(args.out)
    if out.suffix.lower() != ".pmtiles":
        ap.error("--out must be a .pmtiles file")
    out.parent.mkdir(parents=True, exist_ok=True)

    render_date = args.render_date or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source = with_display_query(args.source, args.palette, args.display_category)
    expected = list(iter_tiles(args.bbox, args.minzoom, args.maxzoom))
    rows: list[tuple[int, int, int, bytes]] = []
    no_coverage = 0
    missing = 0

    print(f"bake S-52 region: {args.name}")
    print(f"  bbox: {','.join(str(v) for v in args.bbox)}")
    print(f"  zoom: z{args.minzoom}-{args.maxzoom}  palette={args.palette}  cat={args.display_category}")
    print(f"  tiles: {len(expected)} candidate XYZ requests")

    for i, (z, x, y) in enumerate(expected, start=1):
        url = source.format(z=z, x=x, y=y)
        try:
            blob = fetch_tile(url, args.timeout)
        except (OSError, RuntimeError, TimeoutError) as exc:
            if not args.allow_missing:
                raise SystemExit(f"tile fetch failed at z{z}/{x}/{y}: {exc}") from exc
            missing += 1
            continue
        if blob is None:
            no_coverage += 1
            continue
        tms_y = (1 << z) - 1 - y
        rows.append((z, x, tms_y, sqlite3.Binary(blob)))
        if args.delay and i < len(expected):
            time.sleep(args.delay)

    if not rows:
        raise SystemExit("no S-52 tiles were baked; check bbox/zoom/source server")

    metadata = {
        "name": args.name,
        "format": "png",
        "type": "baselayer",
        "kind": "chart",
        "source": args.source_label,
        "license": args.license,
        "attribution": args.attribution,
        "bounds": ",".join(str(v) for v in args.bbox),
        "minzoom": args.minzoom,
        "maxzoom": args.maxzoom,
        "helm_pack_schema": "helm.offline.region.v1",
        "pack_role": "s52-chart",
        "renderer": "s52",
        "palette": args.palette,
        "display_category": args.display_category,
        "chart_edition": args.edition,
        "chart_epoch": args.chart_epoch or args.edition,
        "render_date": render_date,
        "z_range": f"{args.minzoom}-{args.maxzoom}",
        "tile_count": len(rows),
        "tile_count_expected": len(expected),
        "no_coverage_tile_count": no_coverage,
        "missing_tile_count": missing,
        "generated_by": "pipeline/bake_s52_region_pack.py",
    }

    tmp_mbtiles = None
    if args.mbtiles_out:
        mbtiles_path = Path(args.mbtiles_out)
    else:
        tmp = tempfile.NamedTemporaryFile(prefix="helm-s52-region-", suffix=".mbtiles", delete=False)
        tmp.close()
        tmp_mbtiles = Path(tmp.name)
        mbtiles_path = tmp_mbtiles
    mbtiles_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        write_mbtiles(mbtiles_path, rows, metadata)
        make_pmtiles.main(str(mbtiles_path), str(out), bbox=args.bbox)
    finally:
        if tmp_mbtiles and not args.keep_mbtiles:
            try:
                tmp_mbtiles.unlink()
            except FileNotFoundError:
                pass

    print(f"  kept: {len(rows)}  no_coverage: {no_coverage}  missing: {missing}")
    print(f"  wrote: {out}")
    if args.mbtiles_out or args.keep_mbtiles:
        print(f"  mbtiles: {mbtiles_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
