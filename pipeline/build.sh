#!/usr/bin/env bash
#
# Helm — pipeline/build.sh
# ---------------------------------------------------------------------------
# One-command runner for the full Helm chartplotter data pipeline.
#
# Produces, into web/data/ (and web/tiles/), every artifact the MapLibre
# prototype (web/index.html + web/style.json) expects:
#
#   web/tiles/charts.mbtiles        NOAA raster charts        (fetch_tiles.py)
#   web/tiles/sat.mbtiles           Sentinel-2 cloudless sat  (fetch_tiles.py)
#   web/data/wind.json              VELOCITY U/V grid         (fetch_wind.py)
#   web/data/wind_points.geojson    wind barbs                (fetch_wind.py)
#   web/data/places.geojson         labels (optional)         (fetch_places.py)
#   web/data/depare.geojson         depth areas               (extract_depth.sh)
#   web/data/depcnt.geojson         depth contours            (extract_depth.sh)
#   web/data/soundg.geojson         soundings                 (extract_depth.sh)
#
# Usage:
#   pipeline/build.sh [ENC_CELL]
#
#   ENC_CELL  Optional path to an S-57 ENC cell (.000 file) or a directory of
#             ENC cells. If omitted, the script looks in a few default spots;
#             if none is found, depth extraction is skipped with a clear note.
#
# Contract notes:
#   * set -u so unset vars fail loudly.
#   * We deliberately do NOT set -e: each step is isolated so a single
#     network/tool failure does not abort the rest of the run. Per-step
#     status is tracked and reported in a final summary.
#   * region.env supplies the bbox + source URLs and is sourced verbatim.
# ---------------------------------------------------------------------------

set -u

# ----- locate ourselves & the project -------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"
WEB_DIR="$ROOT_DIR/web"
DATA_DIR="$WEB_DIR/data"
TILES_DIR="$WEB_DIR/tiles"

REGION_ENV="$SCRIPT_DIR/region.env"

# Pick a python interpreter (prefer python3).
PY="$(command -v python3 || command -v python || true)"

# ----- pretty output -------------------------------------------------------
if [ -t 1 ]; then
  C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_GRN=$'\033[32m'
  C_YEL=$'\033[33m'; C_RED=$'\033[31m'; C_CYN=$'\033[36m'; C_RST=$'\033[0m'
else
  C_BOLD=''; C_DIM=''; C_GRN=''; C_YEL=''; C_RED=''; C_CYN=''; C_RST=''
fi

say()   { printf '%s\n' "${C_CYN}==>${C_RST} ${C_BOLD}$*${C_RST}"; }
info()  { printf '%s\n' "    $*"; }
ok()    { printf '%s\n' "    ${C_GRN}ok${C_RST}  $*"; }
warn()  { printf '%s\n' "    ${C_YEL}warn${C_RST} $*"; }
fail()  { printf '%s\n' "    ${C_RED}fail${C_RST} $*"; }

# Step results are accumulated here as "STATUS\tLABEL" lines.
SUMMARY=""
record() { SUMMARY="${SUMMARY}${1}"$'\t'"${2}"$'\n'; }

# Run a step in its own subshell so a non-zero exit (or a `return`) never
# leaks out and kills the parent run. $1=label, rest=command.
run_step() {
  local label="$1"; shift
  say "$label"
  if ( "$@" ); then
    record "OK" "$label"
    ok "$label complete"
  else
    record "FAIL" "$label"
    fail "$label failed (continuing)"
  fi
  printf '\n'
}

# ----- preflight -----------------------------------------------------------
say "Helm pipeline build"
info "project root : $ROOT_DIR"

mkdir -p "$DATA_DIR" "$TILES_DIR"

if [ ! -f "$REGION_ENV" ]; then
  fail "region.env not found at $REGION_ENV — cannot continue"
  exit 1
fi

# region.env is trusted project config: bbox + source URLs.
# shellcheck disable=SC1090
. "$REGION_ENV"
info "sourced $REGION_ENV"

# Provide safe defaults (Key West) for anything region.env didn't define, so
# the script is robust to an older/partial region.env. set -u stays honored
# because we expand with :- guards.
REGION_NAME="${REGION_NAME:-keywest}"
BBOX_W="${BBOX_W:--81.86}"
BBOX_S="${BBOX_S:-24.44}"
BBOX_E="${BBOX_E:--81.68}"
BBOX_N="${BBOX_N:-24.60}"
ZMIN="${ZMIN:-7}"
ZMAX="${ZMAX:-14}"

info "region       : ${REGION_NAME}"
info "bbox W,S,E,N : ${BBOX_W},${BBOX_S},${BBOX_E},${BBOX_N}"
info "zoom range   : ${ZMIN}..${ZMAX}"

if [ -z "$PY" ]; then
  warn "no python3 found on PATH — python steps (tiles/wind/places) will be skipped"
fi
printf '\n'

# Helper: invoke a pipeline python script if both python and the script exist.
# Forwards bbox + zoom as a stable, documented CLI contract:
#   --bbox W,S,E,N  --out <path>  [--zmin Z --zmax Z]  [--source NAME]
py_pipeline() {
  local script="$1"; shift
  if [ -z "$PY" ]; then
    warn "skipping $(basename "$script"): python not available"
    return 2
  fi
  if [ ! -f "$script" ]; then
    warn "skipping $(basename "$script"): not found at $script"
    return 2
  fi
  "$PY" "$script" "$@"
}

# ===========================================================================
# 1) NOAA raster charts -> charts.mbtiles
# ===========================================================================
step_charts() {
  py_pipeline "$SCRIPT_DIR/fetch_tiles.py" \
    --source charts \
    --url "${CHARTS_URL:-}" \
    --bbox "${BBOX_W},${BBOX_S},${BBOX_E},${BBOX_N}" \
    --zmin "$ZMIN" --zmax "$ZMAX" \
    --out "$TILES_DIR/charts.mbtiles"
}
run_step "NOAA charts -> tiles/charts.mbtiles" step_charts

# ===========================================================================
# 2) Sentinel-2 cloudless (EOX) satellite -> sat.mbtiles
# ===========================================================================
step_sat() {
  py_pipeline "$SCRIPT_DIR/fetch_tiles.py" \
    --source sat \
    --url "${SAT_URL:-}" \
    --bbox "${BBOX_W},${BBOX_S},${BBOX_E},${BBOX_N}" \
    --zmin "$ZMIN" --zmax "$ZMAX" \
    --out "$TILES_DIR/sat.mbtiles"
}
run_step "Sentinel-2 satellite -> tiles/sat.mbtiles" step_sat

# ===========================================================================
# 3) Wind -> wind.json (VELOCITY) + wind_points.geojson
# ===========================================================================
step_wind() {
  py_pipeline "$SCRIPT_DIR/fetch_wind.py" \
    --bbox "${BBOX_W},${BBOX_S},${BBOX_E},${BBOX_N}" \
    --out "$DATA_DIR/wind.json" \
    --points "$DATA_DIR/wind_points.geojson"
}
run_step "Wind (Open-Meteo) -> data/wind.json + wind_points.geojson" step_wind

# ===========================================================================
# 4) Places / labels -> places.geojson  (optional script)
# ===========================================================================
if [ -f "$SCRIPT_DIR/fetch_places.py" ]; then
  step_places() {
    py_pipeline "$SCRIPT_DIR/fetch_places.py" \
      --bbox "${BBOX_W},${BBOX_S},${BBOX_E},${BBOX_N}" \
      --out "$DATA_DIR/places.geojson"
  }
  run_step "Places -> data/places.geojson" step_places
else
  say "Places -> data/places.geojson"
  info "${C_DIM}fetch_places.py not present — skipping (optional step)${C_RST}"
  record "SKIP" "Places (fetch_places.py absent)"
  printf '\n'
fi

# ===========================================================================
# 5) Depth (S-57 ENC -> depare/depcnt/soundg geojson) via GDAL ogr2ogr
#    Requires: (a) GDAL, (b) an ENC cell path. Skip gracefully otherwise.
# ===========================================================================
resolve_enc() {
  # Explicit arg wins.
  if [ "${1:-}" != "" ]; then
    printf '%s' "$1"
    return 0
  fi
  # region.env may name a cell.
  if [ "${ENC_CELL:-}" != "" ] && [ -e "${ENC_CELL}" ]; then
    printf '%s' "$ENC_CELL"
    return 0
  fi
  # Probe a few conventional locations for an S-57 base cell (*.000).
  local cand
  for dir in "$ROOT_DIR/enc" "$ROOT_DIR/data/enc" "$SCRIPT_DIR/enc" "$DATA_DIR/enc"; do
    [ -d "$dir" ] || continue
    cand="$(find "$dir" -type f -name '*.000' 2>/dev/null | head -n1)"
    if [ "$cand" != "" ]; then
      printf '%s' "$cand"
      return 0
    fi
  done
  return 1
}

say "Depth (S-57 ENC -> depare/depcnt/soundg)"
ENC_PATH="$(resolve_enc "${1:-}")" || ENC_PATH=""

if ! command -v ogr2ogr >/dev/null 2>&1; then
  warn "GDAL (ogr2ogr) not found — skipping depth extraction"
  info "${C_DIM}install: brew install gdal   (macOS)   |   apt-get install gdal-bin (Debian/Ubuntu)${C_RST}"
  record "SKIP" "Depth (GDAL not installed)"
  printf '\n'
elif [ -z "$ENC_PATH" ]; then
  warn "no ENC cell supplied or found — skipping depth extraction"
  info "${C_DIM}pass an S-57 cell:  pipeline/build.sh /path/to/US5FL...000${C_RST}"
  info "${C_DIM}or drop *.000 cells under  $ROOT_DIR/enc/${C_RST}"
  record "SKIP" "Depth (no ENC cell)"
  printf '\n'
elif [ ! -f "$SCRIPT_DIR/extract_depth.sh" ]; then
  warn "extract_depth.sh not found at $SCRIPT_DIR — skipping depth extraction"
  record "SKIP" "Depth (extract_depth.sh absent)"
  printf '\n'
else
  info "ENC cell     : $ENC_PATH"
  step_depth() {
    # extract_depth.sh contract: <enc_cell> <out_dir>; clips to bbox from env.
    BBOX_W="$BBOX_W" BBOX_S="$BBOX_S" BBOX_E="$BBOX_E" BBOX_N="$BBOX_N" \
      bash "$SCRIPT_DIR/extract_depth.sh" "$ENC_PATH" "$DATA_DIR"
  }
  run_step "Depth -> data/{depare,depcnt,soundg}.geojson" step_depth
fi

# ===========================================================================
# Final summary
# ===========================================================================
say "Pipeline summary"

printf '%s\n' "  ${C_BOLD}Steps${C_RST}"
# Render the recorded step statuses.
printf '%s' "$SUMMARY" | while IFS=$'\t' read -r st label; do
  [ -z "${st:-}" ] && continue
  case "$st" in
    OK)   printf '    %s %s\n' "${C_GRN}[ok]  ${C_RST}" "$label" ;;
    FAIL) printf '    %s %s\n' "${C_RED}[fail]${C_RST}" "$label" ;;
    SKIP) printf '    %s %s\n' "${C_YEL}[skip]${C_RST}" "$label" ;;
    *)    printf '    [%s] %s\n' "$st" "$label" ;;
  esac
done
printf '\n'

# Report which expected artifacts actually exist, with sizes.
printf '%s\n' "  ${C_BOLD}Artifacts${C_RST}"
report_artifact() {
  local path="$1" label="$2"
  if [ -s "$path" ]; then
    local size
    size="$( (du -h "$path" 2>/dev/null | awk '{print $1}') || echo '?' )"
    printf '    %s %-26s %s ${C_DIM}(%s)${C_RST}\n' "${C_GRN}+${C_RST}" "$label" "${path#"$ROOT_DIR"/}" "$size"
  else
    printf '    %s %-26s ${C_DIM}%s — missing${C_RST}\n' "${C_YEL}-${C_RST}" "$label" "${path#"$ROOT_DIR"/}"
  fi
}
report_artifact "$TILES_DIR/charts.mbtiles"      "NOAA charts"
report_artifact "$TILES_DIR/sat.mbtiles"         "Sentinel-2 satellite"
report_artifact "$DATA_DIR/wind.json"            "wind grid (VELOCITY)"
report_artifact "$DATA_DIR/wind_points.geojson"  "wind barbs"
report_artifact "$DATA_DIR/places.geojson"       "places/labels"
report_artifact "$DATA_DIR/depare.geojson"       "depth areas"
report_artifact "$DATA_DIR/depcnt.geojson"       "depth contours"
report_artifact "$DATA_DIR/soundg.geojson"       "soundings"
printf '\n'

# Serve hint.
printf '%s\n' "  ${C_BOLD}Serve the prototype${C_RST}"
if [ -n "$PY" ]; then
  printf '    %s\n' "${C_CYN}$PY -m http.server 8000 --directory \"$WEB_DIR\"${C_RST}"
else
  printf '    %s\n' "${C_CYN}cd \"$WEB_DIR\" && python3 -m http.server 8000${C_RST}"
fi
printf '    %s\n' "then open ${C_BOLD}http://localhost:8000/${C_RST}  (the map remembers view via #hash)"
printf '\n'

# Exit 0 always: this runner is best-effort by design; per-step status is in
# the summary above. (We never set -e.)
exit 0
