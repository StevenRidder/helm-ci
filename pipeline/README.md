# Helm pipeline — the reusable engine

Front-end-agnostic data plumbing for the tracer bullet. **Everything here carries over to
the native Swift app unchanged** — it's plain CLI that produces mbtiles + GeoJSON + wind
JSON, which MapLibre (GL JS *and* Native) consume identically.

| Script | Does | Needs |
|---|---|---|
| `fetch_tiles.py` | lasso bbox → XYZ tiles → offline `.mbtiles` (TMS Y-flip handled) | python3 (stdlib) |
| `bake_s52_region_pack.py` | live S-52 chart tiles → stamped region `.pmtiles` pack | private `helm-tiles`/`helm-server` chart tile origin |
| `fetch_wind.py` | gridded wind → `wind.json` (particles) + `wind_points.geojson` (arrows) | python3 (stdlib) |
| `extract_depth.sh` | NOAA ENC S-57 → `depare`/`depcnt`/`soundg` GeoJSON (depth-on-satellite) | GDAL (`brew install gdal`) |

## Run it

```bash
# one command (wind + places + offline charts; pass an ENC cell to also extract depth)
bash pipeline/build.sh
bash pipeline/build.sh ~/Downloads/US5FLxxx.000

# ...or step by step. NOTE the --bbox= form: a bbox starting with "-" is otherwise
# mistaken for a flag (argparse). Wind covers WIND_BBOX (much larger than the charts).
cd pipeline && cp region.env.example region.env && source region.env
python3 fetch_wind.py  --bbox="$WIND_BBOX" --nx="$WIND_NX" --ny="$WIND_NY" --out ../web/data
python3 fetch_places.py
python3 fetch_tiles.py --source "$SRC_CHART" --bbox="$BBOX" --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" --out ../web/data/$REGION_NAME-charts.mbtiles --name "NOAA"
python3 fetch_tiles.py --source "$SRC_SAT" --fmt jpg --bbox="$BBOX" --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" --out ../web/data/$REGION_NAME-sat.mbtiles --name "Sentinel-2"
python3 bake_s52_region_pack.py --source "http://127.0.0.1:9001/chart/{z}/{x}/{y}.png" --bbox="$BBOX" --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" --palette day --edition "source-edition" --out ../web/data/$REGION_NAME-s52-day.pmtiles
./extract_depth.sh ~/Downloads/US5FLxxx.000 ../web/data   # needs GDAL
```

Then serve the prototype: `cd ../web && python3 -m http.server 8080` → open
http://localhost:8080.

## Notes / ToS
- NOAA chart tiles + ENC: US public domain.
- Sentinel-2 cloudless (EOX): CC-BY-4.0 — attribute "Sentinel-2 cloudless by EOX".
- Open-Meteo: free for non-commercial; production swaps to GFS/ECMWF GRIB (same output format).
- Be polite: `fetch_tiles.py` sleeps between requests; cap zoom for big areas (size grows ~4× per zoom).
- S-52 region packs are point-in-time rendered snapshots. Bake separate packs for day/dusk/night if
  offline palette switching matters, and stamp the source chart edition so the UI can warn later.
- See [../docs/LEGAL.md](../docs/LEGAL.md) before adding Google/Bing/Navionics.
