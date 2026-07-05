#!/usr/bin/env bash
# Public CI sandbox helpers for Helm.
#
# Push feature branches to StevenRidder/helm-ci (full actual tree, all
# workflows) so GitHub Actions minutes stay on the public sandbox instead of a
# private Helm origin. This is intentionally not the sanitized helm-public
# export. After CI is green, open/merge the PR on Helm and delete the sandbox
# branch with: scripts/ci-sandbox.sh delete <branch>.
#
# Requires: git, gh (authenticated), jq, column, network.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CI_REPO="${CI_REPO:-StevenRidder/helm-ci}"
CI_REMOTE="${CI_REMOTE:-ci}"
CI_REMOTE_URL="${CI_REMOTE_URL:-https://github.com/${CI_REPO}.git}"
CANONICAL_REPO="${CANONICAL_REPO:-StevenRidder/Helm}"
WAIT_TIMEOUT_SEC="${WAIT_TIMEOUT_SEC:-7200}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-20}"
MAIN_REF="${MAIN_REF:-origin/main}"
SANDBOX_WORKFLOWS="${SANDBOX_WORKFLOWS:-backend-tests.yml engine-fresh-clone-smoke.yml helmcxx-runtime-guard.yml symbol-selection-smoke.yml web-e2e.yml web-tests.yml}"

die() {
  echo "ci-sandbox: $*" >&2
  exit 1
}

need_tools() {
  command -v git >/dev/null || die "git is required"
  command -v gh >/dev/null || die "GitHub CLI gh is required (https://cli.github.com/)"
  command -v jq >/dev/null || die "jq is required"
  command -v column >/dev/null || die "column is required"
}

repo_root() {
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run from the Helm git worktree"
}

remote_url() {
  git -C "$ROOT" remote get-url "$CI_REMOTE" 2>/dev/null || true
}

ensure_remote() {
  if [ -n "$(remote_url)" ]; then
    return 0
  fi
  echo "ci-sandbox: adding git remote '$CI_REMOTE' -> $CI_REMOTE_URL"
  git -C "$ROOT" remote add "$CI_REMOTE" "$CI_REMOTE_URL"
}

ensure_repo() {
  if gh repo view "$CI_REPO" --json nameWithOwner >/dev/null 2>&1; then
    return 0
  fi
  echo "ci-sandbox: creating public repo $CI_REPO"
  if gh repo create "$CI_REPO" \
    --public \
    --description "Public CI sandbox for Helm — full tree, all GitHub Actions workflows" 2>/tmp/ci-sandbox-create-repo.$$; then
    rm -f /tmp/ci-sandbox-create-repo.$$
    return 0
  fi
  cat /tmp/ci-sandbox-create-repo.$$ >&2
  rm -f /tmp/ci-sandbox-create-repo.$$
  cat >&2 <<EOF
ci-sandbox: could not create $CI_REPO automatically (token may lack repo-create scope).
Create it once as the repo owner, then re-run setup:

  gh repo create $CI_REPO --public \\
    --description "Public CI sandbox for Helm — full tree, all GitHub Actions workflows"

Then:

  scripts/ci-sandbox.sh setup
  scripts/ci-sandbox.sh sync-main
EOF
  die "missing CI sandbox repo $CI_REPO"
}

current_branch() {
  git -C "$ROOT" branch --show-current
}

resolve_branch() {
  local branch="${1:-}"
  if [ -z "$branch" ]; then
    branch="$(current_branch)"
  fi
  [ -n "$branch" ] || die "could not determine branch; pass one explicitly"
  if [ "$branch" = "HEAD" ]; then
    die "detached HEAD; checkout a branch first"
  fi
  printf '%s' "$branch"
}

usage() {
  cat <<EOF
Usage: scripts/ci-sandbox.sh <command> [options] [branch]

Commands:
  setup                 Create $CI_REPO (if missing) and add git remote '$CI_REMOTE'
  push [--no-wait]      Push <branch> (default: current), dispatch workflows, wait for dispatched Actions
  wait                  Wait for in-progress Actions on <branch> (default: current)
  status                Print recent Actions conclusions for <branch> (default: current)
  delete                Delete <branch> from the CI sandbox remote
  sync-main             Push local main to the CI sandbox (refresh baseline after merges)
  open-pr               Push/wait on sandbox, then open a Helm PR for <branch>

Environment:
  CI_REPO               Sandbox repo (default: $CI_REPO)
  CI_REMOTE             Git remote name (default: $CI_REMOTE)
  CI_REMOTE_URL         Sandbox clone URL (default: derived from CI_REPO)
  CANONICAL_REPO        Helm PR target (default: $CANONICAL_REPO)
  WAIT_TIMEOUT_SEC      Max wait for Actions (default: $WAIT_TIMEOUT_SEC)
  POLL_INTERVAL_SEC     Poll interval while waiting (default: $POLL_INTERVAL_SEC)
  MAIN_REF              Ref to seed sandbox main from (default: $MAIN_REF)
  SANDBOX_WORKFLOWS     Space-separated workflow files to dispatch after push
  SANDBOX_WAIT_EVENT    Optional event filter for manual wait/status, e.g. workflow_dispatch

Typical agent loop:
  scripts/ci-sandbox.sh setup
  git checkout -b claude/MY-TASK-slug
  # ... edit, commit ...
  scripts/ci-sandbox.sh push
  git push -u origin claude/MY-TASK-slug
  gh pr create --repo $CANONICAL_REPO ...
  # after merge on Helm:
  scripts/ci-sandbox.sh delete claude/MY-TASK-slug

See docs/CI-SANDBOX.md for Switchboard + private-origin notes.
EOF
}

cmd_setup() {
  need_tools
  repo_root
  ensure_repo
  ensure_remote
  echo "ci-sandbox: ready — remote '$CI_REMOTE' -> $(remote_url)"
  echo "ci-sandbox: next: scripts/ci-sandbox.sh sync-main   # once, to seed main"
}

cmd_push() {
  local wait=1
  local dispatch=1
  local branch=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-wait) wait=0; shift ;;
      --no-dispatch) dispatch=0; shift ;;
      -h|--help) usage; exit 0 ;;
      *) branch="$(resolve_branch "$1")"; shift ;;
    esac
  done
  branch="$(resolve_branch "$branch")"

  need_tools
  repo_root
  ensure_repo
  ensure_remote

  local sha
  sha="$(git -C "$ROOT" rev-parse "$branch")"
  echo "ci-sandbox: pushing $branch @ ${sha:0:12} -> $CI_REPO"
  git -C "$ROOT" push -u "$CI_REMOTE" "refs/heads/${branch}:refs/heads/${branch}"

  local dispatch_since=""
  if [ "$dispatch" = 1 ]; then
    dispatch_since="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    dispatch_workflows "$branch"
  fi

  if [ "$wait" = 1 ]; then
    if [ "$dispatch" = 1 ]; then
      wait_for_runs "$branch" "workflow_dispatch" "$dispatch_since" "$(workflow_count)"
    else
      wait_for_runs "$branch" "${SANDBOX_WAIT_EVENT:-}" "" 1
    fi
  else
    echo "ci-sandbox: pushed; check https://github.com/${CI_REPO}/actions?query=branch%3A${branch}"
  fi
}

workflow_count() {
  set -- $SANDBOX_WORKFLOWS
  printf '%s' "$#"
}

dispatch_workflows() {
  local branch="$1"
  local workflow
  echo "ci-sandbox: dispatching workflows on $CI_REPO@$branch"
  for workflow in $SANDBOX_WORKFLOWS; do
    echo "ci-sandbox: gh workflow run $workflow --ref $branch"
    gh workflow run "$workflow" --repo "$CI_REPO" --ref "$branch"
  done
}

list_runs_json() {
  local branch="$1"
  gh run list \
    --repo "$CI_REPO" \
    --branch "$branch" \
    --limit 30 \
    --json databaseId,name,status,conclusion,createdAt,event,headSha \
    2>/dev/null || printf '[]'
}

summarize_runs() {
  local branch="$1"
  local event_filter="${2:-}"
  local json
  json="$(list_runs_json "$branch")"
  if [ "$json" = "[]" ] || [ -z "$json" ]; then
    echo "ci-sandbox: no Actions runs yet for branch '$branch' on $CI_REPO"
    return 1
  fi
  printf '%s\n' "$json" | jq -r --arg event "$event_filter" '
    sort_by(.createdAt) | reverse | .[]
    | select(($event == "") or (.event == $event)) |
    [
      (.conclusion // .status),
      .name,
      (.headSha[0:12] // "?"),
      .event,
      .createdAt
    ] | @tsv' | column -t -s $'\t'
}

wait_for_runs() {
  local branch="$1"
  local event_filter="${2:-}"
  local since="${3:-}"
  local required_count="${4:-1}"
  local deadline=$(( $(date +%s) + WAIT_TIMEOUT_SEC ))
  local head_sha
  head_sha="$(git -C "$ROOT" rev-parse "$branch")"

  echo "ci-sandbox: waiting for Actions on $CI_REPO@$branch (${head_sha:0:12}), timeout ${WAIT_TIMEOUT_SEC}s"
  if [ -n "$event_filter" ]; then
    echo "ci-sandbox: gating $required_count $event_filter run(s)"
  fi

  while [ "$(date +%s)" -lt "$deadline" ]; do
    local json pending matching
    json="$(list_runs_json "$branch")"
    matching="$(printf '%s' "$json" | jq \
      --arg sha "$head_sha" \
      --arg event "$event_filter" \
      --arg since "$since" \
      '[.[] | select(.headSha == $sha)
        | select(($event == "") or (.event == $event))
        | select(($since == "") or (.createdAt >= $since))]')"
    pending="$(printf '%s' "$matching" | jq '[.[] | select(.status != "completed")] | length')"

    local matching_count
    matching_count="$(printf '%s' "$matching" | jq 'length')"
    if [ "$matching_count" -lt "$required_count" ]; then
      echo "ci-sandbox: found $matching_count/$required_count gated run(s) for ${head_sha:0:12}; sleeping ${POLL_INTERVAL_SEC}s"
      sleep "$POLL_INTERVAL_SEC"
      continue
    fi

    if [ "$pending" = "0" ]; then
      local failed
      failed="$(printf '%s' "$matching" | jq '[.[] | select(.conclusion != "success" and .conclusion != "skipped")] | length')"
      echo ""
      summarize_runs "$branch" || true
      if [ "$failed" != "0" ]; then
        die "CI sandbox failed ($failed run(s) not success/skipped) — see https://github.com/${CI_REPO}/actions?query=branch%3A${branch}"
      fi
      echo "ci-sandbox: all Actions green for ${head_sha:0:12} on $CI_REPO"
      return 0
    fi

    echo "ci-sandbox: $pending run(s) still in progress..."
    sleep "$POLL_INTERVAL_SEC"
  done

  summarize_runs "$branch" || true
  die "timed out waiting for CI sandbox runs on $branch"
}

cmd_wait() {
  local branch
  branch="$(resolve_branch "${1:-}")"
  need_tools
  repo_root
  ensure_remote
  wait_for_runs "$branch" "${SANDBOX_WAIT_EVENT:-}" "" 1
}

cmd_status() {
  local branch
  branch="$(resolve_branch "${1:-}")"
  need_tools
  repo_root
  summarize_runs "$branch" "${SANDBOX_WAIT_EVENT:-}" || exit 1
}

cmd_delete() {
  local branch
  branch="$(resolve_branch "${1:-}")"
  need_tools
  repo_root
  ensure_remote
  echo "ci-sandbox: deleting $CI_REPO:$branch"
  git -C "$ROOT" push "$CI_REMOTE" --delete "$branch"
  echo "ci-sandbox: deleted $branch from $CI_REPO"
}

cmd_sync_main() {
  need_tools
  repo_root
  ensure_repo
  ensure_remote
  local sha
  sha="$(git -C "$ROOT" rev-parse --verify "${MAIN_REF}^{commit}")"
  echo "ci-sandbox: syncing $MAIN_REF @ ${sha:0:12} -> $CI_REPO:main"
  git -C "$ROOT" push "$CI_REMOTE" "${sha}:refs/heads/main"
  echo "ci-sandbox: main synced — https://github.com/${CI_REPO}"
}

cmd_open_pr() {
  local branch
  branch="$(resolve_branch "${1:-}")"
  need_tools
  repo_root

  if ! git -C "$ROOT" show-ref --verify --quiet "refs/heads/${branch}"; then
    die "branch '$branch' not found locally"
  fi

  cmd_push "$branch"

  local origin_remote="${ORIGIN_REMOTE:-origin}"
  echo "ci-sandbox: pushing $branch to canonical repo ($CANONICAL_REPO)"
  git -C "$ROOT" push -u "$origin_remote" "$branch"

  if gh pr view --repo "$CANONICAL_REPO" --head "$branch" >/dev/null 2>&1; then
    gh pr view --repo "$CANONICAL_REPO" --head "$branch" --web
    die "PR already exists for $branch on $CANONICAL_REPO"
  fi

  gh pr create \
    --repo "$CANONICAL_REPO" \
    --head "$branch" \
    --title "$branch" \
    --body "$(cat <<EOF
## CI sandbox

Extensive GitHub Actions ran on [\`${CI_REPO}\`](https://github.com/${CI_REPO}/actions?query=branch%3A${branch}) before opening this PR on \`${CANONICAL_REPO}\`.

Sandbox branch can be deleted after merge:
\`\`\`bash
scripts/ci-sandbox.sh delete ${branch}
\`\`\`
EOF
)"
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    setup) cmd_setup "$@" ;;
    push) cmd_push "$@" ;;
    wait) cmd_wait "$@" ;;
    status) cmd_status "$@" ;;
    delete) cmd_delete "$@" ;;
    sync-main) cmd_sync_main "$@" ;;
    open-pr) cmd_open_pr "$@" ;;
    -h|--help|help|"") usage ;;
    *) die "unknown command '$cmd' (try: scripts/ci-sandbox.sh --help)" ;;
  esac
}

main "$@"
