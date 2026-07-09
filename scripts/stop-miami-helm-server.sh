#!/usr/bin/env bash
PORT="${HELM_MIAMI_PORT:-9160}"
PIDFILE="${HELM_MIAMI_PIDFILE:-/tmp/helm-miami-${PORT}.pid}"
if [ -f "$PIDFILE" ]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
lsof -tiTCP:"$PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
echo "stopped :$PORT"
