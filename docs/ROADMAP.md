# Roadmap

> Phased so the riskiest, highest-value thing is proven first and the cross-platform core
> emerges from working code, not upfront architecture.

## Phase 0 — Foundations & legal clearance

- IP counsel on the OpenCPN GPL boundary (contained component vs. GDAL rebuild) **before**
  any code embeds GPL.
- Confirm Copernicus / NOAA / OpenSeaMap attribution obligations; document that
  PredictWind has no API; open the written-terms check with `api@windy.com`.
- Stand up the **shared C++ core** building green on macOS / iPadOS / iOS, with MapLibre
  Native (Metal) rendering a basic mbtiles inside an empty SwiftUI shell on each platform.
- Create the attribution/ToS guardrail register ([LEGAL.md](LEGAL.md)).

## Phase 0.5 — The tracer bullet

A single macOS screen that proves the magic, end to end:

1. MapLibre map renders.
2. Lasso a bbox → fetch Sentinel-2 + NOAA ENC.
3. Pack mbtiles → cache offline.
4. Overlay ENC `SOUNDG`/`DEPCNT` depth on the satellite imagery.
5. Drop a GRIB wind layer on top.

**Go/no-go:** if that screen feels worth using, the project is real.

## Phase 1 — MVP: native chart + safe on-demand charts + connectivity + own GRIB

- SwiftUI/MapLibre shell on all three platforms.
- On-demand pipeline: NOAA NCDS raster + Sentinel-2, select-area → server-tiler (TMS
  Y-flip) → mbtiles → offline.
- **BYO** "import my own `.mbtiles`" (the ChartLocker bridge).
- Connectivity: SignalK + NMEA0183-over-TCP/UDP + internal GPS.
- AIS with CPA/TCPA + alarms.
- Routes / marks / tracks via GPX.
- Own-GRIB weather (GFS / GFS-Wave / RTOFS) composited and offline-cached.
- Depth-on-satellite.
- Mandatory "supplemental, not for primary nav" disclaimer on satellite.

## Phase 2 — True ENC + owned routing + anchor watch + PredictWind import

- Contained S-52/S-57/CM93 ENC engine (GPL component or GDAL + custom S-52) with
  Day/Dusk/Night palettes, quilting, Chart Groups.
- **Helm Weather Routing** — own isochrone engine + polar library/editor (`.pol`/`.csv`)
  on free NOAA GRIB.
- Anchor watch via background "Always" location + region monitoring + drag notifications.
- Tides/currents harmonics + dashboard instruments.
- **PredictWind import** (Track A) — client-side GPX/GRIB import via file picker + iOS
  `.gpx`/`.grb` share-sheet handlers, kept device-local and out of cloud sync.

## Phase 3 — Licensed premium charts + (conditional) Windy + plugins

- Formal cartography deals for Navionics / C-MAP / NV-Charts via official SDK/IAP
  (iNavX/X-Traverse model), online or licensed-offline, never scraped.
- **Pursue-or-drop** a paid Esri "World Imagery (for Export)" deal inside Esri's SDK.
- Ship the online **Windy WebView tab only if** `api@windy.com` grants written clearance;
  else drop it.
- Plugin / extensibility SDK to carry forward the OpenCPN ecosystem (radar, climatology,
  oTCurrent).
- Autopilot output over network.
- Counsel sign-off on every source before commercial launch.
