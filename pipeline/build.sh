#!/usr/bin/env bash
# Helm pipeline — one-command runner.
# Builds everything the web prototype (and offline charts) need, driven by region.env.
# Tolerant by design: a failed or skipped step never aborts the rest (set -u, NOT set -e).
#
# Usage:
#   bash pipeline/build.sh                         # wind + places + offline charts
#   bash pipeline/build.sh ~/Downloads/USxxx.000   # ...also extract ENC depth
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA="$ROOT/web/data"
mkdir -p "$DATA"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/region.env"

ENC="${1:-}"   # optional NOAA ENC .000 cell for the depth step
step() { printf "\n\033[1m== %s ==\033[0m\n" "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

step "region: $REGION_NAME   charts bbox $BBOX   wind bbox $WIND_BBOX"

# --- quick overlay data (the web prototype needs these) ---
step "weather  (Open-Meteo: wind/rain/temp/pressure/waves/current heatmap fields + wind particles)"
python3 "$SCRIPT_DIR/fetch_weather.py" --bbox="$WIND_BBOX" --nx=14 --ny=14 \
  --layers wind,rain,temp,pressure,waves,current --out "$DATA" \
  || echo "  ! weather step failed (network/rate-limit?) — continuing"

step "places  (OpenStreetMap / Overpass)"
python3 "$SCRIPT_DIR/fetch_places.py" \
  || echo "  ! places step failed (Overpass busy?) — continuing"

# --- ENC depth (optional; needs GDAL + a downloaded cell) ---
step "depth  (NOAA ENC -> GeoJSON)"
if [ -n "$ENC" ] && [ -f "$ENC" ]; then
  if have ogr2ogr; then
    bash "$SCRIPT_DIR/extract_depth.sh" "$ENC" "$DATA" || echo "  ! depth step failed — continuing"
  else
    echo "  ! GDAL not found (brew install gdal) — skipping depth"
  fi
else
  echo "  - no ENC cell passed; skipping depth"
  echo "    (usage: build.sh /path/to/USxxxx.000 — cells at https://www.charts.noaa.gov/ENCs/ENCs.shtml)"
fi

# --- offline chart tiles (optional, larger; the web demo uses LIVE tiles) ---
step "offline charts: NOAA raster -> mbtiles"
python3 "$SCRIPT_DIR/fetch_tiles.py" --source "$SRC_CHART" --bbox="$BBOX" \
  --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" --out "$DATA/$REGION_NAME-charts.mbtiles" \
  --name "NOAA $REGION_NAME" || echo "  ! charts mbtiles failed — continuing"

step "offline charts: Sentinel-2 -> mbtiles"
python3 "$SCRIPT_DIR/fetch_tiles.py" --source "$SRC_SAT" --fmt jpg --bbox="$BBOX" \
  --minzoom "$MINZOOM" --maxzoom "$MAXZOOM" --out "$DATA/$REGION_NAME-sat.mbtiles" \
  --name "Sentinel-2 $REGION_NAME" || echo "  ! sat mbtiles failed — continuing"

step "done"
echo "web/data now contains:"
ls -1 "$DATA" | sed 's/^/  /'
echo
echo "serve it:  cd $ROOT/web && python3 -m http.server 8080   ->  http://localhost:8080"
