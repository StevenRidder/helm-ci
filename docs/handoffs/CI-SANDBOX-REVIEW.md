# CI-SANDBOX-REVIEW — Switchboard handoff

**Status:** Ready for review  
**Author agent:** `cursor/ci-sandbox-setup-891e` (Cloud Agent)  
**PR:** https://github.com/StevenRidder/Helm/pull/354  
**Branch:** `cursor/ci-sandbox-setup-891e`  
**Suggested Switchboard task ID:** `CI-1` (create if missing)  
**Workstream:** `INFRA` or `CLIENT` (CI / agent tooling)

---

## Review request (for the reviewing agent)

Please review the **public CI sandbox** work: scripts, docs, and the intended
`StevenRidder/helm-ci` bootstrap flow. Confirm the design matches the owner's
goal (heavy CI on a public repo, merge on canonical Helm, delete sandbox
branches after merge) and that nothing conflicts with `helm-public` mirror
tooling.

### Review checklist

- [ ] `scripts/ci-sandbox.sh` — setup/push/wait/status/delete/sync-main/open-pr behave correctly
- [ ] Docs clearly distinguish **`helm-ci`** (full-tree CI) vs **`helm-public`** (sanitized mirror)
- [ ] Switchboard agent loop in `docs/AGENT-BOOTSTRAP.md` and `docs/CI-SANDBOX.md` is accurate
- [ ] Owner bootstrap steps are correct (`gh repo create` + `sync-main`)
- [ ] No secrets, private paths, or chart blobs committed
- [ ] Recommend whether post-merge auto-sync of `main` → `helm-ci` is worth adding

### Files changed

| File | Purpose |
|------|---------|
| `scripts/ci-sandbox.sh` | CLI for sandbox push/wait/delete/sync |
| `docs/CI-SANDBOX.md` | Full sandbox guide |
| `docs/DEVELOPMENT.md` | CI sandbox section + mirror clarification |
| `docs/REPO-MAP.md` | Repo map entries |
| `docs/AGENT-BOOTSTRAP.md` | Agent push-to-sandbox-before-PR guidance |

### Blocked follow-up (owner-only)

Cloud agent token could **not** create `StevenRidder/helm-ci` (`Resource not
accessible by integration`). After merge, repo owner must run:

```bash
gh repo create StevenRidder/helm-ci --public \
  --description "Public CI sandbox for Helm — full tree, all GitHub Actions workflows"
git checkout main && git pull origin main
scripts/ci-sandbox.sh setup
scripts/ci-sandbox.sh sync-main
```

---

## Full conversation transcript

### Turn 1 — User question (mirror + CI architecture)

**User:** Check codebase and GitHub repo for how code is pushed from the private
repo to the public mirror `helm-public`. Is that GitHub Actions? Can we push to
public for CI, pull back to private, and use public only for CI testing?

**Findings delivered:**

1. **Mirror is NOT GitHub Actions.** One-way manual script:
   `scripts/publish-public-mirror.sh` — `git archive` + sanitization scans +
   force-push snapshot to `StevenRidder/helm-public`.

2. **Both repos were public** at investigation time (`Helm`, `helm-public`).

3. **CI today runs on `StevenRidder/Helm`** via six workflows; `helm-public`
   only runs three (subset).

4. **`helm-public` is stale** (Jul 1 vs Helm main Jul 5) and has rewritten
   history (~3 snapshot commits).

5. **Reverse pull from mirror is not viable** — different trees, missing
   export-ignored files, no shared branch history.

6. **Recommended pattern:** dedicated public **CI sandbox** with full tree, not
   `helm-public`.

---

### Turn 2 — User question (Switchboard + minute-saving workflow)

**User:** Check Switchboard MCP for how CI works today (private repo Actions,
~hour max). Wants to: push to public repo for extensive CI → merge to private →
delete public code after merge.

**Findings delivered:**

1. **Switchboard does not run CI** — it coordinates agents via `taikun-plan`
   MCP; GitHub Actions fire on push/PR to whichever repo receives the push.

2. **Expensive job:** `engine-fresh-clone-smoke` on **macOS 14**, timeout 120
   min; ~6 min wall clock ≈ **~60 billed minutes** (10× macOS multiplier).

3. **`helm-public` wrong for this** — sanitized, incomplete, 3 workflows only.

4. **Proposed flow:**
   - Create `StevenRidder/helm-ci` (public, full tree)
   - `scripts/ci-sandbox.sh push` → wait for green
   - Push same branch to Helm → PR → Switchboard `complete_claim`
   - `scripts/ci-sandbox.sh delete <branch>` after merge

---

### Turn 3 — User: set it all up

**Implementation:**

- Added `scripts/ci-sandbox.sh` (setup, push, wait, status, delete, sync-main, open-pr)
- Added `docs/CI-SANDBOX.md`
- Updated `docs/DEVELOPMENT.md`, `docs/REPO-MAP.md`, `docs/AGENT-BOOTSTRAP.md`
- Opened draft PR #354 on `StevenRidder/Helm`
- **Blocked:** cloud token cannot create `StevenRidder/helm-ci`; documented owner bootstrap

**Typical loop after owner bootstrap:**

```bash
scripts/ci-sandbox.sh push
git push -u origin <branch>
gh pr create --repo StevenRidder/Helm --fill
# after merge:
scripts/ci-sandbox.sh delete <branch>
```

---

### Turn 4 — User: post to Switchboard for another agent to review + post whole conversation

**This document** satisfies the conversation archive and review handoff.

---

## Switchboard paste blocks (for owner or MCP-enabled agent)

If `taikun-plan` MCP is connected with `project="helm"`, create or update a
review task and attach this handoff.

### Option A — create task (REST API)

```bash
curl -sS -X POST "https://plan.taikunai.com/api/tasks?project=helm" \
  -H "Authorization: Bearer $PM_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "CI-1",
    "title": "Review helm-ci public CI sandbox (PR #354)",
    "workstream": "INFRA",
    "status": "In Review",
    "description": "Review scripts/ci-sandbox.sh, docs/CI-SANDBOX.md, and agent bootstrap updates. Verify helm-ci vs helm-public distinction. Owner must still create StevenRidder/helm-ci and run sync-main.",
    "evidence": {
      "pr_url": "https://github.com/StevenRidder/Helm/pull/354",
      "branch": "cursor/ci-sandbox-setup-891e",
      "handoff": "docs/handoffs/CI-SANDBOX-REVIEW.md"
    }
  }'
```

### Option B — comment on existing task

```text
add_comment(
  task_id="CI-1",
  project="helm",
  body="Review handoff: docs/handoffs/CI-SANDBOX-REVIEW.md — PR https://github.com/StevenRidder/Helm/pull/354 adds public helm-ci sandbox (scripts/ci-sandbox.sh). Cloud agent could not create helm-ci repo; owner bootstrap required. Full conversation transcript is in the handoff doc."
)
```

### Option C — claim for reviewer

```text
search_tasks(workstream="INFRA", project="helm")
# or claim_next(agent_id="<reviewer>/<CI-1>-review", lanes="INFRA", project="helm")
get_task(task_id="CI-1", project="helm")
```

---

## Architecture summary (quick reference)

```text
  Agent branch
       │
       ├─▶ helm-ci (public)     ──▶ all 6 GitHub Actions (free minutes)
       │
       └─▶ Helm (canonical)     ──▶ PR + Switchboard merge webhook → Done
              │
              after merge
              └─▶ delete branch on helm-ci

  helm-public (separate)  ──▶ sanitized mirror via publish-public-mirror.sh
                              NOT used for CI sandbox
```
