# Helm — agent guide

Helm is a web-first marine chartplotter: OpenCPN's `model/` nav core run **headless** behind a clean
web/mobile client, fusing charts + satellite + weather + AIS + routing onto one offline-first screen.
The C++ engine is the safety core (on the boat); everything web-native orbits it as services.

---

## ⚠️ Build gotcha — read this BEFORE you build or run (do not rediscover it)

**`helm-server` is the real one-origin binary, but `engine/bootstrap.sh` does not build it.**

- `engine/vendor/cli/helm_server.cpp` is a complete **one-origin server**: nav WebSocket (`/nav`) +
  S-52 tiles (`/chart/{z}/{x}/{y}.png`) + `/health` + `/catalog` + the static UI, all on **one port
  (default 8080)**. Its `helm-server` target is defined in `engine/patches/0003`, and it's what
  `.claude/run-helm-server.sh` and the `helm-engine` entry in `.claude/launch.json` actually exec.
- **The trap:** `engine/bootstrap.sh` builds only `helm-chartrender chart-spike helm-tiles
  helm-engine` (see the `cmake --build … --target` line). It **omits `helm-server`**. So after a
  clean `bootstrap.sh`, `…/build/cli/helm-server` **does not exist**, and any one-origin launcher
  fails with "no such binary." This is **not** a sign the merge is unbuilt — the code is complete; the
  build target is just missing from the script.
- **Tracked as `ENGINE-12`** on the plan board. Until it lands, to get the one-origin binary:
  ```bash
  engine/bootstrap.sh                                            # clone @ pin → patch → build the rest
  cmake --build /tmp/helm-opencpn/build --target helm-server -j  # then build helm-server explicitly
  ```
  Or run the two separate binaries instead — `helm-engine` (nav WS :8081) + `helm-tiles` (tiles
  :8082) — per [docs/RUNBOOK.md](docs/RUNBOOK.md). Both are built by bootstrap.

Other build prerequisites (wxWidgets **3.2** pin, GNU `patch`/`gpatch`, Xcode CLT) are checked by
`bootstrap.sh`, which fails loud with the exact fix — don't guess those either; read its output.

---

## Tracking your work — the plan board (use the MCP)

The canonical roadmap is a live board at **plan.taikunai.com**, reached through the **`taikun-plan`
MCP**. It is **multi-project** — Helm shares the tool with an unrelated customer plan (Maxwell).

- **ALWAYS pass `project="helm"`** to the MCP tools (`get_task`, `search_tasks`, `board_summary`,
  `update_task`, `add_comment`). **Omitting `project` targets Maxwell — a different customer's board.
  Never write there.**
- Read your task: `get_task(task_id="OWNSHIP-5", project="helm")`. Mark progress:
  `update_task(task_id="OWNSHIP-5", status="In Progress", project="helm")`. Leave evidence with
  `add_comment(..., project="helm")`.
- Statuses are code-verified (a 2026-06-25 audit reconciled the board against the actual code), so
  trust them — but update them as you land work.

## Source of truth (in the repo)

- **[docs/EPICS.md](docs/EPICS.md)** — the 19 epics / ~191 tasks, ordered into waves, **each epic
  lists the files it OWNS**. That ownership is a collision boundary: edit only your epic's files so
  parallel agents don't fight over the same module. `web/index.html` (the shared shell) and
  `web/style.json` are the #1 collision hazard — the `SHELL` epic must extract them first.
- **[docs/FEATURE-TRACKER.md](docs/FEATURE-TRACKER.md)** — living per-feature status.
- **[docs/OPENCPN-REUSE.md](docs/OPENCPN-REUSE.md)** + **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**
  + the ADRs in `docs/decisions/` — why the architecture is the way it is.
- **[docs/RUNBOOK.md](docs/RUNBOOK.md)** — build & run the full stack on macOS.

> If the repo docs and the live board disagree on a status, the **live board (project=helm) is
> canonical** — it was reconciled against the code most recently.
