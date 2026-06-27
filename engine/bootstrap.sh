#!/usr/bin/env bash
#
# Helm headless chart-render — reproducible bootstrap.
#
# Builds the headless S-52 renderer (ocpn::chart-render) + helm-tiles / helm-engine
# from a PINNED OpenCPN upstream + a maintained patch series, with no hand-editing of
# a live clone. This is the source of truth; the clone is disposable.
#
#   engine/vendor/OPENCPN_REF   — pinned remote + SHA
#   engine/patches/000N-*.patch — our edits to upstream-tracked files (applied in order)
#   engine/vendor/cli/*.cpp     — our NEW cli/ files (copied into <clone>/cli/)
#
# Usage:
#   engine/bootstrap.sh [--dir <clone-dir>] [--jobs N] [--smoke] [--clean]
#
# Env overrides:
#   HELM_OCPN_DIR   clone/build dir (default: /tmp/helm-opencpn)
#   WX_CONFIG       wx-config executable (default: homebrew wxwidgets@3.2)
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # engine/
REPO="$(cd "$HERE/.." && pwd)"
PATCHES="$HERE/patches"
OVERLAY="$HERE/vendor/cli"
REF_FILE="$HERE/vendor/OPENCPN_REF"

OCPN_DIR="${HELM_OCPN_DIR:-/tmp/helm-opencpn}"
WX_CONFIG="${WX_CONFIG:-/opt/homebrew/opt/wxwidgets@3.2/bin/wx-config-3.2}"
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
DO_SMOKE=0; DO_CLEAN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)   OCPN_DIR="$2"; shift 2 ;;
    --jobs)  JOBS="$2"; shift 2 ;;
    --smoke) DO_SMOKE=1; shift ;;
    --clean) DO_CLEAN=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# shellcheck disable=SC1090
. "$REF_FILE"
: "${OPENCPN_REMOTE:?OPENCPN_REMOTE missing from $REF_FILE}"
: "${OPENCPN_SHA:?OPENCPN_SHA missing from $REF_FILE}"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\033[31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- prerequisites (fail loud, don't limp) --------------------------------
say "prerequisites"
command -v git   >/dev/null || die "git not found"
command -v cmake >/dev/null || die "cmake not found"
[ -x "$WX_CONFIG" ] || die "wx-config not executable at $WX_CONFIG (need wxWidgets 3.2 — 3.3 removed wxNode). brew install wxwidgets@3.2, or set WX_CONFIG."
# OpenCPN's configure patches a bundled lib (ShapefileCpp) with GNU patch syntax;
# macOS BSD patch fails. Require GNU patch (gpatch) ahead of BSD patch on PATH.
if patch --version 2>/dev/null | grep -qi 'GNU'; then :; else
  command -v gpatch >/dev/null || die "GNU patch required (OpenCPN's ShapefileCpp build patch). brew install gpatch."
  GNUBIN="$(mktemp -d)/gnubin"; mkdir -p "$GNUBIN"
  ln -sf "$(command -v gpatch)" "$GNUBIN/patch"   # expose GNU patch as 'patch' for OpenCPN's configure
  export PATH="$GNUBIN:$PATH"
fi
# The C/C++ toolchain must actually COMPILE, not just be present. A freshly
# installed Xcode whose license hasn't been accepted makes every compile (and even
# /usr/bin/python3) fail with a cryptic "You have not agreed to the Xcode license
# agreements" error. Detect that, auto-fall-back to the already-licensed Command
# Line Tools if available, else stop with the exact fix instead of a confusing
# mid-build failure.
if ! printf 'int main(void){return 0;}\n' | cc -x c - -o /dev/null 2>/dev/null; then
  CLT="/Library/Developer/CommandLineTools"
  if [ -d "$CLT" ] && printf 'int main(void){return 0;}\n' | DEVELOPER_DIR="$CLT" cc -x c - -o /dev/null 2>/dev/null; then
    export DEVELOPER_DIR="$CLT"
    echo "  toolchain: active Xcode unusable -> using Command Line Tools ($CLT)"
  else
    die "C toolchain cannot compile (the active Xcode license is likely unaccepted).
  Fix with ONE of:
    sudo xcodebuild -license accept
    sudo xcode-select -s /Library/Developer/CommandLineTools"
  fi
fi
echo "  wx-config: $WX_CONFIG ($("$WX_CONFIG" --version))"
echo "  pinned:    $OPENCPN_REMOTE @ $OPENCPN_SHA"

# ---- fetch the pinned upstream (shallow, exact SHA) -----------------------
say "fetch OpenCPN @ $OPENCPN_SHA -> $OCPN_DIR"
[ "$DO_CLEAN" = 1 ] && rm -rf "$OCPN_DIR"
if [ -d "$OCPN_DIR/.git" ]; then
  # The pinned SHA is immutable — if it's already in the clone, DON'T re-fetch.
  # (fail-and-fix-early robustness: a redundant network fetch was failing the whole
  # incremental rebuild on a transient blip — "git-remote-https died of signal 15" —
  # when no network was needed at all.)
  if git -C "$OCPN_DIR" cat-file -e "${OPENCPN_SHA}^{commit}" 2>/dev/null; then
    echo "  reusing clone; pinned SHA already present — skipping fetch (offline-safe)"
  else
    echo "  reusing clone; fetching pinned SHA"
    git -C "$OCPN_DIR" fetch --depth 1 origin "$OPENCPN_SHA"
  fi
  git -C "$OCPN_DIR" checkout -q --detach "$OPENCPN_SHA"
  git -C "$OCPN_DIR" reset --hard -q "$OPENCPN_SHA"
  git -C "$OCPN_DIR" clean -fdq -e build   # keep the build dir for incremental rebuilds
else
  mkdir -p "$OCPN_DIR"
  git -C "$OCPN_DIR" init -q
  git -C "$OCPN_DIR" remote add origin "$OPENCPN_REMOTE" 2>/dev/null || true
  git -C "$OCPN_DIR" fetch --depth 1 origin "$OPENCPN_SHA"
  git -C "$OCPN_DIR" checkout -q --detach "$OPENCPN_SHA"
fi
[ "$(git -C "$OCPN_DIR" rev-parse HEAD)" = "$OPENCPN_SHA" ] || die "checkout is not the pinned SHA"

# ---- apply the maintained patch series (in order, fail loud) --------------
say "apply patch series"
shopt -s nullglob
for p in "$PATCHES"/[0-9][0-9][0-9][0-9]-*.patch; do
  name="$(basename "$p")"
  git -C "$OCPN_DIR" apply --check "$p" || die "patch does not apply cleanly: $name"
  git -C "$OCPN_DIR" apply "$p"
  echo "  applied $name"
done

# ---- overlay our NEW cli/ files -------------------------------------------
say "overlay engine/vendor/cli -> $OCPN_DIR/cli"
for f in "$OVERLAY"/*; do
  cp "$f" "$OCPN_DIR/cli/$(basename "$f")"
  echo "  + cli/$(basename "$f")"
done

# ---- configure + build the helm targets -----------------------------------
say "configure (Release)"
cmake -S "$OCPN_DIR" -B "$OCPN_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DwxWidgets_CONFIG_EXECUTABLE="$WX_CONFIG" \
  -DOCPN_BUILD_TEST=OFF >/dev/null

say "build helm targets (-j$JOBS)"
# `helm-server` is the one-origin binary (nav WS + S-52 tiles + /health + /catalog + static UI
# on ONE port, default 8080) that helm_server.cpp implements and that .claude/run-helm-server.sh
# + .claude/launch.json exec. It is built by default here (ENGINE-12) so the reproducible build
# produces build/cli/helm-server and one-origin launchers work with no manual extra step.
# helm-tides / helm-tides-smoke / helm-tides-fetch are the OpenCPN tide engine, its smoke check,
# and the tide-catalog fetch helper; building them by default keeps the tide stack reproducible too.
cmake --build "$OCPN_DIR/build" --target helm-chartrender chart-spike helm-tides helm-tides-smoke helm-tides-fetch helm-tiles helm-engine helm-server -j"$JOBS"

BIN="$OCPN_DIR/build/cli"
say "done — binaries in $BIN"
ls -1 "$BIN"/{helm-tiles,helm-engine,chart-spike,helm-tides-smoke,helm-tides-fetch,helm-server} 2>/dev/null | sed 's/^/  /'
[ -x "$BIN/helm-server" ] || die "helm-server (one-origin :8080) did not build despite being a default target (ENGINE-12) — check the build log above"

# ---- install the DURABLE runtime (so a fresh install / reboot can COLD-START) ----------------
# The engine resolves the S-52 presentation library from HELM_S57_DATA (default ~/.helm/runtime/
# s57data) — NOT /tmp, which is wiped on reboot. (The old binary hardcoded /tmp/opencpn/data/s57data,
# a path bootstrap never created, so a fresh build failed "s52plib load FAILED" on first run.) Copy
# it out of the clone here so `helm-server` just works. Charts (ENC .000) stay user-provided via
# HELM_ENC — Helm ships no chart packs.
RUNTIME="${HELM_RUNTIME_DIR:-$HOME/.helm/runtime}"
if [ -d "$OCPN_DIR/data/s57data" ]; then
  mkdir -p "$RUNTIME"
  rm -rf "$RUNTIME/s57data" && cp -R "$OCPN_DIR/data/s57data" "$RUNTIME/s57data"
  say "installed S-52 presentation library -> $RUNTIME/s57data (durable; override with HELM_S57_DATA)"
else
  say "WARN: $OCPN_DIR/data/s57data not found — set HELM_S57_DATA or helm-server will fail 's52plib load'"
fi
# assert the Step-6 seam invariant survived the reproducible build
syms=$(nm "$BIN/libhelm-chartrender.a" 2>/dev/null | grep -c 'top_frame3Get' || true)
echo "  seam check: top_frame::Get symbols in libhelm-chartrender.a = ${syms:-?} (want 0)"

# assert the arm's-length GPL containment invariant (ENGINE-11): the GPL engine is
# executable-only (no redistributable shared lib) and the client surface is protocol-only.
# Fails the build on a breach. See docs/decisions/0009-arms-length-gpl-containment.md.
"$HERE/containment-check.sh" "$BIN"

if [ "$DO_SMOKE" = 1 ]; then
  # One-origin smoke (ENGINE-12): prove the reproducible build produced a WORKING
  # helm-server, not just a binary on disk. /health (+ /catalog) need no chart data
  # and confirm the one-origin server boots and serves; the S-52 tile render is
  # exercised too when an ENC cell is present. Runs on a private port so it never
  # collides with a dev server on :8080.
  say "smoke: helm-server one-origin (/health + S-52 tile)"
  ENC="${HELM_ENC:-/tmp/ENC_ROOT/US5FL96M/US5FL96M.000}"
  export DYLD_LIBRARY_PATH="/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
  SMOKE_TMP="$(mktemp -d)"
  HELM_BIND=127.0.0.1 HELM_PORT=8088 HELM_TILES_NO_WARMUP=1 \
    HELM_WEB_ROOT="$REPO/web" HELM_CONFIG="$SMOKE_TMP" HELM_ENC="$ENC" \
    "$BIN/helm-server" >/tmp/helm-server-smoke.log 2>&1 &
  pid=$!; sleep 3
  fail() { kill "$pid" 2>/dev/null || true; rm -rf "$SMOKE_TMP"; sed 's/^/    /' /tmp/helm-server-smoke.log; die "$1"; }
  hcode=$(curl -s -o /tmp/helm-health.json -w '%{http_code}' "http://127.0.0.1:8088/health"  || echo ERR)
  ccode=$(curl -s -o /dev/null            -w '%{http_code}' "http://127.0.0.1:8088/catalog" || echo ERR)
  echo "  /health -> http=$hcode   /catalog -> http=$ccode"
  [ "$hcode" = 200 ] || fail "helm-server /health did not return 200 — the one-origin binary is not serving"
  if [ -f "$ENC" ]; then
    tcode=$(curl -s -o /tmp/helm-server-tile.png -w '%{http_code}' "http://127.0.0.1:8088/chart/12/1120/1756.png" || echo ERR)
    tsz=$(wc -c < /tmp/helm-server-tile.png 2>/dev/null | tr -d ' ')
    echo "  /chart/12/1120/1756.png -> http=$tcode bytes=$tsz"
    [ "${tsz:-0}" -gt 1000 ] || fail "helm-server S-52 tile render produced no chart content"
    echo "  ✓ one-origin server rendered S-52 chart content"
  else
    echo "  (no ENC at $ENC; skipped tile render — /health proves the binary serves)"
  fi
  kill "$pid" 2>/dev/null || true
  rm -rf "$SMOKE_TMP"
  echo "  ✓ helm-server one-origin smoke passed"
fi
