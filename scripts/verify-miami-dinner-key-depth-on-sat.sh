#!/usr/bin/env bash
# Dinner Key / Miami depth-on-sat proof with real NOAA ENC US5MIABB.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${HELM_MIAMI_PORT:-9160}"
ENC="${HELM_ENC:-$HOME/.helm/runtime/enc/US5MIABB/US5MIABB.000}"
EVIDENCE="${HELM_MIAMI_EVIDENCE_DIR:-/tmp/helm-miami-dinner-key}"
HASH="${HELM_MIAMI_HASH:-#14/25.706/-80.224}"

die() { echo "verify-miami-dinner-key-depth-on-sat: $*" >&2; exit 1; }
note() { printf '  ok   %s\n' "$*"; }

[ -f "$ENC" ] || die "missing ENC — run scripts/install-miami-dinner-key-enc.sh first"
[ -f "$HOME/.helm/data/depare.geojson" ] || die "missing depth extract — run install script first"
[ -x "$HOME/.helm/build/helm-opencpn/build/cli/helm-server" ] || die "helm-server not built"

if [ ! -d "$ROOT/web/test/node_modules" ]; then
  note "installing web/test dependencies"
  npm --prefix "$ROOT/web/test" ci
fi

export DYLD_LIBRARY_PATH="/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib:${DYLD_LIBRARY_PATH:-}"
export HELM_PORT="$PORT" HELM_BIND=127.0.0.1
export HELM_WEB_ROOT="$ROOT/web"
export HELM_CONFIG="${HELM_CONFIG:-$HOME/.helm/config}"
export HELM_USER_DATA_ROOT="${HELM_USER_DATA_ROOT:-$HOME/.helm/data}"
export HELM_ENC="$ENC" HELM_TILES_NO_WARMUP=1

mkdir -p "$EVIDENCE"
if curl -sf --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  note "reusing helm-server on :$PORT"
  SPID=""
else
  note "starting private helm-server on :$PORT (does not touch :8080)"
  "$HOME/.helm/build/helm-opencpn/build/cli/helm-server" >"$EVIDENCE/helm-server.log" 2>&1 &
  SPID=$!
  for _ in $(seq 1 50); do
    curl -sf --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null && break
    sleep 0.2
  done
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || die "helm-server did not start on :$PORT"
fi

cleanup_server() {
  if [ -n "${SPID:-}" ] && [ "${HELM_MIAMI_STOP_SERVER:-}" = "1" ]; then
    kill "$SPID" 2>/dev/null || true
  fi
}
trap cleanup_server EXIT

(
  cd "$ROOT/web/test"
  HELM_MIAMI_PROOF=1 HELM_HARBOUR_E2E=1 \
  HELM_E2E_URL="http://127.0.0.1:$PORT" HELM_E2E_PORT="$PORT" \
  HELM_MIAMI_HASH="$HASH" HELM_MIAMI_EVIDENCE_DIR="$EVIDENCE" \
    npx playwright test e2e/miami-dinner-key-depth-on-sat.spec.js \
      --config=playwright.harbour.config.js
) | tee "$EVIDENCE/playwright.log"

note "evidence → $EVIDENCE"
echo "  screenshot: $EVIDENCE/miami-dinner-key-depth-on-sat.png"
echo "  manual URL: http://127.0.0.1:$PORT/$HASH  → Layers → Depth on sat"
if [ -n "${SPID:-}" ]; then
  echo "  server:     left running on :$PORT (pid $SPID) — set HELM_MIAMI_STOP_SERVER=1 to auto-stop"
fi
