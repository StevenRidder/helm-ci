# Research dossier

The product definition was produced by a **13-agent workflow** (~662k tokens, ~134 tool
calls): 5 parallel research agents → 1 architecture synthesis → 4 design agents → 2
adversarial critics (feasibility/legal + design-consistency) → 1 final synthesis.

The **full raw output is preserved verbatim** in
[`workflow-raw-output.json`](workflow-raw-output.json) (~246 KB). This file digests the
load-bearing findings and where they live in the curated docs.

## Verification outcome

- **Feasibility / legal critic:** *"Sound — approve with minor corrections."* Tried to
  refute the five highest-risk overclaims (free Google/Bing/Navionics caching; a
  PredictWind routing API; compositing Windy over our chart; OpenCPN-on-iPhone; iOS
  serial NMEA) — all held. Three minor refinements folded into [LEGAL.md](../LEGAL.md).
- **Design / render-safety critic:** flagged the agent-authored HTML mockups as broken
  (truncation, stray `<![CDATA[`, malformed hex). Mockups were therefore re-authored by
  hand; see [../mockups/](../mockups/).

## Key findings → where they landed

| Topic | Finding | Doc |
|---|---|---|
| ChartLocker | Pre-built regional mbtiles ZIPs, not on-demand; live version is buildable but ToS-bound | [CHART-PIPELINE](../CHART-PIPELINE.md) |
| Tile pipeline | bbox→XYZ→fetch→georef→mbtiles (TMS Y-flip); GB-scale at high zoom | [CHART-PIPELINE](../CHART-PIPELINE.md) |
| Source ToS | Sentinel-2/NOAA/OpenSeaMap clean; Google/Bing BYO; Navionics/Esri partnership | [LEGAL](../LEGAL.md) |
| Windy | Leaflet plugin owns its own map; online-only; can't composite; may bar marine apps | [WEATHER](../WEATHER.md) |
| Own weather | Render Windy's catalog from GRIB via WebGL particles/heatmaps — composited, offline | [WEATHER](../WEATHER.md) |
| PredictWind | No public API; import GPX/GRIB only; build own isochrone router | [WEATHER](../WEATHER.md) |
| Depth-on-satellite | wholybee proved S-57 depth parsing; we composite it over satellite | [CHART-PIPELINE](../CHART-PIPELINE.md) |
| OpenCPN on iOS | Rebuild, not a port (wxWidgets/GPL/serial) | [ARCHITECTURE](../ARCHITECTURE.md), [ADR-0001](../decisions/0001-successor-not-fork.md) |
| Stack | Shared C++ core + native Apple UIs; hybrid MapLibre + S-52 renderer | [ARCHITECTURE](../ARCHITECTURE.md) |
| Connectivity | iOS = SignalK/TCP/UDP/BLE/internal GPS; serial macOS-only | [ARCHITECTURE](../ARCHITECTURE.md) |

## Primary sources

- ChartLocker — https://chartlocker.brucebalan.com
- wholybee/chartplotter — https://github.com/wholybee/chartplotter
- Windy Map Forecast API — https://api.windy.com/map-forecast/docs
- PredictWind — https://www.predictwind.com
- GDAL gdal2tiles / MBTiles — https://gdal.org/en/stable/programs/gdal2tiles.html
- WebGL wind lineage — https://github.com/mapbox/webgl-wind ·
  https://github.com/astrosat/windgl · https://github.com/geoql/maplibre-gl-wind ·
  https://github.com/danwild/leaflet-velocity
- OpenCPN — https://opencpn.org
