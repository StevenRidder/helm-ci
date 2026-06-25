#!/usr/bin/env bash
#
# engine/test-engine.sh — end-to-end proof of the headless OpenCPN engine.
#
# Black-box: starts the REAL binaries and asserts their behaviour over the wire, with
# each check mapped to the ENGINE-* task it proves. Run after a build (bootstrap.sh).
#
#   A. One-origin server   — helm-server serves nav WS + S-52 tiles + health + catalog
#                            + UI on one port, with snapshot/delta/seq framing and
#                            immutable tile caching.            (ENGINE-9, ENGINE-12, CHART-3)
#   B. Nav core            — the model's relocated UpdateProgress drives per-fix
#                            geometry + arrival-circle auto-advance; a real NMEA fix
#                            overrides position; source tags stay honest.
#                                                               (ENGINE-3, ENGINE-7, ENGINE-10)
#   C. GPL containment     — the engine is a process behind the protocol, never a
#                            client-linkable library.           (ENGINE-11)
#
# Usage:  engine/test-engine.sh
# Env:    HELM_OCPN_DIR (default /tmp/helm-opencpn), HELM_TEST_PORT (default 8077)

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
BIN="${HELM_OCPN_DIR:-/tmp/helm-opencpn}/build/cli"
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
SPORT="${HELM_TEST_PORT:-8077}"   # one-origin helm-server test port
# Hermetic engine ports: default to FREE ephemeral ports so a concurrent helm-server/
# helm-engine on a shared box can't steal :8081/:10110 and turn Section B's real-data
# checks into misleading nav-core FAILs. Override with HELM_ENGINE_PORT / HELM_NMEA_PORT.
free_port(){ python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));p=s.getsockname()[1];s.close();print(p)'; }
EPORT="${HELM_ENGINE_PORT:-$(free_port)}"   # helm-engine nav WS port
NPORT="${HELM_NMEA_PORT:-$(free_port)}"     # helm-engine NMEA 0183 / AIS ingest port

pass=0; fail=0
P(){ printf '\033[32m  PASS\033[0m  %s\n' "$*"; pass=$((pass+1)); }
F(){ printf '\033[31m  FAIL\033[0m  %s\n' "$*"; fail=$((fail+1)); }
hdr(){ printf '\n\033[1m%s\033[0m\n' "$*"; }
jget(){ python3 -c 'import json,sys;exec("o=json.load(sys.stdin)\nfor k in sys.argv[1].split(\".\"): o=o[k]\nprint(o)")' "$1"; }

[ -x "$BIN/helm-server" ] || { echo "no helm-server at $BIN — run engine/bootstrap.sh first"; exit 2; }

inject_rmc(){ # lat lon  → send one valid GPRMC fix to the engine's NMEA port ($NPORT)
python3 - "$1" "$2" "$NPORT" <<'PY'
import socket,sys
lat=float(sys.argv[1]); lon=float(sys.argv[2]); port=int(sys.argv[3]); la=abs(lat); lo=abs(lon)
lats=f"{int(la):02d}{(la-int(la))*60:07.4f}"; lons=f"{int(lo):03d}{(lo-int(lo))*60:07.4f}"
b=f"GPRMC,120000,A,{lats},{'N' if lat>=0 else 'S'},{lons},{'E' if lon>=0 else 'W'},5.0,015.0,250625,,"
cs=0
for c in b: cs^=ord(c)
s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',port)); s.sendall(f"${b}*{cs:02X}\r\n".encode()); s.close()
PY
}

printf '\033[1m=== Helm engine — end-to-end test ===\033[0m\n'
echo "binaries: $BIN"

# ---------- A) one-origin server ----------
hdr "A. One-origin server  (ENGINE-9 merge · ENGINE-12 build · CHART-3 tiles)"
ST="$(mktemp -d)"
HELM_BIND=127.0.0.1 HELM_PORT=$SPORT HELM_TILES_NO_WARMUP=1 HELM_WEB_ROOT="$REPO/web" HELM_CONFIG="$ST" \
  "$BIN/helm-server" >/tmp/te-server.log 2>&1 &
SPID=$!; sleep 3
# nav-stream framing (snapshot → deltas, strictly increasing seq) via the contract smoke
node "$HERE/stream-smoke.js" 127.0.0.1 $SPORT --ws-only >/tmp/te-smoke.txt 2>&1
if grep -q 'ALL PASS' /tmp/te-smoke.txt; then
  while IFS= read -r l; do P "nav stream:${l#  ok  }"; done < <(grep '  ok   ' /tmp/te-smoke.txt)
else
  F "nav-stream framing failed:"; sed 's/^/        /' /tmp/te-smoke.txt
fi
h=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$SPORT/health" || echo ERR)
[ "$h" = 200 ] && P "GET /health → 200 (liveness)" || F "GET /health → $h"
# real S-52 tile render off the Key West ENC, with immutable caching + 304 revalidation
curl -s -D /tmp/te-th -o /tmp/te-tile.png "http://127.0.0.1:$SPORT/chart/12/1120/1756.png"
tcode=$(awk 'NR==1{print $2}' /tmp/te-th 2>/dev/null); tsz=$(wc -c </tmp/te-tile.png 2>/dev/null | tr -d ' ')
ctype=$(grep -i '^content-type:' /tmp/te-th 2>/dev/null | tr -d '\r' | awk '{print $2}')
{ [ "$tcode" = 200 ] && echo "${ctype:-}" | grep -qi 'image/png' && [ "${tsz:-0}" -gt 1000 ]; } \
  && P "GET /chart S-52 tile → 200 image/png, ${tsz}B real ENC render (CHART-3)" \
  || F "S-52 tile → code=$tcode type=${ctype:-?} bytes=${tsz:-?}"
grep -qi 'cache-control:.*immutable' /tmp/te-th 2>/dev/null \
  && P "tile: Cache-Control immutable (offline-friendly caching)" || F "tile not immutable-cached"
etag=$(grep -i '^etag:' /tmp/te-th 2>/dev/null | tr -d '\r' | awk '{print $2}')
if [ -n "${etag:-}" ]; then
  c304=$(curl -s -o /dev/null -w '%{http_code}' -H "If-None-Match: $etag" "http://127.0.0.1:$SPORT/chart/12/1120/1756.png" || echo ERR)
  [ "$c304" = 304 ] && P "tile: If-None-Match → 304 (cache revalidation works)" || F "If-None-Match → $c304"
else F "tile missing ETag"; fi
cat=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$SPORT/catalog" || echo ERR)
[ "$cat" = 200 ] && P "GET /catalog → 200 (chart-cell catalog)" || F "GET /catalog → $cat"
ui=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$SPORT/" || echo ERR)
[ "$ui" = 200 ] && P "GET / → 200 (serves the UI from one origin)" || F "GET / (UI) → $ui"
kill $SPID 2>/dev/null; wait $SPID 2>/dev/null; rm -rf "$ST"

# ---------- B) nav core: relocated UpdateProgress + auto-advance ----------
hdr "B. Nav core: model UpdateProgress + auto-advance  (ENGINE-3 · ENGINE-7 · ENGINE-10)"
# Start the engine on its OWN (ephemeral) ports — no global `pkill helm-engine`,
# which would also kill other agents' engines on a shared host.
HELM_ENGINE_PORT=$EPORT HELM_NMEA_PORT=$NPORT "$BIN/helm-engine" >/tmp/te-engine.log 2>&1 &
NPID=$!; sleep 1.5
# FAIL-LOUD preflight: every check below depends on the NMEA listener binding. If it
# didn't (port stolen, etc.), ABORT Section B with the REAL cause instead of emitting
# misleading "no override / no advance" FAILs that masquerade as nav-core regressions.
if grep -q "bind/listen on .* failed" /tmp/te-engine.log; then
  F "Section B aborted: helm-engine could NOT bind NMEA :$NPORT — port contention/environment, not a nav-core bug:"
  sed 's/^/        /' /tmp/te-engine.log
else
  snap="$(node "$HERE/nav-capture.js" 127.0.0.1 $EPORT 1 /)"
  shape=$(printf '%s' "$snap" | python3 -c 'import json,sys;a=json.load(sys.stdin).get("active",{});print(int(all(k in a for k in("eta","ttg","vmg","dtg","xte","nextWp")) and "legs" in a))' 2>/dev/null || echo 0)
  [ "$shape" = 1 ] && P "nav snapshot carries the full per-fix math (dtg/xte/eta/ttg/vmg/legs/nextWp)" || F "snapshot missing nav-math fields"
  psrc=$(printf '%s' "$snap" | jget sources.pos 2>/dev/null || echo "?")
  [ "$psrc" = simulated ] && P "honest source tag: pos=\"simulated\" before any real fix (ENGINE-7)" || F "pos source not honestly tagged ($psrc)"
  nw0=$(printf '%s' "$snap" | python3 -c 'import json,sys;print(json.load(sys.stdin)["active"]["nextWp"].split()[0])' 2>/dev/null || echo "?")
  echo "    active waypoint before any fix: $nw0"

  inject_rmc 24.485 -81.800; sleep 2
  f2="$(node "$HERE/nav-capture.js" 127.0.0.1 $EPORT 1 /)"
  src2=$(printf '%s' "$f2" | jget sources.pos 2>/dev/null || echo "?")
  nw2=$(printf '%s' "$f2" | python3 -c 'import json,sys;print(json.load(sys.stdin)["active"]["nextWp"].split()[0])' 2>/dev/null || echo "?")
  [ "$src2" = nmea ] && P "real NMEA fix overrides position: pos source → nmea (CONN-2 / ENGINE-7)" || F "pos source stayed \"$src2\" after RMC inject"
  [ "$nw2" != "$nw0" ] && [ "$nw2" != "?" ] && P "arrival auto-advance: $nw0 → $nw2 (model UpdateProgress, ENGINE-10)" || F "no waypoint advance after reaching WP ($nw0 → $nw2)"

  inject_rmc 24.515 -81.793; sleep 2
  nw3=$(node "$HERE/nav-capture.js" 127.0.0.1 $EPORT 1 / | python3 -c 'import json,sys;print(json.load(sys.stdin)["active"]["nextWp"].split()[0])' 2>/dev/null || echo "?")
  inject_rmc 24.540 -81.786; sleep 2
  nw4=$(node "$HERE/nav-capture.js" 127.0.0.1 $EPORT 1 / | python3 -c 'import json,sys;print(json.load(sys.stdin)["active"]["nextWp"].split()[0])' 2>/dev/null || echo "?")
  { [ "$nw3" != "$nw2" ] && [ "$nw4" != "$nw3" ] && [ "$nw4" != "?" ]; } \
    && P "monotonic advance through the route: $nw2 → $nw3 → $nw4" \
    || F "advance not monotonic ($nw2 → $nw3 → $nw4)"
fi
kill $NPID 2>/dev/null; wait $NPID 2>/dev/null

# ---------- C) GPL containment ----------
hdr "C. GPL containment guard  (ENGINE-11)"
if bash "$HERE/containment-check.sh" "$BIN" >/tmp/te-cont.txt 2>&1; then
  P "containment guard exit 0: GPL engine is executable-only + client is protocol-only"
else
  F "containment guard reported a breach:"; sed 's/^/        /' /tmp/te-cont.txt
fi

# ---------- result ----------
hdr "RESULT"
printf '  %d passed, %d failed\n' "$pass" "$fail"
if [ "$fail" = 0 ]; then printf '\033[32m  ✓ ENGINE end-to-end: all green\033[0m\n'; exit 0
else printf '\033[31m  ✗ failures above\033[0m\n'; exit 1; fi
