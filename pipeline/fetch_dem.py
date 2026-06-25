#!/usr/bin/env python3
"""
fetch_dem.py — bake a LOCAL terrain-RGB DEM for the demo region (offline-first).

Terrarium DEM tiles (AWS open data) are already terrain-RGB PNGs, so we just
download the handful covering the region ONCE at build time and ship them under
web/data/dem/{z}/{x}/{y}.png. At runtime the chart, the depth-contour layer
(maplibre-contour) and the Lab hillshade read these LOCAL tiles — no CDN, works
on a boat with no internet. If online, the same encoding can fall back to the
live AWS source, but nothing requires it.

Source: https://registry.opendata.aws/terrain-tiles/ (Mapzen/Terrarium, public).
Encoding: terrarium  (elevation_m = (R*256 + G + B/256) - 32768; negative = bathymetry).
"""
import math, os, re, sys, time, urllib.request

# Region-driven: read BBOX (West,South,East,North) from region.env so a region switch
# only edits region.env. Falls back to the Key West box if region.env is unreadable.
def _bbox_from_region():
    p = os.path.join(os.path.dirname(__file__), "region.env")
    try:
        m = re.search(r'BBOX="([^"]+)"', open(p).read())
        if m:
            w, s, e, n = (float(x) for x in m.group(1).split(","))
            return w, s, e, n
    except Exception:
        pass
    return -82.00, 24.35, -81.50, 24.70

WEST, SOUTH, EAST, NORTH = _bbox_from_region()
ZMIN, ZMAX = 9, 12        # z12 is plenty for depth contours — maplibre-contour over-zooms past it
SRC = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"
OUT = os.path.join(os.path.dirname(__file__), "..", "web", "data", "dem")


def deg2tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def main():
    os.makedirs(OUT, exist_ok=True)
    got = skipped = failed = 0
    for z in range(ZMIN, ZMAX + 1):
        x0, y1 = deg2tile(WEST, SOUTH, z)
        x1, y0 = deg2tile(EAST, NORTH, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                dst = os.path.join(OUT, str(z), str(x), f"{y}.png")
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    skipped += 1
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                url = SRC.format(z=z, x=x, y=y)
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "helm-pipeline/1.0"})
                        with urllib.request.urlopen(req, timeout=20) as r:
                            data = r.read()
                        with open(dst, "wb") as f:
                            f.write(data)
                        got += 1
                        break
                    except Exception as e:
                        if attempt == 2:
                            print(f"  ! z{z}/{x}/{y}: {e}", file=sys.stderr)
                            failed += 1
                        else:
                            time.sleep(0.5 * (attempt + 1))
    print(f"DEM done: {got} fetched, {skipped} cached, {failed} failed  ->  web/data/dem/")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
