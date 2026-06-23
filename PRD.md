# Helm — Product Requirements Document

**Status:** Draft v0.1 · 2026-06-23
**Owner:** Steve Ridder
**Source:** distilled from a 13-agent research+design+verification workflow (see
[docs/research/](docs/research/)). Every legal/feasibility claim here survived an
adversarial review pass.

---

## 1. Summary

Helm is a cross-platform (macOS, iPadOS, iOS) marine chartplotter that preserves the
full capability of OpenCPN and adds the thing no product on the market does today:
**it fuses charts, satellite imagery, the full weather stack, weather routing, AIS,
and instruments into one screen.**

The wedge, in the user's words:

> "There's nothing in the market that has all this data in one screen. I need Windy for
> some stuff, PredictWind for some stuff, weather apps, and charting/nav apps. One app
> to see all this would be truly killer."

Helm is not "a nicer chart app." It is the single situational picture a passage-maker
currently has to assemble in their head across four apps.

## 2. Problem

A coastal/offshore sailor today runs, in parallel:

- a **charting/nav app** (OpenCPN, Navionics, Aqua Map) for the chart, routes, AIS;
- **Windy** for the good-looking weather layers (wind, swell, rain, gust…);
- **PredictWind** for optimal weather routing and high-res GRIB;
- a **weather app** for the rest.

None of them overlay the others. You read wind in one app, then mentally project it
onto a route you planned in a second app, on a chart that lives in a third. The
information exists; the **fused view does not.**

## 3. Goals / non-goals

### Goals
- Preserve 100% of OpenCPN's core navigation capability (additive, not reductive).
- Run natively and feel native on macOS, iPad, and iPhone (touch-first on iOS).
- Put charts + satellite + weather + routing + AIS + instruments on **one composited
  screen** with per-layer control.
- On-demand chart acquisition for a user-selected area, cached offline.
- Overlay ENC depth on satellite imagery ("see the reef and the depths").
- Render the full Windy-class weather catalog from public GRIB, offline.
- Import PredictWind routes; offer our own isochrone router as an open alternative.
- Offline-first throughout (this is a tool for places with no signal).

### Non-goals (v1)
- Re-implementing all 45+ OpenCPN plugins. v1 ships the core + a plugin SDK; the
  long tail (radar_pi, climatology, etc.) comes later.
- Being a primary-navigation authority on satellite imagery. Satellite is an explicit
  **supplemental** aid (see §10, §11).
- A live "compute the PredictWind route for me" cloud integration — PredictWind has no
  public API; this is impossible and is **not** promised (see §9).
- Embedding Windy's own animated map as a chart overlay — technically impossible and
  ToS-barred; we render our own layers instead (see §8).

## 4. Target user

Primary: the offshore/coastal cruiser who already lives in this toolchain and wants it
collapsed into one app. Secondary: the broader recreational/prosumer sailing market
currently split between Navionics/Aqua Map (charts) and Windy/PredictWind (weather).

## 5. Differentiators (why this wins)

1. **The fused screen** — the only product that composites all four data domains.
2. **On-demand charts + depth-on-satellite** — live ChartLocker + reef-piloting with
   ENC depth overlaid on imagery.
3. **Own weather, open routing** — Windy's catalog without Windy's leash; PredictWind
   import + our own router on free GRIB.
4. **Truly cross-platform native** — same product, native on Mac and on the phone in
   your pocket at the helm.

## 6. Feature requirements

### 6.1 Carried forward from OpenCPN (must preserve)

| Capability | Notes |
|---|---|
| Vector charts (S-57/S-63 ENC, CM93) | Via a dedicated S-52 engine; see [ARCHITECTURE](docs/ARCHITECTURE.md) |
| Raster charts (RNC/KAP), mbtiles | Via MapLibre raster sources |
| Quilting + chart groups | Seamless multi-cell display |
| Routes, marks, tracks | GPX import/export |
| AIS targets + CPA/TCPA + alarms | Guard zones, SART, MOB |
| Tides & currents | Harmonic prediction |
| GRIB weather | Becomes the native weather engine (§8) |
| Dashboard instruments | SOG/COG/HDG/depth/wind/etc. |
| NMEA 0183 & 2000 / SignalK | Network-first on iOS (§ARCHITECTURE) |
| Autopilot output | Over network on iOS; serial on macOS |
| Anchor watch | Background location + drag alarm |
| Day / Dusk / Night schemes | First-class top-level toggle |

### 6.2 New capabilities

- **On-demand chart download** — lasso a bbox, pick sources, pick max zoom, see an
  estimated size, download to offline mbtiles. ([CHART-PIPELINE](docs/CHART-PIPELINE.md))
- **Bring-your-own charts** — import any `.mbtiles` (preserves the existing ChartLocker
  workflow 1:1).
- **Depth-on-satellite** — ENC `DEPARE`/`DEPCNT`/`SOUNDG` rendered translucently over
  satellite raster, as a toggle.
- **Composited weather layers** — wind (animated particles), gust, swell, wave height/
  period, rain, current, pressure, cloud, CAPE — rendered from GRIB, with opacity and a
  forecast-time scrubber. ([WEATHER](docs/WEATHER.md))
- **PredictWind route import** — import an exported GPX route/GRIB, overlaid distinctly,
  kept device-local.
- **Helm weather routing** — own isochrone router on GRIB + boat polars (Phase 2).
- **Command palette (⌘K)** — go to port/waypoint/chart/layer.

## 7. The "one screen" layer model

The chart is the base. Everything else is a controllable layer stack:

```
┌─ Weather (own GRIB) ── wind · gust · swell · wave · rain · current · pressure · cloud
├─ Routing ──────────── your route · imported PredictWind route · Helm-routed
├─ AIS / targets ─────── vessels · CPA/TCPA · MOB
├─ Chart overlay ─────── ENC vector (S-52)  ·  ENC depth-on-satellite
└─ Base ──────────────── ENC raster / satellite / mbtiles (quilted)
```

Each layer: on/off, opacity, and (for weather) a time index. This stack *is* the product.

## 8. Weather stack

- **Primary, ownable, offline:** our own GRIB renderer (GFS / GFS-Wave / RTOFS by
  default — free, public, no branding, same model family as OpenCPN's GRIB plugin).
  Animated wind via WebGL particles (windgl / leaflet-velocity / Mapbox raster-particle
  lineage); scalar layers as heatmaps. **This is the real weather.**
- **Windy:** can only ever be an *optional online tab*, never a chart overlay (its
  Leaflet API owns its own map and cannot composite on ours; it's online-only,
  uncacheable, logo-mandatory, free tier non-production, and may bar marine-nav apps as
  "direct competition"). Ships **only if** Windy grants written clearance; otherwise
  dropped entirely.
- **PredictWind:** no public API. Path is user-initiated GPX/GRIB **import**, displayed
  client-side and labelled honestly as imported, kept device-local.

Full detail + the honesty constraints: [docs/WEATHER.md](docs/WEATHER.md).

## 9. Data sources & license tiers

The on-demand pipeline only *ships* clean sources. See [docs/LEGAL.md](docs/LEGAL.md)
for the binding guardrails — this is the single largest legal exposure in the product.

| Tier | Sources | Disposition |
|---|---|---|
| **Clean — ships** | Sentinel-2 (Copernicus), NOAA ENC/NCDS, OpenSeaMap (overlay) | Fetch, host, cache, redistribute (with attribution) |
| **Bring-your-own** | Google, Bing imagery | User imports their own; we never server-fetch or host |
| **Partnership** | Navionics, Esri/ArcGIS | Only via official paid SDK/agreement; not scraped |

For Steve's **personal use**, BYO covers all four exactly as ChartLocker does today; the
tiers only bind a *distributed* product.

## 10. Platforms & UX principles

- **macOS** — SwiftUI + AppKit. Menus, multi-window, trackpad, drag-drop `.gpx/.grb/.mbtiles`,
  serial NMEA. The fast-moving development platform and where OpenCPN/GDAL can be reused.
- **iPadOS** — SwiftUI + Metal. Touch-first, floating rail, big instrument tiles. The
  real helm tablet.
- **iOS** — SwiftUI + Metal. One-handed underway view: glance row, route bottom-sheet,
  layers FAB, tab bar.
- **Principles:** chart-first / full-bleed; calm glass chrome that recedes; Day/Dusk/Night
  as a first-class control; legible-at-arm's-length instruments; offline-first.

Mockups: [docs/mockups/](docs/mockups/).

## 11. Honest constraints (non-negotiable truths)

These survived adversarial review and must not be re-litigated into overclaims:

1. **OpenCPN-on-iOS is a rebuild, not a port.** wxWidgets is desktop-only; GPLv2+
   conflicts with App Store terms (the "VLC problem"); iOS forbids serial/USB. iOS/iPadOS
   are clean re-implementations on a shared core; only macOS reuses OpenCPN's canvas.
2. **PredictWind has no public API** and won't build one. No live routing integration is
   possible — import only.
3. **Windy cannot be a chart overlay** and is online-only; our own GRIB is the weather.
4. **Satellite imagery is supplemental, not primary navigation.** Clouds hide reefs,
   imagery can paint reefs out, Sentinel-2 is 10 m, satellite-derived bathymetry is only
   ~IHO ZOC-C. A permanent "cross-reference official charts" disclaimer is mandatory.
5. **iOS has no serial/USB NMEA** — connectivity is SignalK / NMEA-over-TCP-UDP / BLE /
   internal GPS; autopilot output over the network. Serial only on macOS.
6. **MapLibre cannot render S-52.** True ENC needs a dedicated S-52 engine composited on
   top of MapLibre — a two-renderer design (load-bearing, not a nicety).

## 12. Architecture (summary)

One shared **C++ nav core** compiled into all three Apple targets, with platform-native
SwiftUI/Metal front-ends, and a **hybrid renderer** (MapLibre Native for raster/satellite/
weather/mbtiles + a dedicated S-52 ENC engine composited on top). The on-demand tiler
runs server/edge-side. Full detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 13. Roadmap (summary)

- **Phase 0** — foundations & legal clearance; shared core builds green on all three.
- **Phase 0.5** — the tracer bullet (see README).
- **Phase 1 (MVP)** — native chart; clean on-demand charts + BYO import; SignalK/NMEA;
  AIS + CPA/TCPA; GPX routes; own-GRIB weather; depth-on-satellite.
- **Phase 2** — true S-52 ENC; own isochrone router + polars; anchor watch; tides/currents;
  PredictWind import.
- **Phase 3** — licensed premium charts; conditional Windy tab; plugin SDK.

Full detail: [docs/ROADMAP.md](docs/ROADMAP.md).

## 14. Risks & open questions

- **ENC engine:** contain OpenCPN's GPL S-52 vs. rebuild on GDAL — gates Phase 2 and the
  license posture. ([ADR-0002](docs/decisions/0002-enc-engine.md))
- **App Store + GPL** may force a 100% permissive rebuild path.
- **On-demand tiler hosting** (cost, source-credential custody, abuse/rate-limits) drives
  unit economics — undecided.
- **Windy marine-nav clearance** may be denied outright; plan survives on own-GRIB.
- **Business model** must fund any Windy Pro / Esri / Navionics licensing if commercialized.
- **Plugin parity** — "all of OpenCPN" includes a big plugin ecosystem; risk of
  over-promising before the SDK exists.
- **PredictWind GPX** may carry waypoints only (losing per-leg ETA/wind metadata).
- **Anchor-watch background location** is the likeliest App Store review friction point.
- **Satellite/SDB liability** even with disclaimers — keep SDB shading conservative.

## 15. Success criteria

- **Tracer bullet:** one screen showing satellite + ENC depth overlay + a live GRIB wind
  layer, offline, that *feels worth using*. If yes, proceed.
- **MVP:** Steve plans and sails a real passage using only Helm on the Mac and the phone —
  charts, weather, route, AIS — without opening Windy, PredictWind, or a chart app.
