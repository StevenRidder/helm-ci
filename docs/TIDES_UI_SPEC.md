# Tides — UI polish + chartplotter integration (internal spec)

Owner: CHART agent. Codex keeps the harmonic **engine** (TIDES-1/2/3/5);
this spec covers the **presentation layer** + the two thin **read routes** the dashboard needs.

## Why this exists
Codex's tide engine (OpenCPN TCMgr, offline, source-tagged, license-gated, regression-tested) is solid.
The prototype `web/tides.html` is honest and architecturally right but (a) is a **standalone page** outside
the chartplotter, (b) uses **its own tokens** (`--cyan:#61dcc8`/`--bg:#071014`), not ours, (c) draws a
**crude 9-point curve** (no grid / now-marker / hi-lo / datum), and (d) is bottlenecked by an API that
exposes **only `GET /tides/summary`** — so the 24 h curve is **9 serial round-trips**, each rebuilding the
engine under a global mutex.

Fix the API first (it unblocks the visuals), then rebuild the UI as a SHELL drop-in on our tokens, and put
tides **on the chart** (station markers + tap card) — the native-chartplotter pattern.

## Keep (the differentiator — do not regress)
Source/provenance ledger, the `redistribution-cleared` / `commercial-review` / `explicit-opt-in` badges,
**datum + station distance**, and honest degradation (`Unavailable` / `not applicable` / `none`). Most
consumer tide apps hide datum and provenance; surfacing them is the brand. Stays offline-only, no CDN.

---

## 1. Backend — two read routes + engine caching  (`helm_server.cpp` + `helm_tides`)

The C++ `TideEngine` is richer than the HTTP surface. Add two routes that compute under the **existing
`g_tide_mtx`** (TCMgr is process-global, non-reentrant), and **cache one loaded engine per policy** so we
stop reconstructing + re-reading harmonic files on every request.

### `GET /tides/curve?lat&lon&start&hours&step[&all=1]`
One request → the whole curve. Loops `engine.Predict(stationIndex, t)` for each sample under a single lock
and a single engine load (replaces the UI's N round-trips).
- `start` UTC ISO-8601 (default now), `hours` (default 24, cap 96), `step` minutes (default 30, min 10).
- Resolves the nearest usable **tide** station once (`PredictNearest`/`NearestTideStation`), then samples it.
- Response:
  ```json
  { "ok": true, "engine": "opencpn-tcmgr", "source_policy": "redistributable-only",
    "station": { /* same TideStation shape as /tides/summary */ },
    "datum_m": 1.01, "unit": "meters",
    "start_utc": "...Z", "step_min": 30,
    "samples": [ { "t_utc": "...Z", "value_m": 0.55 }, ... ],
    "events": [ { "kind": "high_water", "event_utc": "...Z", "value_m": 1.33 },
                { "kind": "low_water",  "event_utc": "...Z", "value_m": 0.21 } ] }
  ```
  `events` = the high/low extrema **inside the window** (walk `NextHighLowEvent` from `start` to `start+hours`)
  so the UI can mark them on the curve. Errors in-body (`ok:false`), HTTP 200, `Cache-Control: no-store`.

### `GET /tides/stations?bbox=w,s,e,n[&limit=200][&all=1]`
Enumerate stations for map markers (the engine already has `Stations()`; HTTP never exposed it).
- Filter `is_tide() && usable` within the bbox; cap `limit` (default 200, hard cap 1000); if no bbox, return
  the nearest `limit` to the bbox centre or refuse (require bbox to bound cost).
- GeoJSON `FeatureCollection` (drops straight into a MapLibre source):
  ```json
  { "type": "FeatureCollection", "source_policy": "redistributable-only", "count": 37,
    "features": [ { "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": { "index": 12, "name": "Suva, Central, Fiji", "type": "T",
                      "datum_m": 1.01, "has_datum": true,
                      "source_redistribution_cleared": true, "source_enabled_by_default": true,
                      "source_license": "Harmonics/public-domain" } } ] } }
  ```

### Engine caching
Today every `/tides/summary` constructs a fresh `TideEngine` + reloads sources. Hold a `static`
`TideEngine` per policy (built lazily, guarded by `g_tide_mtx`); all three routes reuse it. Latency drops
from "reload-per-sample" to "predict-per-sample".

---

## 2. UI polish  (rebuild as `web/tides.js`, our tokens)

Port the `tides.html` content into a SHELL panel module, restyled to **index.html tokens** — drop
`tides.html`'s private set:

| use | token |
|---|---|
| page/panel surface | `--glass: rgba(13,19,27,.74)` over `#05080c`, `.glass` blur material |
| accent (active/line/now-marker) | `--accent: #5bc0ff` (not `#61dcc8`) |
| text / dim / faint | `--ctext:#eef4f9` · `--cdim:#9bb0c0` · `--cdim2:#6f8597` |
| ok / warn / danger | `--ok:#46e0a0` · `--warn:#ffc06a` · `--danger:#ff6b6b` |
| "owned/free" provenance tag | gold `#f5c451` |
| type | system stack, `font-variant-numeric: tabular-nums` |
| radii | cards 13–16px, chips 999px, `.5px` borders |

Reuse shell classes (`.lbl` uppercase micro-label, `.row`, `.sub`, chip pills) so it's the same material as
Layers/Connections.

### The curve → a real tide instrument (the headline fix)
Hand-rolled SVG is fine; make it read like an instrument, driven by `/tides/curve`:
- **Smooth line** (30-min samples = 48 pts; optional Catmull-Rom/monotone smoothing) + soft `--accent` area fill.
- **Datum / zero line** (dashed, labelled with the datum value + unit) — the reference navigators read against.
- **Gridlines + axis labels**: time-of-day ticks on x (local tz), height ticks on y.
- **"Now" marker**: a vertical `--accent` line at current time + a value callout dot on the curve.
- **High/low markers**: pin each `events[]` extremum on the curve with ▲/▼ + time + height (this connects the
  big headline number to the plot — today they're disconnected).
- Optional scrub/hover → readout at the cursor time.

### Copy + chrome
- Product voice: **"Tides"** (not "Tide Engine"); real place names (not "Licensed default"); drop "OpenCPN TCMgr,
  running on this private Helm origin." Keep provenance honest but human ("Free / public-domain", "Commercial-review").
- **Kill the hardcoded `/chart/12/1120/1756.png` wallpaper** (one fixed tile behind every station; hurts legibility).
- Fix `kind.replace('_',' ')` (only replaces first underscore); use a label map.

---

## 3. Integration — SHELL drop-in, two surfaces  (no monolith edits)

`window.HelmShell` is live (`web/shell.js`, on main). Build everything in **`web/tides.js`** + a style
fragment; namespace every id `helm-tides-*`. The only SHELL-owned touch is one `<script src="tides.js">` in
`index.html` (mirrors how `ais-pins.js` is wired) — request it from SHELL rather than hand-editing the body.

### (a) Tides panel (the deep-dive dashboard)
```js
HelmShell.registerPanel({
  id: 'helm-tides-panel', epic: 'TIDES', title: 'Tides', icon: '<svg…/>',
  render(body, { map }) { /* hero readout + curve + next-event + source/policy ledger, our tokens */ },
  onOpen(body, { map }) { /* refresh /tides/curve + /tides/summary at the boat/cursor */ }
});
HelmShell.registerCommand({ id:'helm-tides-open', epic:'TIDES', title:'Open tides',
  run(){ HelmShell.panel('helm-tides-panel').open(); } });
```

### (b) Tide-station markers on the chart + tap card (the primary UX)
Precedented exactly by AIS targets + Places POIs.
- `web/style/helm-tides-stations.json`: a `helm-tides-src` GeoJSON source (loaded from `/tides/stations` for
  the current viewport) + a `helm-tides-station` circle/symbol layer. Register at load via
  `HelmShell.registerStyleFragment('TIDES', {...})` (no manifest edit), or add to `web/style/manifest.json`
  (SHELL-owned → request a draw-position slot).
- Refresh the source on `moveend` (debounced) from `/tides/stations?bbox=<viewport>`.
- `map.on('click','helm-tides-station', e => …)` → a glass `Popup` (HTML builder mirroring `aisPopupHTML`):
  current height, next high/low + time, station name + distance + datum, a sparkline mini-curve, and the
  source/policy chip. Guard `if (measuring()) return;`; add `mouseenter/leave` cursor feedback.

### (c) "Next tide" instrument-bar cell (always-on glance)
A `.it` cell ("Next ▲ 16:38 · 1.33 m" at the boat) fed by `HelmShell.onNav` (ownship position) → periodic
`/tides/summary`. Optional but high-value for an underway view.

---

## 4. Sequencing & ownership
1. **Land the tide engine on main first.** It's currently uncommitted in the shared tree (touches
   `helm_server.cpp` = CHART's file + the cli CMake = ENGINE's patch). Consolidate it (snapshot Codex's
   current state, commit as the baseline) so routes + UI have a stable base — coordinate so no in-flight
   work is lost.
2. Backend routes + caching → curl-verify (`/tides/curve` one call returns N samples + events; `/tides/stations`
   returns a FeatureCollection).
3. `web/tides.js` panel (our tokens, the instrument curve) → Playwright-verify against the dev server
   (index.html + HelmShell + tide routes).
4. Station layer + tap card → Playwright-verify markers render + tap opens the card.
5. Instrument-bar cell.

Codex retains: harmonic engine, station/datum/**confidence** model (TIDES-2 — surface `TideConfidence` in the
panel once it lands), currents/residuals (TIDES-3), and the **Pass Condition Estimator** (TIDES-5, the
high-risk advisory). This spec deliberately stops at presentation + read routes and **never** asserts safety.
