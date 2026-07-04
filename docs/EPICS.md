# Helm — Epic Plan (the board)

> **The single source of truth for _what to build, in what order, by which parallel stream._** Generated 2026-06-25 from a full read of every project `.md`, then **reconciled against the actual code by a multi-agent audit (2026-06-25)** — 13 task statuses corrected and 5 wiring tasks added (`ENGINE-12`, `CHART-14`, `ALARM-10`, `AI-16`, `AI-17`). Mirrored live on **plan.taikunai.com** (`project=helm` via the `taikun-plan` MCP). If this doc and the live board disagree, the **board is canonical**. Companion to [FEATURE-TRACKER.md](FEATURE-TRACKER.md) and the ADRs in [decisions/](decisions/).

## The one rule

**Each epic owns its own files.** That `owns` list is a _collision boundary_: an agent working an epic edits only those files, so two streams never fight over the same module. The two shared files every UI epic used to collide on — `web/index.html` (the shell) and `web/style.json` — are de-fanged by the **SHELL** epic, which must land first and gives every other epic a registration hook + its own style fragment. Lock **SHELL** and **CONTRACT**, and the wave-2 streams fan out almost collision-free.

## Board at a glance

- **23 epics** · **234 tasks** — 🟢 63 done · 🟡 23 in-progress · 🔴 0 blocked · ⚪ 148 to-do  _(+`CLIENT`: 18 web-client-hardening tasks from the 2026-06-26 front-end / MapLibre best-practices audit; +`LABS`: 7 experimental pro-maritime features from the 2026-06-26 cruise/military/commercial-charting survey — see [LABS.md](LABS.md); +`WATCHMATE`: 9 voyage-memory/watchkeeping tasks — see [WATCHMATE.md](WATCHMATE.md))_

| Wave | Theme | Epics | Tasks done |
|---|---|---|---|
| **1** | Foundations & unblockers | BACKEND, CHART, CONTRACT, ENGINE, SHELL | 25/51 |
| **2** | Reference-client capabilities | AIS, ALARM, CONN, OFFLINE, OWNSHIP, ROUTE, TOOLS, WX | 29/78 |
| **3** | Higher-order capabilities | AI, BOARD, PILOT, PLACES, ROUTING, TIDES, WATCHMATE | 9/65 |
| **4** | Native + commercial (last) | NATIVE | 0/15 |
| **✚** | Cross-cutting · web-client hardening | CLIENT | 0/18 |
| **🧪** | Experimental · pro-maritime survey (Labs) | LABS | 0/7 |

## How to run it (parallel streams)

- **Status legend:** 🟢 done & wired · 🟡 in progress / one side built · 🔴 blocked · ⚪ to-do. ⛔ = **blocking** (gates other work). `↳` = task dependencies (may cross epics).

- **`parallelSafe`** epics live entirely in their own files and can run concurrently. `parallelSafe=False` epics register through SHELL, so they serialize on shell edits — run them one at a time within a wave, or after SHELL ships its API.

- **Waves are dependency order, not a calendar.** Wave 1 = unblocked now; higher waves wait on deps.

## ▶ Start here

1. **SHELL first, solo** (`SHELL-1/2/3`) — unblocks ~10 wave-2 UI epics. 2. **In parallel (own files, no shell): CONTRACT + ENGINE hardening** (incl. `ENGINE-12` — add `helm-server` to the build so the one-origin binary actually ships). 3. **After SHELL lands, fan out wave 2** — highest value: `ROUTE-3`, `OWNSHIP-5/6`, `TOOLS-7` (persistence, gates BOAT-1 → ROUTING), then `AIS`, `CONN`, `WX`.


---

# Wave 1 — Foundations & unblockers

_Foundations that are largely DONE plus the two load-bearing un-blockers. ENGINE (nav core), CHART (S-52 tile engine), CONTRACT (streaming + now folded-in secure transport), and BACKEND (FastAPI companion) own engine/ C++ and contract files with near-zero web/index.html overlap, so they run concurrently. CRITICAL: SHELL is in wave 1 and BLOCKING — it extracts the index.html panel-registration API and splits style.json into per-domain fragments. Wave-2 epics depend on SHELL-1/SHELL-2 before they fan out, which is what serializes the 12-epic shell collision. Note wave 1 is NOT fully done: ENGINE-9 (merge), ENGINE-10 (UpdateProgress relocation, in-progress — math already shipped), CONTRACT-5b/6/7/9/10/12-16, and all of SHELL are open and gate downstream work._


## 🟢 `BACKEND` — Companion service core — FastAPI, health, secrets, smoke

**Wave 1 · done · 5/5 done · ⛓ serializes on SHELL**

> The offline-first FastAPI companion that orbits the engine (places/AI/community/give-back), auto-detected by the web app with graceful fallback, honest-stub without keys, env-only secrets, health/mode report, and a no-network smoke test.

- **Owns (collision boundary):** `backend/main.py`, `backend/test_smoke.py`, `backend/README.md`
- **Done =** FastAPI service (main.py routing store/agents/context/llm/publisher) running offline-first; honest-stub + graceful-degradation when no keys; web auto-detects at 127.0.0.1:8090 and falls back to sample data; env-only secrets (.env gitignored); GET /health mode report; 22-check no-network/no-keys smoke test green. main.py uses APIRouter-per-domain includes so PLACES/AI each own their router module and append one include line only.

- [x] 🟢 **BACKEND-1** — FastAPI companion service skeleton + APIRouter-per-domain includes (routes → store/agents/context/llm/publisher) ⛔
- [x] 🟢 **BACKEND-2** — Honest-stub / graceful-degradation modes + web auto-detect fallback  ↳ BACKEND-1
- [x] 🟢 **BACKEND-3** — Env-only secrets handling (.env never committed)  ↳ BACKEND-1
- [x] 🟢 **BACKEND-4** — GET /health mode report (LLM provider, NFL/OSM live-vs-mock)  ↳ BACKEND-1
- [x] 🟢 **BACKEND-5** — Standalone 22-check no-network/no-keys smoke test  ↳ BACKEND-1

## 🟡 `CHART` — S-52 ENC tile engine + quilting + hardening

**Wave 1 · mixed · 7/14 done · ⚡ parallel-safe**

> True S-52 vector ENC rendered headless to PNG tiles over HTTP, multi-cell quilted, composited under live nav — fail-loud, deterministic, byte-identical cross-process — extending to encrypted/composite formats and the clean-room relicensing path.

- **Owns (collision boundary):** `engine/vendor/cli/helm_tiles.cpp`, `engine/vendor/cli/helm_server.cpp`, `engine/vendor/cli/chart_spike.cpp`, `engine/vendor/cli/chart_stubs.cpp`, `pipeline/extract_depth.sh`
- **Done =** helm-tiles serves /chart/{z}/{x}/{y}.png; multi-cell quilting with transparent NODTA; deterministic log-scale per-tile cell pick; SCAMIN/safety-contour correctness; fail-loud status codes; MallocPreScribble regression guard; ETag/304 immutable caching; depth-on-satellite compositing (all done). Open extensions: engine-side S-52 Day/Dusk/Night palette, display-category selector, chart-object query face, chart groups, S-63/oeSENC/CM93 encrypted+composite formats, and the clean-room S-52 rebuild on permissive GDAL/OGR/PROJ + MVT vector-tile path (relicensing insurance).

- [x] 🟢 **CHART-1** — Headless S-52 vector ENC renderer (s57chart, no GL/window) ⛔  ↳ ENGINE-1
- [x] 🟢 **CHART-2** — ocpn::chart-render static library + AbstractTopFrame headless seam + chart_stubs.cpp ⛔  ↳ CHART-1
- [x] 🟢 **CHART-3** — S-52 chart-tile HTTP server (slippy tiles, immutable ETag+304) ⛔  ↳ CHART-1
- [x] 🟢 **CHART-4** — Multi-cell quilting + deterministic log-scale cell pick (NODTA transparent)  ↳ CHART-3
- [x] 🟢 **CHART-5** — Native-scale SCAMIN / safety-contour correctness + fail-closed on bad scale ⛔  ↳ CHART-1
- [x] 🟢 **CHART-6** — s52plib headless determinism + MallocPreScribble regression guard + real DPmm  ↳ CHART-5
- [x] 🟢 **CHART-7** — Depth-on-satellite compositing + depare/depcnt/soundg extraction  ↳ CHART-4
- [ ] ⚪ **CHART-8** — Engine-side S-52 Day/Dusk/Night palette switch (not raster reskin)  ↳ CHART-3
- [ ] ⚪ **CHART-9** — S-52 display-category selector (Base/Std/All/Mariner) + overzoom/SCAMIN warning  ↳ CHART-3
- [ ] ⚪ **CHART-10** — Chart-object query face (tap any S-57 object → attributes) + plain-language card  ↳ CHART-3
- [ ] ⚪ **CHART-11** — Chart groups / region sets management  ↳ CHART-3
- [ ] ⚪ **CHART-12** — S-63 / oeSENC / CM93 encrypted+composite chart formats  ↳ CHART-4
- [ ] ⚪ **CHART-13** — Clean-room S-52 rebuild on permissive GDAL/OGR/PROJ + MVT vector-tile path (relicensing insurance, gated on IP counsel)  ↳ CHART-5, ENGINE-11
- [ ] ⚪ **CHART-14** — Align standalone helm-tiles caching with helm-server (immutable ETag+304, currently no-cache)  ↳ CHART-3

## 🟡 `CONTRACT` — Streaming contract + secure transport — nav frame, command-plane, channels, TLS, pairing, tokens, APNs

**Wave 1 · mixed · 5/17 done · ⛓ serializes on SHELL**

> The locked WS+HTTP contract AND its transport-security boundary as one ownership domain: snapshot+delta+seq nav framing, conn.* router with ack+owner-token, staleness tiers, resilience primitives (resume/channels/backpressure), plus one TLS origin, Bonjour, TOFU pairing, bearer-token roles, and APNs — everything native clients inherit.

- **Owns (collision boundary):** `web/server-endpoint.js`, `web/nav-client.js`, `engine/conn-smoke.js`
- **Touches shared (coordinate):** `engine/vendor/cli/helm_server.cpp`
- **Done =** Snapshot+delta+seq framing with keyframes; conn.* router + ack + owner-token; LIVE/LAGGING/STALE/OFFLINE staleness tiers; configurable bind localhost==LAN; engine address resolver; /health (done) + /catalog (partial); lastSeq resume, channels/subscriptions, client-chosen rate, alarm-reliability tier, HTTP/2 tile mux landed; one TLS origin (nav WS + chart + catalog/health/pair); Bonjour _helm._tcp; TOFU pairing (QR/PIN → token + cert pin, offline); bearer tokens with view-only/owner roles; APNs critical alerts + remote off-boat drag alert with local fallback. CONTRACT owns the frame DECODE + event-emitter (nav-client.js) and the auth-header/URL-resolution seam (server-endpoint.js); consumers subscribe to typed events and never parse frames.

- [x] 🟢 **CONTRACT-1** — WS command-plane (conn.* router + ack + owner-token) ⛔  ↳ ENGINE-2
- [x] 🟢 **CONTRACT-2** — Snapshot+delta+seq nav framing with periodic keyframe + nav-client.js decode/event-emitter ⛔  ↳ ENGINE-3
- [x] 🟢 **CONTRACT-3** — Staleness & heartbeat tiers (LIVE/LAGGING/STALE/OFFLINE) + 2s ping ⛔  ↳ CONTRACT-2
- [x] 🟢 **CONTRACT-4** — Configurable bind + engine address resolver (local==remote transparency) ⛔  ↳ CONTRACT-2
- [x] 🟢 **CONTRACT-5a** — /health liveness endpoint  ↳ CONTRACT-4
- [ ] 🟡 **CONTRACT-5b** — /catalog chart-cell endpoint (editions + bbox) _(in-progress)_  ↳ CONTRACT-4
- [ ] ⚪ **CONTRACT-6** — lastSeq resume on reconnect (delta-since instead of full snapshot)  ↳ CONTRACT-2
- [ ] ⚪ **CONTRACT-7** — Channels/subscriptions model + client-chosen nav rate (1–4 Hz)  ↳ CONTRACT-2
- [ ] ⚪ **CONTRACT-8** — bbox-culled AIS streaming (gated on channels CONTRACT-7)  ↳ CONTRACT-7, ENGINE-4
- [ ] 🟡 **CONTRACT-9** — Reconnect + latest-wins backpressure coalescing _(in-progress)_  ↳ CONTRACT-2
- [ ] ⚪ **CONTRACT-10** — Alarm-reliability tier + alarm wire schema (persist + re-send until ACK, exempt from coalescing) — singly-owned alarm frame contract ⛔  ↳ CONTRACT-2, ALARM-1
- [ ] ⚪ **CONTRACT-11** — HTTP/2 (or HTTP/3) tile multiplexing  ↳ CHART-3
- [ ] ⚪ **CONTRACT-12** — One TLS origin collapsing nav WS + chart HTTP + catalog/health/pair ⛔  ↳ CONTRACT-4, CHART-3, ENGINE-9
- [ ] 🟡 **CONTRACT-13** — Bonjour/mDNS discovery (_helm._tcp, TXT v/name/tls/fingerprint) _(in-progress)_  ↳ CONTRACT-12
- [ ] ⚪ **CONTRACT-14** — TOFU pairing (QR/PIN → token + cert pin, no CA, offline) ⛔  ↳ CONTRACT-12
- [ ] ⚪ **CONTRACT-15** — Bearer tokens + view-only/owner roles on /nav,/chart,/catalog  ↳ CONTRACT-14
- [ ] ⚪ **CONTRACT-16** — APNs critical alerts + remote/off-boat anchor-drag alert (local fallback)  ↳ CONTRACT-15, CONTRACT-10, ALARM-1

## 🟡 `ENGINE` — Headless nav core (OpenCPN model/ + patch series)

**Wave 1 · mixed · 8/12 done · ⚡ parallel-safe**

> One cohesive C++ safety core links OpenCPN model/ headless, runs Routeman/AIS/tracks/persistence, and stays the single source of truth for live nav — the foundation every other stream consumes.

- **Owns (collision boundary):** `engine/bootstrap.sh`, `engine/patches/0001..0005`, `engine/vendor/cli/helm_engine.cpp`, `engine/vendor/cli/helm_spike.cpp`, `engine/mock-engine.js`, `engine/stream-smoke.js`, `engine/wsclient-test.js`
- **Done =** Engine builds green from pinned OpenCPN SHA + patch series via bootstrap.sh; headless Routeman drives active-route nav; AIS decode/CPA/TCPA; always-on track recording; navobj.db persistence survives restart; per-field source tagging never fakes position; mock-engine + stream-smoke pass on localhost and LAN. NOTE: per-fix nav MATH (BRG/DTW/DTG/XTE/ETA/TTG/VMG) is SHIPPED and streaming ~1Hz (ENGINE-3 done) — agents must NOT rebuild it; only the clean code relocation into model Routeman (ENGINE-10) remains.

- [x] 🟢 **ENGINE-1** — Vendored OpenCPN + maintained patch series build (bootstrap.sh) ⛔
- [x] 🟢 **ENGINE-2** — Reuse OpenCPN model/ as nav engine (ocpn::model link, zero GUI-wx) ⛔  ↳ ENGINE-1
- [x] 🟢 **ENGINE-3** — Headless Routeman active-route nav + auto-advance + per-fix BRG/DTW/DTG/XTE/ETA/TTG/VMG (math SHIPPED, streaming ~1Hz) ⛔  ↳ ENGINE-2
- [x] 🟢 **ENGINE-4** — AIS decode + multipart reassembly + CPA/TCPA/range/bearing + age-out  ↳ ENGINE-2
- [x] 🟢 **ENGINE-5** — Always-on distance-gated track recording (ActiveTrack)  ↳ ENGINE-2
- [x] 🟢 **ENGINE-6** — GPX + SQLite navobj persistence (InsertRoute, survives restart)  ↳ ENGINE-2
- [x] 🟢 **ENGINE-7** — Per-field source tagging primitive (never fakes position) ⛔  ↳ ENGINE-2
- [x] 🟢 **ENGINE-8** — Mock-engine + stream-smoke harnesses (localhost==LAN)  ↳ ENGINE-2
- [ ] 🟡 **ENGINE-9** — Merge helm-engine + helm-tiles into one binary _(in-progress)_  ↳ ENGINE-3, CHART-3
- [ ] 🟡 **ENGINE-10** — Finish UpdateProgress code relocation into model Routeman (math already shipped via app-side reuse — do NOT rebuild the math) _(in-progress)_  ↳ ENGINE-3
- [ ] ⚪ **ENGINE-11** — Arm's-length GPL containment interface (S-52 engine never statically linked into a distributed binary; boat-server↔thin-client boundary)  ↳ ENGINE-2, CHART-2
- [ ] ⚪ **ENGINE-12** — Add helm-server to bootstrap.sh default build targets + smoke  ↳ ENGINE-9, CHART-3

## ⚪ `SHELL` — Shared-shell extraction — index.html partial API + style.json fragment split

**Wave 1 · not-started · 0/3 done · ⛓ serializes on SHELL**

> The #1 collision hazard de-fanged: index.html's 85KB monolith exposes a panel-registration API (per-epic partials) and style.json splits into per-domain layer fragments merged at build, so 12 wave-2/3 epics append to their OWN files instead of fighting the shell.

- **Owns (collision boundary):** `web/index.html`, `web/style.json`, `web/serve.py`
- **Done =** A panel-registration / per-epic <!-- EPIC:XXX --> partial convention lets each epic register its panel/toolbar/⌘K entry via a small JS hook without editing the monolith body; style.json is split into per-domain layer fragments (helm-wx-*/helm-ais-*/helm-place-*/helm-chart-*/helm-ownship-*) merged at build with a stable layer-namespace convention; both land BEFORE wave-2 fan-out. SHELL is the singular owner of index.html and style.json structure; downstream epics own only their registered partial/fragment.

- [ ] ⚪ **SHELL-1** — Panel-registration API / per-epic <!-- EPIC:XXX --> partial convention in index.html ⛔
- [ ] ⚪ **SHELL-2** — Split style.json into per-domain layer fragments (helm-{wx,ais,place,chart,ownship}-*) merged at build ⛔
- [ ] ⚪ **SHELL-3** — Stable ⌘K / toolbar registration hook each epic appends one entry to ⛔  ↳ SHELL-1

---

# Wave 2 — Reference-client capabilities

_Reference-client capabilities that consume the locked contract, live in their OWN module files, and append to the shell via SHELL's registration API — the cleanest parallelism in the project. AIS (collision.js/ais-meta.js), ALARM (alarms.js), WX (wind/field/isobars/radar/cog/temporal + pipeline), OFFLINE (pipeline + pmtiles/draw/lab harness), CONN (connections.js) barely touch each other. OWNSHIP, ROUTE (now with its own route-edit.js), and TOOLS still register panels through SHELL but serialize on shared shell edits, so they are NOT parallelSafe with each other. ROUTE-3 (direct-manipulation route editing — the flagged single biggest gap) is the highest-value start once SHELL-1 lands. BOAT-1 (under TOOLS) must land this wave — it gates wave-3 ROUTING-1/ROUTING-9 and the skipper-specific autopilot guardrails in PILOT._


## 🟡 `AIS` — AIS display — symbology, target card, list, guard zone, SART/DSC

**Wave 2 · mixed · 1/9 done · ⚡ parallel-safe**

> OpenCPN-class AIS: full symbology set, rich tap card, sortable target list, CPA vector cone, guard-zone alarm, moored suppression, SART/DSC distress surfacing, and deck.gl AIS-at-scale.

- **Owns (collision boundary):** `web/collision.js`, `web/ais-meta.js`, `web/integrations/ais-deck.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** AIS targets render with OpenCPN-class tap card (done); full symbology set (Class A/B, ATON, base, SART/MOB, lost cross-out); sortable target list table; CPA vector cone / tactical overlay; user-defined guard-zone alarm (builds on CONTRACT-10 alarm schema + ALARM-1); moored/slow suppression UI; SART/DSC reception surfaced; deck.gl scatter/heatmap for busy harbors (bbox-culled, gated on CONTRACT-8). Owns helm-ais-* style fragment.

- [x] 🟢 **AIS-1** — AIS targets + OpenCPN-class tap card (flag/type/nav-status/risk/voyage/ROT/LOST)  ↳ ENGINE-4, CONTRACT-2
- [ ] ⚪ **AIS-2** — Full AIS symbology set (class A/B, ATON, base, SART/MOB, lost cross-out)  ↳ AIS-1, SHELL-2
- [ ] ⚪ **AIS-3** — AIS target list (sortable table by CPA/range/name)  ↳ AIS-1
- [ ] ⚪ **AIS-4** — CPA vector cone / tactical overlay + speed-scaled predictor on targets  ↳ AIS-1
- [ ] ⚪ **AIS-5** — AIS guard zone / proximity alarm (on frozen alarm schema)  ↳ AIS-1, ALARM-1, CONTRACT-10
- [ ] ⚪ **AIS-6** — Suppress moored/slow targets UI (g_ShowMoored_Kts)  ↳ AIS-1
- [ ] ⚪ **AIS-7** — SART / DSC distress reception surfacing ⛔  ↳ AIS-1, ENGINE-4, CONTRACT-10
- [ ] 🟡 **AIS-8** — deck.gl AIS-at-scale rendering (bbox-culled — transitively blocked on CONTRACT-7 channels via CONTRACT-8) _(in-progress)_  ↳ AIS-1, CONTRACT-8
- [ ] ⚪ **AIS-9** — Buddy / named-MMSI tagging  ↳ AIS-1

## 🟡 `ALARM` — Safety alarms — anchor/depth/XTE/arrival/MOB/guard + reliability

**Wave 2 · mixed · 5/10 done · ⚡ parallel-safe**

> The deterministic alarm core: anchor-drag, depth/shallow, off-course XTE, arrival, CPA collision + COLREGs, plus MOB, generic guard zone, safety-contour check, audible no-fix — all real-source-guarded and reliably delivered.

- **Owns (collision boundary):** `web/alarms.js`
- **Touches shared (coordinate):** `web/index.html`
- **Done =** Anchor watch + drag, depth/shallow, XTE, arrival, CPA/COLREGs alarms all done and real-source-guarded; add MOB mark + drift, generic geographic guard-zone, safety-contour check, audible no-fix/data-lost alarm; alarms hook the CONTRACT alarm-reliability tier (CONTRACT-10 owns the wire schema — frozen before new alarm types) and (native era) APNs critical alerts via CONTRACT-16.

- [x] 🟢 **ALARM-1** — Anchor watch + debounced drag alarm (settable radius, drift readout) ⛔  ↳ CONTRACT-2
- [x] 🟢 **ALARM-2** — Depth/shallow alarm (real-source guarded)  ↳ CONTRACT-2, ENGINE-7
- [x] 🟢 **ALARM-3** — Off-course (XTE) alarm (real-source guarded)  ↳ ENGINE-3, CONTRACT-2
- [x] 🟢 **ALARM-4** — Arrival alarm (DTW math)  ↳ ENGINE-3, CONTRACT-2
- [x] 🟢 **ALARM-5** — CPA/TCPA collision alarm + COLREGs maneuver suggestion  ↳ ENGINE-4, CONTRACT-2
- [ ] 🟡 **ALARM-6** — MOB mark + go-to + set/drift search-area estimate _(in-progress)_  ↳ ALARM-1, CONTRACT-10
- [ ] ⚪ **ALARM-7** — Generic geographic guard-zone / boundary alarm (Watchdog)  ↳ ALARM-1, CONTRACT-10
- [ ] ⚪ **ALARM-8** — Safety-contour check (route/position crosses contour)  ↳ ALARM-1, CHART-5
- [ ] ⚪ **ALARM-9** — Audible no-fix / data-lost alarm (make ENGINE-LOST badge audible)  ↳ ALARM-1, OWNSHIP-3
- [ ] ⚪ **ALARM-10** — Wire audible feed-loss alarm to the existing STALE/OFFLINE badge (groundwork in setSource + alarms beep loop)  ↳ ALARM-1, OWNSHIP-3

## 🟡 `CONN` — Connectivity — drivers, connections UI, source-priority, serial/internet sources

**Wave 2 · mixed · 4/10 done · ⚡ parallel-safe**

> User-managed boat-data connections: TCP-client/server/UDP drivers with persisted live status, NMEA 0183 ingest, serial NMEA (macOS), SignalK surfaced in UI, N2K, internet AIS, source-priority/multiplexer + raw NMEA monitor.

- **Owns (collision boundary):** `web/connections.js`
- **Touches shared (coordinate):** `web/index.html`
- **Done =** TCP-client/server/UDP drivers persisted to ~/.helm/connections.json with reconnect/backoff and per-connection live status in nav frame; NMEA 0183 RMC/DPT/DBT/MWV/HDT over TCP 10110/UDP; SignalK promoted from env into the connections UI; source-priority/filtering UI + raw NMEA data-monitor view; serial/USB NMEA (macOS-only note); native N2K beyond SignalK gateway; internet AIS (MarineTraffic/AISHub/own feed) source. Registers its Connections panel via SHELL.

- [x] 🟢 **CONN-1** — Multi-source drivers (TCP-client/server/UDP) with reconnect/backoff, persisted ⛔  ↳ CONTRACT-1
- [x] 🟢 **CONN-2** — NMEA 0183 over TCP/UDP ingest (port 10110, checksum-validated)  ↳ CONN-1, ENGINE-7
- [x] 🟢 **CONN-3** — Runtime connection manager + Connections UI (add/edit/delete, live status)  ↳ CONN-1, SHELL-1
- [x] 🟢 **CONN-4** — Per-connection live status in nav frame  ↳ CONN-1, CONTRACT-2
- [ ] 🟡 **CONN-5** — SignalK WebSocket input promoted from HELM_SIGNALK env into Connections UI _(in-progress)_  ↳ CONN-3
- [ ] ⚪ **CONN-6** — Source-priority / filtering / multiplexer UI  ↳ CONN-3
- [ ] ⚪ **CONN-7** — NMEA debug / raw data-monitor view  ↳ CONN-3
- [ ] ⚪ **CONN-8** — NMEA 2000 native (OpenCPN comm_drv) beyond SignalK gateway  ↳ CONN-1
- [ ] ⚪ **CONN-9** — Serial/USB NMEA input (macOS-only; iOS has no serial path)  ↳ CONN-1
- [ ] ⚪ **CONN-10** — Internet AIS source (MarineTraffic/AISHub/own feed) into the target stream  ↳ CONN-1, ENGINE-4

## 🟡 `OFFLINE` — Offline charts — on-demand download, mbtiles/PMTiles, pre-baked packs, vendored frontend

**Wave 2 · mixed · 2/9 done · ⚡ parallel-safe**

> Cache only the passage corridor: lasso-bbox on-demand download with size estimate, BYO mbtiles import, PMTiles packs, pre-baked S-52 region packs with edition stamp + staleness/out-of-coverage warnings, on-client pack management, and the fully-vendored no-CDN frontend (incl. Lab loader harness + offline glyphs).

- **Owns (collision boundary):** `pipeline/fetch_tiles.py`, `pipeline/fetch_sat_tiles.py`, `pipeline/mbtiles_server.py`, `pipeline/make_pmtiles.py`, `pipeline/make_pmtiles.sh`, `pipeline/fetch_glyphs.py`, `pipeline/gen_demo_data.py`, `pipeline/build.sh`, `web/offline-packs.js`, `web/integrations/pmtiles.js`, `web/integrations/draw.js`, `web/integrations/lab.js`, `web/integrations/_maplibre-shim.js`, `web/test/e2e/offline4-pack-selector.spec.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Lasso-bbox → mbtiles pipeline (CLI done) wired to a real Download drawer UI with pre-fetch size estimate + zoom caps (note: drawer UI is currently a MOCKUP — near-greenfield, not finishing wiring); BYO mbtiles/ChartLocker pack selector wired to a local catalog, with copy/import management still to finish; PMTiles offline pack container (.py + .sh) + Martin tile server; vendored no-CDN frontend + offline Noto Sans glyphs + lazy-isolated Lab loader (done); pre-baked S-52 region packs (batch bake over XYZ pyramid) with edition/render-date/palette/z-range stamp; pack staleness + out-of-coverage warning; per-palette packs; region bundle (charts+basemap+depth+places); on-client list/size/delete + edition-diff delta updates.

- [x] 🟢 **OFFLINE-1** — On-demand chart tile fetch pipeline (lasso bbox → mbtiles, TMS Y-flip) + sat tiles
- [x] 🟢 **OFFLINE-2** — Offline-first permanent cache + vendored frontend (no CDN) + offline glyphs + lazy-isolated Lab loader  ↳ OFFLINE-1
- [ ] ⚪ **OFFLINE-3** — Lasso → Download drawer UI + pre-fetch size estimate + zoom caps (currently mockup — near-greenfield UI)  ↳ OFFLINE-1, SHELL-1
- [ ] ⚪ **OFFLINE-4** — BYO mbtiles import UI / ChartLocker bridge (pack selector wired; copy/import management remains)  ↳ OFFLINE-1, SHELL-1
- [ ] 🟡 **OFFLINE-5** — PMTiles offline raster pack container (.py + .sh) + Martin tile server _(in-progress)_  ↳ OFFLINE-1
- [ ] ⚪ **OFFLINE-6** — Pre-baked S-52 region packs (batch bake XYZ) + edition/palette/z-range stamp ⛔  ↳ CHART-3, OFFLINE-5
- [ ] ⚪ **OFFLINE-7** — Pack staleness + out-of-coverage warning + per-palette packs  ↳ OFFLINE-6
- [ ] ⚪ **OFFLINE-8** — Region bundle (charts+basemap+depth+places) + on-client pack mgmt + delta updates  ↳ OFFLINE-6, OFFLINE-7
- [ ] ⚪ **OFFLINE-9** — Route-corridor tile prefetch / GET /prefetch manifest  ↳ OFFLINE-6, ROUTE-2

## 🟡 `OWNSHIP` — Ownship cockpit — instrument bar, follow, orientation, predictor

**Wave 2 · mixed · 4/9 done · ⛓ serializes on SHELL**

> The live cockpit: instrument bar, ownship marker + track trail, follow-mode, course-up/head-up rotation, range rings, predictor ghost — the always-on underway view driven by the nav stream.

- **Owns (collision boundary):** `web/ownship.js`, `web/track.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Instrument bar + ownship marker + track trail render from nav stream; honesty badge wired; neutral-globe start + frame-on-first-fix done; follow-mode/center-on-ownship, course-up/head-up/north-up rotation, look-ahead+auto-zoom-to-speed, range rings, EBL/VRM, and predicted-position ghost shipped. Registers ownship panel via SHELL; owns helm-ownship-* style fragment.

- [x] 🟢 **OWNSHIP-1** — Instrument bar + ownship marker + route inspector from nav stream  ↳ CONTRACT-2
- [x] 🟢 **OWNSHIP-2** — Always-on track trail display (engine-owned)  ↳ ENGINE-5, CONTRACT-2
- [x] 🟢 **OWNSHIP-3** — Honesty badge (LIVE/SIM/ENGINE·SIM POS/ENGINE LOST)  ↳ ENGINE-7, CONTRACT-3
- [x] 🟢 **OWNSHIP-4** — Neutral-globe start + frame-on-first-fix (no hardcoded location)  ↳ OWNSHIP-1
- [ ] 🟡 **OWNSHIP-5** — Follow-mode / center-on-ownship _(in-progress)_  ↳ OWNSHIP-1, SHELL-1, SHELL-2
- [ ] 🟡 **OWNSHIP-6** — Course-up / head-up / north-up chart orientation _(in-progress)_  ↳ OWNSHIP-1
- [ ] ⚪ **OWNSHIP-7** — Look-ahead offset + auto-zoom-to-speed  ↳ OWNSHIP-5
- [ ] ⚪ **OWNSHIP-8** — Range rings + speed-scaled predictor vector + predicted-position ghost  ↳ OWNSHIP-1
- [ ] ⚪ **OWNSHIP-9** — EBL / VRM electronic bearing line + variable range marker  ↳ OWNSHIP-1

## 🟡 `ROUTE` — Route & waypoint editing — direct manipulation, multi-route, GPX

**Wave 2 · mixed · 2/9 done · ⛓ serializes on SHELL**

> Tap-to-drop, long-press-insert, drag-with-live-recompute, move/delete/reverse/split, multi-route list, drop-by-lat/lon or range/bearing, waypoint properties, and full GPX import/export round-trip — the single biggest functional gap closed.

- **Owns (collision boundary):** `web/nav-source.js`, `web/route-edit.js`
- **Touches shared (coordinate):** `web/index.html`, `web/server-endpoint.js`
- **Done =** Create/save/activate route → navobj.db works (done); the new interactive verbs live in a dedicated web/route-edit.js (NOT in nav-source.js, which is only the 104-line SIM source) wired over the command router through CONTRACT's dispatch seam: edit/move/delete/reverse/split; multi-route list with activate-by-pick; drop waypoint by lat/lon or range/bearing; waypoint properties (arrival radius/icon/notes); GPX import/export UI round-trip; great-circle vs rhumb-line toggle; retrace-track-home.

- [x] 🟢 **ROUTE-1** — Create/save/activate route in UI → navobj.db (Terra Draw → route.create)  ↳ ENGINE-6, CONTRACT-1
- [x] 🟢 **ROUTE-2** — Live route line + active-leg highlight from streamed geometry  ↳ CONTRACT-2
- [ ] ⚪ **ROUTE-3** — Route/waypoint edit/move/delete/reverse/split over command router (web/route-edit.js, via CONTRACT dispatch seam) ⛔  ↳ ROUTE-1, CONTRACT-1, SHELL-1
- [ ] 🟡 **ROUTE-4** — Multi-route list management + activate-by-pick _(in-progress)_  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-5** — Drop waypoint by lat/lon or range/bearing  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-6** — Waypoint properties (arrival radius / icon / notes)  ↳ ROUTE-3
- [ ] 🟡 **ROUTE-7** — GPX import/export UI round-trip (load file, export route/track) _(in-progress)_  ↳ ENGINE-6
- [ ] ⚪ **ROUTE-8** — Great-circle vs rhumb-line toggle  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-9** — Retrace-my-track-home (reverse recorded track → route)  ↳ ENGINE-5, ROUTE-3

## 🟡 `TOOLS` — Chart tools, persistence, units, command palette, boat profile, attribution

**Wave 2 · mixed · 2/9 done · ⛓ serializes on SHELL**

> The chartplotter utility belt + state: measure ruler/scale bar, cursor lat/lon format, units UI, ⌘K palette chrome, settings/layer/theme/units/board persistence, boat profile, design tokens, and the legal-load-bearing attribution rendering.

- **Owns (collision boundary):** `web/measure.js`, `web/coordinates.js`, `web/integrations/measures.js`, `web/integrations/cog-disclaimer.js`, `web/test/e2e/tools2-coordinates.spec.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Measure ruler + scale bar (done); cursor lat/lon coordinate-format readout; units selection UI (NM/kn/m/ft/fathom); ⌘K palette chrome wired enough for fuzzy nav (NL handler lives in AI); persistence layer for settings/layers/theme/units/boards; boat profile (draft/air-draft/polars/comfort limits); design-token file (tokens.css → HelmTheme); day/dusk/night UI toggle; satellite supplemental disclaimer + per-source attribution RENDERING (Copernicus Sentinel data, OpenSeaMap ODbL share-alike, Windy clickable logo, NOAA courtesy) + Overpass self-host/mirror obligation tracked. TOOLS CONSUMES WX's cog.js — it does not own it.

- [x] 🟢 **TOOLS-1** — Measure / range-bearing ruler + scale bar
- [ ] 🟡 **BOAT-1** — Boat profile model (draft/air-draft/LOA/comfort limits) — GATED on TOOLS-7 persistence _(in-progress)_ ⛔  ↳ TOOLS-7
- [ ] ⚪ **TOOLS-2** — Cursor lat/lon coordinate-format readout (DMS/DM.m/decimal)
- [ ] 🟡 **TOOLS-3** — ⌘K command palette chrome + fuzzy go-to (port/waypoint/chart/layer) _(in-progress)_  ↳ SHELL-3
- [ ] ⚪ **TOOLS-4** — Units selection UI (NM/kn/m/ft/fathom)  ↳ TOOLS-7
- [x] 🟢 **TOOLS-5** — Day/Dusk/Night UI palette toggle + night-vision red-on-black
- [ ] 🟡 **TOOLS-6** — Satellite supplemental disclaimer + per-source attribution RENDERING (Copernicus/OpenSeaMap ODbL/Windy logo/NOAA) + Overpass mirror obligation _(in-progress)_
- [ ] ⚪ **TOOLS-7** — Persistence layer (settings/layers/theme/units/boards survive reload) ⛔
- [ ] ⚪ **TOOLS-8** — Design-token file (tokens.css → HelmTheme)

## 🟡 `WX` — Weather rendering — scalar stack, particles, isobars, radar, ribbon

**Wave 2 · mixed · 9/13 done · ⚡ parallel-safe**

> Windy-parity weather rendered offline from our own GRIB/Open-Meteo: full scalar catalog, animated wind/current particles, isobars, radar, forecast scrubber, route-weather ribbon, with per-layer toggle/opacity — mostly-done, with Tier-2 GRIB/ensemble/PredictWind/true-wind as the open extensions.

- **Owns (collision boundary):** `web/wind-layer.js`, `web/field-layer.js`, `web/isobars.js`, `web/radar.js`, `web/depth-contours.js`, `web/true-wind.js` (WX-13), `web/wx-value-codec.js` (WX-10), `web/wx-grib.js` (WX-10), `web/integrations/contour.js`, `web/integrations/temporal.js`, `web/integrations/cog.js`, `web/integrations/mercator.js`, `pipeline/fetch_weather.py`, `pipeline/fetch_wind.py`, `pipeline/fetch_dem.py`, `pipeline/make_demo_cog.py`, `pipeline/make_geotiff.py`, `pipeline/make_depth_contours.py`, `pipeline/make_value_tiles.py` (WX-10), `pipeline/fetch_grib.py` (WX-10)
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Full scalar stack (wind/gust/rain/temp/SST/cloud/pressure/CAPE/waves/swell/current), animated wind+current particles, MSLP isobars, RainViewer radar, forecast scrubber+play with data-age, route-weather ribbon, DEM depth contours, per-layer on/off+opacity — all offline-rendered and SHIPPED (WX-1..9 done); load-failure surfaced. WX is SOLE owner of cog.js (GRIB/COG render utility — TOOLS/ROUTING consume, never edit) and temporal.js (time-scrubber — BOARD has its own web/board.js). Tier-2 raw GRIB + value-encoded tile contract + ensemble GFS-vs-ECMWF + PredictWind import + true-wind are the open extensions.

- [x] 🟢 **WX-1** — Full offline weather scalar stack (Open-Meteo, our renderer)
- [x] 🟢 **WX-2** — GPU animated wind-particle layer (10m u/v, projection-aware)  ↳ WX-1
- [x] 🟢 **WX-3** — Ocean-current particle layer (RTOFS/Mercator u/v)  ↳ WX-2
- [x] 🟢 **WX-4** — Pressure isobars (MSLP marching-squares + Chaikin)  ↳ WX-1
- [x] 🟢 **WX-5** — RainViewer radar nowcast overlay (degrades offline)
- [x] 🟢 **WX-6** — Forecast time-scrubber + play + forecast-age display (temporal.js)  ↳ WX-1
- [x] 🟢 **WX-7** — Weather-along-route ribbon  ↳ WX-1, ROUTE-2
- [x] 🟢 **WX-8** — DEM depth contours (maplibre-contour, off-thread)  ↳ WX-1
- [x] 🟢 **WX-9** — Per-layer on/off + opacity controls + load-failure surfacing  ↳ WX-1
- [ ] ⚪ **WX-10** — Tier-2 raw GRIB ingestion (NOMADS/ECMWF/ICON) + value-encoded (Mercator) tile contract (cog.js)  ↳ WX-1
- [ ] ⚪ **WX-11** — Ensemble GFS-vs-ECMWF confidence/spread display  ↳ WX-10
- [ ] ⚪ **WX-12** — PredictWind GPX/GRIB import (device-local, labelled, excluded from sync)  ↳ WX-1
- [ ] ⚪ **WX-13** — True-wind TWA/TWD derivation from apparent + boat motion  ↳ CONTRACT-2

---

# Wave 3 — Higher-order capabilities

_Higher-order capabilities depending on wave-2 substrate: TIDES (helm_tides.cpp relocation), ROUTING (needs polars+GRIB+routes+tides; ROUTING-1 gated on BOAT-1 from wave 2), PLACES & AI (need BACKEND + WX + places store), WATCHMATE (needs route/weather/tide/AIS/alarm/AI substrates), BOARD (needs TOOLS persistence + instrument stream + its own board.js). PLACES, AI, WATCHMATE, and BOARD are parallelSafe when they stay in their own backend/web namespaces; TIDES and ROUTING serialize on shared engine/contract files. AI-5's probe-contract enforcement + faces gate the plugin-SDK work in wave 4._


## 🟡 `AI` — AI copilot — spacetime probe, dossiers, briefings, NL ⌘K

**Wave 3 · mixed · 4/17 done · ⚡ parallel-safe**

> Deterministic-cored, LLM-narrated substrate: spacetime probe resolver + uniform sample() faces (with a probe-contract enforcement bar for all new layers/plugins), place/destination dossier primitives, NL ⌘K, explain-this, RAG, offline-aware LLM mode, and cite-source/freshness guardrails. Watchmate owns the user-facing voyage memory, watchkeeper, handoff, logbook, and passage-timeline product.

- **Owns (collision boundary):** `backend/agents.py`, `backend/context.py`, `backend/llm.py`
- **Touches shared (coordinate):** `web/index.html`, `backend/main.py`
- **Done =** resolve_context + /context + /narrate + provider-pluggable LLMClient + ReAct research agents + where-to-go recommender all done; finish probe sample() faces for stubbed layers (depth/tides/AIS/weather/climatology) AND establish the enforceable 'a layer is not done until it can be sampled' probe contract as a discrete bar for new layers/plugins; wire real NL ⌘K + fuzzy go-to; cited destination/deep-read dossier primitives; generic explain-this; offline-aware LLM mode; and advise-don't-act + cite-source/freshness guardrails enforced. User-facing living passage, watchkeeper advisories, forecast-diff voyage windows, and smart logbook are consolidated under WATCHMATE; AI only supplies optional generated-comment/helper logic for those surfaces. NOTE: AI-4 (where-to-go) shipped against a STUBBED boat profile; promoting to the real BOAT-1 model is a wave-2/3 enrichment, not a rebuild.

- [x] 🟢 **AI-1** — resolve_context + /context + /narrate backend (source-tagged Slice) ⛔  ↳ BACKEND-1, WX-1
- [x] 🟢 **AI-2** — Provider-pluggable LLMClient abstraction (env-only keys) ⛔  ↳ BACKEND-1
- [x] 🟢 **AI-3** — ReAct research agents + dossier cards (get_weather/fetch_page/search_web)  ↳ AI-2
- [x] 🟢 **AI-4** — Where-to-go recommender (deterministic pre-filter + LLM rank + schema) — shipped against a STUBBED boat profile; BOAT-1 is a later enrichment  ↳ AI-3, PLACES-2
- [ ] 🟡 **AI-5** — Probe sample() faces for stubbed layers (depth/tides/AIS/weather/climatology) + enforceable probe-contract bar for new layers/plugins _(in-progress)_ ⛔  ↳ AI-1, CHART-10, TIDES-2, ENGINE-4
- [ ] ⚪ **AI-6** — Real NL command + fuzzy go-to ⌘K wired to actions  ↳ AI-2, TOOLS-3, SHELL-3
- [ ] ⚪ **AI-7** — Cited destination dossier primitives — living passage scope folded into WATCHMATE  ↳ AI-1, ROUTING-3, AI-3
- [ ] 🟡 **AI-8** — Cited RAG pipeline over cruiser web (Noonsite/blogs/forums) _(in-progress)_  ↳ AI-3
- [ ] ⚪ **AI-9** — Forecast-diff narration helper — product scope folded into WATCHMATE-7  ↳ AI-13, WX-11
- [ ] ⚪ **AI-10** — Explain-this on chart object / weather / alarm  ↳ AI-1, CHART-10
- [ ] ⚪ **AI-11** — Watchkeeper narration helper — advisory product folded into WATCHMATE-5  ↳ AI-13, ALARM-5
- [ ] ⚪ **AI-12** — Logbook narration helper — structured voyage log folded into WATCHMATE  ↳ AI-13, ENGINE-5
- [ ] 🟡 **AI-13** — Advise-don't-act + cite-source/freshness/horizon guardrails (enforced) _(in-progress)_ ⛔  ↳ AI-1
- [ ] ⚪ **AI-14** — Offline-aware LLM mode (cloud dockside, on-device + cached offshore)  ↳ AI-2, OFFLINE-2
- [ ] ⚪ **AI-15** — Real climatology / tropical-cyclone tier (NOAA/COGOW/NHC/JTWC) + horizon/confidence honesty labeling  ↳ AI-1, WX-10
- [ ] ⚪ **AI-16** — Wire the /dossier ReAct card to a place/point tap in the web UI  ↳ AI-3, PLACES-3
- [ ] ⚪ **AI-17** — Implement an enforceable probe-contract (sample()) bar — base class/registry/test  ↳ AI-5

## 🟡 `WATCHMATE` — Voyage memory, watch handoff, and advisory timeline

**Wave 3 · mixed · 0/9 done · ⚡ parallel-safe**

> A structured voyage memory layer that journals the past, explains the current watch, and projects future route-aware decision windows. The LLM may summarize and comment, but the structured journal, source records, freshness, confidence, and human notes stay authoritative. Full contract: [WATCHMATE.md](WATCHMATE.md).

- **Owns (collision boundary):** `docs/WATCHMATE.md`; future implementation should use `backend/watchmate.py` or `backend/watchmate/`, `web/watchmate.js`, and `helm-watchmate-*` style/layer namespaces.
- **Consumes (does not seize ownership):** ROUTE active-leg/ETA/XTE state, WX forecast age/route-weather, TIDES source/confidence/pass data, AIS risk/target state, ALARM lifecycle, AI narration/guardrails, CONTRACT source/staleness semantics.
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`, `backend/main.py`, and engine stream/schema files only through future board tasks that explicitly own the seam.
- **Done =** Watchmate ships a local-first voyage journal event store; passage timeline UI; watch handoff summaries; source/confidence-tagged advisory cards; human notes and acknowledged decisions; forecast-diff narration; voyage review/export; and golden no-invention tests. Every record exposes source, freshness, confidence, and a why/explain path. Watchmate advises, never acts.

- [ ] 🟡 **WATCHMATE-1** — Epic contract: Watchmate voyage memory + advisory timeline ⛔
- [ ] ⚪ **WATCHMATE-2** — Structured voyage journal event store ⛔  ↳ WATCHMATE-1, ROUTE-2, WX-7, TIDES-8, AIS-1, ALARM-12
- [ ] ⚪ **WATCHMATE-3** — Passage timeline UI: past, current watch, and next decision windows  ↳ WATCHMATE-2, ROUTE-4, WX-6, WX-7, TIDES-4
- [ ] ⚪ **WATCHMATE-4** — Watch handoff summaries: what changed since last watch  ↳ WATCHMATE-2, AI-13
- [ ] ⚪ **WATCHMATE-5** — Current-watch advisor cards with source/confidence reasoning  ↳ WATCHMATE-2, AI-13, ALARM-3, ALARM-5, WX-11, TIDES-4
- [ ] ⚪ **WATCHMATE-6** — Human notes, decisions, and acknowledged actions in the voyage log  ↳ WATCHMATE-2, AI-13
- [ ] ⚪ **WATCHMATE-7** — Forecast-diff and future risk-window narration  ↳ WATCHMATE-3, WATCHMATE-5, WX-11, WX-14, TIDES-3, TIDES-5
- [ ] ⚪ **WATCHMATE-8** — Voyage review, export, and passage dossier handoff  ↳ WATCHMATE-4, WATCHMATE-6, AI-16
- [ ] ⚪ **WATCHMATE-9** — Golden voyage scenarios and no-invention tests  ↳ WATCHMATE-4, WATCHMATE-5, WATCHMATE-7, AI-13, TIDES-6

## ⚪ `BOARD` — Smart Board — composable dashboard, tiles, automations

**Wave 3 · not-started · 0/7 done · ⚡ parallel-safe**

> A Home-Assistant-style composable instrument dashboard: drag-to-build resizable tiles from any SignalK path, history sparklines, per-tile threshold alarms, context-switching boards by mode, and a trigger→condition→action rule builder.

- **Owns (collision boundary):** `web/board.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Composable resizable multi-board tile grid; any-SignalK-path tile; history sparklines + trend; per-tile threshold alarms (notification+haptic+sound, on the CONTRACT-10 alarm schema); context-switching boards by mode (Underway/Anchor/Engine/Racing/Night/Docking); trigger→condition→action automation rule builder; boards persist via TOOLS persistence. BOARD owns its OWN web/board.js (its scrubber/state needs differ from WX's temporal.js — it does NOT touch temporal.js).

- [ ] ⚪ **BOARD-1** — Composable drag-to-build resizable multi-board tile grid (web/board.js) ⛔  ↳ TOOLS-7, OWNSHIP-1
- [ ] ⚪ **BOARD-2** — Any-SignalK-path tile (tanks/batteries/bilge/RPM/autopilot)  ↳ BOARD-1, CONN-5
- [ ] ⚪ **BOARD-3** — Tiles with history sparklines + trend  ↳ BOARD-1
- [ ] ⚪ **BOARD-4** — Per-tile threshold alarms (notification + haptic + sound, on CONTRACT-10 schema)  ↳ BOARD-2, ALARM-1, CONTRACT-10
- [ ] ⚪ **BOARD-5** — Context-switching boards by mode (Underway/Anchor/Racing/Night/Docking)  ↳ BOARD-1
- [ ] ⚪ **BOARD-6** — Automation rule builder (trigger→condition→action)  ↳ BOARD-4, BOARD-5
- [ ] ⚪ **BOARD-7** — Pilot dashboard tile / automation surface for already-safe PILOT actions (not command semantics)  ↳ BOARD-6, PILOT-2

## ⚪ `PILOT` — Autopilot control — state, guarded commands, adapters, approval

**Wave 3 · not-started · 0/7 done · ⚡ parallel-safe**

> Skipper-approved autopilot control: read pilot state first; define a guarded owner-only command
> contract; emit standard SignalK/NMEA route or heading output; spike B&G/Navico proprietary
> +/-1 and +/-10 commands only from captured hardware traffic; bridge AIS maneuver advice into a
> manual approval flow. AIS/AI may advise, but only PILOT commands, and only after skipper approval.

- **Owns (collision boundary):** `web/pilot.js`, `docs/AUTOPILOT.md`
- **Coordinates (does not seize ownership):** command-plane/auth through CONTRACT, connection/output adapters through CONN, route data through ROUTE/ENGINE, maneuver recommendations through AIS.
- **Done =** Read-only pilot state widget; canonical `pilot.*` command contract with owner-role checks, ACK/NACK, stale-source rejection, and audit log; standard SignalK/NMEA output adapter for route/heading intent; B&G/Navico +/-1/+/-10 spike hardware-validated before any live enablement; route-follow approval UI; AIS/CPA maneuver approval bridge; self-test/interlocks. BOARD may render tiles/prompts, but does not own actuation semantics.

- [ ] ⚪ **PILOT-1** — Read-only autopilot status model + widget (mode, heading, target, rudder, source, freshness)  ↳ CONN-5, CONN-8, CONTRACT-2, CONTRACT-3
- [ ] ⚪ **PILOT-2** — Guarded pilot command contract (`pilot.setMode`, `pilot.setHeading`, `pilot.adjustHeading`, `pilot.followRoute`, `pilot.cancel`, `pilot.approveManeuver`)  ↳ CONTRACT-1, CONTRACT-10, CONTRACT-15, AI-13
- [ ] ⚪ **PILOT-3** — Standard SignalK/NMEA route and heading output adapter  ↳ PILOT-2, CONN-1, CONN-2, CONN-5, CONN-8, ENGINE-3, ROUTE-2, ROUTE-3
- [ ] ⚪ **PILOT-4** — B&G/Navico proprietary +/-1/+/-10 course-change spike (feature-flagged, hardware-capture driven)  ↳ PILOT-1, PILOT-2, CONN-7, CONN-8, CONTRACT-15
- [ ] ⚪ **PILOT-5** — Route-follow / steer-to-waypoint approval UI  ↳ PILOT-2, PILOT-3, ROUTE-4, ALARM-3, ALARM-4
- [ ] ⚪ **PILOT-6** — AIS/CPA maneuver approval bridge (AIS suggests; PILOT stages; skipper confirms)  ↳ PILOT-2, AIS-12, AIS-13, AIS-14, ALARM-5, ENGINE-13, AI-13
- [ ] ⚪ **PILOT-7** — Safety interlocks, audit log, and self-test  ↳ PILOT-2, CONTRACT-3, CONTRACT-10, CONTRACT-15, TOOLS-7

## 🟡 `PLACES` — Places & community — overlay, cards, saved pins, give-back

**Wave 3 · mixed · 2/10 done · ⚡ parallel-safe**

> Anchorages/marinas/fuel/services from OSM/OpenSeaMap offline-cached, rich detail cards, saved cross-device pins/collections, Helm-owned reviews backend, and NFL/OSM give-back — the owned-data community moat.

- **Owns (collision boundary):** `web/community.js`, `backend/store.py`, `backend/publisher.py`, `pipeline/fetch_places.py`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`, `backend/main.py`
- **Done =** OSM/OpenSeaMap places overlay offline-cached with amenity-typed clustered symbols (done); source-tagged place store + owned pins/reviews CRUD + saved places (done); rich anchorage/marina detail cards; saved-place collections/lists; anchorage intelligence (shelter/holding); NFL track push + settings tile; OSM Notes + node-edit give-back with review queue; fleet position sharing + voyage recap. Owns helm-place-* style fragment + an APIRouter module appended to main.py.

- [x] 🟢 **PLACES-1** — OSM/OpenSeaMap places overlay (offline-cached, clustered, amenity icons)  ↳ BACKEND-1
- [x] 🟢 **PLACES-2** — Source-tagged place store + owned pins/reviews CRUD + saved places  ↳ BACKEND-1
- [ ] 🟡 **PLACES-3** — Rich anchorage/marina detail cards + navigate-here _(in-progress)_  ↳ PLACES-1
- [ ] ⚪ **PLACES-4** — Saved-place collections / shareable lists  ↳ PLACES-2
- [ ] ⚪ **PLACES-5** — Anchorage intelligence (computed shelter-by-wind + holding + boats-here-now)  ↳ PLACES-3, WX-1
- [ ] 🟡 **PLACES-6** — NFL track push publisher + cadence/offline-queue + opt-in settings tile (BYO key) _(in-progress)_  ↳ PLACES-2, CONTRACT-2
- [ ] 🟡 **PLACES-7** — OSM Notes give-back (Tier 1) + contribution record/queue _(in-progress)_  ↳ PLACES-2
- [ ] ⚪ **PLACES-8** — OSM node edits give-back (Tier 2, OAuth2 + review queue)  ↳ PLACES-7
- [ ] ⚪ **PLACES-9** — Helm fleet opt-in position sharing + voyage-recap sharing  ↳ PLACES-2, NATIVE-10
- [ ] ⚪ **PLACES-10** — NFL reciprocity outreach + personal-experimental NFL bbox pull (experimental flag, never shipped)  ↳ PLACES-6

## 🟡 `ROUTING` — Weather routing — isochrone engine, polars, laylines, advisors

**Wave 3 · mixed · 0/9 done · ⛓ serializes on SHELL**

> Helm's own isochrone weather router on free GRIB + boat polars: polar editor, laylines, departure-time what-if, scrub-the-boat-forward ghost, virtual-buoy point forecast, depth-aware dock-to-dock — assumptions shown, confidence honest.

- **Owns (collision boundary):** `web/routing.js`
- **Touches shared (coordinate):** `web/index.html`
- **Done =** Deterministic isochrone router on free GRIB + polars; polar import/editor; laylines; departure-window optimizer; scrub-the-boat-forward ghost + virtual-buoy clickable route-point forecast; tidal-gate-aware ETA; depth-aware dock-to-dock auto-routing with shown assumptions. ROUTING owns web/routing.js; it CONSUMES WX's cog.js (calls, never edits). LLM narration lives in AI epic. GATE NOTE: ROUTING-1 needs BOAT-1 (wave-2 TOOLS persistence task) landed first.

- [ ] ⚪ **ROUTING-1** — Boat polars import + editor (.pol/.csv) — GATED on BOAT-1 (wave-2) ⛔  ↳ BOAT-1
- [ ] ⚪ **ROUTING-2** — Isochrone weather router (free GRIB + polars, isochrones + ETA) ⛔  ↳ ROUTING-1, WX-10, ROUTE-3
- [ ] 🟡 **ROUTING-3** — Spacetime probe — sample weather along worldline W(P(t),t) (deterministic sampling primitive) _(in-progress)_  ↳ WX-1, ROUTE-2
- [ ] ⚪ **ROUTING-4** — Scrub-the-boat-forward ghost ownship + valid-time weather  ↳ ROUTING-3, OWNSHIP-8
- [ ] ⚪ **ROUTING-5** — Clickable route-point forecast (virtual buoy)  ↳ ROUTING-3
- [ ] ⚪ **ROUTING-6** — Laylines (tide/shift-corrected)  ↳ ROUTING-1, WX-13, TIDES-2
- [ ] ⚪ **ROUTING-7** — Departure-window what-if optimizer (candidate departure times)  ↳ ROUTING-2
- [ ] ⚪ **ROUTING-8** — Tidal-gate-aware route ETA  ↳ ROUTING-2, TIDES-2
- [ ] ⚪ **ROUTING-9** — Depth-aware dock-to-dock auto-routing (shown assumptions, leg-by-leg confirm)  ↳ ROUTING-2, CHART-5, BOAT-1

## 🟡 `TIDES` — Tides & pass conditions — official tides, local pass current, confidence

**Wave 3 · mixed · 3/7 done · ⛓ serializes on SHELL**

> Government tide predictions are the base layer, but the product is confidence-banded pass conditions: official/source-tagged tide stations, datum handling, predicted-vs-observed current, wind/swell residuals, local slack delay, and an observation log for remote passes/bars.

- **Owns (collision boundary):** `engine/vendor/cli/helm_tides.cpp`
- **Touches shared (coordinate):** `engine/vendor/cli/helm_engine.cpp`, `web/index.html`, `web/style.json`
- **Done =** tcmgr.cpp relocated gui→core into a NEW translation unit engine/vendor/cli/helm_tides.cpp (ENGINE owns helm_engine.cpp; TIDES only adds an include line) so it never edits the nav loop; harmonic tide prediction with government/source-tagged tide stations; datum + station-distance confidence; predicted-vs-observed currents; wind/swell lagoon-fill residuals; local pass model with observation log, slack-delay tuning, and Plan B warning; tide/pass dashboard wired to the weather scalar/probe contract. Remote-pass output is always advisory and never a raw "safe" claim.

- [x] 🟢 **TIDES-1** — Harmonic tide engine — offline, source-tagged water-level core ⛔  ↳ ENGINE-2
- [x] 🟢 **TIDES-2** — Government tide stations + datum + confidence model  ↳ TIDES-1
- [ ] ⚪ **TIDES-3** — Predicted-vs-observed currents + wind/swell residuals  ↳ TIDES-2, WX-9
- [ ] ⚪ **TIDES-4** — Tides/pass dashboard — next tide, slack estimate, confidence, station distance  ↳ TIDES-2, TIDES-5
- [ ] ⚪ **TIDES-5** — Pass Condition Estimator — local pass model, observations, wind/wave factor, slack-delay confidence ⛔  ↳ TIDES-2, TIDES-3, TOOLS-7, WX-1, CHART-7
- [x] 🟢 **TIDES-6** — Pin numeric harmonic regression test — free-source station/time/height + HW/LW event tripwire  ↳ TIDES-1
- [x] 🟢 **TIDES-7** — Enforce harmonic-data licensing policy — free-only default + unverified source gates  ↳ TIDES-1

---

# Wave 4 — Native + commercial (last)

_The user's explicit rule: native comes LAST, after the web contract is locked and boat-tested. NATIVE (now absorbing the commercial CLOUD concerns as the wave-4 'ship it' epic) depends on the shared-core compile + TOFU pairing + the documented protocol (NOT channels — the compile needs the protocol, not the optimization). The license-posture sub-task (NATIVE-12) can actually start early but the shippable cloud product gates on native + secure transport._


## ⚪ `NATIVE` — Native Apple clients + commercial — shared core compile, clients, cloud sync, packaging, appliance

**Wave 4 · not-started · 0/15 done · ⛓ serializes on SHELL**

> After the web contract is locked and boat-tested: compile the shared C++ core for Apple targets, ship a WKWebView first-proof, then native macOS/iPad/iPhone/Watch clients + CarPlay/widgets over the documented protocol — and the commercial layer riding on top (cloud sync, hosting, three-tier packaging, notarized DMG, license posture, appliance).

- **Owns (collision boundary):** _(coordination epic)_
- **Touches shared (coordinate):** `backend/main.py`
- **Done =** Shared C++ nav core compiles for macOS/iPadOS/iOS (needs the protocol — not necessarily channels); WKWebView-wrapped web UI proves an iPad over Bonjour; native macOS SwiftUI/AppKit (+ serial NMEA via CONN-9), iPad SwiftUI+Metal, one-handed iPhone clients; Apple Watch anchor-watch/MOB + CarPlay/widgets/Live Activity; NWPathMonitor + iOS background anchor-watch; internal/BLE GPS input; onboarding/first-run flow; iOS companion deep-read tier; cloud route/mark + fleet sync; hosted tiling + GRIB delivery + remote watch; three-tier Free/Cloud/Appliance packaging; notarized non-App-Store DMG; BSL-1.1→Apache-2.0 license posture + GPL/GDAL boundary + attribution register; certified reference-hardware list + DC-DC UPS appliance + parallel sea-trial. Speaks only the documented JSON/WS + PNG/HTTP protocol (App-Store-clean).

- [ ] ⚪ **NATIVE-1** — Shared C++ nav core compiles for Apple targets (needs the core protocol/contract, NOT channels) ⛔  ↳ ENGINE-2, CONTRACT-2, CONTRACT-14
- [ ] ⚪ **NATIVE-2** — WKWebView-wrapped web UI as first iOS proof (zero new code)  ↳ CONTRACT-13, CONTRACT-3
- [ ] ⚪ **NATIVE-3** — Tauri desktop shell + packaging  ↳ CONTRACT-12
- [ ] ⚪ **NATIVE-4** — Native macOS SwiftUI/AppKit client (+ serial NMEA via CONN-9)  ↳ NATIVE-1, CONN-9
- [ ] ⚪ **NATIVE-5** — Native iPad SwiftUI+Metal client (MapLibre Native)  ↳ NATIVE-1, NATIVE-2
- [ ] ⚪ **NATIVE-6** — One-handed iPhone client + NWPathMonitor + background anchor-watch  ↳ NATIVE-5, CONTRACT-16
- [ ] ⚪ **NATIVE-7** — Apple Watch (anchor-watch/MOB/complications) + CarPlay/widgets/Live Activity  ↳ NATIVE-6
- [ ] ⚪ **NATIVE-8** — Internal/BLE GPS input on native + onboarding/first-run flow (connect-boat/build-board/download-home-waters/boat-profile)  ↳ NATIVE-4, BOAT-1
- [ ] ⚪ **NATIVE-9** — iOS companion app deep-read tier (full dossier text/photos/links)  ↳ NATIVE-6, AI-7
- [ ] ⚪ **NATIVE-10** — Cloud route/mark + fleet sync (CloudKit/own backend, excludes PredictWind imports) ⛔  ↳ CONTRACT-15, ROUTE-3
- [ ] ⚪ **NATIVE-11** — Hosted chart tiling + cloud GRIB delivery + remote watch  ↳ NATIVE-10, CONTRACT-16
- [ ] ⚪ **NATIVE-12** — BSL-1.1→Apache-2.0 license posture + GPL/GDAL boundary + attribution register (can start early) ⛔  ↳ ENGINE-11
- [ ] ⚪ **NATIVE-13** — Notarized macOS DMG distribution (non-App-Store, VLC-problem sidestep)  ↳ NATIVE-12, NATIVE-4
- [ ] ⚪ **NATIVE-14** — Three-tier packaging (Free/Cloud/Appliance) + plugin SDK / layer probe contract  ↳ NATIVE-11, AI-5
- [ ] ⚪ **NATIVE-15** — Certified reference-hardware list + DC-DC UPS appliance + parallel sea-trial alongside OpenCPN  ↳ NATIVE-13

---

# Cross-cutting — Web-client hardening (front-end best-practices audit)

_Not wave-gated. A **2026-06-26 multi-agent audit** measured the MapLibre web client against current best practices (**MapLibre GL JS 5.24.0** — the latest release; **deck.gl 9.3.x**). Verdict: the stack and versions are current, and the nav **ingress** path is already best-practice — rAF latest-wins coalescing (`nav-client.js:277`), ownship dead-reckoning between fixes (`ownship.js:196`), gesture-guarded follow (`ownship.js:59-73`), and solid WebSocket backoff/resume/watchdog. The gaps cluster in three places: the **egress render path** (every dynamic layer updates via full-FeatureCollection `setData`; `feature-state`/`updateData` and `promoteId` are used nowhere), the **offline/PWA story** (no service worker or web-app manifest despite the offline-first charter — the shell can't survive an offline reload), and **observability + supply-chain** (no global error surface, no dependency lockfile/audit, web tests not wired to CI)._

_`CLIENT` is deliberately **cross-cutting**: it OWNS the genuinely-new infra files (service worker, PWA manifest, vendor lockfile, web test runner, shared logger + weather ramp) and **coordinates** the in-place perf fixes inside each owner epic's files (named per task, edited through that epic's seam — it does not seize OWNSHIP/AIS/WX/CONTRACT files). Start anywhere: `CLIENT-1..4` are isolated, cheap, high-payoff; `CLIENT-5` (`promoteId`) unblocks the whole data-path tier. Companion notes in [FEATURE-TRACKER.md](FEATURE-TRACKER.md)._

## ⚪ `CLIENT` — Web-client hardening — MapLibre render path, offline/PWA, observability, supply-chain

**Cross-cutting · not-started · 0/18 done · ⚡ parallel-safe (new infra) + ⛓ coordinates on owner epics**

> Bring the MapLibre web client fully onto best practices: kill the real-time render-path churn (the ~60 fps ownship-overlay re-serialize, the O(n²) track rebuild, full-`setData` everywhere), adopt `promoteId` + `updateData`/`feature-state`, bound AIS to the viewport, ship a real offline-first PWA (service worker + manifest + OPFS PMTiles), consolidate the five weather renderers off the main thread, and close the engineering-hygiene gaps (dependency lockfile + CVE audit, web tests in CI, global error surface, CSP, one persistence layer, a11y). Every change is verified against `helm-server` in the preview and must not regress the honesty / fail-loud rules.

- **Owns (new files):** `web/sw.js`, `web/manifest.webmanifest`, `web/vendor/package.json` (+ lockfile), `web/test/run.mjs` (web smoke/unit runner), `web/log.js` (leveled logger), `web/wx-ramp.js` (one shared weather color-ramp + sampler)
- **Coordinates (in-place fixes — owner epic in parens, edit via their seam):** `web/ownship.js`,`web/track.js` (OWNSHIP) · `web/integrations/ais-deck.js`,`web/collision.js` (AIS) · `web/index.html`, style fragments (SHELL) · `web/nav-client.js` (CONTRACT) · `web/wind-layer.js`,`web/field-layer.js`,`web/isobars.js`,`web/wx-live.js`,`web/integrations/*` (WX) · `web/integrations/pmtiles.js`,`web/vendor/*` (OFFLINE) · `web/persist.js` (TOOLS)
- **Done =** real-time updates run via `updateData`/`feature-state` keyed by stable feature ids, with the ownship overlay + track no longer re-serializing every frame and AIS bounded to the viewport; the app shell + glyphs/sprite + tiles survive an offline reload as an installable PWA; the five weather renderers share one ramp/sampler and rasterize off the main thread; the vendor bundle carries a lockfile + CVE audit, the web smoke/unit tests run in CI, and a global error surface + CSP + single persistence layer close the safety/hygiene gaps. Each task carries its own acceptance check.

- [ ] ⚪ **CLIENT-1** — Stop the ~60 fps ownship-overlay re-serialize — gate `redrawOverlay()` on actual movement, not every rAF frame (`web/ownship.js:204`) · _coord OWNSHIP_
- [ ] ⚪ **CLIENT-2** — Cap + Douglas–Peucker-simplify the ownship track; kill the O(n²) full-LineString `setData` per fix (`web/track.js:22,27`) · _coord OWNSHIP_
- [ ] ⚪ **CLIENT-3** — Fix the deck.gl `MapboxOverlay` leak on Lab disable — `removeControl` + null the ref; handle the re-add-after-remove gotcha (`web/integrations/ais-deck.js:73`) · _coord AIS; feeds AIS-8_
- [ ] ⚪ **CLIENT-4** — Global error surface — `window.onerror` + `unhandledrejection` + `map.on('error')` + bootstrap `try/catch` + a visible "degraded" banner (`web/index.html:669`) ⛔ · _coord SHELL_
- [ ] ⚪ **CLIENT-5** — Add `promoteId`/`generateId` (MMSI + stable ids) to every dynamic GeoJSON source — the prerequisite for diff-updates + feature-state (`web/style.json:91`) ⛔ · _coord SHELL/AIS/PLACES/CHART_
- [ ] ⚪ **CLIENT-6** — Migrate AIS/track/route live updates from full `setData` to `updateData(GeoJSONSourceDiff)` (`web/index.html:966`, `web/track.js:22`)  ↳ CLIENT-5
- [ ] ⚪ **CLIENT-7** — Move selection/hover/alarm-highlight restyles to `setFeatureState` (+ `['feature-state',…]` paint) — no `setData` for pure style changes  ↳ CLIENT-5
- [ ] ⚪ **CLIENT-8** — Wire the client bbox AIS cull (`client.setBbox`) to a debounced map `moveend`/`zoomend` — bound target count to the viewport (`web/nav-client.js:429`)  ↳ CONTRACT-8 · _coord CONTRACT_
- [ ] ⚪ **CLIENT-9** — Replace the per-frame `JSON.parse(JSON.stringify())` deep clone in `mergeState` with a targeted merge (`web/nav-client.js:92`) · _coord CONTRACT_
- [ ] ⚪ **CLIENT-10** — Set source `maxzoom:12` + `cluster` on dense point GeoJSON (soundings/POIs); long-term move soundings/depth-areas to vector tiles (xref CHART-13) · _coord CHART/PLACES_
- [ ] ⚪ **CLIENT-11** — Service worker (Workbox): precache the app shell (index.html + ~33 JS + vendor + CSS) **+ glyphs/sprite** + runtime-cache same-origin chart/sat tiles → offline-reload-survivable ⛔ · _coord OFFLINE_
- [ ] ⚪ **CLIENT-12** — Web-app manifest (`manifest.webmanifest`, `display:standalone`, icons, `viewport-fit`) → installable PWA; document iOS PWA storage caps  ↳ CLIENT-11 · _coord OFFLINE_
- [ ] ⚪ **CLIENT-13** — Generalize PMTiles to OPFS-stored downloadable packs (near-native read, no IndexedDB overhead) → charts/sat fully offline (`web/integrations/pmtiles.js`)  ↳ CLIENT-11, OFFLINE-5
- [ ] ⚪ **CLIENT-14** — Consolidate the five scalar-weather renderers + unify the three divergent color ramps + one `sample()` signature (`web/index.html:763`, `web/wx-live.js:19`, `web/wind-layer.js:47`) · _coord WX_
- [ ] ⚪ **CLIENT-15** — Move weather rasterization off the main thread — `OffscreenCanvas`→`ImageBitmap` (drop synchronous `toDataURL`) + isobars marching-squares in a Web Worker (`web/field-layer.js:69`, `web/wx-live.js:97`, `web/isobars.js`)  ↳ CLIENT-14 · _coord WX_
- [ ] ⚪ **CLIENT-16** — Vendor `package.json` + lockfile pinning every vendored lib + CI `npm audit`/Dependabot + make `build.mjs` repo-relative (drop the hard-coded home path) (`web/vendor/build.mjs:4`, `web/vendor/README.md`) · _coord OFFLINE_
- [ ] ⚪ **CLIENT-17** — Wire the web smoke tests into CI (`engine/test-engine.sh` or a `test` script) + add unit tests for collision/CPA, ais-risk tiers, ais-guard, true-wind, wx-value-codec (`web/persist.smoke.js`, `web/alarms.smoke.js` + new)
- [ ] ⚪ **CLIENT-18** — Hardening: CSP + `innerHTML` audit; route all persistence through `HelmStore` (`ais-guard.js`/`ais-vectors.js`/`server-endpoint.js` bypass it); leveled logger gating the 137 `console.*`; a11y labels + opt-in `tsc --checkJs` · _coord TOOLS/SHELL_

---

# Experimental — Labs (pro-maritime survey)

_Not wave-gated. Born from a **2026-06-26 survey** of advanced charting tech in the cruise / military / commercial-ship world (S-100 layered ENCs, Furuno-style AR nav, AI-lookout sensor fusion, dynamic under-keel clearance, military Additional Military Layers). The through-line: nearly every pro innovation is **fusion + a new layer** — which is Helm's exact thesis and the layer-marketplace ([BUSINESS-MODEL.md §10](BUSINESS-MODEL.md)). LABS is where we prove the cruiser-grade version of each, flag-gated and advisory-only, before it graduates to a real workstream or a sellable layer. Full spec with per-task acceptance: **[LABS.md](LABS.md)**._

## 🧪 `LABS` — Experimental pro-maritime features (advisory-only, flag-gated)

**Experimental · not-started · 0/7 done · ⚡ parallel-safe (own `web/labs/**` + `backend/labs/**` namespace)**

> Flag-gated, advisory-only experiments mounted on the existing lazy-isolated Lab loader (OFFLINE-2): a cruiser-grade dynamic under-keel-clearance "pass advisor", a camera-as-a-layer AI lookout, AR heads-up pilotage, an S-100 ingestion spike, shareable cruiser layers + RTZ, and an RTK spike. The proving ground for the layer marketplace's hero layers. Each graduates to a real workstream / sellable layer only after boat-testing.

- **Owns (collision boundary):** `web/labs/**` (e.g. `web/labs/loader.js`, `web/labs/guardrail.js`), `backend/labs/**` (e.g. `backend/labs/ukc.py`), `docs/LABS.md`
- **Consumes (never edits):** the nav stream + alarm schema (CONTRACT-10), the layer/probe contract (AI-5/AI-17), source-tagging (ENGINE-7), the SHELL registration hooks, and the OFFLINE-owned Lab loader harness (`web/integrations/lab.js`). A Lab that needs a core change files a task against the owning epic and depends on it.
- **Shared guardrail (every LABS task):** supplemental, never authoritative; source-tagged + confidence-labelled; never overrides real AIS/radar/official ENC; advise-don't-act (AI-13); off by default behind the Labs flag.
- **Done =** the Labs surface + guardrail wrapper ship (LABS-1); the flagship pass advisor computes green/amber/red transit windows offline from charted-depth + tide + swell + draft (LABS-2); camera-fused AI lookout + AR pilotage prove the camera-as-a-layer model (LABS-3/4); the S-100 spike yields an ADR + a rendered sample dataset (LABS-5); cruiser-layer + RTZ exchange round-trips (LABS-6); RTK fix-quality surfaces honestly (LABS-7). Each task carries its own acceptance check ([LABS.md](LABS.md)).

- [ ] ⚪ **LABS-1** — Labs framework & advisory guardrail (flag-gated, lazy-isolated Lab surface) ⛔
- [ ] ⚪ **LABS-2** — Reef & Bar Pass Advisor — cruiser-grade dynamic under-keel clearance [FLAGSHIP]  ↳ LABS-1, BOAT-1, TIDES-2, WX-1, CHART-5, CHART-7, ROUTE-2, ALARM-8
- [ ] ⚪ **LABS-3** — Camera-as-a-Layer AI Lookout (machine-vision collision aid)  ↳ LABS-1, ENGINE-4, ALARM-5, CONTRACT-10, AI-13, AI-14, CONN-1, AI-5, AI-17
- [ ] ⚪ **LABS-4** — AR Heads-Up Pilotage Overlay (nav data on the live camera view)  ↳ LABS-1, AIS-1, ROUTE-2, CHART-10, OWNSHIP-1, NATIVE-2, NATIVE-5
- [ ] ⚪ **LABS-5** — S-100 layer ingestion spike + layer-contract alignment  ↳ LABS-1, CHART-3, AI-5, AI-17, TIDES-2, WX-1
- [ ] ⚪ **LABS-6** — Shareable cruiser layers (AML/NUDL pattern) + RTZ route exchange  ↳ LABS-1, PLACES-2, ENGINE-7, ROUTE-3, SHELL-1, NATIVE-14
- [ ] ⚪ **LABS-7** — RTK / precise-positioning spike (anchor-drop and bommie avoidance) [optional]  ↳ LABS-1, CONN-1, ENGINE-7

---

# Collision map (resolved)

- web/index.html (85KB shared shell) is the #1 hazard — RESOLVED by making SHELL a wave-1 BLOCKING epic that owns index.html outright and ships a panel-registration / <!-- EPIC:XXX --> partial API (SHELL-1) + ⌘K registration hook (SHELL-3). Every wave-2/3 epic that adds UI (OWNSHIP-5, ROUTE-3, AIS-2, CONN-3, OFFLINE-3/4, TOOLS-3, AI-6) now DEPENDS on SHELL-1/SHELL-3 in its task deps, so the 12-epic shell collision is serialized through one owner and one API rather than concurrent edits to the monolith body.
- web/style.json (shared map layers) — RESOLVED by SHELL-2 (wave-1 BLOCKING): style.json is split into per-domain layer fragments (helm-wx-*, helm-ais-*, helm-place-*, helm-chart-*, helm-ownship-*) merged at build. CHART/WX/AIS/OWNSHIP/PLACES/OFFLINE each own their fragment; layer-namespace convention prevents two epics editing the same JSON object. AIS-2 and OWNSHIP-5 carry explicit deps on SHELL-2.
- web/server-endpoint.js is owned by CONTRACT; ROUTE touchesShared it for route.* commands. MITIGATION: CONTRACT lands a stable command-dispatch + auth-header seam (CONTRACT-1/CONTRACT-12); ROUTE-3 consumes it via web/route-edit.js without editing the resolver core. (SECURE merged into CONTRACT, so the former CONTRACT/SECURE fight over this file is gone — one owner now.)
- web/nav-client.js is now explicitly OWNED by CONTRACT (frame decode + event-emitter, CONTRACT-2). OWNSHIP/ROUTE/ALARM/AIS subscribe to typed events and never parse frames themselves — no shared ownership.
- engine/vendor/cli/helm_engine.cpp is owned solely by ENGINE. TIDES owns a SEPARATE translation unit engine/vendor/cli/helm_tides.cpp (TIDES-1) and only adds an include line to helm_engine.cpp (listed as touchesShared, not owns) — the nav loop is never edited by TIDES. ENGINE-9 (merge engine+tiles) lands before CONTRACT-12 (TLS origin) so the transport work targets one binary.
- engine/vendor/cli/helm_server.cpp is owned by CHART (tile server); CONTRACT touchesShared it for the TLS-origin/token/pairing transport work (CONTRACT-12..16). MITIGATION: CHART owns the tile-serving render path; CONTRACT adds the TLS/auth front-door as a wrapping layer with a stable seam, not by editing CHART's render code.
- backend/main.py routing table is touched by BACKEND (skeleton), PLACES (/places,/saved,/reviews,/giveback), AI (/context,/narrate,/whereto), and NATIVE (cloud sync). MITIGATION: BACKEND-1 establishes APIRouter-per-domain includes so PLACES/AI/NATIVE each own their router module (store.py/agents.py/publisher.py) and only append one include line to main.py.
- web/integrations/cog.js — RESOLVED: WX is the SOLE owner (it is a GRIB/COG render utility). TOOLS and ROUTING are pure consumers — they call it, never list it in owns. (TOOLS's disclaimer concern moved to its own web/integrations/cog-disclaimer.js to avoid any name confusion.)
- web/integrations/temporal.js — RESOLVED: WX is the SOLE owner (forecast time-scrubber, WX-6). BOARD's scrubber/state needs differ and live in its own web/board.js (BOARD-1) — BOARD does not touch temporal.js.
- ALARM (alarms.js) and CONTRACT (alarm-reliability tier) must agree on the alarm wire schema — RESOLVED: CONTRACT-10 is the SINGLE owner of the alarm frame contract and is marked blocking; AIS-5/AIS-7, ALARM-6/7, and BOARD-4 all carry an explicit dep on CONTRACT-10 so the schema is frozen before any epic builds new alarm types onto it.
- engine/vendor/cli/chart_stubs.cpp (links into the headless chart lib) is now owned by CHART (CHART-2). web/serve.py is owned by SHELL (dev static server alongside the shell). web/integrations/lab.js + web/integrations/_maplibre-shim.js (Lab loader harness) are owned by OFFLINE (OFFLINE-2). pipeline/fetch_glyphs.py + fetch_sat_tiles.py + make_pmtiles.{py,sh} are owned by OFFLINE. No file is now orphaned.
- web/integrations/lab.js + _maplibre-shim.js (the lazy-isolated Lab LOADER harness) stay owned by OFFLINE (OFFLINE-2). The new LABS epic owns a SEPARATE `web/labs/**` + `backend/labs/**` feature namespace that the loader MOUNTS — LABS never edits the loader or any core epic file; a Lab that needs a core change files a task against the owning epic and depends on it (LABS-1 is the gate, marked blocking).

---

# Porting / tracking

Mirrors the taikun-plan model 1:1 (epics = workstreams, tasks = `{EPIC}-{N}` with `⛔ blocking` + `↳ deps`). Live on **plan.taikunai.com**; agents read/update via the `taikun-plan` MCP with **`project="helm"`** (`board_summary`/`get_task`/`search_tasks` to read, `update_task`/`add_comment` to write; `ask_plan` for board-grounded Q&A). Omitting `project` targets a different customer's board — never do that.
