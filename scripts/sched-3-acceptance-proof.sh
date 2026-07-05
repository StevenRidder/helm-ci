#!/usr/bin/env bash
# SCHED-3 acceptance: live scheduler + server-fed artifact routes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="${HELM_SCHED3_EVIDENCE_DIR:-$ROOT/test-results/sched-3-live-artifacts}"
mkdir -p "$EVIDENCE_DIR"

echo "== SCHED-3 unit tests =="
node "$ROOT/web/tests/chart-scheduler-artifact-index.test.js" | tee "$EVIDENCE_DIR/unit-index.log"
node "$ROOT/web/tests/chart-scheduler-blend.test.js" | tee "$EVIDENCE_DIR/unit-blend.log"
node "$ROOT/web/test/rendermodel5-pyramid-parity.test.cjs" | tee "$EVIDENCE_DIR/rm5-parity.log"

echo "== SCHED-3 server artifact routes (optional — needs helm-server on HELM_PORT) =="
PORT="${HELM_PORT:-8080}"
BASE="http://127.0.0.1:${PORT}"
if curl -sf "$BASE/health" >/dev/null 2>&1; then
  curl -sf "$BASE/artifact/index.json" | tee "$EVIDENCE_DIR/server-index.json" | head -c 200
  echo "..."
  ETAG=$(curl -sI "$BASE/artifact/13/2241/3357.json" | awk -F': ' 'tolower($1)=="etag"{print $2}' | tr -d '\r')
  echo "sample tile ETag: $ETAG" | tee "$EVIDENCE_DIR/server-etag.log"
  CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "If-None-Match: $ETAG" "$BASE/artifact/13/2241/3357.json")
  echo "304 revalidation: HTTP $CODE" | tee -a "$EVIDENCE_DIR/server-etag.log"
  test "$CODE" = "304" || { echo "expected 304 for artifact If-None-Match"; exit 1; }
else
  echo "skip server route proof — $BASE/health unreachable (start helm-server with US5GA2BC ENC)" | tee "$EVIDENCE_DIR/server-skip.log"
fi

echo "== SCHED-3 Playwright proof =="
export HELM_SCHED3=1
export HELM_SCHED3_EVIDENCE_DIR="$EVIDENCE_DIR"
cd "$ROOT"
npx playwright test web/test/e2e/sched-3-live-artifacts.spec.js | tee "$EVIDENCE_DIR/playwright.log"

echo "SCHED-3 acceptance proof complete → $EVIDENCE_DIR"
