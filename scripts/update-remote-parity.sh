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
GIT_REMOTE_URL="${HELM_GIT_REMOTE_URL:-git@github.com:StevenRidder/Helm.git}"
GIT_SSH_KEY="${HELM_GIT_SSH_KEY:-$HOME/.ssh/id_ed25519_github_helm}"
ALLOW_DIRTY="${HELM_ALLOW_DIRTY:-0}"
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
  --replace-running    Stop processes listening on :PORT, :8093, and :8095 before start
  -h, --help           Show this help

Env:
  HELM_ALLOW_DIRTY=1   Allow running from a checkout with local source changes
  HELM_BASEMAP_UPSTREAM=http://host:8091
                       Start cache-backed basemap proxy on :8091
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

require_clean_tree() {
  [ "$ALLOW_DIRTY" = 1 ] && return 0
  local dirty
  dirty="$(git status --porcelain)"
  [ -z "$dirty" ] && return 0
  echo "update-remote-parity: checkout has local changes; refusing to mix local drift with GitHub main." >&2
  echo "$dirty" >&2
  echo "Commit/stash/remove these changes, or set HELM_ALLOW_DIRTY=1 if you really mean to run from a dirty tree." >&2
  exit 21
}

git_pull_main() {
  if [ -f "$GIT_SSH_KEY" ]; then
    echo "update-remote-parity: pulling main over SSH ($GIT_SSH_KEY)"
    env GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes" git fetch "$GIT_REMOTE_URL" main
  else
    # No dedicated SSH key (a cloud agent, or a Mac whose key dropped) — pull over HTTPS so the machine
    # can STILL sync instead of dead-ending on an SSH origin. Works with gh's git credential helper
    # (`gh auth setup-git`) or a token embedded in HELM_GIT_HTTPS_URL. Removes the hard SSH-key
    # dependency that otherwise blocks a keyless machine from ever reaching the latest main.
    local url="${HELM_GIT_HTTPS_URL:-https://github.com/StevenRidder/Helm.git}"
    echo "update-remote-parity: no SSH key — pulling main over HTTPS ($url)"
    git fetch "$url" main
  fi
  git merge --ff-only FETCH_HEAD
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

require_clean_tree

if [ "$PULL" = 1 ]; then
  git_pull_main
fi

if [ "$BUILD" = 1 ]; then
  engine/bootstrap.sh
fi


ENC="$(HELM_SAMPLE_ENC_CELL=US5FL4CR scripts/install-sample-enc.sh | tail -n 1)"
[ -f "$ENC" ] || { echo "update-remote-parity: expected ENC missing: $ENC" >&2; exit 1; }

if [ "$START" = 1 ]; then
  BASEMAP_ARGS=()
  stop_port "$PORT"
  if [ -n "${HELM_BASEMAP_UPSTREAM:-}" ]; then
    stop_port 8091
    BASEMAP_ARGS=(--basemap-proxy)
  fi
  stop_port 8093
stop_port 8094
  stop_port 8095
  echo "update-remote-parity: starting Helm on :$PORT with weather :8093, fill :8095, and $ENC"
  exec env HELM_ENC="$ENC" scripts/start-helm.sh --port "$PORT" --weather "${BASEMAP_ARGS[@]}" --fill
fi
