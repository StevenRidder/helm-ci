# Cloud-Agent MCP Access — every fleet, one board

How **any** Helm cloud agent — Cursor, Claude Code (web + local), Codex, CI — reaches the
**Switchboard** MCP server (`taikun-plan` at `https://plan.taikunai.com/mcp`, `project=helm`).
Generalizes the Cursor-only setup in [CLOUD-AGENT-SWITCHBOARD.md](CLOUD-AGENT-SWITCHBOARD.md).

> **Where these files live.** This kit belongs on **`main`** so every fleet's checkout has it.
> (It's committed on a feature branch as the delivery vehicle — merge to `main` in Wave C0.)

## Two ways to connect (a runtime uses whichever it supports)

| Mode | For | How |
|---|---|---|
| **A · Native MCP** | runtimes with an MCP client — **Claude Code** (web + local), IDEs | [`.mcp.json`](../.mcp.json) registers `taikun-plan` as an HTTP MCP server; tools appear as `mcp__taikun-plan__*` |
| **B · CLI shim** | runtimes with **no MCP picker** — **Cursor Cloud Agents** (Pro+), Codex, CI | [`scripts/switchboard.sh`](../scripts/switchboard.sh) — a stdlib-only HTTP/SSE client, same tool surface, no deps |

Both authenticate with the **same one secret** and hit the **same server**. Native is nicer
(real tools); the CLI is the universal fallback that works anywhere Python 3 runs.

## The one secret

`SWITCHBOARD_TOKEN` (alias `PM_MCP_TOKEN`) — a **scoped bearer** from Switchboard
(`create_scoped_token`, `project=helm`, `kind=agent`, scopes `write:tasks`,`write:ixp`).
**Never committed** — injected per runtime as an env var/secret. `.mcp.json` and the CLI both
read it from the environment (`Bearer ${SWITCHBOARD_TOKEN}`).

> **Env-var name matters for native MCP.** `.mcp.json` reads exactly `${SWITCHBOARD_TOKEN}`.
> The **CLI** shim also accepts `PM_MCP_TOKEN`. If your **scoped-runner plan** injects the token
> under a different fixed name, do one of: (a) name/alias the runner's secret `SWITCHBOARD_TOKEN`
> (simplest — native + CLI both work), or (b) change the single `${SWITCHBOARD_TOKEN}` reference in
> `.mcp.json` to your name. We deliberately do **not** auto-copy the secret between env-var names
> (that would write the bearer to a session file/transcript).

## Per-fleet setup — the only owner action is *inject the secret*

Everything else is in the repo already.

| Fleet | Inject the secret here | Auto-boot | Native MCP? |
|---|---|---|---|
| **Cursor Cloud Agents** | Dashboard → Cloud Agents → **Secrets** → `SWITCHBOARD_TOKEN` | `.cursor/environment.json` → `scripts/cloud-agent-install.sh` | no — uses the CLI shim |
| **Claude Code — web** | code.claude.com → your **environment** → Environment variables → `SWITCHBOARD_TOKEN` | `.claude/hooks/session-start.sh` (SessionStart) | **yes** — `.mcp.json` + `enableAllProjectMcpServers` |
| **Claude Code — local/IDE** | your shell env (`export SWITCHBOARD_TOKEN=…`) | — | **yes** — `.mcp.json` (approve the project server once) |
| **Codex cloud agents** | Codex env/secret config | run `scripts/switchboard.sh doctor` from the Codex setup / `AGENTS.md` | via CLI shim |
| **GitHub Actions / CI** | repo/org **Secret** `SWITCHBOARD_TOKEN` → job `env:` | a workflow step runs `scripts/switchboard.sh doctor` | via CLI shim |

*Restart the agent/session after adding the secret — running VMs don't pick up new secrets until restart.*

## Using it

**Native (Claude Code):** the tools are just there — `mcp__taikun-plan__get_task`, `…board_summary`, etc.

**CLI (any runtime):**
```bash
scripts/switchboard.sh doctor                                   # verify token + board access
scripts/switchboard.sh boot --runtime <fleet> --agent-id <fleet>/<TASK>   # session handshake
scripts/switchboard.sh call get_task '{"task_id":"INTEG-1","project":"helm"}'
scripts/switchboard.sh call add_comment '{"task_id":"INTEG-1","project":"helm","body":"…"}'
```
`--runtime` is any label (`cursor`,`claude`,`codex`,`ci`); it's recorded on the board, not gated.

## One-time token provisioning (per fleet)

From an already-authorized session: `create_scoped_token` (`project=helm`, `kind=agent`,
scopes `write:tasks`,`write:ixp`) → paste the value into that fleet's secret store above.
Rotate with `revoke_scoped_token` + a fresh one. Prefer the runtime's **redacted/runtime-secret**
type so the token isn't echoed in transcripts.

## What's in this kit

| File | Role |
|---|---|
| `.mcp.json` | native `taikun-plan` HTTP MCP server (Claude Code / IDEs) |
| `.claude/settings.json` | registers the SessionStart hook + `enableAllProjectMcpServers` (auto-approve for non-interactive agents) |
| `.claude/hooks/session-start.sh` | Claude Code web boot: chmod the CLI, verify board access, or print setup guidance if the token is missing |
| `scripts/switchboard-mcp.py` | the stdlib HTTP/SSE client (shared with the Cursor branch — byte-identical) |
| `scripts/switchboard.sh` | thin wrapper → the client |
| `scripts/cloud-agent-install.sh` | Cursor/CI install hook (chmod + token check + `doctor`) |
| `docs/CLOUD-AGENT-SWITCHBOARD.md` | the Cursor-specific appendix (dashboard screenshots-in-words) |

## Security

- Never commit the token. `.mcp.json`/CLI reference `${SWITCHBOARD_TOKEN}` from the env only.
- A missing token fails **gracefully** — the MCP server just shows unavailable and the hook prints
  setup guidance; it never breaks a session.
- Rotate on suspicion (`revoke_scoped_token`); one scoped token per fleet keeps blast radius small.
