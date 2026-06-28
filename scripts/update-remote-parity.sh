#!/usr/bin/env bash
# Pull/build/install the verified fresh-install chart stack, then start Helm.
#
# Intended use on the remote Mac after GitHub has the known-good commit:
#   scripts/update-remote-parity.sh --replace-running
#
# Without --replace-running, the script refuses to touch existing listeners and
# prints the PIDs that need to be stopped first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${HELM_PORT:-8080}"
HASH="${HELM_VERIFY_HASH:-#11/24.52/-81.77}"
PULL=1
BUILD=1
START=1
VERIFY_ONLY=0
REPLACE=0

usage() {
  cat <<EOF
Usage: scripts/update-remote-parity.sh [options]

Options:
  --port N             Helm server port (default: $PORT)
  --hash HASH          Verification hash (default: $HASH)
  --no-pull            Do not git pull
  --no-build           Do not run engine/bootstrap.sh
  --verify-only        Only run Playwright verification against the live server
  --replace-running    Stop processes listening on :PORT and :8095 before start
  -h, --help           Show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --port) shift; PORT="$1" ;;
    --hash) shift; HASH="$1" ;;
    --no-pull) PULL=0 ;;
    --no-build) BUILD=0 ;;
    --verify-only) VERIFY_ONLY=1; START=0; PULL=0; BUILD=0 ;;
    --replace-running) REPLACE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "update-remote-parity: unknown arg '$1'" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "$ROOT"

pids_on_port() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

stop_port() {
  local port="$1" pids
  pids="$(pids_on_port "$port")"
  [ -z "$pids" ] && return 0
  if [ "$REPLACE" != 1 ]; then
    echo "update-remote-parity: port $port is busy:"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    echo "Re-run with --replace-running to stop these listeners, or stop them yourself."
    exit 20
  fi
  echo "update-remote-parity: stopping listener(s) on :$port"
  kill $pids 2>/dev/null || true
  sleep 1
}

if [ "$VERIFY_ONLY" = 1 ]; then
  exec scripts/verify-live-ui.sh "http://127.0.0.1:$PORT" "$HASH"
fi

if [ "$PULL" = 1 ]; then
  git pull --ff-only origin main
fi

if [ "$BUILD" = 1 ]; then
  engine/bootstrap.sh
fi

ENC="$(HELM_SAMPLE_ENC_CELL=US5FL4CR scripts/install-sample-enc.sh | tail -n 1)"
[ -f "$ENC" ] || { echo "update-remote-parity: expected ENC missing: $ENC" >&2; exit 1; }

if [ "$START" = 1 ]; then
  stop_port "$PORT"
  stop_port 8095
  echo "update-remote-parity: starting Helm on :$PORT with $ENC"
  exec env HELM_ENC="$ENC" scripts/start-helm.sh --port "$PORT" --fill
fi
