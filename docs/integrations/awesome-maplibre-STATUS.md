# Awesome-MapLibre Lab — Status & Handoff

_Last updated: 2026-06-24 · Branch: `claude/awesome-maplibre-exploration-acctbi` · Commit: `1ec6c01`_

> **Offline-first + production update (2026-06-25).** Made the whole thing offline-first (CDN is
> nice-to-have, never required) and promoted contours to production:
>
> - **Contours → production.** maplibre-contour now drives a real **DEM depth-contour** layer in the
>   Layers drawer (`web/depth-contours.js`, lazy-loaded), computed off-thread from a **local** terrain-RGB
>   DEM. The hand-rolled `web/isolines.js` (marching squares, disabled in prod) is **deleted**.
>   - **Bug fixed (2026-06-25): the DEM URL must be ABSOLUTE.** maplibre-contour fetches DEM tiles inside a
>     Web Worker, which has no document base and throws "Failed to parse URL" on a relative path — so
>     contours silently never rendered. `depth-contours.js`/`contour.js` now resolve the DEM URL against
>     the page origin (`new URL('data/dem/', document.baseURI)`). Verified in a real browser: **456 contour
>     features generated / 373 painted** at the live region.
>   - **Region note:** the public sample uses the Key West demo region. Local builds can
>     switch regions by copying `pipeline/region.env.example` to `pipeline/region.env`.
> - **No more runtime CDN.** Every Lab toggle's data is now local, baked once at build time:
>   `pipeline/fetch_dem.py` → `web/data/dem/` (contours + the mercator hillshade), local rain-forecast
>   frames for the temporal control, `pipeline/make_demo_cog.py` → `web/data/demo-sst-cog.tif` for cog://,
>   and deck.gl AIS now seeds from the real `data/ais-sample.geojson`. Verified zero esm.sh/unpkg/remote-DEM/
>   RainViewer/geomatico requests at runtime.
> - **Labels work offline.** Vendored the Noto Sans glyph ranges (`pipeline/fetch_glyphs.py` → `web/fonts/`,
>   `style.json` glyphs now local) and fixed a latent bug — `Open Sans Regular` (which 404s on demotiles)
>   was unified to `Noto Sans Regular` across the style + contour/measure modules.
> - **Still online-by-design (graceful):** the satellite/NOAA basemap tiles (offline via the chart-download
>   pipeline) and `radar.js`'s live RainViewer nowcast (degrades to no-op offline).
>
> **Integration update (2026-06-24, branch `integrate/awesome-maplibre-v5`).** The handoff
> items below are now **done** — merged onto current `main` and verified locally with real internet:
>
> 1. **Prod regression on MapLibre v5.24.0 — PASS.** Static audit of every production file vs the
>    real v4→v5 breaking-change list: **low risk, no code changes required** (the Map is built with
>    only `container/style/hash` so the `canvasContextAttributes` break doesn't apply; all `.on()`
>    calls are standalone so the Subscription-return break is inert). Live headless run confirmed
>    structural parity (14 layers / 11 sources), every subsystem working (wind particles, field
>    heatmap, radar, isobars wiring, ownship + follow, anchor alarm), the globe projection engaging
>    and reverting, and **zero** new exceptions — the only console errors are environmental
>    (unreachable satellite/radar tiles + a CJK glyph 404, identical on v4).
> 2. **Vendored offline-first into `web/vendor/`.** All CDN deps (MapLibre core + the 8 plugin
>    bundles) are now local esbuild bundles; the `index.html` import map and script/css tags point
>    at `web/vendor/` — **no `esm.sh`/`unpkg` at runtime** (verified: every module loads `200` from
>    localhost, zero CDN requests). See `web/vendor/README.md` for versions + rebuild steps.
> 3. **`index.html` merge conflict resolved** (clean additive merge onto current `main`).
>
> Bonus: the two breakers flagged below (deck.gl duplicate-`@deck.gl/core`, maplibre-contour under
> v5) **both instantiate cleanly** from the vendored bundles — deck.gl is now one shared bundle, and
> contour adds its layers without error. The plugins' *data sources* (Terrarium DEM, RainViewer,
> demo COG) still need wiring for a believable demo (handoff step 3 below) — that part is unchanged.

## What this is

A "Lab" drawer wired into the tracer-bullet web app (`web/index.html`) that exercises
ten tools from [awesome-maplibre](https://github.com/maplibre/awesome-maplibre)
against Helm's real map. Each integration maps onto a Helm differentiator or replaces
home-rolled code. The production UI is untouched — everything new lives behind the
flask (🧪) rail icon and a set of toggles.

See also: `docs/decisions/0006-awesome-maplibre-integrations.md` (ADR) and
`docs/integrations/awesome-maplibre.md` (per-library rationale).

## Architecture (how it's wired)

- **`web/index.html`** — adds an ESM **import map** pinning each plugin to a CDN
  (`esm.sh` / `unpkg`), a MapLibre **shim** (`web/integrations/_maplibre-shim.js`)
  so every plugin shares the single `window.maplibregl` instance, and the Lab drawer markup.
- **MapLibre upgraded 4.7.1 → 5.24.0** (loaded from `unpkg`) — unlocks the **globe**
  projection. The existing `wind-layer.js` rides on top unchanged.
- **`web/integrations/lab.js`** — the drawer controller. Each toggle **lazy-imports**
  its module the first time it's switched on, so a slow CDN or one broken plugin
  **never blocks initial page load** and can't take down the other integrations.
  Failures surface as a toast ("… failed to load — see console").
- **`web/integrations/*.js`** — one module per integration (pmtiles, cog, contour,
  mercator, draw, measures, temporal, ais-deck). Each exports an enable/disable pair
  the drawer calls.
- **Server-side pieces** (not runnable in-browser): `pipeline/make_pmtiles.sh`
  (PMTiles packing) and `pipeline/martin/config.yaml` (Martin tile server for offline packs).

The ten integrations:

| Toggle | Library | Replaces / enables |
|---|---|---|
| Globe projection | MapLibre v5 core | new capability (great-circle at scale) |
| PMTiles offline raster | `pmtiles` | replaces `.mbtiles` container |
| COG overlay (`cog://`) | `maplibre-cog-protocol` | GRIB/depth/imagery, no tiler |
| Contours from DEM | `maplibre-contour` | replaces `isolines.js` |
| Value-encoded tiles | Mercator-style | weather-tile contract vs `field-*.json` blob |
| Draw route / lasso area | `terra-draw` + maplibre adapter | route editing, bbox → Download drawer |
| Measure distance/bearing | `maplibre-gl-measures` | new tool |
| Temporal control | `maplibre-gl-temporal-control` | time scrubber (RainViewer demo) |
| AIS at scale | `deck.gl` | scatter + heatmap for many vessels |
| (server) Martin | `martin` | off-the-shelf tile server for offline packs |

**Explicitly NOT adopted:** native raster-particle layer (Mapbox-GL-only) — we keep `wind-layer.js`.

## What I verified

### Static / API correctness (done)
I pulled every plugin's published package from the **npm registry** and checked my
glue code against the real exported API. This caught and fixed three bugs before they
could reach a browser:
- `maplibre-gl-temporal-control` is a **default export** and only toggles layer
  visibility — so `temporal.js` now adds the layers itself.
- Terra Draw's MapLibre adapter takes `{ map }` (object), not a positional arg.
- (Plus the v5 shim / shared-instance wiring.)

### Live browser smoke test (done, with one caveat)
Ran a **headless Chromium test via Playwright 1.56** (`/opt/pw-browsers`, `--no-sandbox`).
Because this build sandbox's network policy **blocks `unpkg`/`esm.sh`** (only the npm
registry is reachable), I vendored `maplibre-gl` locally just for the test (removed
afterward — the committed page keeps the CDN, which a real browser reaches fine).

**6/6 checks passed:**
- MapLibre **v5.24.0** loads, style parses, `satellite` layer present
- **Globe projection** engages — `map.getProjection()` → `{type:"globe"}`
- Lab drawer opens; all ten toggles render
- Production tracer-bullet UI intact (route inspector, instruments, AIS sample, nav badge)
- A plugin toggle with an unreachable CDN **fails gracefully** — toast shown,
  **0 page errors**, map stays alive (validates the lazy-load isolation design)

## Where it ends up — what's NOT yet verified

The seven CDN-loaded plugins have **not been exercised at runtime** (their bundles
couldn't load in the sandbox). Static API review + graceful-degradation are proven;
actual rendering is not. Likeliest to need a tweak:
- **deck.gl** — duplicate `@deck.gl/core` resolution via esm.sh import map.
- **maplibre-contour@0.1.0** — confirm it speaks v5's promise-based `addProtocol`.

---

## Handoff: what a local agent needs to do to wrap this up

You have real internet, so the CDNs will load. Budget ~30–60 min.

### 1. Run it and walk every toggle (~15 min)
```bash
cd web && python3 -m http.server 8080   # open http://localhost:8080, click the 🧪 (Lab) rail icon
```
For each of the ten toggles: switch on, confirm it does something visible, check the
browser console for errors, switch off, confirm clean teardown. Note: some toggles
need data that the pipeline hasn't generated yet (see step 3).

### 2. Fix the two likely breakers
- **deck.gl**: if you see duplicate-module or "two instances of `@deck.gl/core`"
  errors, pin all `@deck.gl/*` and `@luma.gl/*` to a single version in the
  `index.html` import map (or load deck's pre-bundled UMD). File: `web/integrations/ais-deck.js`.
- **maplibre-contour**: verify `addProtocol` returns/handles a Promise under v5; the
  0.1.0 API may differ. File: `web/integrations/contour.js`.

### 3. Provide demo data for the data-dependent toggles
The style references geojson the pipeline doesn't generate in a fresh checkout
(`depare/depcnt/soundg/wind_points/places`). For a believable demo:
- **Contours**: point at a real Terrarium DEM source (or a small local sample).
- **COG / Mercator / Temporal**: wire one real source each — e.g. a GFS wind field
  for value-encoded tiles, a RainViewer frame for temporal, a single COG for `cog://`.
- **AIS at scale**: `web/data/ais-sample.geojson` exists — point deck.gl at it and
  bump the count to show it scaling.

### 4. (Optional but on-brand) Vendor the plugins for offline-first
Helm is a chartplotter — it should work without internet. Consider downloading the
pinned plugin bundles from the npm registry into `web/vendor/` and switching the
import map from CDN URLs to local paths. This also makes the headless smoke test
fully runnable in CI.

### 5. Promote one integration from "wired" to "production"
Best first candidate: **contours** — swap `isolines.js` for `maplibre-contour` in the
real weather drawer (not just the Lab toggle), since it deletes home-rolled code and
is low-risk. Second: **PMTiles** for the offline raster path.

### 6. Update the commit's caveat
Commit `1ec6c01`'s message says "browser smoke test still pending." Once you've walked
the toggles, that's no longer true — note the runtime verification in your next commit
or the ADR's status.

### Test scaffold (for reference)
The Playwright script I used is not committed (it lived in scratch). To recreate: serve
`web/`, launch Chromium with `--no-sandbox`, assert `window.map.getStyle().layers`,
toggle `[data-lab="globe"]` and check `map.getProjection().type === "globe"`, toggle a
plugin and assert the page survives. If you vendor maplibre (step 4) it runs offline.
