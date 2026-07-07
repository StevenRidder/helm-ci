#!/usr/bin/env bash
# ENC-4 — extract region depth GeoJSON from the active ENC cell into user-data (~/.helm/data).
# Idempotent: skips when depth-provenance.json matches the current HELM_ENC mtime.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HELM_RUNTIME_DIR="${HELM_RUNTIME_DIR:-$HOME/.helm/runtime}"
HELM_SAMPLE_ENC="${HELM_SAMPLE_ENC:-$HELM_RUNTIME_DIR/enc/US5FL4CR/US5FL4CR.000}"
OUT="${HELM_USER_DATA_ROOT:-${HELM_CONFIG:-$HOME/.helm}/data}"
ENC="${HELM_ENC:-}"

if [ -z "$ENC" ] && [ -f "$HELM_SAMPLE_ENC" ]; then
  ENC="$HELM_SAMPLE_ENC"
fi
if [ -z "$ENC" ]; then
  ENC="$(find "${HELM_ENC_ROOT:-$HELM_RUNTIME_DIR/enc}" -name '*.000' -type f 2>/dev/null | head -1 || true)"
fi

[ -n "$ENC" ] && [ -f "$ENC" ] || {
  echo "extract-user-depth: no ENC .000 cell (set HELM_ENC or install sample ENC)" >&2
  exit 1
}
command -v ogr2ogr >/dev/null 2>&1 || {
  echo "extract-user-depth: GDAL ogr2ogr not found (brew install gdal)" >&2
  exit 1
}

mkdir -p "$OUT"
PROV="$OUT/depth-provenance.json"
ENC_MTIME="$(python3 - "$ENC" <<'PY'
import os, sys
print(int(os.path.getmtime(sys.argv[1])))
PY
)"
if [ -f "$PROV" ] && [ -f "$OUT/depare.geojson" ]; then
  if python3 - "$PROV" "$ENC" "$ENC_MTIME" <<'PY'
import json, os, sys
prov_path, enc, enc_mtime = sys.argv[1], sys.argv[2], int(sys.argv[3])
with open(prov_path, encoding="utf-8") as f:
    prov = json.load(f)
ok = (
    prov.get("source") == "enc"
    and prov.get("enc_path") == os.path.abspath(enc)
    and prov.get("enc_mtime") == enc_mtime
    and os.path.isfile(os.path.join(os.path.dirname(prov_path), "depare.geojson"))
)
sys.exit(0 if ok else 1)
PY
  then
    echo "extract-user-depth: up to date for $(basename "$ENC" .000) -> $OUT"
    exit 0
  fi
fi

echo "extract-user-depth: extracting $(basename "$ENC" .000) -> $OUT"
bash "$REPO_ROOT/pipeline/extract_depth.sh" "$ENC" "$OUT"
