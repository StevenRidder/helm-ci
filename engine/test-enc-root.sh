#!/usr/bin/env bash
# INTAKE-4: prove helm-server recursively loads, catalogs, SENC-compiles, and
# renders multiple ENC cells from one registered root. Pass two or more .000
# paths, or let the test use the first cells under ~/.helm/runtime/enc.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
BIN="${HELM_OCPN_DIR:-$HOME/.helm/build/helm-opencpn}/build/cli"
SERVER="${HELM_SERVER_BIN:-$BIN/helm-server}"
S57_DATA="${HELM_S57_DATA:-$HOME/.helm/runtime/s57data}"

die() { echo "test-enc-root: $*" >&2; exit 1; }
[ -x "$SERVER" ] || die "helm-server not built at $SERVER"
[ -f "$S57_DATA/S52RAZDS.RLE" ] || die "S-52 data missing at $S57_DATA"

free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

declare -a SOURCES=()
if [ "$#" -gt 0 ]; then
  SOURCES=("$@")
else
  while IFS= read -r path; do
    SOURCES+=("$path")
    [ "${#SOURCES[@]}" -ge 2 ] && break
  done < <(find "${HELM_ENC_TEST_ROOT:-$HOME/.helm/runtime/enc}" -type f -name '*.000' 2>/dev/null | sort)
fi
[ "${#SOURCES[@]}" -ge 2 ] || die "need at least two real .000 cells (pass their paths as arguments)"

TMP="${TMPDIR:-/tmp}/helm-enc-root-test.$$"
ROOT="$TMP/chart root"
SENC="$TMP/senc"
CONFIG="$TMP/config"
LOG="$TMP/helm-server.log"
CATALOG="$TMP/catalog.json"
mkdir -p "$ROOT" "$SENC" "$CONFIG"

PID=""
cleanup() {
  if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  [ "${HELM_KEEP_TEST_TMP:-0}" = 1 ] || rm -rf "$TMP"
}
trap cleanup EXIT

expected_ids=""
index=0
for source in "${SOURCES[@]}"; do
  [ -f "$source" ] || die "cell not found: $source"
  index=$((index + 1))
  id="$(basename "$source" .000)"
  expected_ids="${expected_ids}${expected_ids:+,}$id"
  destination="$ROOT/region-$index/$(basename "$(dirname "$source")")"
  mkdir -p "$destination"
  cp -R "$(dirname "$source")"/. "$destination"/
done

PORT="${HELM_TEST_PORT:-$(free_port)}"
RELAY_PORT="${HELM_RELAY_PORT:-$(free_port)}"
HELM_BIND=127.0.0.1 \
HELM_PORT="$PORT" \
HELM_RELAY_PORT="$RELAY_PORT" \
HELM_TILES_NO_WARMUP=1 \
HELM_WEB_ROOT="$REPO/web" \
HELM_CONFIG="$CONFIG" \
HELM_S57_DATA="$S57_DATA" \
HELM_SENC_DIR="$SENC" \
HELM_ENC_ROOT="$ROOT" \
  "$SERVER" >"$LOG" 2>&1 &
PID=$!

for _ in $(seq 1 300); do
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/health"; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then cat "$LOG" >&2; die "helm-server exited during ENC load"; fi
  sleep 0.2
done

curl -sf "http://127.0.0.1:$PORT/catalog" >"$CATALOG" || { cat "$LOG" >&2; die "catalog unavailable"; }
python3 - "$CATALOG" "$expected_ids" "${HELM_REQUIRE_FOREIGN_ENC:-0}" <<'PY'
import json, sys
catalog = json.load(open(sys.argv[1]))
expected = set(sys.argv[2].split(','))
cells = catalog.get('cells') or []
ids = {cell.get('id') for cell in cells}
missing = expected - ids
assert not missing, f"catalog missing cells: {sorted(missing)}; got {sorted(ids)}"
assert catalog.get('count') == len(cells) >= 2, catalog
assert catalog.get('chart_loaded') is True, catalog
assert catalog.get('chart_status') == 'loaded', catalog
for cell in cells:
    assert 'edition' in cell and 'editionDate' in cell, cell
    bbox = cell.get('bbox')
    coverage = cell.get('coverage') or {}
    assert isinstance(bbox, list) and len(bbox) == 4, cell
    assert coverage.get('status') == 'available', cell
    assert coverage.get('bbox') == bbox, cell
if sys.argv[3] == '1':
    assert any(not str(cell.get('id', '')).startswith('US') for cell in cells), ids
PY

python3 - "$CATALOG" "$PORT" >"$TMP/tile-urls" <<'PY'
import json, math, sys, urllib.parse
catalog = json.load(open(sys.argv[1]))
port = int(sys.argv[2])
for cell in catalog['cells']:
    west, south, east, north = cell['bbox']
    lon, lat = (west + east) / 2, (south + north) / 2
    scale = max(1, int(cell['scale']))
    zoom = round(math.log2(max(1.0, 559082264.029 * math.cos(math.radians(lat)) / scale)))
    zoom = min(18, max(2, zoom))
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat = min(85.05112878, max(-85.05112878, lat))
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    cell_id = urllib.parse.quote(str(cell['id']), safe='')
    print(f"http://127.0.0.1:{port}/chart/{zoom}/{x}/{y}.png?cells={cell_id}")
PY

tile_index=0
while IFS= read -r url; do
  tile_index=$((tile_index + 1))
  curl -sf "$url" -o "$TMP/tile-$tile_index.png" || { cat "$LOG" >&2; die "tile failed: $url"; }
  python3 - "$TMP/tile-$tile_index.png" <<'PY'
import sys
data = open(sys.argv[1], 'rb').read()
assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) > 50
PY
done <"$TMP/tile-urls"

senc_count="$(find "$SENC" -type f -name '*.S57' | wc -l | tr -d ' ')"
[ "$senc_count" -ge 2 ] || { find "$SENC" -maxdepth 2 -type f >&2; cat "$LOG" >&2; die "expected at least two compiled SENC files, got $senc_count"; }

grep -q "scanning ${#SOURCES[@]} ENC file(s)" "$LOG"
grep -q "loaded ${#SOURCES[@]} ENC cell(s), rejected 0" "$LOG"
echo "helm-server recursive ENC root passed: ${#SOURCES[@]} cells, $senc_count SENC files, catalog + per-cell tiles on :$PORT"
