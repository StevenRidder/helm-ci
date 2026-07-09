#!/usr/bin/env bash
# QA-L-2 depth-on-sat fusion preset screenshot proof — Fiji (mock packd) + St Marys (live harbour).
#
# Proof bar: both legs assert rendered depth features AND ENC extract provenance
# (HelmEncDepthSources mode 'enc'). The St Marys leg therefore REQUIRES the live server
# to serve /user-data/ depth GeoJSON extracted from its loaded cell. Fiji-only runs must
# be requested explicitly (HELM_QAL2_ALLOW_FIJI_ONLY=1) — a silent skip is not a pass.
# US regression twin with real NOAA ENC: scripts/verify-miami-dinner-key-depth-on-sat.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="${HELM_QAL2_EVIDENCE_DIR:-$ROOT/test-results/qa-l2-depth-on-sat}"
HARBOUR_PORT="${HELM_HARBOUR_PORT:-8080}"
FIJI_PORT="${HELM_QAL2_FIJI_PORT:-8078}"

die() { echo "verify-qa-l2-depth-on-sat: $*" >&2; exit 1; }
note() { printf '  ok   %s\n' "$*"; }

mkdir -p "$EVIDENCE_DIR"
export HELM_QAL2=1
export HELM_QAL2_EVIDENCE_DIR="$EVIDENCE_DIR"

if [ ! -d "$ROOT/web/test/node_modules" ]; then
  note "installing web/test dependencies"
  npm --prefix "$ROOT/web/test" ci
fi

echo "[qa-l2] Fiji depth-on-sat (mock packd on serve.py :$FIJI_PORT)"
export HELM_OFFLINE20_MOCK_PACKD=1
export HELM_E2E_URL="http://127.0.0.1:$FIJI_PORT"
export HELM_E2E_PORT="$FIJI_PORT"
(
  cd "$ROOT/web/test"
  npx playwright test e2e/qa-l2-depth-on-sat-fiji-st-marys.spec.js \
    --config=playwright.qa-l2.config.js \
    --grep "Fiji"
) | tee "$EVIDENCE_DIR/fiji-playwright.log"

if curl -sf --max-time 5 "http://127.0.0.1:$HARBOUR_PORT/health" >/dev/null 2>&1; then
  echo "[qa-l2] St Marys depth-on-sat (live helm-server :$HARBOUR_PORT)"
  PROV="$(curl -sf --max-time 5 "http://127.0.0.1:$HARBOUR_PORT/user-data/depth-provenance.json" 2>/dev/null || true)"
  if [ -z "$PROV" ]; then
    die "live helm-server on :$HARBOUR_PORT has no ENC depth extract (/user-data/depth-provenance.json 404).
  The St Marys proof requires real ENC depth vectors, not the bundled demo.
  Fix: run scripts/extract-user-depth.sh (GDAL) or scripts/extract-enc-depth-pyogrio.py
  against the server's loaded cell, into its HELM_USER_DATA_ROOT, then re-run."
  fi
  note "live depth extract: $(echo "$PROV" | tr -d '\n' | head -c 120)"
  export HELM_HARBOUR_E2E=1
  export HELM_E2E_URL="http://127.0.0.1:$HARBOUR_PORT"
  export HELM_E2E_PORT="$HARBOUR_PORT"
  export HELM_HARBOUR_HASH="${HELM_QAL2_ST_MARYS_HASH:-#13/30.862/-81.487}"
  if [[ "${HELM_QAL2_HEADED:-}" == "1" ]]; then
    note "headed Chrome enabled (HELM_QAL2_HEADED=1)"
  fi
  (
    cd "$ROOT/web/test"
    npx playwright test e2e/qa-l2-depth-on-sat-fiji-st-marys.spec.js \
      --config=playwright.qa-l2.config.js \
      --grep "St Marys"
  ) | tee "$EVIDENCE_DIR/st-marys-playwright.log"
elif [ "${HELM_QAL2_ALLOW_FIJI_ONLY:-}" = "1" ]; then
  note "skip St Marys (HELM_QAL2_ALLOW_FIJI_ONLY=1) — helm-server not healthy on :$HARBOUR_PORT"
  echo "St Marys leg SKIPPED by request — this run proves the Fiji CI leg only, not live ENC depth" \
    >"$EVIDENCE_DIR/st-marys-skip.log"
else
  die "helm-server not healthy on :$HARBOUR_PORT — the St Marys live-ENC leg cannot run.
  Start helm-server with US5GA2BC loaded (plus its depth extract), or run the Miami twin:
  scripts/verify-miami-dinner-key-depth-on-sat.sh. To accept a Fiji-only run explicitly,
  set HELM_QAL2_ALLOW_FIJI_ONLY=1."
fi

note "QA-L-2 evidence → $EVIDENCE_DIR"
echo "  screenshots: $EVIDENCE_DIR/qa-l2-*.png"
echo "  state:       $EVIDENCE_DIR/qa-l2-*-state.json"
