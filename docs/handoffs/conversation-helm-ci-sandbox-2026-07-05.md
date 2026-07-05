# Helm CI Sandbox — Conversation Export

**Date:** 2026-07-05  
**Topic:** Public mirror (`helm-public`), CI sandbox (`helm-ci`), Switchboard, GitHub Actions  
**PR:** https://github.com/StevenRidder/Helm/pull/354  
**Branch:** `cursor/ci-sandbox-setup-891e`

---

## Turn 1

### User

> Check my codebase and the GitHub repo and check out how we actually push code from our private repo, which is now public, to the public mirror, Helm public. Is that using GitHub Actions? And if so, is there a way to push code to a public repo and then pull it back to a private repo and only use a public repo for CI testing, like we're doing now in the Helm repo? Thanks for watching!

### Assistant

**How the public mirror works today**

**It is not GitHub Actions.** Publishing to `StevenRidder/helm-public` is a **manual, local bash script**: `scripts/publish-public-mirror.sh`.

The flow is:

1. Run from a **clean** checkout of the canonical repo (`StevenRidder/Helm`).
2. **`git archive`** exports a tree that respects `.gitattributes` `export-ignore` (strips business docs, publish scripts, chart data, etc.).
3. **Sanitization scans** block private paths, internal doc references, and secret patterns.
4. **Runtime guards** verify the export still has the live basemap/chart UI contract.
5. Build a **fresh commit** in a temp clone and **`git push --force-with-lease`** to `helm-public/main`.

So it's a **one-way sanitized snapshot**, not a normal git mirror with shared history. `helm-public` had only **3 commits**, all publish snapshots — not the full commit graph from `Helm`.

---

**What runs CI where**

| Repo | Workflows |
|------|-----------|
| **`StevenRidder/Helm`** (canonical) | `backend-tests`, `helmcxx-runtime-guard`, `symbol-selection-smoke`, `engine-fresh-clone-smoke`, `web-tests`, `web-e2e` |
| **`StevenRidder/helm-public`** (mirror) | `engine-fresh-clone-smoke`, `web-tests`, `web-e2e` only |

Public repos receive **unlimited free** GitHub-hosted Actions minutes.

Both repos were **public** at investigation time. The mirror was also **stale**: `Helm/main` was ahead of `helm-public/main` (last publish ~4 days older).

There is **no workflow** in either repo that auto-runs `publish-public-mirror.sh`.

---

**Can you push to public, pull back to private, and use public only for CI?**

**Partially — but not with the tooling you have today, and not with a simple `git pull`.**

**What you already have:**

- **Private → public:** `scripts/publish-public-mirror.sh` (manual).
- **Private ← canonical repo:** `scripts/bootstrap-private-install.sh` and `scripts/update-remote-parity.sh` pull from **`StevenRidder/Helm`**, not `helm-public`.
- There is **no script or Action** to pull from `helm-public` back into `Helm`.

**Why reverse sync is awkward with the current mirror:**

1. **Different histories** — each publish is essentially a new snapshot commit + force push.
2. **Different trees** — `Helm` had ~15k tracked objects; `helm-public` ~1.4k.
3. **You can't "pull the mirror back" wholesale** without reintroducing stripped private material or losing private-only files.

**Patterns that would work:**

| Goal | Approach |
|------|----------|
| **Use public repo only for CI** | Already partly true on `helm-public`; subset of workflows only |
| **Automate private → public** | Add a GitHub Action on `Helm` that runs the publish script |
| **Accept contributions on public, land in private** | Cherry-pick or manually port into `Helm` |
| **Single repo now that `Helm` is public** | Consolidate CI on `Helm`; keep `helm-public` only for scrubbed external view |
| **True bidirectional sync** | Different architecture (filter-repo, subtree split), not current snapshot publisher |

**Practical recommendation:** Use a **new full-copy public CI repo**, not `helm-public`. Flow: push branch to public CI → green → push same branch to Helm → PR → merge → delete public branch.

---

## Turn 2

### User

> Ok set all that up please

### Assistant

**What was added**

**`scripts/ci-sandbox.sh`** — commands:

| Command | What it does |
|---------|----------------|
| `setup` | Create `helm-ci` (if you have permission) + add `ci` remote |
| `push` | Push branch to sandbox and wait for Actions (default 2h timeout) |
| `push --no-wait` | Push only |
| `wait` / `status` | Poll or print run results |
| `delete` | Remove branch from sandbox after Helm merge |
| `sync-main` | Refresh sandbox `main` from local `main` |
| `open-pr` | Wait for green CI → push to Helm → open PR |

**Docs:** `docs/CI-SANDBOX.md`, plus updates to `DEVELOPMENT.md`, `REPO-MAP.md`, and `AGENT-BOOTSTRAP.md`.

**PR:** https://github.com/StevenRidder/Helm/pull/354 (draft)

---

**One-time bootstrap (after merging PR #354)**

Cloud agent hit `Resource not accessible by integration` creating `StevenRidder/helm-ci`. Run locally as repo owner:

```bash
gh repo create StevenRidder/helm-ci --public \
  --description "Public CI sandbox for Helm — full tree, all GitHub Actions workflows"

git checkout main && git pull origin main
scripts/ci-sandbox.sh setup
scripts/ci-sandbox.sh sync-main
```

---

**Day-to-day loop**

```bash
git checkout -b claude/MY-TASK-slug
# ... edit, commit ...

scripts/ci-sandbox.sh push          # → helm-ci, wait for green (free public minutes)
git push -u origin claude/MY-TASK-slug
gh pr create --repo StevenRidder/Helm --fill

# Switchboard: complete_claim with the Helm PR URL

# After merge:
scripts/ci-sandbox.sh delete claude/MY-TASK-slug
```

Or: `scripts/ci-sandbox.sh open-pr claude/MY-TASK-slug`

---

**Important distinctions**

- **`helm-ci`** = full-tree CI sandbox (this setup)
- **`helm-public`** = sanitized external mirror (`publish-public-mirror.sh`) — not for CI
- **Switchboard** still closes tasks on **Helm PR merges**, not sandbox pushes

---

## Turn 3 (continued from Turn 2 — Switchboard deep dive)

### User

> So, check out our MCP tool called Switchboard and see how we do CI testing today. The way I understand it, it uses the private repo's actions, maximum actions at about an hour. So, what I want to do is start pushing my code to another public repo for fun, do the CI testing there, then push it and merge it to the private and then delete the code in the public. That way I can do extensive CI testing still without wasting minutes and then pull it back down after it's tested, delete the code because it's merged back into the private main branch.

### Assistant

**What Switchboard does vs. what runs CI**

**Switchboard is not the CI runner.** It is Taikun's agent coordination board (`plan.taikunai.com`), used via the `taikun-plan` MCP. Agents:

1. Claim tasks on the board
2. Work on a branch (convention: `<runtime>/<TASK-ID>-slug`)
3. Push and call `complete_claim` with branch/SHA/PR evidence
4. Wait for a human merge — **Switchboard marks Done via a GitHub merge webhook** (`github_pr_merged`)

Switchboard does **not** trigger or orchestrate GitHub Actions. CI fires automatically when code is pushed or a PR is opened on whichever GitHub repo receives that push.

Chain today:

```text
Agent pushes branch → StevenRidder/Helm → GitHub Actions runs → PR merged → Switchboard webhook marks Done
```

---

**How CI actually runs today**

All workflows live on **`StevenRidder/Helm`**:

| Workflow | Runner | Timeout | Cost note |
|----------|--------|---------|-----------|
| `engine-fresh-clone-smoke` | **macOS 14** | **120 min** | ~6 min wall clock ≈ **~60 billed minutes** (macOS 10× multiplier) |
| `symbol-selection-smoke` | ubuntu | 15 min | 1× |
| `helmcxx-runtime-guard` | ubuntu | default | 1× |
| `backend-tests` | ubuntu | default | 1× |
| `web-tests` / `web-e2e` | ubuntu | default | 1× |

The macOS job is the expensive one — especially if Helm is **private** again.

---

**Why `helm-public` is the wrong target**

- Sanitized snapshot model
- Only 3 of 6 workflows
- Missing files from `export-ignore`
- Rewritten history on each publish

**Recommended:** dedicated public **`StevenRidder/helm-ci`** with full tree.

```text
  Agent branch
       │
       ├─▶ helm-ci (public)     ──▶ all 6 GitHub Actions (free minutes)
       │
       └─▶ Helm (canonical)     ──▶ PR + Switchboard merge webhook → Done
              │
              after merge
              └─▶ delete branch on helm-ci
```

---

## Turn 4

### User

> Update what you did as a task on switchboard so I can have another agent review it. Post the whole conversation too please

### Assistant

Could **not** post directly to Switchboard from the cloud agent — no `taikun-plan` MCP or `PM_MCP_TOKEN` in that environment; GitHub token also couldn't add PR comments.

**Prepared in-repo instead:**

- **Handoff doc:** `docs/handoffs/CI-SANDBOX-REVIEW.md`
- **PR updated:** https://github.com/StevenRidder/Helm/pull/354
- **Suggested Switchboard task:** `CI-1` — Review helm-ci public CI sandbox (PR #354)

**Switchboard paste blocks** (for MCP-enabled agent or owner with `PM_MCP_TOKEN`):

```bash
curl -sS -X POST "https://plan.taikunai.com/api/tasks?project=helm" \
  -H "Authorization: Bearer $PM_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "CI-1",
    "title": "Review helm-ci public CI sandbox (PR #354)",
    "workstream": "INFRA",
    "status": "In Review",
    "description": "Review scripts/ci-sandbox.sh, docs/CI-SANDBOX.md, and agent bootstrap updates.",
    "evidence": {
      "pr_url": "https://github.com/StevenRidder/Helm/pull/354",
      "branch": "cursor/ci-sandbox-setup-891e",
      "handoff": "docs/handoffs/CI-SANDBOX-REVIEW.md"
    }
  }'
```

```text
add_comment(
  task_id="CI-1",
  project="helm",
  body="Review handoff: docs/handoffs/CI-SANDBOX-REVIEW.md — PR #354 adds helm-ci sandbox. Full conversation in docs/handoffs/conversation-helm-ci-sandbox-2026-07-05.md"
)
```

---

## Turn 5

### User

> Export this conversation as a .md so I can copy it

### Assistant

This file.

---

## Files created / changed in this work

| File | Purpose |
|------|---------|
| `scripts/ci-sandbox.sh` | CLI: setup, push, wait, status, delete, sync-main, open-pr |
| `docs/CI-SANDBOX.md` | Full sandbox guide |
| `docs/handoffs/CI-SANDBOX-REVIEW.md` | Switchboard review handoff + checklist |
| `docs/handoffs/conversation-helm-ci-sandbox-2026-07-05.md` | This conversation export |
| `docs/DEVELOPMENT.md` | CI sandbox section |
| `docs/REPO-MAP.md` | Repo map entries |
| `docs/AGENT-BOOTSTRAP.md` | Agent push-to-sandbox guidance |

---

## Key references in the codebase

- `scripts/publish-public-mirror.sh` — sanitized one-way push to `helm-public`
- `scripts/bootstrap-private-install.sh` — pull canonical Helm to install dir
- `scripts/update-remote-parity.sh` — pull/build/verify on remote Mac
- `.github/workflows/` — six workflows on Helm; three on `helm-public`
- `docs/AGENT-BOOTSTRAP.md` — Switchboard agent protocol
- `docs/EPICS.md` — Switchboard MCP tools: `board_summary`, `get_task`, `search_tasks`, `update_task`, `add_comment`, `ask_plan` with `project="helm"`

---

## Architecture (final)

```text
                    ┌─────────────────────────┐
  Agent work ──────▶│  helm-ci (public)       │
  (feature branch)  │  full code, all workflows│
                    └───────────┬─────────────┘
                                │ Actions (free minutes)
                                ▼
                         CI green?
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
   push same branch/commits          delete branch from helm-ci
   open PR on Helm (canonical)
              │
              ▼
   merge → Switchboard webhook marks Done

  helm-public (separate) ──▶ sanitized mirror via publish-public-mirror.sh
                             NOT used for CI sandbox
```

---

## Owner actions still pending

1. Merge PR #354
2. Create `StevenRidder/helm-ci` and run `scripts/ci-sandbox.sh setup && scripts/ci-sandbox.sh sync-main`
3. Post `CI-1` review task to Switchboard (paste blocks above) if not already done
4. Have reviewing agent read this file + `docs/handoffs/CI-SANDBOX-REVIEW.md` and review PR #354
