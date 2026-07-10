#!/bin/bash
# Helm — connect Claude Code cloud agents to the Switchboard (taikun-plan) MCP.
# Native tools come from .mcp.json (project MCP server); this makes the CLI
# fallback runnable and verifies board access at session start.
# See docs/CLOUD-AGENT-MCP.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Local sessions get the MCP natively via .mcp.json; the boot check is for
# remote cloud agents (code.claude.com on the web).
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

chmod +x scripts/switchboard.sh scripts/switchboard-mcp.py scripts/cloud-agent-install.sh 2>/dev/null || true

if [ -n "${SWITCHBOARD_TOKEN:-}${PM_MCP_TOKEN:-}" ]; then
  if scripts/switchboard.sh doctor >/tmp/switchboard-doctor.json 2>&1; then
    echo "[switchboard] board access OK (taikun-plan · project=helm). Native MCP via .mcp.json; CLI: scripts/switchboard.sh"
  else
    echo "[switchboard] token present but 'doctor' failed — check the token's project/scope. See docs/CLOUD-AGENT-MCP.md"
  fi
else
  echo "[switchboard] No SWITCHBOARD_TOKEN in this environment."
  echo "  Set it once: code.claude.com → your environment → Environment variables → SWITCHBOARD_TOKEN"
  echo "  (bearer from Switchboard create_scoped_token, project=helm, kind=agent). New sessions then get the"
  echo "  taikun-plan MCP automatically. See docs/CLOUD-AGENT-MCP.md"
fi
