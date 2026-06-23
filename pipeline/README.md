# Helm pipeline — the reusable engine

Front-end-agnostic data plumbing for the tracer bullet. **Everything here carries over to
the native Swift app unchanged** — it's plain CLI that produces mbtiles + GeoJSON + wind
JSON, which MapLibre (GL JS *and* Native) consume identically.

| Script | Does | Needs |
|---|---|---|
| `fetch_tiles.py` | lasso bbox → XYZ tiles → offline `.mbtiles` (TMS Y-flip handled) | python3 (stdlib) |
| `fetch_wind.py` | gridded wind → `wind.json` (particles) + `wind_points.geojson` (arrows) | python3 (stdlib) |
| `extract_depth.sh` | NOAA ENC S-57 → `depare`/`depcnt`/`soundg` GeoJSON (depth-on-satellite) | GDAL (`brew install gdal`) |

## Run it

```bash
cd pipeline
source region.env          # bbox + sources (default: Key West)

# 1) NOAA charts → offline mbtiles   (pure python, runs now)
python3 fetch_tiles.py --source "$SRC_CHART" --bbox "$BBOX" \
    --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" \
    --out ../web/data/$REGION_NAME-charts.mbtiles --name "NOAA $REGION_NAME"

# 2) Sentinel-2 satellite → offline mbtiles
python3 fetch_tiles.py --source "$SRC_SAT" --fmt jpg --bbox "$BBOX" \
    --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" \
    --out ../web/data/$REGION_NAME-sat.mbtiles --name "Sentinel-2 $REGION_NAME"

# 3) wind grid   (pure python, runs now)
python3 fetch_wind.py --bbox "$BBOX" --out ../web/data

# 4) ENC depth → GeoJSON   (needs GDAL + a downloaded ENC .000 cell)
#    grab the cell covering the bbox from https://www.charts.noaa.gov/ENCs/ENCs.shtml
./extract_depth.sh ~/Downloads/US5FLxxx.000 ../web/data
```

Then serve the prototype: `cd ../web && python3 -m http.server 8080` → open
http://localhost:8080.

## Notes / ToS
- NOAA chart tiles + ENC: US public domain.
- Sentinel-2 cloudless (EOX): CC-BY-4.0 — attribute "Sentinel-2 cloudless by EOX".
- Open-Meteo: free for non-commercial; production swaps to GFS/ECMWF GRIB (same output format).
- Be polite: `fetch_tiles.py` sleeps between requests; cap zoom for big areas (size grows ~4× per zoom).
- See [../docs/LEGAL.md](../docs/LEGAL.md) before adding Google/Bing/Navionics.
