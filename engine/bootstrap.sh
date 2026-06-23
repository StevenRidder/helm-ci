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
echo "  wx-config: $WX_CONFIG ($("$WX_CONFIG" --version))"
echo "  pinned:    $OPENCPN_REMOTE @ $OPENCPN_SHA"

# ---- fetch the pinned upstream (shallow, exact SHA) -----------------------
say "fetch OpenCPN @ $OPENCPN_SHA -> $OCPN_DIR"
[ "$DO_CLEAN" = 1 ] && rm -rf "$OCPN_DIR"
if [ -d "$OCPN_DIR/.git" ]; then
  echo "  reusing clone; hard-resetting to pinned SHA"
  git -C "$OCPN_DIR" fetch --depth 1 origin "$OPENCPN_SHA"
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
cmake --build "$OCPN_DIR/build" --target helm-chartrender chart-spike helm-tiles helm-engine -j"$JOBS"

BIN="$OCPN_DIR/build/cli"
say "done — binaries in $BIN"
ls -1 "$BIN"/{helm-tiles,helm-engine,chart-spike} 2>/dev/null | sed 's/^/  /'
# assert the Step-6 seam invariant survived the reproducible build
syms=$(nm "$BIN/libhelm-chartrender.a" 2>/dev/null | grep -c 'top_frame3Get' || true)
echo "  seam check: top_frame::Get symbols in libhelm-chartrender.a = ${syms:-?} (want 0)"

if [ "$DO_SMOKE" = 1 ]; then
  say "smoke: render one tile"
  ENC="${HELM_ENC:-/tmp/ENC_ROOT/US5FL96M/US5FL96M.000}"
  [ -f "$ENC" ] || { echo "  (no ENC at $ENC; skipping smoke render)"; exit 0; }
  "$BIN/helm-tiles" >/tmp/helm-bootstrap-smoke.log 2>&1 &
  pid=$!; sleep 3
  code=$(curl -s -o /tmp/helm-smoke.png -w '%{http_code}' "http://127.0.0.1:8082/chart/12/1120/1756.png" || echo ERR)
  sz=$(wc -c < /tmp/helm-smoke.png 2>/dev/null | tr -d ' ')
  kill "$pid" 2>/dev/null || true
  echo "  tile 12/1120/1756 -> http=$code bytes=$sz"
  [ "${sz:-0}" -gt 1000 ] && echo "  ✓ rendered chart content" || die "smoke render produced no chart content"
fi
