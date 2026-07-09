#!/usr/bin/env bash
# Start persistent Miami/Dinner Key helm-server on :9160 (does not touch :8080).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${HELM_MIAMI_PORT:-9160}"
PIDFILE="${HELM_MIAMI_PIDFILE:-/tmp/helm-miami-${PORT}.pid}"
LOG="${HELM_MIAMI_LOG:-/tmp/helm-miami-server.log}"
ENC="${HELM_ENC:-$HOME/.helm/runtime/enc/US5MIABB/US5MIABB.000}"

die() { echo "start-miami-helm-server: $*" >&2; exit 1; }

[ -f "$ENC" ] || die "missing $ENC — run scripts/install-miami-dinner-key-enc.sh"
[ -x "$HOME/.helm/build/helm-opencpn/build/cli/helm-server" ] || die "helm-server not built"

if [ -f "$PIDFILE" ]; then
  OLD="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null && curl -sf --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null; then
    echo "start-miami-helm-server: already running pid=$OLD on :$PORT"
    exit 0
  fi
fi

lsof -tiTCP:"$PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
sleep 0.5

export DYLD_LIBRARY_PATH="/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib:${DYLD_LIBRARY_PATH:-}"
export HELM_PORT="$PORT" HELM_BIND=127.0.0.1
export HELM_WEB_ROOT="$ROOT/web"
export HELM_CONFIG="${HELM_CONFIG:-$HOME/.helm/config}"
export HELM_USER_DATA_ROOT="${HELM_USER_DATA_ROOT:-$HOME/.helm/data}"
export HELM_ENC="$ENC" HELM_TILES_NO_WARMUP=1

nohup "$HOME/.helm/build/helm-opencpn/build/cli/helm-server" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"

for _ in $(seq 1 60); do
  if curl -sf --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null; then
    echo "start-miami-helm-server: up pid=$(cat "$PIDFILE") http://127.0.0.1:$PORT/"
    exit 0
  fi
  sleep 0.25
done

die "failed to become healthy — see $LOG"
