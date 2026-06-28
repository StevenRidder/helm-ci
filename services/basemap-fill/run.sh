#!/bin/sh
# ============================================================================
#  Helm basemap-fill proxy launcher (CHART-16) — the ONLINE-FILL underlay cache.
#  Clean-IP raster tile cache (EOX Sentinel-2 by default). Runs on :8095 —
#  NOT :8091 (that's the offline mbtiles basemap server; WX-15 owns that port).
#  Cache persists in ~/.helm/basemap-fill-cache (no size cap by decision).
# ============================================================================
export HELM_FILL_PORT="${HELM_FILL_PORT:-8095}"
export HELM_FILL_CACHE="${HELM_FILL_CACHE:-$HOME/.helm/basemap-fill-cache}"
export HELM_FILL_REFRESH_DAYS="${HELM_FILL_REFRESH_DAYS:-30}"

# REUSE-IF-UP: never double-bind; leave a running instance alone.
if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:$HELM_FILL_PORT/health" 2>/dev/null; then
  echo "basemap-fill already up on :$HELM_FILL_PORT — reusing."
  exit 0
fi
exec python3 "$(dirname "$0")/server.py" "$HELM_FILL_PORT"
