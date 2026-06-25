# Helm — Feature Tracker (living)

> **v1 · 2026-06-25** · the single mutable source of truth for *what's built, what's next*.
> Baseline: [FEATURE-AUDIT.md](FEATURE-AUDIT.md) (immutable point-in-time audit, 2026-06-24).
> Provenance for phase + parity: [PRD](../PRD.md) · [ROADMAP](ROADMAP.md) · [VISION](VISION.md) ·
> [COMPETITIVE](COMPETITIVE.md) · [OPENCPN-REUSE](OPENCPN-REUSE.md).
> Strategy (Steve): **perfect the web client first → native (Mac → iPad → iPhone) last.** The web
> client is the reference impl of the one engine protocol native inherits, so every feature here is
> built once, web-first, and boat-tested.

**Legend:** 🟢 done & wired end-to-end · 🟡 partial (one side built) · 🔴 missing · ⚪ planned (future phase)

---

## Build sequence (control-plane first)

The interactive features all hang off one prerequisite — the **client→server command-plane** — which
shipped with connections. Each new interactive verb reuses that same JSON command router.

| # | Step | Status |
|---|------|--------|
| 1 | **WS command-plane** (conn.* router + ack + owner-token gate) | 🟢 **done** — `c092955` |
| 2 | **Runtime connections + Connections UI** (TCP-client/server/UDP, persisted, live status) — boat-verified vs Vesper Cortex | 🟢 **done** — `c092955`/`4779073` |
| 3 | **Track recording** — *always-on automatic* (no on-screen control), distance-gated (records the anchor swing like OpenCPN); engine-owned trail + map line | 🟢 **done** — `4623f78`+ |
| 4 | **Route create/save/activate** — draw a route → persisted to navobj.db (OpenCPN's SQLite store, reused) → active + survives restart | 🟢 **done** — `route.create` |
| 4a | **Route/waypoint *edit*/delete + multi-route list** in UI over the same router | 🔴 **next (interactive)** |
| 4b | **Anchor watch + drag alarm** — drop at fix, settable swing radius (−/+), live drift readout, **debounced** critical alarm (a single GPS jitter can't trip it) — boat-verified on the live Fiji fix | 🟢 **done** (on-screen; remote/off-boat alert still Phase 2) |
| 5 | Follow-mode / center-on-ownship + course-up / head-up orientation | 🔴 later |
| 6 | Cursor lat/lon + coord-format, range rings, EBL/VRM, drop-waypoint-by-range/bearing (tool cluster) | 🔴 later |
| 7 | Cheap alarms now the math exists: arrival, off-course (XTE), depth/shallow, audible no-fix, AIS guard zone | 🔴 later |
| 8 | Anchor watch + drag alarm → remote/off-boat alert | ⚪ Phase 2 |
| 9 | True-wind (TWA/TWD) + AIS target list + full AIS symbology set | ⚪ later |
| 10 | GPX import/export UI round-trip + waypoint properties | 🟡 later |
| 11 | Tides & currents (tcmgr.cpp gui→core) + current arrows | ⚪ Phase 2 |
| 12 | Weather routing: isochrone router + polars on free NOAA GRIB (+ laylines) | ⚪ Phase 2 |
| 13 | Native Apple clients + autopilot output + cloud sync + AI copilot | ⚪ Phase 1+/F |

---

## Feature matrix

### Connectivity & data-in
- 🟢 Runtime-configurable connections (add/edit/delete sources in Settings UI; engine owns + persists `~/.helm/connections.json`) — `4779073`
- 🟢 WS command-plane (conn.list/upsert/delete + ack; the bidirectional protocol native inherits) — `c092955`
- 🟢 Live position/depth/wind/AIS in (real fix overrides sim per-field; source tags truthful) — boat-verified, Vesper Cortex `:39150`
- 🟢 Multi-source drivers: **TCP-client connect-out**, TCP-server, UDP, with reconnect/backoff
- 🟢 Per-connection live status in nav frame (Connected/Connecting/No-data/Error + msg count + age)
- 🟢 NMEA 0183 over TCP/UDP (RMC/DPT/DBT/MWV/HDT) · 🟢 SignalK input (still `HELM_SIGNALK` env — fold into the connections UI)
- 🟡 NMEA 2000 (only via SignalK gateway; direct N2K-over-IP via OpenCPN `comm_drv` deferred — engine pumps no wx event loop)
- 🟡 Source-priority / filtering UI (engine has per-field freshness; no control) · 🔴 NMEA debug/monitor view
- ⚪ Internal GPS (native) · ⚪ Autopilot output (Phase 1 network / Phase 3 full) · ⚪ BLE

### Charts & display
- 🟢 Satellite + NOAA RNC raster · 🟢 True S-52 vector ENC (headless) · 🟢 Multi-cell quilting (transparent NODTA)
- 🟢 **Depth-on-satellite** (the wedge) · 🟢 Depth-area fill + contours + soundings
- 🟡 Day/Dusk/Night (UI reskins raster; true engine-side S-52 night not switched) · 🟡 Depth shading bands (no safety-depth tuning)
- 🟡 mbtiles BYO + on-demand bbox download (CLI exists; UI is a mockup — wire to real download) · ⚪ Pre-baked offline tile packs ([ADR-0008](decisions/0008-prebaked-offline-tile-packs.md))
- 🔴 S-52 display category (Base/Std/All/Mariner) · 🟡 SCAMIN/overzoom warning · 🟡 Chart-object query (only soundings tappable)
- 🔴 Course-up/head-up orientation · 🔴 Follow / center-on-ownship · 🟡 Course/heading predictor vector · ⚪ Chart groups
- 🔴 S-63 / CM93 / relief-shading / sonar bathymetry — **out of scope (not planned)**

### Routes / waypoints / marks
- 🟢 Active route nav + auto-advance + per-field math (BRG/DTW/DTG/XTE/ETA/TTG/VMG), drawn + highlighted
- 🟡 **Create routes in UI — DONE**: draw (Terra Draw) → `route.create` → engine persists via OpenCPN's `NavObj_dB::InsertRoute` (reused, in-core) to **navobj.db** (SQLite, not XML — Gemini's critique was outdated), swaps the active route, streams the geometry back, survives restart (startup reads the same navobj schema directly). *Next:* waypoint edit/move/delete, a multi-route list, activate-by-pick. Storage decision logged: reuse OpenCPN's navobj SQLite (writes via `InsertRoute`; startup read is a direct SELECT to avoid `pWayPointMan` headless).
- 🟡 GPX import/export UI round-trip (engine loads GPX; no UI round-trip) · 🟡 Great-circle vs rhumb toggle
- 🔴 Waypoint properties (arrival radius/icon/notes) · 🔴 Drop waypoint by lat/lon or range/bearing · 🔴 Auto-routing / dock-to-dock

### Tracks
- 🟢 **Track recording + display** — *always-on automatic, no on-screen control*; **distance-gated** (OpenCPN Medium: ≥4s & ≥~3.7m moved) so the anchor **swing is captured** and a dead-still boat adds nothing; engine-owned trail, map line auto-displays. Clear/pause remain on the command-plane (track.clear/track.arm) for a future Settings action — `4623f78`+
- 🟡 GPX export of the recorded track (in-memory today; export is step 10) · ⚪ Retrace-track-home (Phase A) · ⚪ Smart logbook (Phase F)

### Tools
- 🟢 Measure / range-bearing ruler (multi-segment, live HUD, undo) · 🟢 Scale bar
- 🟡 Cursor lat/lon + coord-format choice (DMS/DM.m/decimal) · 🔴 Range rings · 🔴 EBL/VRM
- 🟡 Command palette ⌘K (chrome only, unwired) · 🟡 Units selection UI (fixed NM/kn) · 🔴 Split-screen

### Safety & alarms
- 🟢 AIS targets + **OpenCPN-class tap card** (`ais-meta.js` + `aisPopupHTML`): @-stripped name, flag-from-MMSI, ship type, nav-status badge, 3-tier CPA/TCPA risk block, voyage (dest/ETA), size, ROT, "last heard / LOST". **Engine end DONE** — `helm_server.cpp` `AisRow` now forwards `navStatus/shipType/callsign/destination/eta/length/beam/draught/rot/imo` straight out of OpenCPN's already-decoded `AisTargetData` (+ `ais_trim` strips `@`-padding at source). Boat-verified live: e.g. *TWICE 🇩🇪 Class B · Sailing · Call DF7159 · 15×5 m*. Class-A-only fields (navStatus/dest/ETA/draught) correctly empty in a Class-B anchorage.
- 🟢 CPA/TCPA + collision alarm + COLREGs maneuver (boat-verified, real alarm fired)
- 🟢 Depth/shallow (REAL-source guarded — never alarms on the simulated fill) / off-course (XTE) / arrival alarms — wired off the nav frame · 🔴 AIS guard zone still to do
- 🟢 Anchor watch + drag alarm (on-screen, debounced, settable radius — `alarms.js`) · ⚪ remote/off-boat drag alert — Phase 2 core
- ⚪ MOB mark + go-to + drift estimate · 🔴 AIS guard zone (PRD Phase 1) · 🔴 AIS target list (table)
- 🔴 AIS symbology set (Class A/B, ATON, base station, SART/MOB, lost-target) · 🟡 SART/DSC reception (decoded, not surfaced)
- 🟡 Suppress moored/slow (engine flag, no UI) · 🟡 No-fix alarm (badge, not audible) · ⚪ Safety-contour check · 🔴 Internet AIS

### Weather
- 🟢 Full scalar stack (wind/gust/rain/temp/SST/cloud/pressure/CAPE/waves/swell/current), offline (Open-Meteo)
- 🟢 Animated wind particles · 🟢 Forecast scrubber + play · 🟢 Radar overlay · 🟢 Weather-along-route ribbon
- 🟢 **Isobars** — re-enabled smooth & Windy-style (`isobars.js`): bilinear-UPSAMPLE + blur the coarse field → marching-squares → Chaikin curves, adaptive hPa interval, re-contoured per scrubber frame; shows on the Pressure layer · ⚪ GRIB/PredictWind import (Phase 2) · ⚪ Windy tab (Phase 3, conditional)

### Routing (weather/passage)
- ⚪ Isochrone router + polars editor (Phase 2) · ⚪ Routing on free NOAA GRIB · 🔴 Laylines · 🔴 True-wind (TWA/TWD)
- ⚪ Departure advisor (Phase D) · ⚪ Tidal-gate / tide-aware ETA (Phase 2)

### Tides & currents
- ⚪ Harmonic tide prediction + stations (OpenCPN tcmgr.cpp gui→core; PRD Phase 1) · ⚪ Time-animated current arrows (Phase 2)

### Places / community
- 🟢 OSM/OpenSeaMap places overlay (anchorages/marinas/fuel/services), offline-cached
- ⚪ Rich place cards (Phase E) · ⚪ NoForeignLand push (Phase 2; `nflPush()` wired to backend, off-by-default)
- ⚪ Fleet opt-in / scoped position sharing (Phase E, privacy-by-default) · ⚪ Helm pins & reviews backend (Phase E)

### AI / spacetime
- 🟡 Spacetime probe (tap point+time → source-tagged slice; FastAPI backend merged; prose stubbed)
- ⚪ NL command & search (real ⌘K) · ⚪ Passage briefing / watchkeeper (advisory-only) · ⚪ Explain-this · ⚪ Smart logbook

### Offline
- 🟢 Weather stack offline · 🟢 Places cached · 🟡 On-demand mbtiles caching (CLI; UI mockup) · ⚪ Pre-baked tile packs (ADR-0008)
- 🟡 Offline-first as safety (UI never touches internet at sea; community/AI must degrade gracefully)

### Native clients (all ⚪ until the web contract is locked + boat-tested — Steve's rule)
- 🟡 Shared C++ nav core compiled headless (proven) — Apple-target compile is Phase 0/1
- ⚪ macOS SwiftUI/AppKit · ⚪ iPadOS SwiftUI/Metal · ⚪ iOS one-handed · ⚪ Smart Board dashboard (Phase B)
- ⚪ Glance surfaces (Watch / widgets / Live Activity / CarPlay) · 🟡 Settings/theme/board persistence (connections persist; rest = Phase A)

---

## Don't-lose-these — gaps surfaced from COMPETITIVE / OPENCPN-REUSE (beyond the basic-chartplotter matrix)

These are real features competitors ship or OpenCPN parity demands, easy to forget because no code exists yet:

- **Anchor watch + remote/off-boat drag alert** — category's #1 safety feature (Aqua Map AnchorLink, Orca Guard, B&G/Raymarine). Modern bar is *remote* push, not just on-screen.
- **Tides & currents** — whole subsystem absent; gates tidal-gate routing. Needs tcmgr.cpp relocation.
- **Weather routing (isochrone + polars)** — a defining competitive axis (Orca, Savvy Navvy, PredictWind). Distinct from the weather *display* stack already shipped.
- **Dock-to-dock / point-to-point auto-routing** — "Google Maps for boats" (Savvy Navvy's signature); depth/hazard-aware = Vision Phase A.
- **Configurable dashboard / Smart Board** — fixed instrument bar today; composable gauges core to the business model.
- **Autopilot output** (steer-to-waypoint; net on iOS, serial on macOS; Watch control) — OpenCPN parity; the command-plane is the natural rail.
- **Chart groups / region sets** · **Cloud sync of routes/marks** (monetization engine) · **Plugin SDK** (radar_pi/climatology/oTCurrent).
- **MOB drift estimate** (project search area from set/drift) · **Apple Watch app + CarPlay** (open lane — only Orca has Watch).
- **AI copilot / passage briefings / watchkeeper narration** — a whole product pillar + revenue driver; spacetime probe is the only partial piece.

---

## Caveats (known, honest)

1. **Sim falls back to a DEMO origin, per field.** When a field's real feed is stale the nav frame emits the
   *simulated* value tagged `src:"simulated"` (truthful), and the simulated **position interpolates along the
   built-in Key West demo route** (`gLat/gLon` init to `ROUTE[0]`). Consequences: (a) before any real fix, a new/offshore
   user sees the boat at the *demo* coordinates, not their location; (b) freshness is per-field, so you can get real
   SOG/depth while position still reads simulated (a half-real ownship). Source tags are honest, but **the UI must make
   the simulated-position state unmistakable** and ideally suppress the demo origin until a first real fix or geolocation.
   *To test moving-boat features honestly while stationary at anchor, replay a recorded NMEA log
   (`nc 127.0.0.1 10110 < passage.nmea`) rather than relying on a zero-SOG fix.*
2. **~~"Share my track" checkbox~~ — FIXED (`4623f78`).** It was a one-shot *position* push to NoForeignLand mislabeled
   as track sharing. Relabeled **"Share my position"** (off-by-default, backend-mediated); **real track recording is now
   the REC control.** Remaining honesty item: NFL push is Phase 2 — keep it off-by-default, scoped, revocable before it
   ships in front of users.
