#!/bin/sh
# helm-first-run.sh — first-run chart-library bootstrap (INTAKE-6).
#
# One command that takes a fresh (or hand-wired) Helm box to the shipped
# "register your chart folders" convention (chart-intake-v1):
#
#   1. ensure the chart-roots registry + default chart root exist,
#   2. register any existing customer folders passed via --root (recursive
#      scan, files stay put — the OpenCPN Add Directory model),
#   3. rebuild the in-place chart index,
#   4. ask a running helm-packd to rescan (no restart needed),
#   5. print what was found, per persona.
#
# Both customer shapes run the exact same flow; only the folder contents differ:
#   ENC-only   --root points at a folder tree of S-57 *.000 cells
#   sat-first  --root points at a folder tree of *.mbtiles/*.pmtiles packs
# The two coexist in one tree: each consumer claims its own extensions
# (helm-packd takes tile packs, helm-server takes ENC cells via HELM_ENC_ROOT,
# the layer manifest takes *.geojson overlays).
#
# Usage:
#   helm-first-run.sh [--root DIR [--label NAME]]... [--config-dir DIR]
#                     [--default-root DIR] [--packd-url URL]
#
#   --root DIR       Register an existing chart folder (repeatable). Files are
#                    indexed in place; nothing is moved or renamed.
#   --label NAME     Public label for the most recent --root (no paths).
#   --config-dir DIR Registry/index location (default $HELM_CONFIG or ~/.helm/config).
#   --default-root DIR
#                    Default chart root to create if the registry is new
#                    (default $HELM_DEFAULT_CHART_ROOT or ~/.helm/charts).
#   --packd-url URL  Running helm-packd to poke (default http://127.0.0.1:8091).
#   --no-packd       Skip the live helm-packd rescan poke (for callers that
#                    restart the daemon themselves, e.g. the installer).
#
# Fail-loud policy: registration/index errors abort with the named cause; an
# unreachable helm-packd is reported and the registry still takes effect on its
# next start — never a silent skip.
set -eu

self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
intake="$self_dir/../pipeline/chart_intake.py"
[ -f "$intake" ] || {
  echo "helm-first-run: chart_intake.py not found at $intake — broken install (re-run scripts/install-helmcxx-runtime.sh)" >&2
  exit 2
}
command -v python3 >/dev/null 2>&1 || { echo "helm-first-run: python3 is required" >&2; exit 2; }

PACKD_URL="http://127.0.0.1:${HELM_PACKD_PORT:-8091}"
ROOTS=""    # newline-separated "path<TAB>label" records
LAST_ROOT=""

append_root() {  # append_root <path> <label>
  ROOTS="${ROOTS}${1}$(printf '\t')${2}
"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      shift; [ -n "${1:-}" ] || { echo "helm-first-run: --root needs a directory" >&2; exit 2; }
      [ -z "$LAST_ROOT" ] || append_root "$LAST_ROOT" ""
      LAST_ROOT="$1" ;;
    --label)
      shift; [ -n "${1:-}" ] || { echo "helm-first-run: --label needs a value" >&2; exit 2; }
      [ -n "$LAST_ROOT" ] || { echo "helm-first-run: --label must follow a --root" >&2; exit 2; }
      append_root "$LAST_ROOT" "$1"; LAST_ROOT="" ;;
    --config-dir)
      shift; [ -n "${1:-}" ] || { echo "helm-first-run: --config-dir needs a directory" >&2; exit 2; }
      HELM_CONFIG="$1"; export HELM_CONFIG ;;
    --default-root)
      shift; [ -n "${1:-}" ] || { echo "helm-first-run: --default-root needs a directory" >&2; exit 2; }
      HELM_DEFAULT_CHART_ROOT="$1"; export HELM_DEFAULT_CHART_ROOT ;;
    --packd-url)
      shift; [ -n "${1:-}" ] || { echo "helm-first-run: --packd-url needs a URL" >&2; exit 2; }
      PACKD_URL="$1" ;;
    --no-packd)
      PACKD_URL="" ;;
    -h|--help)
      sed -n '2,38p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      echo "helm-first-run: unknown argument: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done
[ -z "$LAST_ROOT" ] || append_root "$LAST_ROOT" ""

# chart_intake exits 1 when the rebuilt index carries invalid charts. That must
# not silently abort registration here — the summary below is the loud reporter
# for index errors (and exits 1 itself). Real intake failures (exit 2) abort.
run_intake() {
  rc=0
  python3 "$intake" "$@" >/dev/null || rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then exit "$rc"; fi
}

# 1. Ensure the registry + default root exist (and build the index once).
echo "==> ensuring chart-roots registry + default chart root"
run_intake rescan

# 2. Register each customer folder in place.
printf '%s' "$ROOTS" | while IFS="$(printf '\t')" read -r root label; do
  [ -n "$root" ] || continue
  if [ -n "$label" ]; then
    echo "==> registering chart root: $root (label: $label)"
    run_intake register "$root" --label "$label"
  else
    echo "==> registering chart root: $root"
    run_intake register "$root"
  fi
done

# 3+5. Rebuild the index and print the per-persona summary. The summary reader
# exits 1 when the index says "error" so invalid charts fail this bootstrap loud
# (catalog itself also exits 1 then — defer that so the summary names the bad charts).
echo "==> chart library after rescan"
catalog_file=$(mktemp "${TMPDIR:-/tmp}/helm-first-run.XXXXXX")
trap 'rm -f "$catalog_file"' EXIT
catalog_rc=0
python3 "$intake" catalog >"$catalog_file" || catalog_rc=$?
if [ "$catalog_rc" -ne 0 ] && [ "$catalog_rc" -ne 1 ]; then
  # exit 1 means "index says error" — the summary below names the bad charts.
  # Anything else is a real intake failure whose cause is already on stderr.
  echo "helm-first-run: chart_intake catalog failed (exit $catalog_rc)" >&2
  exit "$catalog_rc"
fi
python3 - "$catalog_file" <<'PY'
import json, sys

with open(sys.argv[1], encoding="utf-8") as stream:
    index = json.load(stream)
by_type = {"tile_pack": 0, "enc": 0, "overlay": 0}
for chart in index.get("charts", []):
    by_type[chart["chart_type"]] = by_type.get(chart["chart_type"], 0) + 1
groups = {(c["root_id"], c["group"]) for c in index.get("charts", [])}
roots = index.get("roots", [])

print(f"    charts indexed : {index.get('chart_count', 0)} across {len(roots)} root(s), {len(groups)} group(s)")
print(f"    tile packs     : {by_type['tile_pack']}  (sat-first base + basemaps -> helm-packd :8091)")
print(f"    ENC cells      : {by_type['enc']}  (S-52 vector charts -> helm-server :8080 via HELM_ENC_ROOT)")
print(f"    overlays       : {by_type['overlay']}  (GeoJSON -> layer manifest)")
for root in roots:
    marker = " (default)" if root.get("default") else ""
    status = "" if root.get("status") == "available" else f"  [{root.get('status')}: {root.get('reason', 'unavailable')}]"
    print(f"    root {root['id']}: {root.get('label', 'Charts')}{marker} — {root.get('chart_count', 0)} chart(s){status}")

status = index.get("status")
if status == "error":
    bad = [c for c in index.get("charts", []) if c["validation"]["status"] == "error"]
    print(f"    INDEX STATUS: error — {len(bad)} invalid chart(s):", file=sys.stderr)
    for chart in bad:
        print(f"      {chart['relative_path']}: {chart['validation']['code']} — {chart['validation']['message']}", file=sys.stderr)
    sys.exit(1)
if status == "warning":
    print(f"    index status: warning ({index.get('warning_count', 0)} warning(s) — see `chart_intake.py catalog`)")
if by_type["enc"]:
    print("    note: ENC cells render when helm-server's HELM_ENC_ROOT covers their folder")
    print("          (recursive; the registry above is the library/catalog surface).")
PY

# 4. Live rescan on a running helm-packd — visible fallback when it is down.
if [ -z "$PACKD_URL" ]; then
  echo "==> skipping live helm-packd rescan (--no-packd) — caller restarts the daemon"
elif command -v curl >/dev/null 2>&1 && curl -fsS -o /dev/null --max-time 3 "$PACKD_URL/health" 2>/dev/null; then
  echo "==> helm-packd is up at $PACKD_URL — triggering live rescan"
  curl -fsS -X POST --max-time 30 "$PACKD_URL/rescan" || {
    echo "helm-first-run: POST $PACKD_URL/rescan FAILED — restart helm-packd to pick up the registry" >&2
    exit 1
  }
  echo ""
else
  echo "==> helm-packd not reachable at $PACKD_URL — registry takes effect on its next start"
fi

registry_file="${HELM_CHART_ROOTS_FILE:-${HELM_CONFIG:-$HOME/.helm/config}/chart-roots.json}"
echo "==> done. Registry: $registry_file (private, 0600)"
echo "    Manage roots: python3 $intake list|register|unregister|rescan|catalog"
