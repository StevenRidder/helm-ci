#!/usr/bin/env python3
"""
Helm on-demand tiler — the heart of "lasso an area, fetch charts, cache offline."

Fetches XYZ raster tiles for a bounding box across a zoom range and packs them into
a single offline .mbtiles file (SQLite). Pure standard library — no GDAL needed.

This is the engine piece that carries over to ANY front-end (web or native Swift):
MapLibre (GL JS and Native) both read .mbtiles raster sources the same way.

INTAKE-8 — download and import are one library, two front doors. When --out is
omitted, the pack is deposited into the customer's DEFAULT REGISTERED CHART ROOT
(chart_intake registry, ~/.helm/charts by default) under DOWNLOADS/, next to a
<stem>.metadata.json sidecar (source label, license, bbox, download date, and the
render_date freshness key the catalog staleness path reads). The recursive chart
discovery (INTAKE-3: helm-packd / mbtiles_server fingerprint the tree per catalog
request) then picks it up with no extra step — the lasso result is immediately a
toggleable library layer.

Note the --bbox=VALUE (equals) form: a western/southern bbox begins with '-', which
argparse reads as an option flag in the space-separated form. Equals binds it as the value.

Usage (drawer default — lands in the chart library):
    python3 fetch_tiles.py --source "https://.../{z}/{x}/{y}.png" \
        --bbox="-81.86,24.44,-81.68,24.60" --minzoom 9 --maxzoom 15 \
        --name "NOAA Key West" --source-label "NOAA ENC charts" \
        --license "Public domain (NOAA)"

Usage (explicit path — advanced):
    ... --out ../web/data/key-west-charts.mbtiles

Key correctness detail: .mbtiles stores rows in TMS convention (y=0 at south),
which is flipped from XYZ slippy tiles (y=0 at north). We flip on write.
"""
from __future__ import annotations

import argparse, datetime, json, math, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

UA = "HelmTiler/0.1 (+https://github.com/StevenRidder/Helm)"
DOWNLOADS_SUBDIR = "DOWNLOADS"

def deg2num(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _safe_filename(name, fallback="helm-tiles"):
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name)).strip("-.") or fallback
    return stem if stem.endswith(".mbtiles") else stem + ".mbtiles"

def library_destination(filename):
    """Resolve <default registered chart root>/DOWNLOADS/<filename>.

    Uses the INTAKE-2 chart-root registry so a downloaded pack and a hand-placed
    pack land in the same registered tree. First run bootstraps the registry and
    the default root exactly like `chart_intake.py register` would.
    """
    from chart_intake import IntakeError, default_paths, ensure_registry  # stdlib-only sibling
    roots_file, _, default_root = default_paths()
    registry = ensure_registry(roots_file, default_root)
    root = next((r for r in registry["roots"] if r.get("default")), None) or registry["roots"][0]
    root_path = Path(root["path"])
    if not root_path.is_dir():
        raise IntakeError(f"registered chart root is unavailable: {root['label']}")
    dest_dir = root_path / DOWNLOADS_SUBDIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / filename, root

def write_sidecar(out_path, a, bbox, got, total, miss):
    """Emit the <stem>.metadata.json the chart index + pack catalog both read.

    render_date is the freshness key the /catalog staleness path requires
    (decision #10) — for a download, the tiles are current as of the fetch.
    tile_count* keys feed the same coverage honesty the baked packs report.
    """
    w, s, e, n = bbox
    sidecar = {
        "schema": "helm.chart_intake.download.v1",
        "title": a.name,
        "source": a.source_label or urllib.parse.urlsplit(a.source).hostname or "download",
        "source_url": a.source,
        "source_downloaded": _utc_now_iso(),
        "license": a.license,
        "bounds": f"{w},{s},{e},{n}",
        "minzoom": a.minzoom,
        "maxzoom": a.maxzoom,
        "render_date": _utc_now_iso(),
        "tile_count": got,
        "tile_count_expected": total,
        "missing_tile_count": miss,
        "coverage_status": "complete" if miss == 0 else "partial",
    }
    if a.attribution:
        sidecar["attribution"] = a.attribution
    if miss:
        sidecar["coverage_warning"] = f"{miss} of {total} requested tiles were not returned by the source."
    sidecar_path = Path(str(out_path)[: -len(".mbtiles")] + ".metadata.json") \
        if str(out_path).endswith(".mbtiles") else Path(str(out_path) + ".metadata.json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar_path

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="XYZ URL template with {z}/{x}/{y}")
    ap.add_argument("--bbox", required=True, help="W,S,E,N (lon/lat)")
    ap.add_argument("--minzoom", type=int, default=9)
    ap.add_argument("--maxzoom", type=int, default=15)
    ap.add_argument("--out", default=None,
                    help="explicit output path (advanced); default deposits into the registered chart library")
    ap.add_argument("--filename", default=None,
                    help="output basename inside the chart library (no directories)")
    ap.add_argument("--fmt", default="png", help="png | jpg")
    ap.add_argument("--name", default="Helm tiles")
    ap.add_argument("--source-label", dest="source_label", default="",
                    help="human source label for the sidecar (e.g. 'NOAA ENC charts')")
    ap.add_argument("--license", default="unknown", help="license note for the sidecar")
    ap.add_argument("--attribution", default="", help="attribution note for the sidecar")
    ap.add_argument("--delay", type=float, default=0.04, help="seconds between requests (be polite)")
    a = ap.parse_args(argv)

    if a.filename and os.path.basename(a.filename) != a.filename:
        print(f"error: --filename must be a bare filename, not a path: {a.filename}", file=sys.stderr)
        return 2

    library_root = None
    if a.out:
        out_path = Path(a.out)
    else:
        from chart_intake import IntakeError
        try:
            out_path, library_root = library_destination(a.filename or _safe_filename(a.name))
        except IntakeError as exc:
            print(f"error: chart_library_unavailable: {exc}", file=sys.stderr)
            return 2

    w, s, e, n = (float(v) for v in a.bbox.split(","))
    if os.path.exists(out_path):
        os.remove(out_path)
    con = sqlite3.connect(out_path)
    cur = con.cursor()
    cur.execute("CREATE TABLE metadata (name text, value text)")
    cur.execute("CREATE TABLE tiles (zoom_level int, tile_column int, tile_row int, tile_data blob)")
    cur.execute("CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row)")
    for k, v in {"name": a.name, "format": a.fmt, "type": "baselayer", "version": "1.0",
                 "bounds": f"{w},{s},{e},{n}", "minzoom": str(a.minzoom),
                 "maxzoom": str(a.maxzoom)}.items():
        cur.execute("INSERT INTO metadata VALUES (?,?)", (k, v))

    got = miss = total = 0
    for z in range(a.minzoom, a.maxzoom + 1):
        x0, y0 = deg2num(w, n, z)   # NW corner
        x1, y1 = deg2num(e, s, z)   # SE corner
        zget = zmiss = ztot = 0     # per-zoom counters
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                ztot += 1
                url = a.source.format(z=z, x=x, y=y)
                try:
                    data = fetch(url)
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as ex:
                    zmiss += 1
                    continue
                tms_y = (2 ** z - 1) - y   # XYZ -> TMS flip
                cur.execute("INSERT OR REPLACE INTO tiles VALUES (?,?,?,?)",
                            (z, x, tms_y, sqlite3.Binary(data)))
                zget += 1
                if a.delay:
                    time.sleep(a.delay)
        got += zget; miss += zmiss; total += ztot
        con.commit()
        print(f"  z{z}: {zget} kept, {zmiss} missing ({ztot} seen)", file=sys.stderr)

    con.commit()
    con.close()

    if got == 0:
        # An empty pack in the library would show up as a blank "chart" — fail loud instead.
        os.remove(out_path)
        print(f"error: no_tiles_fetched: 0 of {total} tiles were returned by {a.source}; "
              "nothing was deposited", file=sys.stderr)
        return 3

    sidecar_path = write_sidecar(out_path, a, (w, s, e, n), got, total, miss)
    kb = os.path.getsize(out_path) // 1024
    print(f"done -> {out_path}  ({got}/{total} tiles, {kb} KB)")
    print(f"sidecar -> {sidecar_path.name}")
    if library_root is not None:
        print(f"library: deposited in registered chart root \"{library_root['label']}\" — "
              "it appears in /catalog on the next request (no rescan needed)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
