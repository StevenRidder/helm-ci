#!/usr/bin/env bash
set -euo pipefail

# Publish a sanitized snapshot of the private Helm repo to the stable public mirror.
# This script is private-side tooling and is excluded from git archive via .gitattributes.

PUBLIC_REPO="${PUBLIC_REPO:-StevenRidder/helm-public}"
PUBLIC_REMOTE_URL="${PUBLIC_REMOTE_URL:-https://github.com/${PUBLIC_REPO}.git}"
SOURCE_REF="${1:-HEAD}"
COMMIT_MESSAGE="${PUBLIC_COMMIT_MESSAGE:-Publish public snapshot}"
WORK_ROOT="${WORK_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/helm-public-publish.XXXXXX")}"
ARCHIVE="${WORK_ROOT}/source.tar"
EXPORT_DIR="${WORK_ROOT}/export"
PUBLIC_CLONE="${WORK_ROOT}/public"

HIDDEN_PATH_RE='^(PRD\.md|docs/(AGENT-BOOTSTRAP|AUDIT-2026-06-26|BUSINESS-MODEL|ROADMAP|FEATURE-AUDIT|FEATURE-TRACKER|EPICS|LABS|VISION|SPACETIME-PROBE|WEATHER-ROUTING|BRIEFINGS|PUBLIC-ALPHA-CHECKLIST|HANDOFF-TESTING|TIDES_UI_SPEC)\.md|docs/posts/|docs/mockups/|docs/integrations/awesome-maplibre-STATUS\.md|docs/decisions/(0003-license-posture|0006-destination-dossier-and-briefings|0007-spacetime-probe|0010-distribution-and-packaging-posture)\.md|scripts/(publish-public-mirror|bootstrap-private-install|update-remote-parity)\.sh|\.gitattributes$|.*\.(mbtiles|kap|000|s57|S57|s63|S63|senc|SENC|grb|grb2|grib2|zip)$|charts/|cache/|chart-packs/|basemaps/|tiles/|\.helm/|web/data/charts/|web/data/sat/|web/data/wxtiles/|pipeline/region\.env$)'
PUBLIC_SAMPLE_PATH_ALLOW_RE='^([0-9]+:)?web/data/predictwind-demo\.grb2$'
HIDDEN_TEXT_RE='PRD\.md|ROADMAP\.md|FEATURE-AUDIT\.md|FEATURE-TRACKER\.md|EPICS\.md|LABS\.md|VISION\.md|SPACETIME-PROBE\.md|WEATHER-ROUTING\.md|BRIEFINGS\.md|PUBLIC-ALPHA-CHECKLIST\.md|HANDOFF-TESTING\.md|TIDES_UI_SPEC\.md|docs/mockups|docs/posts|0003-license-posture|0010-distribution-and-packaging-posture|0006-destination-dossier-and-briefings|0007-spacetime-probe|awesome-maplibre-STATUS|BUSINESS-MODEL|COMPETITIVE|BUILD-PLAN-COMMUNITY-LLM|nfl-outreach-draft|AGENT-BOOTSTRAP|CLAUDE\.md|AGENTS\.md'
HARD_SECRET_RE='(/Users/steveridder|Dropbox|PM_MCP_TOKEN|taikun-plan|plan\.taikunai|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY)'
RUNTIME_GUARD_FILES=(
  web/index.html
  web/style.json
  web/style/helm-chart-basemaps.json
  web/server-endpoint.js
  web/alarms.js
  web/depth-contours.js
  engine/vendor/cli/helm_server.cpp
  pipeline/extract_depth.sh
  docs/RUNBOOK.md
  services/basemap-fill/README.md
  services/basemap-fill/run.sh
  services/basemap-fill/server.py
)
RUNTIME_REQUIRED_TEXT=(
  'Online fill'
  'helm-chart-online-fill'
  'data-layer="helm-chart-online-fill"'
  'data-base="navionics" checked'
  'data-base="googlesat"'
  'data-base="bingsat"'
  'data-base="arcgis"'
  'localhost:8091/navionics'
  'localhost:8091/googlesat'
  'localhost:8091/bingsat'
  'localhost:8091/arcgis'
  'ui.onlineFill'
  'basemap/eox'
  '8095'
  '~/.helm/basemap-fill-cache'
  'HELM_USER_DATA_ROOT'
  '/user-data/'
  '~/.helm/data'
)
RUNTIME_FORBIDDEN_TEXT=(
  'NOAA public chart'
  'Sentinel-2 sample'
  'BYO chart pack'
  'BYO imagery A'
  'BYO imagery B'
  'BYO imagery C'
)

die() {
  echo "publish-public-mirror: $*" >&2
  exit 1
}

require_clean_private_tree() {
  git diff --quiet || die "private worktree has unstaged changes; publish from a clean checkout"
  git diff --cached --quiet || die "private worktree has staged changes; publish from a clean checkout"
}

scan_tree() {
  local tree_dir="$1"
  local rel_files
  rel_files="$(cd "$tree_dir" && find . -type f -not -path './.git/*' | sed 's#^\./##' | LC_ALL=C sort)"

  if printf '%s\n' "$rel_files" | rg -n "$HIDDEN_PATH_RE" | rg -v "$PUBLIC_SAMPLE_PATH_ALLOW_RE" >/tmp/helm-public-hidden-paths.$$; then
    cat /tmp/helm-public-hidden-paths.$$
    rm -f /tmp/helm-public-hidden-paths.$$
    die "hidden private paths are present in export"
  fi
  rm -f /tmp/helm-public-hidden-paths.$$

  if (cd "$tree_dir" && rg -n "$HIDDEN_TEXT_RE" --glob '!web/vendor/**') >/tmp/helm-public-hidden-text.$$; then
    cat /tmp/helm-public-hidden-text.$$
    rm -f /tmp/helm-public-hidden-text.$$
    die "hidden private references are present in export"
  fi
  rm -f /tmp/helm-public-hidden-text.$$

  if (cd "$tree_dir" && rg -n "$HARD_SECRET_RE" --glob '!web/vendor/**') >/tmp/helm-public-hard-secrets.$$; then
    cat /tmp/helm-public-hard-secrets.$$
    rm -f /tmp/helm-public-hard-secrets.$$
    die "hard secret/private-machine pattern found in export"
  fi
  rm -f /tmp/helm-public-hard-secrets.$$
}

scan_runtime_contract() {
  local tree_dir="$1"
  local term

  for term in "${RUNTIME_REQUIRED_TEXT[@]}"; do
    if ! (cd "$tree_dir" && rg -F -q -- "$term" "${RUNTIME_GUARD_FILES[@]}"); then
      die "runtime guard failed: expected '$term' in private/live UI or basemap-fill files"
    fi
  done

  if ! (cd "$tree_dir" && rg -q 'Navionics chart|Local chart pack' web/index.html); then
    die "runtime guard failed: expected a local/user-owned chart-pack label in web/index.html"
  fi

  if ! (cd "$tree_dir" && rg -q 'Google satellite|Local imagery A' web/index.html); then
    die "runtime guard failed: expected first local/user-owned imagery slot in web/index.html"
  fi

  if ! (cd "$tree_dir" && rg -q 'Bing satellite|Local imagery B' web/index.html); then
    die "runtime guard failed: expected second local/user-owned imagery slot in web/index.html"
  fi

  if ! (cd "$tree_dir" && rg -q 'ArcGIS satellite|Local imagery C' web/index.html); then
    die "runtime guard failed: expected third local/user-owned imagery slot in web/index.html"
  fi

  for term in "${RUNTIME_FORBIDDEN_TEXT[@]}"; do
    if (cd "$tree_dir" && rg -F -n -- "$term" web/index.html web/style.json web/style/helm-chart-basemaps.json); then
      die "runtime guard failed: public placeholder label '$term' is present in live UI/style"
    fi
  done
}

main() {
  command -v git >/dev/null || die "git is required"
  command -v gh >/dev/null || die "GitHub CLI gh is required"
  command -v rg >/dev/null || die "ripgrep rg is required"
  command -v rsync >/dev/null || die "rsync is required"

  git rev-parse --is-inside-work-tree >/dev/null || die "run from the private Helm git worktree"
  require_clean_private_tree

  mkdir -p "$EXPORT_DIR"
  git archive --format=tar --output="$ARCHIVE" "$SOURCE_REF"
  tar -xf "$ARCHIVE" -C "$EXPORT_DIR"

  echo "Checking private/live runtime basemap contract..."
  scan_runtime_contract "$EXPORT_DIR"

  echo "Scanning sanitized export..."
  scan_tree "$EXPORT_DIR"

  if ! gh repo view "$PUBLIC_REPO" --json nameWithOwner >/dev/null 2>&1; then
    gh repo create "$PUBLIC_REPO" --public --description "Clean public mirror of Helm marine navigation alpha"
  fi

  mkdir -p "$PUBLIC_CLONE"
  git -C "$PUBLIC_CLONE" init -b main
  git -C "$PUBLIC_CLONE" remote add origin "$PUBLIC_REMOTE_URL"
  rsync -a --delete --exclude '.git/' "${EXPORT_DIR}/" "${PUBLIC_CLONE}/"

  echo "Checking public mirror runtime basemap contract..."
  scan_runtime_contract "$PUBLIC_CLONE"

  echo "Scanning public mirror working tree..."
  scan_tree "$PUBLIC_CLONE"

  (
    cd "$PUBLIC_CLONE"
    git add -A
    git -c user.name=StevenRidder -c user.email=steve@6elementlabs.com commit -m "$COMMIT_MESSAGE"
    local current_public_ref
    current_public_ref="$(git ls-remote "$PUBLIC_REMOTE_URL" refs/heads/main | awk '{print $1}')"
    if [ -n "$current_public_ref" ]; then
      git push --force-with-lease=refs/heads/main:"$current_public_ref" origin main
    else
      git push origin main
    fi
  )

  echo "Published ${PUBLIC_REPO} from ${SOURCE_REF}."
  echo "Review clone: ${PUBLIC_CLONE}"
}

main "$@"
