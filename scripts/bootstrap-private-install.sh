#!/usr/bin/env bash
# Clone/update the private Helm repo into a durable install directory, then run
# the parity updater. This is for a Mac that has the GitHub deploy/user key.
set -euo pipefail

INSTALL_DIR="${HELM_INSTALL_DIR:-$HOME/Dropbox/Git/Helm}"
REMOTE="${HELM_GIT_REMOTE_URL:-git@github.com:StevenRidder/Helm.git}"
SSH_KEY="${HELM_GIT_SSH_KEY:-$HOME/.ssh/id_ed25519_github_helm}"
BRANCH="${HELM_GIT_BRANCH:-main}"

usage() {
  cat <<EOF
Usage: scripts/bootstrap-private-install.sh [options] [-- updater-options]

Options:
  --install-dir DIR    Durable checkout directory (default: $INSTALL_DIR)
  --remote URL         Git remote (default: $REMOTE)
  --ssh-key PATH       SSH key for GitHub (default: $SSH_KEY)
  --branch NAME        Branch to install (default: $BRANCH)
  -h, --help           Show this help

Everything after -- is passed to scripts/update-remote-parity.sh.
The updater is run with --replace-running so the old :8080/:8095 listeners are
stopped before the verified stack starts.
EOF
}

UPDATER_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --install-dir) shift; INSTALL_DIR="$1" ;;
    --remote) shift; REMOTE="$1" ;;
    --ssh-key) shift; SSH_KEY="$1" ;;
    --branch) shift; BRANCH="$1" ;;
    --) shift; UPDATER_ARGS=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) echo "bootstrap-private-install: unknown arg '$1'" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

git_with_auth() {
  if [ -f "$SSH_KEY" ]; then
    env GIT_SSH_COMMAND="ssh -i $SSH_KEY -o IdentitiesOnly=yes" git "$@"
  else
    git "$@"
  fi
}

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "bootstrap-private-install: updating $INSTALL_DIR from $REMOTE $BRANCH"
  git_with_auth -C "$INSTALL_DIR" fetch "$REMOTE" "$BRANCH"
  git_with_auth -C "$INSTALL_DIR" checkout "$BRANCH"
  git_with_auth -C "$INSTALL_DIR" merge --ff-only FETCH_HEAD
else
  if [ -e "$INSTALL_DIR" ]; then
    echo "bootstrap-private-install: $INSTALL_DIR exists but is not a git checkout" >&2
    exit 20
  fi
  echo "bootstrap-private-install: cloning $REMOTE $BRANCH into $INSTALL_DIR"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git_with_auth clone --branch "$BRANCH" "$REMOTE" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
exec env HELM_GIT_REMOTE_URL="$REMOTE" HELM_GIT_SSH_KEY="$SSH_KEY" \
  scripts/update-remote-parity.sh --replace-running "${UPDATER_ARGS[@]}"
