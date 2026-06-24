# Helm — Client Feature Audit

**Status:** v1 · 2026-06-24 · branch `claude/opencpn-client-audit-xg6x7x`
**Scope:** A complete, feature-by-feature audit of the Helm client (`web/` + the `engine/`
it talks to), benchmarked against **OpenCPN** (the app Helm succeeds), professional **MFD
chartplotters** (Garmin GPSMAP, Raymarine Axiom, B&G/Simrad, Furuno), and **iOS marine
apps** (Aqua Map, Navionics Boating, iNavX, qtVlm, TimeZero, Savvy Navvy, Orca, SEAiq).
**Goal:** make sure nothing is forgotten before we commit to the native build.

> Method: code read of `web/index.html`, `web/style.json`, `web/nav-source.js`, the JS
> overlay modules, and the C++ engine (`engine/vendor/cli/helm_engine.cpp`,
> `helm_tiles.cpp`); competitor feature sets gathered from manufacturer docs, manuals,
> Panbo/Practical-Sailor reviews, and the OpenCPN manual + plugin catalog.

---

## 0. Legend

| Mark | Meaning |
|---|---|
| ✅ | Built **and wired** end-to-end (engine → UI, or self-contained in UI) |
| ◐ | Partial / prototype / present but shallow |
| ⚠ | **Present but wired to FAKE or static data** — looks real, isn't live |
| ⬜ | Missing — **on the roadmap** (phase noted) |
| ✖ | Missing — **not currently planned** (decide: build or consciously skip) |
| N/A | Out of scope for a tablet/phone app (hardware-class feature) |

"TS" = table-stakes (essentially every competitor has it). "Diff" = differentiator.

---

## 1. Executive summary

**The architecture is sound and the hard parts are genuinely proven.** OpenCPN's `model/`
nav core runs headless and streams real `Routeman` navigation over a WebSocket; the S-52
ENC renderer produces real chart tiles over HTTP. Those are the two things everyone said
were hard, and they work.

**But there is a seam where the engine and the UI do not meet.** The engine already
computes more than the client displays, and several flagship interactions are either
missing or wired to placeholder data. The "beautiful client" today is a well-built *shell*
over a mostly-real *engine*, with key connecting wires unrun.

**The five findings that matter most:**

1. **✅ Live AIS — WIRED (2026-06-24).** *Was: the engine drove OpenCPN's real `AisDecoder`
   and streamed full per-target range/bearing/CPA/TCPA/heading/class/MMSI, but the UI read a
   static `data/ais-sample.geojson` and the popup showed only name/SOG/COG/CPA — TCPA
   discarded.* Now `applyNav()` drives the `ais` map source from the engine's `ais[]` array,
   and the tap inspector renders the full detail — **name · class · MMSI · SOG · COG · HDG ·
   range · bearing · CPA · TCPA**, with a "⚠ Close approach" flag (CPA < 2 NM, TCPA 0–30
   min). The static sample still shows in sim mode (no engine). See `web/index.html`
   (`updateAisFromEngine` + `aisPopupHTML`).

2. **✅ Measure / range-bearing ("draw distance") tool — BUILT (2026-06-24).** *Was: no
   ruler anywhere.* Now `web/measure.js` adds a click-to-drop ruler (Mapbox-idiom mechanics
   + Apple-idiom glass HUD): per-leg **range + bearing °T** labels, a live rubber-band to the
   cursor, cumulative total in the HUD, ⌫ undo, double-click/Esc to finish. Toggled from the
   left rail; great-circle math agrees with the engine's BRG/DTW.

3. **✅ Live route line — WIRED (2026-06-24).** *Was: the magenta route read from a static
   `data/route.geojson`, so a different loaded GPX left the chart disagreeing with the
   instruments.* The engine now streams the model route's geometry (`route` in the nav frame:
   coords + `activeLeg`); the UI draws the line from it and highlights the active leg. Sim
   mode keeps the static file. See `helm_engine.cpp` + `updateRouteFromEngine` in `web/index.html`.

4. **◐ Alarms — CPA collision alarm now wired (2026-06-24); others still pending.** The AIS
   **CPA/TCPA collision alarm** is built (`web/collision.js`): it flags the most threatening
   target, highlights it on the chart (intercept line + pulsing ring), classifies the
   encounter against the **COLREGs** and states give-way/stand-on + the prescribed maneuver,
   with a permanent "you are responsible" disclaimer. Still missing (Phase 2): anchor watch,
   arrival, off-course, depth alarms — the `collision.js` banner/audio channel is the reusable
   seam for them.

5. **◐ Multi-cell S-52 tiler — UPGRADED (2026-06-24); full quilting next.** *Was: one
   hard-coded cell (`US5FL96M`).* `helm_tiles.cpp` now loads a **folder of ENC cells** and picks
   the **zoom-appropriate** covering cell per tile (overview→harbour as you zoom) — the
   tile-layer analogue of OpenCPN's quilt reference-chart pick, headless. Still to do: per-tile
   *compositing* (finer-on-coarser, NODTA→transparent) for seamless cross-cell quilting, and
   chart groups. See [CHART-QUILTING.md](CHART-QUILTING.md) — incl. where OpenCPN's quilt code
   falls short vs ours.

Everything else below is catalogued so we can decide build-vs-skip deliberately rather than
discover a hole at sea.

---

## 2. What Helm has today (precise inventory)

### Engine (`engine/vendor/cli/helm_engine.cpp`, `helm_tiles.cpp`)
- ✅ OpenCPN `Routeman` headless: `ActivateRoute`, `ActivateNextPoint` auto-advance, active waypoint.
- ✅ Per-fix nav math: BRG, DTW, DTG, XTE, ETA, TTG, VMG (the `UpdateProgress` relocation).
- ✅ GPX route load (pugixml); falls back to a built-in Key West sample.
- ✅ Real position-in: **NMEA 0183 over TCP 10110** (RMC/DPT/DBT/MWV/HDT, checksum-validated) **and SignalK** client (position, SOG, COG-true, HDG-true, depth, apparent wind).
- ✅ Per-field source truth (`nmea` / `signalk` / `simulated`) — never badges sim as real.
- ✅ **AIS: OpenCPN `AisDecoder` headless** — decode + multipart reassembly + **CPA/TCPA/range/bearing**, class, name; ages targets out >10 min; streams as `"ais":[…]` in the nav frame.
- ✅ S-52 ENC → PNG tiles over HTTP 8082 (`RenderRegionViewOnDC`), fail-closed on bad scale, transparent no-coverage tiles.

### UI (`web/index.html` + `style.json` + modules)
- ✅ MapLibre map; Day/Dusk/Night raster reskin; draggable route inspector; instrument bar.
- ✅ Live nav over `ws://127.0.0.1:8081` with honest sim fallback + LIVE/SIM/ENGINE-LOST badge.
- ✅ Own-ship marker (position + COG rotation) driven by the live feed.
- ✅ Layer toggles: satellite (Sentinel-2), NOAA raster, S-52 engine tiles, depth areas, soundings, route, places, AIS.
- ✅ Weather overlays via Open-Meteo: wind/gust/rain/radar/temp/SST/cloud/waves/swell/pressure/CAPE/current, animated particles, opacity, forecast scrubber + play (`field-layer.js`, `wind-layer.js`, `radar.js`, `isolines.js`).
- ◐ Click popups for **soundings, places, AIS** (AIS popup is shallow + fed by the static sample).
- ◐ Rail nav (chart/layers/weather/routes/ais/places/download/settings); download + settings drawers are **mockups**.
- ⚠ Search box + ⌘K command palette — **visual only, no handler**.

---

## 3. The wiring gaps (engine has it, UI ignores it)

| What the engine produces | Where | What the UI does with it |
|---|---|---|
| `ais[]` with range/brg/**CPA/TCPA**/hdg/class/mmsi/name | `helm_engine.cpp:513-537` | ✅ **wired** — drives the `ais` source + rich tap popup (`web/index.html`) |
| Loaded GPX route geometry | `helm_engine.cpp` (Routeman) | ✅ **wired** — `route`{coords,activeLeg} drives the line + active-leg highlight |
| Dangerous-target CPA flag (`g_CPAWarn_NM=2.0`) | engine AIS state | ✅ **wired** — CPA alarm + COLREGs guidance (`web/collision.js`) |
| Per-field `sources` (nmea/signalk/sim) | nav frame | ✅ shown as tooltip + badge (good) |
| Active waypoint name/brg, DTW, nextWp | nav frame | ✅ inspector + instrument bar (good) |

**All three wires are now closed** (AIS, CPA alarm, and live route geometry — 2026-06-24).
The route line required a few lines of engine JSON (the model route's coords + active leg) in
addition to the UI work.

---

## 4. Feature-by-feature capability matrix

Benchmarked against OpenCPN (OCPN), pro MFDs, and iOS apps. Status is **Helm's**.

### 4.1 Charts & cartography

| Feature | TS/Diff | Helm | Notes / where |
|---|---|---|---|
| Raster basemap (satellite) | TS | ✅ | Sentinel-2 via MapLibre |
| NOAA raster charts (RNC) | TS | ✅ | tile source |
| True S-52 vector ENC (S-57) | TS | ✅ | **multi-cell**, zoom-aware cell selection (`helm_tiles.cpp`) |
| **Chart quilting** (seamless multi-cell) | TS | ◐ | per-tile cell **selection** done; cross-cell **compositing** next ([CHART-QUILTING.md](CHART-QUILTING.md)) |
| **Chart groups** (region sets) | TS | ⬜ | OCPN core; Phase 2 |
| S-63 encrypted ENC | TS(offshore) | ✖ | OCPN via plugin; licensing-gated |
| CM93 worldwide vector | Diff | ✖ | OCPN core; not planned v1 |
| mbtiles (BYO charts) | Diff | ⬜ | PRD "bring-your-own"; Phase 1 |
| Day / Dusk / Night palettes | TS | ◐ | UI reskins raster; **true S-52 night palette** not switched engine-side |
| Depth-area fill + contours + soundings | TS | ✅ | `depare`/`depcnt`/`soundg` layers |
| Depth shading bands (safety/shallow/deep) | TS | ◐ | static fill ramp; no user safety-depth control |
| **Depth-on-satellite** (ENC depth over imagery) | **Diff★** | ⬜ | the headline differentiator; NODTA→transparent still pending (`engine/README`) |
| S-52 display category (Base/Std/All/Mariner) | TS | ✖ | OCPN core; not yet |
| SCAMIN / overzoom indication | TS | ◐ | engine honors SCAMIN; UI has no scale warning |
| Chart-object query (tap any S-57 object) | TS | ✖ | OCPN core; only soundings tappable now |
| On-demand chart download (lasso bbox) | **Diff★** | ⚠ | drawer is a **mockup**; pipeline exists CLI-side |
| Relief shading / 3D / Mariner's-Eye | Diff | ✖ | MFD premium; not a Helm goal |
| Quickdraw/SonarChart user bathymetry | Diff | ✖ | needs sonar; out of scope |

### 4.2 Navigation & routing

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| Active route nav + auto-advance | TS | ✅ | real Routeman |
| XTE / BRG / DTW / DTG / ETA / TTG / VMG | TS | ✅ | engine-computed, shown |
| Great-circle vs rhumb | TS | ◐ | GC used; no toggle |
| Route line drawn on chart | TS | ✅ | engine streams route coords + active leg; UI draws + highlights |
| Create / edit / delete routes & marks in UI | TS | ⬜ | read-only today; Phase 2 (editing) |
| Waypoint properties (arrival radius, icon, notes) | TS | ✖ | not in UI |
| GPX import/export (UI) | TS | ◐ | engine loads GPX; **no UI import/export** |
| Tracks (record + display) | TS | ⬜ | OCPN `ActiveTrack`; Phase 2 |
| Auto-routing / dock-to-dock | Diff | ✖ | MFD/Navionics/Savvy; not planned (liability) |
| **Weather routing (isochrones + polars)** | Diff | ⬜ | PRD Phase 2; own isochrone router |
| Laylines (sailing) | Diff | ✖ | B&G signature; consider for sailing credibility |
| North/Course/Head-up orientation | TS | ✖ | **only north-up**; MFDs + OCPN have all three |
| Course/heading predictor vector | TS | ◐ | own-ship rotates to COG; no predictor line |
| Follow / center-on-ownship mode | TS | ✖ | map doesn't auto-follow the boat |
| Send-to-GPS / receive | TS(OCPN) | ✖ | niche; skip |

### 4.3 AIS & collision avoidance

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| AIS target display on chart | TS | ✅ | live `ais[]` stream drives the map (sample only in sim mode) |
| Target details on tap | TS | ✅ | name/class/MMSI/SOG/COG/HDG/range/brg/CPA/**TCPA** |
| **CPA / TCPA computation** | TS | ✅ | engine computes; **UI now shows both** + close-approach flag |
| CPA collision **alarm** + dangerous-target flag | TS | ✅ | `web/collision.js` — banner + chart highlight + COLREGs action |
| Guard zone / proximity | TS | ✖ | OCPN Watchdog; not yet |
| COG/heading vector on targets | TS | ◐ | triangle rotates to COG; no speed-scaled vector |
| AIS target list (sortable table) | TS | ✖ | OCPN core; not in UI |
| Suppress moored/slow targets | TS | ◐ | engine has `g_ShowMoored_Kts`; no UI control |
| AIS-SART / MOB / DSC reception | TS | ◐ | decoder supports class; not surfaced in UI |
| Buddy / named MMSI | Diff | ✖ | OCPN; nice-to-have |
| Class B / ATON / base-station symbols | TS | ✖ | single triangle symbol today |
| AIS via internet (AISHub/MarineTraffic) | Diff | ✖ | iOS-app pattern; engine path is NMEA/SignalK |

### 4.4 Instruments & sailing data

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| SOG / COG / HDG / depth / position | TS | ✅ | instrument bar |
| Apparent + **true** wind (speed/angle/dir) | TS | ◐ | shows wind spd/dir; **apparent only**, no TWA/TWD derivation |
| STW / water temp / baro / heel / trim | TS | ✖ | not ingested/shown |
| Engine data (RPM/fuel/tanks via N2K) | TS | ✖ | OCPN engine dash; not planned v1 |
| Configurable dashboards/gauges | TS | ✖ | fixed instrument bar only |
| **Polars / target boat speed / performance %** | Diff | ✖ | B&G H5000 turf; ties to weather routing (Phase 2) |
| SailSteer-style tactical page | Diff | ✖ | sailing differentiator; consider |
| Start-line / race timer | Diff | ✖ | racing; likely skip |
| Sun/moon, sunrise/sunset | TS(OCPN) | ✖ | easy add |

### 4.5 Weather

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| Wind/gust/rain/temp/SST/cloud/pressure/CAPE | TS | ✅ | Open-Meteo, our own render |
| Waves / swell / current layers | TS | ✅ | vector layers |
| Animated wind particles | Diff | ✅ | WebGL `wind-layer.js` |
| Forecast time scrubber + play | TS | ✅ | when `forecast.json` present |
| Radar (precip) overlay | TS | ✅ | `radar.js` |
| Isobars / pressure isolines | TS | ◐ | code exists; **disabled** (jagged coarse grid) |
| **GRIB file import (BYO)** | TS | ✖ | OCPN core; PRD says own-GRIB engine — no user import yet |
| PredictWind GPX/GRIB import | Diff | ⬜ | PRD Phase 2 |
| Windy tab (conditional) | Diff | ⬜ | Phase 3, only if cleared |

### 4.6 Tides & currents

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| Harmonic tide prediction + stations | TS | ⬜ | OCPN `tcmgr` (gui→core relocation); Phase 2 |
| Tidal current arrows (time-animated) | TS | ⬜ | Phase 2 |
| Tide-aware route ETA | Diff | ✖ | OCPN route planner; later |

### 4.7 Alarms & safety

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| **Anchor watch / drag alarm** | TS | ⬜ | PRD Phase 2; every competitor has it (Aqua Map's flagship) |
| AIS CPA collision alarm | TS | ✅ | `web/collision.js` — most-threatening target, give-way/stand-on + maneuver |
| Arrival alarm | TS | ✖ | trivial given DTW |
| Off-course (XTE) alarm | TS | ✖ | trivial given XTE |
| Depth / shallow-water alarm | TS | ✖ | given live depth |
| MOB (man-overboard mark + go-to) | TS | ⬜ | PRD Phase 2 |
| Guard zone / boundary alarm | TS | ✖ | OCPN Watchdog |
| Data-lost / no-fix alarm | TS | ◐ | "ENGINE LOST" badge exists; not an audible alarm |

### 4.8 Measurement & utility tools

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| **Measure / range-bearing ruler** | TS | ✅ | `web/measure.js` — per-leg range + bearing °T, live HUD |
| Multi-segment cumulative measure | TS | ✅ | cumulative total in the HUD |
| Range rings (ownship / waypoint) | TS | ✖ | OCPN + every MFD |
| EBL / VRM | TS(MFD) | ✖ | electronic bearing line / variable range marker |
| Drop waypoint by lat/lon or range/bearing | TS | ✖ | — |
| Cursor lat/lon + range/brg readout | TS | ◐ | MapLibre scale bar only; no cursor pick |
| Scale bar | TS | ✅ | `ScaleControl` |

### 4.9 Connectivity & ecosystem

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| SignalK input | TS | ✅ | engine client |
| NMEA 0183 over TCP/UDP | TS | ✅ | engine listener (RMC/DPT/DBT/MWV/HDT) |
| NMEA 2000 (gateway) | TS | ◐ | via SignalK; not direct |
| Internal GPS | TS(iOS) | ⬜ | native app; browser geolocation possible |
| Autopilot output | TS | ⬜ | OCPN `autopilot_output`; Phase 3 |
| Source priority / multiplexer / filtering | TS | ◐ | engine has per-field freshness override; no UI config |
| Cloud sync (routes/marks) | Diff | ⬜ | ARCHITECTURE notes CloudKit; later |
| Apple Watch / CarPlay | Diff | ✖ | native-app era; note for later |
| Data monitor / NMEA debug view | TS(OCPN) | ✖ | dev aid; nice-to-have |

### 4.10 UI / UX conventions

| Feature | TS/Diff | Helm | Notes |
|---|---|---|---|
| Day / Dusk / Night | TS | ✅ | first-class toggle |
| Glass chrome / chart-first | Diff | ✅ | strong, matches mockups |
| Command palette (⌘K) + search | Diff | ⚠ | **visual only** |
| Split-screen / dual chart | TS(MFD) | ✖ | desktop later |
| Units selection (NM/kn/m/ft/fathom) | TS | ◐ | fixed NM/kn; settings drawer is mockup |
| Touch gestures / one-handed iOS view | TS | ⬜ | native app |
| Follow-mode / quick "center on boat" | TS | ✖ | see 4.2 |

### 4.11 Helm's own differentiators (the reason it exists)

| Feature | Helm | Notes |
|---|---|---|
| **One fused screen** (charts+sat+weather+AIS+route+instruments) | ✅ | the wedge — present and good |
| **Depth-on-satellite** | ⬜ | NODTA→transparent compositing still pending — **build this; it's the moat** |
| **On-demand multi-source chart download** | ⚠ | mockup UI; CLI pipeline exists |
| **Own full weather stack, offline** | ✅ | Open-Meteo render, our own layers |
| **True BYO / no subscription lock-in** | ⬜ | mbtiles import; Phase 1 |
| Places overlay (OSM/OpenSeaMap) | ✅ | wired |
| NoForeignLand push | ⬜ | Phase 2 |

---

## 5. What the competition has that we should consciously decide on

Grouped by "did we forget this?" — the answer for each should be *build*, *defer*, or
*deliberately skip*, not *oops*.

**Almost certainly build (table-stakes everywhere, cheap given what we have):**
- Measure/ruler tool · live AIS wiring + rich popup with TCPA · live route line · anchor
  watch · AIS CPA alarm · arrival/off-course/depth alarms · MOB · range rings ·
  follow-mode · course-up/head-up · UI GPX import/export · true-wind derivation ·
  cursor lat/lon + range/brg readout · functional ⌘K/search.

**Build because it's our moat (differentiators):**
- Depth-on-satellite compositing · real on-demand chart download · weather routing
  (isochrones + polars) · BYO mbtiles import.

**Defer (Phase 2/3, correctly):**
- Chart quilting + chart groups · multi-cell S-52 · tides & currents · tracks display ·
  route/waypoint editing · PredictWind import · autopilot output · cloud sync · Windy tab.

**Sailing credibility (decide — Helm targets cruisers/sailors):**
- Laylines · polars/target-speed · SailSteer-style tactical page. At least laylines +
  polars pair naturally with the planned weather router.

**Deliberately skip (out of scope or liability/hardware):**
- Sonar/fishfinder, live sonar (LiveScope/ActiveTarget), radar hardware overlay,
  Quickdraw/SonarChart user bathymetry, S-63 encrypted charts, auto-routing/dock-to-dock,
  SiriusXM weather, engine-room N2K dashboards, race start-line timers, send-to-GPS.
  (Radar *precip* overlay we already have via Open-Meteo; radar *hardware* is N/A.)

---

## 6. Recommended build order (client-facing, value-first)

1. ~~**Live AIS end-to-end**~~ — ✅ **DONE (2026-06-24).** Consumes `s.ais`, drives the `ais`
   GeoJSON source, rich tap popup (name/MMSI/class/range/brg/CPA/**TCPA**/SOG/COG/HDG) +
   close-approach flag. CPA color rule in `style.json` already applies. (named feature #2, real)
2. ~~**Measure / range-bearing tool**~~ — ✅ **DONE (2026-06-24).** `web/measure.js`:
   click-to-drop ruler, per-leg range + bearing °T, live rubber-band, cumulative HUD,
   undo/Esc. *(named feature #1, delivered)*
3. ~~**AIS CPA alarm + dangerous-target surfacing**~~ — ✅ **DONE (2026-06-24).** `web/collision.js`:
   flags the worst target, chart intercept-line + pulsing ring, COLREGs give-way/stand-on +
   maneuver, one-shot audible alert, mute/ack. The banner/audio channel is reusable for
   anchor/arrival/depth alarms.
4. ~~**Live route line**~~ — ✅ **DONE (2026-06-24).** Engine emits the model route's coords +
   active leg in the nav frame; UI draws from it and highlights the active leg, so chart and
   inspector agree.
5. **Anchor watch** — set point + radius, drag alarm; the most-used safety feature in the
   whole category (it's Aqua Map's flagship).
6. **Follow-mode + course-up**, **cursor readout + range rings**, **true-wind**, **UI GPX
   import/export** — the cluster of small table-stakes that make it feel like a chartplotter.
7. **Depth-on-satellite** (engine NODTA→transparent) — the differentiator; start once the
   table-stakes loop feels right.

Items 1–4 are JS plus a few lines of engine JSON; no new C++ subsystems. They convert the
shell into a real, trustworthy chartplotter face and deliver both features the audit was
asked to verify.

---

## 7. Out-of-scope confirmations (so they're on record, not forgotten)

- **Sonar / radar hardware**: N/A for a tablet/phone app. (We render *weather* radar/precip,
  not marine radar returns.)
- **iOS serial/USB NMEA**: impossible per platform; connectivity is SignalK/NMEA-over-IP/BLE/
  internal GPS (already the engine's design).
- **Encrypted/commercial charts (S-63, Navionics, C-MAP)**: licensing-gated; BYO/partnership
  only — see `docs/LEGAL.md`.
- **Auto-routing / dock-to-dock**: deliberately not built (liability + it's the incumbents'
  moat) — see `docs/COMPETITIVE.md`.

---

*Cross-references: `PRD.md` §6 (feature requirements), `docs/OPENCPN-REUSE.md` (reuse map),
`docs/ROADMAP.md` (phasing), `docs/COMPETITIVE.md` (positioning), `engine/README.md`
(engine state + next increments).*

---

## 8. Competitor feature reference (iOS apps + pro MFDs)

Benchmarked Helm feature-by-feature against the current (2024–2026) field so nothing is
forgotten. Each capsule: platform · core strength · **what Helm must match** / **can
leapfrog**. (Sources: manufacturer docs, manuals, Panbo/Practical-Sailor reviews, App
Store listings — gathered for this audit.)

### 8.1 iOS / cross-platform apps (Helm's true peer group)

| App | Platforms | Core strength | Helm gap to match | Where Helm wins |
|---|---|---|---|---|
| **Aqua Map** | iOS/iPad/Mac/Android | Best-in-class **anchor alarm** (off-boat mirroring + email/Telegram), weekly **USACE bathymetry**, hybrid auto/manual routing, one-time chart pricing, ActiveCaptain+Waterway Guide | anchor watch, ruler (has it), AIS CPA/TCPA (has it), tide/current | fused weather stack, depth-on-satellite, own GRIB |
| **Navionics Boating** | iOS/iPad/Android | The **chart-data moat** (SonarChart HD, daily updates), Auto Guidance+, 1M+ ActiveCaptain POIs, Plotter Sync | nothing critical (their AIS CPA/TCPA is historically *weak* — a Helm opening) | offline-everything, no chart-subscription lock-in, real AIS CPA/TCPA, fusion |
| **iNavX** | iOS/iPad/Mac/Android | **BYO multi-provider charts** (Navionics/NV/CHS/Explorer/Imray), deep NMEA-over-WiFi, **autopilot output**, **internet AIS "AIS Live"**, GRIB w/ animation | internet-AIS option, autopilot output, GPX UI round-trip | modern UX, fusion, own weather, depth-on-sat |
| **qtVlm** | Win/Mac/Linux/Pi/iOS/Android | **Best free isochrone weather routing** (pivots, multi-routing, 250+ polars, wave/current-aware), start-line mode, anchor alarm free | weather routing + polars (our Phase 2), laylines | modern UX, charts, fusion, satellite |
| **TimeZero / TZ iBoat** | iOS/iPad (+Furuno MFD) | **TZ Maps + PhotoFusion** (satellite-fused charts), TZ Online AIS, Furuno-ecosystem cloud sync, ruler w/ TTG | PhotoFusion ≈ our depth-on-sat (validate ours), internet AIS, cloud sync | own weather stack, no-subscription posture, true depth-on-sat |
| **Savvy Navvy** | iOS/iPad/Android/web | "Google-Maps-for-boats" **auto-routing** w/ wind/tide/current, clean UX | (auto-routing is deliberately out of scope for us) | offline-everything, BYO, OpenCPN-grade nav core, fusion |
| **Orca** | iOS/iPad/Mac/Watch/Android (+ own hardware) | **The real threat**: own fast vector charts (no per-region fee), **satellite "Hybrid" charts**, sail/isochrone routing (8000 polars, ECMWF), **MarineTraffic internet AIS**, **Apple Watch autopilot**, Guard Mode anchor, cloud sync, autopilot for all major brands | satellite-hybrid (≈ depth-on-sat), internet AIS, Guard-Mode-style anchor, cloud sync, **Apple Watch** | depth-on-**sat** w/ ENC soundings, full Windy-class weather catalog, true BYO/offline, OpenCPN power |
| **C-MAP (Boating/Embark)** | iOS/iPad/Android/web | Cheap Premium (~$15/yr), HRB + Custom Depth Shading + REVEAL satellite, Autorouting, **internet AIS (C-MAP Traffic)**, free Navico Plotter Sync | (no NMEA-in, no CPA/TCPA — a Helm opening) | instrument integration, AIS CPA/TCPA, fusion |
| **Weather4D R&N** | iOS/iPad/Mac | ~60 GRIB models (ECMWF/ARPEGE/AROME/ICON + HYCOM/Copernicus currents), isochrone routing w/ CSV polars + multi-sail-set, tidal-stream "5th dimension", MOB drift estimate | model breadth, **MOB drift estimate**, tidal streams | own composited overlay (theirs is raster-chart-bound), modern UX |
| **SEAiq** | iOS/iPad | Pro/official ENC focus, NMEA instruments, true-wind/VMG | (niche pro overlap) | UX, weather, fusion |

**Cross-app pattern that matters for Helm:** the modern threats (Orca, TimeZero) win on
**satellite-fused charts** — exactly Helm's depth-on-satellite differentiator, *if we ship
it*. Several apps add **internet AIS** (MarineTraffic/AISHub/own network) so targets show
with **no hardware** — a cheap, high-visibility feature our NMEA/SignalK-only engine could
add as an option. And **Apple Watch** + **cloud sync** are now common; note for the native
era.

### 8.2 Professional MFD chartplotters (the capability ceiling)

| System | Sailing-relevant strengths | Helm parity status |
|---|---|---|
| **Garmin GPSMAP** | Auto Guidance+, Quickdraw user bathymetry, **SailAssist** (laylines, polars, **Race Start Guidance**, enhanced wind rose, set/drift), ActiveCaptain ecosystem, full alarm suite, MOB, measure + range/bearing projection | Helm matches core nav; lacks laylines/polars (Phase 2), alarms, MOB, measure, range rings |
| **Raymarine Axiom / LightHouse** | **Anchor mode** (GNSS swing+drag circles, chain/depth tuning), **dynamic polar laylines** (500+ polars), SmartStart, **AIS intercept graphics** (graphic CPA), dangerous-target alarm (AIS+radar), ClearCruise AR, point-to-point + vessel-to-point rulers, VRM/EBL | model for our **AIS CPA graphics** + **anchor mode**; lacks laylines/polars, alarms, rulers |
| **B&G Zeus/Vulcan (+H5000)** | **The sailing reference**: SailSteer, **tide+shift-corrected laylines**, SailingTime, RacePanel/StartLine (time-to-burn, Zero Burn Line), Advanced WindPlot, "What If?", polars/targets, PredictWind routing + Departure Planner | the bar for serious **sailing tactics** — laylines/polars/wind-shift are the credibility gap to close if we court racers |
| **Furuno NavNet TZtouch3/XL** | **Risk Visualizer** (360° collision vs plain CPA/TCPA), AI Avoidance Route, BathyVision + PhotoFusion charts, free worldwide NavCenter GRIB; **weak on sailing** | charts/weather parallels; Risk-Visualizer-style 360° collision is an idea beyond plain CPA/TCPA |

**MFD takeaways for Helm:** (1) **Anchor mode** with a drawn swing/drag circle is universal
and expected — build it properly, not just a radius alarm. (2) **Dangerous-target alarm**
spanning a *safe distance + time-to-reach* (CPA/TCPA) is table-stakes — our engine already
computes the inputs. (3) **Graphic CPA** (draw the closing geometry, not just numbers) is
the premium move and a natural fit once AIS is wired. (4) **Laylines + polars** are the
sailing-credibility gap; they pair with the planned weather router. (5) Sonar/radar
hardware, SiriusXM, digital switching, engine-room N2K — correctly **out of scope**.

## 9. Research-driven additions to the gap list

Items the competitor sweep surfaced as **near-universal table-stakes that Helm lacks** and
that were thin or missing in §4 — fold these into planning:

- **Internet AIS option** (MarineTraffic/AISHub/own feed) — Orca, C-MAP, iNavX, TimeZero
  all show AIS targets with *no hardware*. Cheap, high-visibility; complements (not
  replaces) the engine's NMEA/SignalK AIS. *New consideration — not previously listed.*
- **AIS target list** (sortable by CPA/range/name) — every navigator-grade app/MFD has it.
- **AIS symbology set** — Class A vs B, ATON (real/virtual), base station, SART/MOB icons,
  lost-target cross-out. Helm draws one triangle today.
- **Drop waypoint by lat/lon and by range/bearing** — universal; Helm has neither.
- **Coordinate-format choice** (DMS / DM.m / decimal) + cursor lat-lon readout — universal.
- **Remote / off-boat anchor alerts** (Aqua Map AnchorLink, Orca Guard Mode push to phone/
  watch) — the modern anchor-watch bar is *remote notification*, not just an on-screen alarm.
- **MOB drift estimate** (Weather4D) — projects search area from set/drift; a differentiator
  beyond a plain MOB mark, and we have wind+current inputs.
- **Cloud sync of routes/marks across devices** — Garmin/Navionics/Orca/TimeZero standard;
  noted for the native era (ARCHITECTURE mentions CloudKit).
- **Apple Watch** (instruments + autopilot control) and **CarPlay** — increasingly expected;
  Orca ships Watch autopilot. Native-era note.

**Where Helm already leads the field (keep these sharp):** Day/**Dusk**/Night as a
first-class toggle (most apps only do day/night); a genuinely **fused** single screen
(no competitor composites charts+satellite+full-weather+AIS+instruments); **own** offline
Windy-class weather (not chart-bound like Navionics/C-MAP, not subscription-bound like
PredictWind); true **BYO / no chart-subscription lock-in**; and the OpenCPN `model/` nav
core under the hood (real Routeman, not a re-derived approximation).

**Open white space — features few or NO competitor does well (Helm could own these):**
- **CarPlay** — essentially *nobody* in the field ships it. Open lane.
- **First-class Apple Watch** — only Orca (instruments + autopilot); the majors (Navionics,
  Aqua Map, iNavX) have none. Native-era opening.
- **Command-palette / fast fuzzy search UX** — rare in marine software, and **Helm already
  has the ⌘K chrome built** (just unwired in `index.html`). Finishing it is a cheap,
  distinctive win, not a new feature.
- **Unified macOS + iPad + iPhone app with seamless cloud sync** — the field is fragmented
  (most apps are iOS-only or mobile-only; desktop is Windows). Helm's shared-core plan is
  exactly this positioning gap.
- **Cruiser social graph baked into a real chartplotter** — NoForeignLand owns the social
  layer but has weak charts; nobody fuses best-in-class charts + the community graph. PRD
  already scopes NFL push; pull is the harder, differentiated half.
- Minor niche ideas worth noting: **SEAiq-style docking aid** (fender distance + closing
  speed), **AIS record & playback** (SEAiq), **Risk-Visualizer-style 360° collision**
  (Furuno) beyond plain CPA/TCPA.

*Research method note: feature sets gathered via web research across manufacturer/manual/
review sources (Garmin, Raymarine, B&G/Simrad, Furuno; Aqua Map, Navionics, iNavX, qtVlm,
TimeZero, Savvy Navvy, Orca, C-MAP, Weather4D, SEAiq, NoForeignLand). Vendor sites
frequently block automated fetch, so some specifics rest on indexed search extracts
cross-checked across sources. Treat exact prices/version numbers as "as reported"; feature
presence/absence is well-corroborated.*
