# Platform-Neutral Agent Bootstrap

This is the shared onboarding contract for any agent working on Helm: Codex, Claude, Cursor,
human-operated scripts, or another runtime. Local runtime files such as `AGENTS.md`, `CLAUDE.md`, or
editor rules may add mechanics, but this document is the portable version to hand to a new agent.

Helm is a web-first marine chartplotter: OpenCPN's `model/` nav core runs headless behind a
web/mobile client. Multiple agents work in parallel, so coordination happens through Switchboard at
`plan.taikunai.com` and every agent must stay inside its assigned epic's file boundary.

## Agent identity

Use a stable id that names the runtime and the scope:

```text
<runtime>/<EPIC-or-TASK>-<short-slug>
```

Examples:

```text
codex/CHART-8-palette
claude/OWNSHIP-5-cog-sog
cursor/SHELL-2-style-fragments
```

## Start sequence

Before touching files:

1. Read the root `AGENTS.md`, then this file, in full.
2. Read `docs/EPICS.md` for your assigned epic or task. Record the outcome, owned files, wave,
   dependencies, and task list.
3. Skim `docs/ARCHITECTURE.md`, `docs/OPENCPN-REUSE.md`, `docs/FEATURE-TRACKER.md`, and
   `docs/RUNBOOK.md`.
4. Resolve the correct Switchboard project before registering. For Helm work the selected project
   should be `helm`; if the resolver points elsewhere, stop and follow the returned project-specific
   startup prompt instead.
5. Enlist with Switchboard through the `taikun-plan` MCP using the selected project on every call.

## Switchboard MCP enlistment

Never omit the `project` argument. If you omit it, older MCP tools target Maxwell, a different
customer's live board.

First, run the project preflight tool. It lists all boards, validates any project you were given,
infers the project from a task or lane when possible, and returns both `selected_project` and a
copy/paste `startup_prompt`.

For normal Helm work:

```text
prepare_agent_session(runtime="<codex|claude|cursor|other>",
                      agent_id="<runtime>/<scope>-<slug>",
                      project="helm",
                      task_id="<TASK-ID if assigned>",
                      lane="<EPIC if assigned>",
                      model="<model>")
```

If you only know a task or lane, let Switchboard resolve it:

```text
prepare_agent_session(runtime="<codex|claude|cursor|other>",
                      agent_id="<runtime>/<scope>-<slug>",
                      task_id="<TASK-ID>",
                      lane="<EPIC>",
                      model="<model>")
```

Follow the returned `selected_project` exactly. For Helm agents it should be `helm`. If the response
is `project_task_mismatch`, `project_lane_mismatch`, or `choice_required`, do not register or claim
work yet. Use the returned `next_step` or ask the human. Example: if `task_id="SEAM-1"` resolves to
`project="vulkan"`, you are on the Vulkan renderer board, not the Helm board.

After the project is selected, call these tools at session start:

```text
get_working_agreement(project="helm")
register_agent(agent_id="<runtime>/<scope>-<slug>",
               runtime="<codex|claude|cursor|other>",
               lane="<EPIC>",
               model="<model>",
               control_json="{...}",
               protocol_json="{...}",
               project="helm")
list_unacked_messages(project="helm", to_agent="<agent_id>")
list_unblock_requests(project="helm", owner_agent="<agent_id>")
list_active_agents(project="helm", lane="<EPIC>")
```

Use `control_json` to truthfully advertise your control fidelity. Examples:

```json
{"mode":"repo_edit","ports":"private_only","writes":"owned_files_only"}
{"mode":"advisory_poll","writes":"comments_only"}
{"mode":"supervised_apply","requires_human_for":"push,deploy,service_restart"}
```

Use the protocol envelope returned by `get_working_agreement` for `protocol_json`; at the time this
guide was written, Helm uses Switchboard `ixp.v1`.

## Finding work

If a human assigned a task:

```text
get_task(task_id="<TASK-ID>", project="helm")
get_agent_state(task_id="<TASK-ID>", project="helm")
```

If a human assigned only an epic:

```text
search_tasks(workstream="<EPIC>", project="helm")
ask_plan(question="What is the best unblocked task in <EPIC> for <agent_id>?", project="helm")
```

If the agent is allowed to self-claim:

```text
claim_next(agent_id="<agent_id>", lanes="<EPIC>", project="helm")
```

Work only the returned claim. If a dependency is not Done, pick another unblocked task or add a
comment explaining the block.

## Lane discipline

Each epic in `docs/EPICS.md` lists the files it owns. Edit only those files.

Do not edit `web/index.html` or `web/style.json` unless the live board says the `SHELL` prerequisite
has landed and your task explicitly owns that change. If your task needs another epic's files, leave
a task comment describing the need and stop at the boundary.

## Branches and completion

Work in a private branch/worktree. Obey the live branch convention returned by
`get_working_agreement(project="helm")`; the current neutral shape is:

```text
<runtime>/<TASK-ID>-<slug>
```

Never push directly to `main`. Push your branch before claiming progress.

For any substantial code change, run CI on the public full-tree sandbox before
opening or merging the Helm PR. This avoids burning private-origin minutes and
proves the actual code tree, not the sanitized public mirror:

```bash
scripts/ci-sandbox.sh doctor
scripts/ci-sandbox.sh push
git push -u origin <branch>
```

See [CI-SANDBOX.md](CI-SANDBOX.md). `complete_claim` must reference the **Helm**
PR URL and should include the `helm-ci` Actions URL. After the Helm PR merges,
refresh the sandbox baseline and delete the temporary sandbox branch:

```bash
scripts/ci-sandbox.sh refresh-main
scripts/ci-sandbox.sh delete <branch>
```

`helm-ci` is full-tree CI. It is not `helm-public`, and it is not sanitized.

During long work, keep presence fresh:

```text
heartbeat(agent_id="<agent_id>", project="helm")
```

When pushed and ready for review:

```text
complete_claim(claim_id="<claim_id>",
               evidence="{\"branch\":\"...\",\"head_sha\":\"...\",\"pr_url\":\"...\"}",
               project="helm")
```

This moves the task to In Review. Agents never set Done; the GitHub merge webhook records the merge
SHA and marks Done.

## Runtime and port safety

The live boat screen uses `:8080`. Do not start a test server there and do not kill that process.
Use private ports `9001+` and private build/runtime snapshots. Do not rebuild shared temporary
OpenCPN clones out from under other agents.

## Copy/paste starter prompt

```text
You are one of several agents building Helm, a web-first marine chartplotter using OpenCPN's
headless model/nav core behind web/mobile clients. You are assigned:

    EPIC: <EPIC>
    TASK: <TASK-ID or "claim next unblocked task in this epic">

Start by reading AGENTS.md and docs/AGENT-BOOTSTRAP.md, then docs/EPICS.md for <EPIC>, then the
architecture/runbook docs named there. Enlist with Switchboard via the taikun-plan MCP using
project="helm": call get_working_agreement, register_agent with agent_id="<runtime>/<scope>-<slug>",
drain list_unacked_messages and list_unblock_requests, then read or claim your task. Before that
normal handshake, call prepare_agent_session with your runtime, agent id, assigned task/lane, and
project="helm"; follow its selected_project exactly. If it says the task belongs to another project
such as project="vulkan", stop Helm work and re-enlist using the returned startup_prompt.

Edit only files owned by <EPIC> in docs/EPICS.md. Do not edit web/index.html or web/style.json
unless the live board says the SHELL prerequisite has landed and your task owns that change. Use a
private branch/worktree, private test ports, and never touch the live :8080 Helm screen.

Before work, check dependencies and active agents. During work, add task comments for decisions,
blockers, and cross-epic needs. Before opening or merging the Helm PR, run
scripts/ci-sandbox.sh doctor and scripts/ci-sandbox.sh push so the full actual tree passes in
StevenRidder/helm-ci. When pushed and ready for review, call complete_claim with branch, head_sha,
the Helm PR URL, and the helm-ci Actions URL; never set Done yourself. After merge, run
scripts/ci-sandbox.sh refresh-main and scripts/ci-sandbox.sh delete <branch>.
```
