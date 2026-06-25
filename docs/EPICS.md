# Helm — Epic Plan (the board)

> **The single source of truth for _what to build, in what order, by which parallel stream._** Generated 2026-06-25 from a full read of every project `.md` (688 capabilities inventoried → deduped → decomposed → adversarially critique-refined). Companion to [FEATURE-TRACKER.md](FEATURE-TRACKER.md) (per-feature status) and the ADRs in [decisions/](decisions/).

## The one rule

**Each epic owns its own files.** That `owns` list is a _collision boundary_: an agent working an epic edits only those files, so two streams never fight over the same module. The two shared files that every UI epic used to collide on — `web/index.html` (85KB shell) and `web/style.json` — are de-fanged by the **SHELL** epic, which must land first and gives every other epic a registration hook + its own style fragment. Lock **SHELL** and **CONTRACT**, and the wave-2 streams fan out almost collision-free.

## Board at a glance

- **19 epics** · **186 tasks** — 🟢 57 done · 🟡 20 in-progress · 🔴 0 blocked · ⚪ 109 to-do

| Wave | Theme | Epics | Tasks done |
|---|---|---|---|
| **1** | Foundations & unblockers | BACKEND, CHART, CONTRACT, ENGINE, SHELL | 25/49 |
| **2** | Reference-client capabilities | AIS, ALARM, CONN, OFFLINE, OWNSHIP, ROUTE, TOOLS, WX | 28/77 |
| **3** | Higher-order capabilities | AI, BOARD, PLACES, ROUTING, TIDES | 4/45 |
| **4** | Native + commercial (last) | NATIVE | 0/15 |

## How to run it (parallel streams)

- **Status legend:** 🟢 done & wired · 🟡 in progress / one side built · 🔴 blocked · ⚪ to-do. ⛔ = **blocking** (gates other work). `↳` = task dependencies (may cross epics).

- **`parallelSafe`** on an epic = it lives entirely in its own files and can run concurrently with other same-wave epics. `parallelSafe=False` epics still register through SHELL, so they serialize on shell edits — run them one-at-a-time _within_ a wave, or after SHELL ships its API.

- **Waves are dependency order, not a calendar.** Wave 1 = unblocked now; higher waves wait on deps. Pick any unblocked epic in the current wave and point an agent at it.

## ▶ Start here (the first three streams)

Given how much foundation is already 🟢 done, the highest-leverage opening moves:

1. **SHELL (do this first, solo).** `SHELL-1/2/3` — the panel-registration API + `style.json` fragment split. Tiny (3 tasks) but **it unblocks ~10 wave-2 UI epics**. Until it lands, the UI streams can't safely run in parallel.

2. **In parallel with SHELL (zero collision — different files): CONTRACT + ENGINE hardening.** `CONTRACT-6/7/9` (resume · channels · backpressure) and `ENGINE-9/10` (merge to one binary · finish the `UpdateProgress` relocation — the math already ships, do **not** rebuild it). These touch `engine/` + contract files only, never the shell.

3. **The moment SHELL lands, fan out wave 2.** Highest value first: **ROUTE-3** (direct-manipulation route editing — the single biggest functional gap), **OWNSHIP-5/6** (follow-mode + course-up — basic chartplotter UX still missing), and **TOOLS-7** (persistence — it gates `BOAT-1`, units, and Smart Board). Then **AIS**, **CONN** (SignalK into the UI), **WX** Tier-2 — each in its own module, truly concurrent.

> **Critical-path watch:** `TOOLS-7` (persistence) → `BOAT-1` (boat profile) → `ROUTING-1` (polars) → the whole weather-routing epic. If weather routing matters for the season, start the `TOOLS-7 → BOAT-1` chain early in wave 2.


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

**Wave 1 · mixed · 7/13 done · ⚡ parallel-safe**

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
- [ ] 🟡 **CHART-10** — Chart-object query face (tap any S-57 object → attributes) + plain-language card _(in-progress)_  ↳ CHART-3
- [ ] ⚪ **CHART-11** — Chart groups / region sets management  ↳ CHART-3
- [ ] ⚪ **CHART-12** — S-63 / oeSENC / CM93 encrypted+composite chart formats  ↳ CHART-4
- [ ] ⚪ **CHART-13** — Clean-room S-52 rebuild on permissive GDAL/OGR/PROJ + MVT vector-tile path (relicensing insurance, gated on IP counsel)  ↳ CHART-5, ENGINE-11

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
- [ ] ⚪ **CONTRACT-13** — Bonjour/mDNS discovery (_helm._tcp, TXT v/name/tls/fingerprint)  ↳ CONTRACT-12
- [ ] ⚪ **CONTRACT-14** — TOFU pairing (QR/PIN → token + cert pin, no CA, offline) ⛔  ↳ CONTRACT-12
- [ ] ⚪ **CONTRACT-15** — Bearer tokens + view-only/owner roles on /nav,/chart,/catalog  ↳ CONTRACT-14
- [ ] ⚪ **CONTRACT-16** — APNs critical alerts + remote/off-boat anchor-drag alert (local fallback)  ↳ CONTRACT-15, CONTRACT-10, ALARM-1

## 🟡 `ENGINE` — Headless nav core (OpenCPN model/ + patch series)

**Wave 1 · mixed · 8/11 done · ⚡ parallel-safe**

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
- [ ] ⚪ **ENGINE-9** — Merge helm-engine + helm-tiles into one binary  ↳ ENGINE-3, CHART-3
- [ ] 🟡 **ENGINE-10** — Finish UpdateProgress code relocation into model Routeman (math already shipped via app-side reuse — do NOT rebuild the math) _(in-progress)_  ↳ ENGINE-3
- [ ] ⚪ **ENGINE-11** — Arm's-length GPL containment interface (S-52 engine never statically linked into a distributed binary; boat-server↔thin-client boundary)  ↳ ENGINE-2, CHART-2

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

_Reference-client capabilities that consume the locked contract, live in their OWN module files, and append to the shell via SHELL's registration API — the cleanest parallelism in the project. AIS (collision.js/ais-meta.js), ALARM (alarms.js), WX (wind/field/isobars/radar/cog/temporal + pipeline), OFFLINE (pipeline + pmtiles/draw/lab harness), CONN (connections.js) barely touch each other. OWNSHIP, ROUTE (now with its own route-edit.js), and TOOLS still register panels through SHELL but serialize on shared shell edits, so they are NOT parallelSafe with each other. ROUTE-3 (direct-manipulation route editing — the flagged single biggest gap) is the highest-value start once SHELL-1 lands. BOAT-1 (under TOOLS) must land this wave — it gates wave-3 ROUTING-1/ROUTING-9._


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

**Wave 2 · mixed · 5/9 done · ⚡ parallel-safe**

> The deterministic alarm core: anchor-drag, depth/shallow, off-course XTE, arrival, CPA collision + COLREGs, plus MOB, generic guard zone, safety-contour check, audible no-fix — all real-source-guarded and reliably delivered.

- **Owns (collision boundary):** `web/alarms.js`
- **Touches shared (coordinate):** `web/index.html`
- **Done =** Anchor watch + drag, depth/shallow, XTE, arrival, CPA/COLREGs alarms all done and real-source-guarded; add MOB mark + drift, generic geographic guard-zone, safety-contour check, audible no-fix/data-lost alarm; alarms hook the CONTRACT alarm-reliability tier (CONTRACT-10 owns the wire schema — frozen before new alarm types) and (native era) APNs critical alerts via CONTRACT-16.

- [x] 🟢 **ALARM-1** — Anchor watch + debounced drag alarm (settable radius, drift readout) ⛔  ↳ CONTRACT-2
- [x] 🟢 **ALARM-2** — Depth/shallow alarm (real-source guarded)  ↳ CONTRACT-2, ENGINE-7
- [x] 🟢 **ALARM-3** — Off-course (XTE) alarm (real-source guarded)  ↳ ENGINE-3, CONTRACT-2
- [x] 🟢 **ALARM-4** — Arrival alarm (DTW math)  ↳ ENGINE-3, CONTRACT-2
- [x] 🟢 **ALARM-5** — CPA/TCPA collision alarm + COLREGs maneuver suggestion  ↳ ENGINE-4, CONTRACT-2
- [ ] ⚪ **ALARM-6** — MOB mark + go-to + set/drift search-area estimate  ↳ ALARM-1, CONTRACT-10
- [ ] ⚪ **ALARM-7** — Generic geographic guard-zone / boundary alarm (Watchdog)  ↳ ALARM-1, CONTRACT-10
- [ ] ⚪ **ALARM-8** — Safety-contour check (route/position crosses contour)  ↳ ALARM-1, CHART-5
- [ ] ⚪ **ALARM-9** — Audible no-fix / data-lost alarm (make ENGINE-LOST badge audible)  ↳ ALARM-1, OWNSHIP-3

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

- **Owns (collision boundary):** `pipeline/fetch_tiles.py`, `pipeline/fetch_sat_tiles.py`, `pipeline/make_pmtiles.py`, `pipeline/make_pmtiles.sh`, `pipeline/fetch_glyphs.py`, `pipeline/gen_demo_data.py`, `pipeline/build.sh`, `web/integrations/pmtiles.js`, `web/integrations/draw.js`, `web/integrations/lab.js`, `web/integrations/_maplibre-shim.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Lasso-bbox → mbtiles pipeline (CLI done) wired to a real Download drawer UI with pre-fetch size estimate + zoom caps (note: drawer UI is currently a MOCKUP — near-greenfield, not finishing wiring); BYO mbtiles import UI (also MOCKUP); PMTiles offline pack container (.py + .sh) + Martin tile server; vendored no-CDN frontend + offline Noto Sans glyphs + lazy-isolated Lab loader (done); pre-baked S-52 region packs (batch bake over XYZ pyramid) with edition/render-date/palette/z-range stamp; pack staleness + out-of-coverage warning; per-palette packs; region bundle (charts+basemap+depth+places); on-client list/size/delete + edition-diff delta updates.

- [x] 🟢 **OFFLINE-1** — On-demand chart tile fetch pipeline (lasso bbox → mbtiles, TMS Y-flip) + sat tiles
- [x] 🟢 **OFFLINE-2** — Offline-first permanent cache + vendored frontend (no CDN) + offline glyphs + lazy-isolated Lab loader  ↳ OFFLINE-1
- [ ] ⚪ **OFFLINE-3** — Lasso → Download drawer UI + pre-fetch size estimate + zoom caps (currently mockup — near-greenfield UI)  ↳ OFFLINE-1, SHELL-1
- [ ] ⚪ **OFFLINE-4** — BYO mbtiles import UI / ChartLocker bridge (currently mockup — near-greenfield UI)  ↳ OFFLINE-1, SHELL-1
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
- [ ] ⚪ **OWNSHIP-5** — Follow-mode / center-on-ownship  ↳ OWNSHIP-1, SHELL-1, SHELL-2
- [ ] ⚪ **OWNSHIP-6** — Course-up / head-up / north-up chart orientation  ↳ OWNSHIP-1
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
- [ ] ⚪ **ROUTE-4** — Multi-route list management + activate-by-pick  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-5** — Drop waypoint by lat/lon or range/bearing  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-6** — Waypoint properties (arrival radius / icon / notes)  ↳ ROUTE-3
- [ ] 🟡 **ROUTE-7** — GPX import/export UI round-trip (load file, export route/track) _(in-progress)_  ↳ ENGINE-6
- [ ] ⚪ **ROUTE-8** — Great-circle vs rhumb-line toggle  ↳ ROUTE-3
- [ ] ⚪ **ROUTE-9** — Retrace-my-track-home (reverse recorded track → route)  ↳ ENGINE-5, ROUTE-3

## 🟡 `TOOLS` — Chart tools, persistence, units, command palette, boat profile, attribution

**Wave 2 · mixed · 1/9 done · ⛓ serializes on SHELL**

> The chartplotter utility belt + state: measure ruler/scale bar, cursor lat/lon format, units UI, ⌘K palette chrome, settings/layer/theme/units/board persistence, boat profile, design tokens, and the legal-load-bearing attribution rendering.

- **Owns (collision boundary):** `web/measure.js`, `web/integrations/measures.js`, `web/integrations/cog-disclaimer.js`
- **Touches shared (coordinate):** `web/index.html`, `web/style.json`
- **Done =** Measure ruler + scale bar (done); cursor lat/lon coordinate-format readout; units selection UI (NM/kn/m/ft/fathom); ⌘K palette chrome wired enough for fuzzy nav (NL handler lives in AI); persistence layer for settings/layers/theme/units/boards; boat profile (draft/air-draft/polars/comfort limits); design-token file (tokens.css → HelmTheme); day/dusk/night UI toggle; satellite supplemental disclaimer + per-source attribution RENDERING (Copernicus Sentinel data, OpenSeaMap ODbL share-alike, Windy clickable logo, NOAA courtesy) + Overpass self-host/mirror obligation tracked. TOOLS CONSUMES WX's cog.js — it does not own it.

- [x] 🟢 **TOOLS-1** — Measure / range-bearing ruler + scale bar
- [ ] 🟡 **BOAT-1** — Boat profile model (draft/air-draft/LOA/comfort limits) — GATED on TOOLS-7 persistence _(in-progress)_ ⛔  ↳ TOOLS-7
- [ ] ⚪ **TOOLS-2** — Cursor lat/lon coordinate-format readout (DMS/DM.m/decimal)
- [ ] 🟡 **TOOLS-3** — ⌘K command palette chrome + fuzzy go-to (port/waypoint/chart/layer) _(in-progress)_  ↳ SHELL-3
- [ ] ⚪ **TOOLS-4** — Units selection UI (NM/kn/m/ft/fathom)  ↳ TOOLS-7
- [ ] 🟡 **TOOLS-5** — Day/Dusk/Night UI palette toggle + night-vision red-on-black _(in-progress)_
- [ ] 🟡 **TOOLS-6** — Satellite supplemental disclaimer + per-source attribution RENDERING (Copernicus/OpenSeaMap ODbL/Windy logo/NOAA) + Overpass mirror obligation _(in-progress)_
- [ ] ⚪ **TOOLS-7** — Persistence layer (settings/layers/theme/units/boards survive reload) ⛔
- [ ] ⚪ **TOOLS-8** — Design-token file (tokens.css → HelmTheme)

## 🟡 `WX` — Weather rendering — scalar stack, particles, isobars, radar, ribbon

**Wave 2 · mixed · 9/13 done · ⚡ parallel-safe**

> Windy-parity weather rendered offline from our own GRIB/Open-Meteo: full scalar catalog, animated wind/current particles, isobars, radar, forecast scrubber, route-weather ribbon, with per-layer toggle/opacity — mostly-done, with Tier-2 GRIB/ensemble/PredictWind/true-wind as the open extensions.

- **Owns (collision boundary):** `web/wind-layer.js`, `web/field-layer.js`, `web/isobars.js`, `web/radar.js`, `web/depth-contours.js`, `web/integrations/contour.js`, `web/integrations/temporal.js`, `web/integrations/cog.js`, `web/integrations/mercator.js`, `pipeline/fetch_weather.py`, `pipeline/fetch_wind.py`, `pipeline/fetch_dem.py`, `pipeline/make_demo_cog.py`, `pipeline/make_geotiff.py`, `pipeline/make_depth_contours.py`
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

_Higher-order capabilities depending on wave-2 substrate: TIDES (helm_tides.cpp relocation), ROUTING (needs polars+GRIB+routes+tides; ROUTING-1 gated on BOAT-1 from wave 2), PLACES & AI (need BACKEND + WX + places store), BOARD (needs TOOLS persistence + instrument stream + its own board.js). PLACES, AI, and BOARD are parallelSafe (separate backend modules / own files); TIDES and ROUTING serialize on shared engine/contract files. AI-5's probe-contract enforcement + faces gate the plugin-SDK work in wave 4._


## 🟡 `AI` — AI copilot — spacetime probe, dossiers, briefings, NL ⌘K

**Wave 3 · mixed · 2/15 done · ⚡ parallel-safe**

> Deterministic-cored, LLM-narrated copilot: spacetime probe resolver + uniform sample() faces (with a probe-contract enforcement bar for all new layers/plugins), place dossiers, living passage/destination briefings with dual-axis timeline, NL ⌘K, explain-this, watchkeeper, smart logbook — advise, never act.

- **Owns (collision boundary):** `backend/agents.py`, `backend/context.py`, `backend/llm.py`
- **Touches shared (coordinate):** `web/index.html`, `backend/main.py`
- **Done =** resolve_context + /context + /narrate + provider-pluggable LLMClient + ReAct research agents + where-to-go recommender all done; finish probe sample() faces for stubbed layers (depth/tides/AIS/weather/climatology) AND establish the enforceable 'a layer is not done until it can be sampled' probe contract as a discrete bar for new layers/plugins; wire real NL ⌘K + fuzzy go-to; living passage/destination dossiers + dual-axis timeline + background diff-narration; explain-this; watchkeeper; smart logbook; advise-don't-act + cite-source/freshness guardrails enforced; offline-aware LLM mode. NOTE: AI-4 (where-to-go) shipped against a STUBBED boat profile; promoting to the real BOAT-1 model is a wave-2/3 enrichment, not a rebuild.

- [ ] 🟡 **AI-1** — resolve_context + /context + /narrate backend (source-tagged Slice) _(in-progress)_ ⛔  ↳ BACKEND-1, WX-1
- [ ] 🟡 **AI-2** — Provider-pluggable LLMClient abstraction (env-only keys) _(in-progress)_ ⛔  ↳ BACKEND-1
- [x] 🟢 **AI-3** — ReAct research agents + dossier cards (get_weather/fetch_page/search_web)  ↳ AI-2
- [x] 🟢 **AI-4** — Where-to-go recommender (deterministic pre-filter + LLM rank + schema) — shipped against a STUBBED boat profile; BOAT-1 is a later enrichment  ↳ AI-3, PLACES-2
- [ ] ⚪ **AI-5** — Probe sample() faces for stubbed layers (depth/tides/AIS/weather/climatology) + enforceable probe-contract bar for new layers/plugins ⛔  ↳ AI-1, CHART-10, TIDES-2, ENGINE-4
- [ ] ⚪ **AI-6** — Real NL command + fuzzy go-to ⌘K wired to actions  ↳ AI-2, TOOLS-3, SHELL-3
- [ ] ⚪ **AI-7** — Living passage + destination dossiers + dual-axis (valid/issue-time) timeline + quick-notes-vs-deep-read tiers  ↳ AI-1, ROUTING-3, AI-3
- [ ] 🟡 **AI-8** — Cited RAG pipeline over cruiser web (Noonsite/blogs/forums) _(in-progress)_  ↳ AI-3
- [ ] ⚪ **AI-9** — Background ingestion + forecast-diff 'what changed & does it matter' narration  ↳ AI-7, ROUTING-2
- [ ] ⚪ **AI-10** — Explain-this on chart object / weather / alarm  ↳ AI-1, CHART-10
- [ ] ⚪ **AI-11** — Watchkeeper risk narration + departure advisor + router-style advisory  ↳ AI-1, ALARM-5, ROUTING-2
- [ ] ⚪ **AI-12** — Smart auto-narrated logbook from track + instruments  ↳ AI-2, ENGINE-5
- [ ] 🟡 **AI-13** — Advise-don't-act + cite-source/freshness/horizon guardrails (enforced) _(in-progress)_ ⛔  ↳ AI-1
- [ ] ⚪ **AI-14** — Offline-aware LLM mode (cloud dockside, on-device + cached offshore)  ↳ AI-2, OFFLINE-2
- [ ] ⚪ **AI-15** — Real climatology / tropical-cyclone tier (NOAA/COGOW/NHC/JTWC) + horizon/confidence honesty labeling  ↳ AI-1, WX-10

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
- [ ] ⚪ **BOARD-7** — Autopilot output over network (steer-to-waypoint, command-plane)  ↳ BOARD-6, CONTRACT-1

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
- [ ] ⚪ **PLACES-6** — NFL track push publisher + cadence/offline-queue + opt-in settings tile (BYO key)  ↳ PLACES-2, CONTRACT-2
- [ ] 🟡 **PLACES-7** — OSM Notes give-back (Tier 1) + contribution record/queue _(in-progress)_  ↳ PLACES-2
- [ ] ⚪ **PLACES-8** — OSM node edits give-back (Tier 2, OAuth2 + review queue)  ↳ PLACES-7
- [ ] ⚪ **PLACES-9** — Helm fleet opt-in position sharing + voyage-recap sharing  ↳ PLACES-2, NATIVE-10
- [ ] ⚪ **PLACES-10** — NFL reciprocity outreach + personal-experimental NFL bbox pull (experimental flag, never shipped)  ↳ PLACES-6

## ⚪ `ROUTING` — Weather routing — isochrone engine, polars, laylines, advisors

**Wave 3 · not-started · 0/9 done · ⛓ serializes on SHELL**

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

## ⚪ `TIDES` — Tides & currents — tcmgr.cpp gui→core + dashboard

**Wave 3 · not-started · 0/4 done · ⛓ serializes on SHELL**

> Harmonic tide & current prediction ported from OpenCPN tcmgr.cpp into the headless core via a SEPARATE translation unit, with stations, time-animated current arrows, and dashboard instruments — the substrate tide-aware routing depends on.

- **Owns (collision boundary):** `engine/vendor/cli/helm_tides.cpp`
- **Touches shared (coordinate):** `engine/vendor/cli/helm_engine.cpp`, `web/index.html`, `web/style.json`
- **Done =** tcmgr.cpp relocated gui→core into a NEW translation unit engine/vendor/cli/helm_tides.cpp (ENGINE owns helm_engine.cpp; TIDES only adds an include line) so it never edits the nav loop; harmonic tide prediction with tide stations; time-animated tidal-current arrow field; tide/current dashboard instruments; sea-level layer wired to the weather scalar contract.

- [ ] ⚪ **TIDES-1** — tcmgr.cpp gui→core relocation into helm_tides.cpp (harmonic math in headless core) ⛔  ↳ ENGINE-2
- [ ] ⚪ **TIDES-2** — Harmonic tide prediction + tide stations  ↳ TIDES-1
- [ ] ⚪ **TIDES-3** — Time-animated tidal-current arrow field  ↳ TIDES-2, WX-9
- [ ] ⚪ **TIDES-4** — Tides/currents dashboard instruments + sea-level layer  ↳ TIDES-2

---

# Wave 4 — Native + commercial (last)

_The user's explicit rule: native comes LAST, after the web contract is locked and boat-tested. NATIVE (now absorbing the commercial CLOUD concerns as the wave-4 'ship it' epic) depends on the shared-core compile + TOFU pairing + the documented protocol (NOT channels — the compile needs the protocol, not the optimization). The license-posture sub-task (NATIVE-12) can actually start early but the shippable cloud product gates on native + secure transport._


## ⚪ `NATIVE` — Native Apple clients + commercial — shared core compile, clients, cloud sync, packaging, appliance

**Wave 4 · not-started · 0/15 done · ⛓ serializes on SHELL**

> After the web contract is locked and boat-tested: compile the shared C++ core for Apple targets, ship a WKWebView first-proof, then native macOS/iPad/iPhone/Watch clients + CarPlay/widgets over the documented protocol — and the commercial layer riding on top (cloud sync, hosting, three-tier packaging, notarized DMG, license posture, appliance).

- **Owns (collision boundary):** _(coordination epic — no files)_
- **Touches shared (coordinate):** `backend/main.py`
- **Done =** Shared C++ nav core compiles for macOS/iPadOS/iOS (needs the protocol — not necessarily channels); WKWebView-wrapped web UI proves an iPad over Bonjour; native macOS SwiftUI/AppKit (+ serial NMEA via CONN-9), iPad SwiftUI+Metal, one-handed iPhone clients; Apple Watch anchor-watch/MOB + CarPlay/widgets/Live Activity; NWPathMonitor + iOS background anchor-watch; internal/BLE GPS input; onboarding/first-run flow; iOS companion deep-read tier; cloud route/mark + fleet sync; hosted tiling + GRIB delivery + remote watch; three-tier Free/Cloud/Appliance packaging; notarized non-App-Store DMG; BSL-1.1→Apache-2.0 license posture + GPL/GDAL boundary + attribution register; certified reference-hardware list + DC-DC UPS appliance + parallel sea-trial. Speaks only the documented JSON/WS + PNG/HTTP protocol (App-Store-clean).

- [ ] 🟡 **NATIVE-1** — Shared C++ nav core compiles for Apple targets (needs the core protocol/contract, NOT channels) _(in-progress)_ ⛔  ↳ ENGINE-2, CONTRACT-2, CONTRACT-14
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

# Collision map (resolved)

The places two epics could have fought over a file, and how the boundary was drawn so they don't:

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

---

# Porting to a tracked board

This mirrors the taikun-plan model 1:1 — **epics = workstreams**, **tasks = `{EPIC}-{N}`** with status + `⛔ blocking` + `↳ deps`. It can be loaded into a plan instance (like plan.taikunai.com) for live tracking without restructuring. Status here is the snapshot at generation; update task boxes as streams land, or promote to a board for multi-stream burndown.

