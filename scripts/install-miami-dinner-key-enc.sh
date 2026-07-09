#!/usr/bin/env bash
# Install NOAA ENC US5MIABB (Biscayne Bay / Dinner Key area) into ~/.helm/runtime/enc
# and extract depth GeoJSON into ~/.helm/data for depth-on-satellite overlays.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CELL="${HELM_MIAMI_ENC_CELL:-US5MIABB}"
URL="${HELM_MIAMI_ENC_URL:-https://www.charts.noaa.gov/ENCs/${CELL}.zip}"
ENC_ROOT="${HELM_ENC_ROOT:-$HOME/.helm/runtime/enc}"
DEST="$ENC_ROOT/$CELL"
STAGE="$(mktemp -d "/tmp/helm-miami-enc.XXXXXX")"
USER_DATA="${HELM_USER_DATA_ROOT:-$HOME/.helm/data}"

die() { echo "install-miami-dinner-key-enc: $*" >&2; exit 1; }
note() { printf '  ok   %s\n' "$*"; }

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

command -v curl >/dev/null || die "curl required"
command -v unzip >/dev/null || die "unzip required"

mkdir -p "$ENC_ROOT" "$USER_DATA"
echo "install-miami-dinner-key-enc: downloading $CELL"
curl -fL "$URL" -o "$STAGE/$CELL.zip"
unzip -q -o "$STAGE/$CELL.zip" -d "$STAGE"
FOUND="$(find "$STAGE" -name "$CELL.000" -print -quit)"
[ -n "$FOUND" ] || die "download did not contain $CELL.000"

rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$(dirname "$FOUND")"/. "$DEST"/
ENC="$DEST/$CELL.000"
note "installed $ENC"

if command -v ogr2ogr >/dev/null 2>&1; then
  bash "$ROOT/pipeline/extract_depth.sh" "$ENC" "$USER_DATA"
elif python3 -c "import pyogrio, geopandas" >/dev/null 2>&1; then
  python3 "$ROOT/scripts/extract-enc-depth-pyogrio.py" "$ENC" "$USER_DATA"
else
  die "need GDAL (brew install gdal) or: pip3 install pyogrio geopandas"
fi

note "Miami Dinner Key ENC ready"
echo "  ENC:       $ENC"
echo "  depth:     $USER_DATA/{depare,depcnt,soundg}.geojson"
echo "  map hash:  #14/25.706/-80.224"
