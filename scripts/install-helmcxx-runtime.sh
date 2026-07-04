#!/usr/bin/env bash
#
# HELMC++-6: install the boat-side C++ runtime into deterministic directories.
#
# This is intentionally a boring copy/install script. It does not build, fetch,
# run Docker, create a virtualenv, or start services. Build with engine/bootstrap.sh
# first, then run this script as the user/root context appropriate for the target
# directories.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_CLI="${HELM_BUILD_CLI_DIR:-${HELM_OCPN_DIR:-$HOME/.helm/build/helm-opencpn}/build/cli}"
WEB_SOURCE="${HELM_WEB_SOURCE:-$ROOT/web}"
RUNTIME_SOURCE="${HELM_RUNTIME_SOURCE:-$HOME/.helm/runtime}"

PREFIX="${HELM_INSTALL_PREFIX:-/opt/helm}"
CONFIG_DIR="${HELM_INSTALL_CONFIG_DIR:-/etc/helm}"
STATE_DIR="${HELM_INSTALL_STATE_DIR:-/var/lib/helm}"
CACHE_DIR="${HELM_INSTALL_CACHE_DIR:-/var/cache/helm}"
LOG_DIR="${HELM_INSTALL_LOG_DIR:-/var/log/helm}"
PACKS_DIR="${HELM_INSTALL_PACKS_DIR:-/srv/helm/packs}"
WX_PACKS_DIR="${HELM_INSTALL_WX_PACKS_DIR:-/srv/helm/wx-packs}"
STAGING_ROOT="${HELM_INSTALL_STAGING_ROOT:-}"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: scripts/install-helmcxx-runtime.sh [options]

Install Helm's C++ boat runtime into deterministic runtime directories.

Options:
  --build-cli DIR       Directory containing helm-server/helm-packd/helm-envd/helm-basemap-cache.
  --web-root DIR        Source web directory to install as the static cockpit.
  --runtime-source DIR  Source runtime asset directory containing s57data.
  --prefix DIR          Runtime prefix, default /opt/helm.
  --config-dir DIR      Config directory, default /etc/helm.
  --state-dir DIR       Durable state directory, default /var/lib/helm.
  --cache-dir DIR       Regenerable cache directory, default /var/cache/helm.
  --log-dir DIR         Log directory, default /var/log/helm.
  --packs-dir DIR       Local MBTiles/PMTiles directory, default /srv/helm/packs.
  --wx-packs-dir DIR    Environmental pack release directory, default /srv/helm/wx-packs.
  --staging-root DIR    Prepend DIR to every absolute install destination for proof/testing.
  --dry-run             Print the install plan without copying files.
  -h, --help            Show this help.

The script never starts services. Use the templates under packaging/systemd or
packaging/launchd after installation.
USAGE
}

die() {
  printf 'install-helmcxx-runtime: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '==> %s\n' "$*"
}

require_abs() {
  local name="$1" path="$2"
  case "$path" in
    /*) ;;
    *) die "$name must be an absolute path: $path" ;;
  esac
}

dest_path() {
  local path="$1"
  if [ -n "$STAGING_ROOT" ]; then
    printf '%s/%s\n' "${STAGING_ROOT%/}" "${path#/}"
  else
    printf '%s\n' "$path"
  fi
}

install_file() {
  local src="$1" dst="$2" mode="$3"
  [ -f "$src" ] || die "missing file: $src"
  if [ "$DRY_RUN" = 1 ]; then
    printf 'copy %s -> %s\n' "$src" "$dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  chmod "$mode" "$dst"
}

copy_dir() {
  local src="$1" dst="$2"
  [ -d "$src" ] || die "missing directory: $src"
  if [ "$DRY_RUN" = 1 ]; then
    printf 'copy-dir %s -> %s\n' "$src" "$dst"
    return
  fi
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -R "$src/." "$dst/"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --build-cli) shift; BUILD_CLI="${1:-}" ;;
    --web-root) shift; WEB_SOURCE="${1:-}" ;;
    --runtime-source) shift; RUNTIME_SOURCE="${1:-}" ;;
    --prefix) shift; PREFIX="${1:-}" ;;
    --config-dir) shift; CONFIG_DIR="${1:-}" ;;
    --state-dir) shift; STATE_DIR="${1:-}" ;;
    --cache-dir) shift; CACHE_DIR="${1:-}" ;;
    --log-dir) shift; LOG_DIR="${1:-}" ;;
    --packs-dir) shift; PACKS_DIR="${1:-}" ;;
    --wx-packs-dir) shift; WX_PACKS_DIR="${1:-}" ;;
    --staging-root) shift; STAGING_ROOT="${1:-}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

for pair in \
  "prefix:$PREFIX" \
  "config-dir:$CONFIG_DIR" \
  "state-dir:$STATE_DIR" \
  "cache-dir:$CACHE_DIR" \
  "log-dir:$LOG_DIR" \
  "packs-dir:$PACKS_DIR" \
  "wx-packs-dir:$WX_PACKS_DIR"
do
  require_abs "${pair%%:*}" "${pair#*:}"
done
[ -z "$STAGING_ROOT" ] || require_abs "staging-root" "$STAGING_ROOT"

for bin in helm-server helm-packd helm-envd helm-basemap-cache; do
  [ -x "$BUILD_CLI/$bin" ] || die "$bin missing or not executable in $BUILD_CLI"
done
[ -d "$WEB_SOURCE" ] || die "web root missing: $WEB_SOURCE"
[ -d "$RUNTIME_SOURCE/s57data" ] || die "runtime s57data missing: $RUNTIME_SOURCE/s57data; run engine/bootstrap.sh first"

PREFIX_DST="$(dest_path "$PREFIX")"
CONFIG_DST="$(dest_path "$CONFIG_DIR")"
STATE_DST="$(dest_path "$STATE_DIR")"
CACHE_DST="$(dest_path "$CACHE_DIR")"
LOG_DST="$(dest_path "$LOG_DIR")"
PACKS_DST="$(dest_path "$PACKS_DIR")"
WX_PACKS_DST="$(dest_path "$WX_PACKS_DIR")"

log "installing C++ runtime binaries"
for bin in helm-server helm-packd helm-envd helm-basemap-cache; do
  install_file "$BUILD_CLI/$bin" "$PREFIX_DST/bin/$bin" 0755
done

log "installing cockpit web assets"
copy_dir "$WEB_SOURCE" "$PREFIX_DST/web"

log "installing durable runtime assets"
copy_dir "$RUNTIME_SOURCE/s57data" "$STATE_DST/runtime/s57data"
if [ -d "$RUNTIME_SOURCE/tcdata" ]; then
  copy_dir "$RUNTIME_SOURCE/tcdata" "$STATE_DST/runtime/tcdata"
fi

if [ "$DRY_RUN" != 1 ]; then
  mkdir -p \
    "$CONFIG_DST" \
    "$STATE_DST/runtime/enc" \
    "$STATE_DST/data" \
    "$CACHE_DST/senc" \
    "$CACHE_DST/tile-cache" \
    "$CACHE_DST/tides" \
    "$CACHE_DST/basemap-fill" \
    "$CACHE_DST/work" \
    "$LOG_DST" \
    "$PACKS_DST" \
    "$WX_PACKS_DST"
fi

log "writing runtime environment"
if [ "$DRY_RUN" = 1 ]; then
  printf 'write %s/helm-runtime.env\n' "$CONFIG_DST"
else
  cat >"$CONFIG_DST/helm-runtime.env" <<EOF
# Generated by scripts/install-helmcxx-runtime.sh.
# Target paths are deterministic and do not depend on a build checkout.
HELM_BIND=0.0.0.0
HELM_PORT=8080
HELM_WEB_ROOT=$PREFIX/web
HELM_CONFIG=$CONFIG_DIR
HELM_RUNTIME_DIR=$STATE_DIR/runtime
HELM_S57_DATA=$STATE_DIR/runtime/s57data
HELM_TCDATA_DIR=$STATE_DIR/runtime/tcdata
HELM_SENC_DIR=$CACHE_DIR/senc
HELM_TIDES_CACHE_DIR=$CACHE_DIR/tides
HELM_FILL_CACHE=$CACHE_DIR/basemap-fill
HELM_USER_DATA_ROOT=$STATE_DIR/data
HELM_ENC=$STATE_DIR/runtime/enc/US5FL4CR/US5FL4CR.000
HELM_MBTILES_DIR=$PACKS_DIR
HELM_WX_PACKS_DIR=$WX_PACKS_DIR
HELM_PACKD_PORT=8091
HELM_ENVD_PORT=8094
HELM_BASEMAP_CACHE_PORT=8095
HELM_TILES_NO_WARMUP=1
EOF
  chmod 0644 "$CONFIG_DST/helm-runtime.env"
fi

log "installed Helm runtime plan"
printf '  prefix:      %s%s\n' "$PREFIX" "${STAGING_ROOT:+ (staged at $PREFIX_DST)}"
printf '  config:      %s%s\n' "$CONFIG_DIR" "${STAGING_ROOT:+ (staged at $CONFIG_DST)}"
printf '  state:       %s%s\n' "$STATE_DIR" "${STAGING_ROOT:+ (staged at $STATE_DST)}"
printf '  cache:       %s%s\n' "$CACHE_DIR" "${STAGING_ROOT:+ (staged at $CACHE_DST)}"
printf '  logs:        %s%s\n' "$LOG_DIR" "${STAGING_ROOT:+ (staged at $LOG_DST)}"
printf '  local packs: %s%s\n' "$PACKS_DIR" "${STAGING_ROOT:+ (staged at $PACKS_DST)}"
printf '  wx packs:    %s%s\n' "$WX_PACKS_DIR" "${STAGING_ROOT:+ (staged at $WX_PACKS_DST)}"
