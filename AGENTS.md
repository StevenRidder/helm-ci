# Helm Agent Guide

Helm is a web-first marine chartplotter: OpenCPN's `model/` navigation core runs
headless behind web/mobile clients. Several agents work here at once, so the
first rule is simple: coordinate through Switchboard, work in your own branch or
worktree, and never touch the live `:8080` boat screen.

This root file is the first-stop contract for Codex, Claude, Cursor, and any
other runtime that clones the repo. The longer portable guide is
[`docs/AGENT-BOOTSTRAP.md`](docs/AGENT-BOOTSTRAP.md).

## Required Start Sequence

Before touching files:

1. Read this file and [`docs/AGENT-BOOTSTRAP.md`](docs/AGENT-BOOTSTRAP.md).
2. Read [`docs/EPICS.md`](docs/EPICS.md) for the assigned epic or task.
3. Skim [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
   [`docs/OPENCPN-REUSE.md`](docs/OPENCPN-REUSE.md),
   [`docs/FEATURE-TRACKER.md`](docs/FEATURE-TRACKER.md), and
   [`docs/RUNBOOK.md`](docs/RUNBOOK.md).
4. Enlist with Switchboard using `project="helm"` on every tool call.
5. Work only on the returned task or explicit human assignment.

Use a stable agent id:

```text
<runtime>/<EPIC-or-TASK>-<short-slug>
```

Examples: `codex/CHART-8-palette`, `claude/OWNSHIP-5-cog-sog`,
`cursor/SHELL-2-style-fragments`.

## Switchboard Rules

Always pass `project="helm"` to Switchboard tools. Omitting it can target another
project board.

At session start:

```text
prepare_agent_session(..., project="helm")
get_working_agreement(project="helm")
register_agent(..., project="helm")
list_unacked_messages(project="helm", to_agent="<agent_id>")
list_unblock_requests(project="helm", owner_agent="<agent_id>")
```

Use `complete_claim` only after the branch is pushed and evidence exists. Agents
move work to In Review; Done is reserved for GitHub/default-branch provenance.

## CI Is Full-Tree `helm-ci`

The CI overflow path is mandatory for substantial changes before opening or
merging the canonical Helm PR:

```bash
scripts/ci-sandbox.sh doctor
scripts/ci-sandbox.sh open-pr <branch>
```

`helm-ci` is the public CI sandbox with the full actual Helm tree. It is not
`helm-public`, and it is not sanitized. Do not use `helm-public` for CI.

`open-pr` pushes the branch to public `helm-ci`, waits for the full dispatched
CI suite, pushes the exact same SHA back to canonical Helm, stamps the required
`helm-ci/full-suite` status on that SHA, and then opens the Helm PR. If you run
the steps manually, the required sequence is:

```bash
scripts/ci-sandbox.sh push <branch>
git push -u origin <branch>
scripts/ci-sandbox.sh prove <branch>
gh pr create --repo StevenRidder/Helm --fill
```

GitHub branch protection requires `helm-ci/full-suite` before `main` can move.
If public CI did not run and pass for the exact SHA, the private/canonical PR is
not mergeable.

After the Helm PR merges:

```bash
scripts/ci-sandbox.sh refresh-main
scripts/ci-sandbox.sh delete <branch>
```

Record the `helm-ci` Actions URL in the Switchboard task comment or
`complete_claim` evidence:

```text
https://github.com/StevenRidder/helm-ci/actions?query=branch%3A<branch>
```

If `scripts/ci-sandbox.sh doctor` fails, fix the reported setup issue before
claiming CI is green.

## Work Boundaries

Each epic in [`docs/EPICS.md`](docs/EPICS.md) lists owned files. Stay in those
files. Do not edit `web/index.html` or `web/style.json` unless the task owns that
change and the board says the prerequisite is landed.

Do not push directly to `main`. Use a branch matching the live agreement, usually:

```text
<runtime>/<TASK-ID>-<slug>
```

## Live Runtime Safety

`:8080` is the live boat screen. Do not start a server there and do not kill that
process. Use private ports `9001+` and private build/runtime snapshots. To update
the live screen, merge to `main` first, then deliberately refresh the live
snapshot with Steve's approval.
