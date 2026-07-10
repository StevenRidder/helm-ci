#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x scripts/switchboard.sh scripts/switchboard-mcp.py 2>/dev/null || true

if [[ -z "${SWITCHBOARD_TOKEN:-}" && -z "${PM_MCP_TOKEN:-}" ]]; then
  cat <<'EOF'
Switchboard: no SWITCHBOARD_TOKEN in this Cloud Agent environment.

One-time owner setup (Cursor web UI):
  1. Open https://cursor.com/dashboard/cloud-agents
  2. Secrets tab → Add secret
  3. Name: SWITCHBOARD_TOKEN
  4. Value: your Switchboard bearer token (project=helm, kind=agent)
  5. Restart the Cloud Agent

Agents then run:
  scripts/switchboard.sh doctor
  scripts/switchboard.sh boot --agent-id cursor/<TASK>-slug

See docs/CLOUD-AGENT-SWITCHBOARD.md
EOF
  exit 0
fi

scripts/switchboard.sh doctor
