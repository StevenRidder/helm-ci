# Helm

**One screen for everything on the water.**

Helm is a modern, cross-platform marine chartplotter — a successor to [OpenCPN](https://opencpn.org)
that carries its full feature set forward onto macOS, iPad, and iPhone, and fuses the
data a sailor currently juggles across four apps into a single situational picture:

> charts + satellite imagery + Windy-class weather layers + PredictWind routing +
> AIS + instruments — composited on one chart, offline-first.

Today a cruiser bounces between Windy (for some weather layers), PredictWind (for
routing), a separate weather app (for the rest), and a charting/nav app (for the
chart itself). Nothing on the market shows it all on one screen. **That is the product.**

## Status

Pre-alpha. Holds the product definition, architecture, research, the canonical UI, and now
the **first real code** — a reusable data pipeline + a MapLibre prototype
(see [TRACER-BULLET.md](TRACER-BULLET.md)). Native app is the next step.

## The three differentiators

1. **One fused screen.** Charts, satellite, the full weather stack, your route, AIS
   targets and instruments, composited as toggleable layers on a single chart —
   instead of four apps and a guess.
2. **On-demand charts + depth-on-satellite.** Lasso an area, fetch charts, cache them
   offline — the live version of [ChartLocker](https://chartlocker.brucebalan.com) —
   and overlay ENC depth soundings *on top of* satellite imagery, so you see the reef
   **and** the numbers. (Inspired by the S-57 depth rendering in
   [wholybee/chartplotter](https://github.com/wholybee/chartplotter).)
3. **Own weather + open routing.** Windy's whole layer catalog (wind, gust, swell,
   wave, rain, current, pressure, cloud) rendered from public GRIB as *our own*
   composited overlay — offline, no ToS strings — plus PredictWind route import and
   our own isochrone weather router.

## Start here

| Doc | What it is |
|-----|------------|
| [PRD.md](PRD.md) | The product requirements — read this first |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Shared C++ core + native Apple UIs + hybrid renderer |
| [docs/CHART-PIPELINE.md](docs/CHART-PIPELINE.md) | On-demand tiler + depth-on-satellite |
| [docs/WEATHER.md](docs/WEATHER.md) | Own-GRIB overlay + Windy + PredictWind |
| [docs/COMPETITIVE.md](docs/COMPETITIVE.md) | Market landscape + where Helm wins |
| [docs/integrations/noforeignland.md](docs/integrations/noforeignland.md) | NoForeignLand + community-places overlay scope |
| [TRACER-BULLET.md](TRACER-BULLET.md) | **The first code** — run the pipeline + prototype |
| [pipeline/](pipeline/) | Reusable engine: tiler · depth · wind |
| [web/](web/) | MapLibre prototype + shared `style.json` |
| [docs/LEGAL.md](docs/LEGAL.md) | Source licensing tiers — **read before touching a tile** |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases 0–3 |
| [docs/decisions/](docs/decisions/) | Architecture decision records (ADRs) |
| [docs/research/](docs/research/) | The multi-agent research dossier + raw output |
| [docs/mockups/](docs/mockups/) | UI mockups (macOS / iPad / iPhone) |

## The tracer bullet (first code)

Prove the magic before architecting anything. A macOS spike that:

1. renders a MapLibre map,
2. lets you lasso a bounding box and fetches Sentinel-2 + NOAA ENC for it,
3. packs the tiles into mbtiles and caches them offline,
4. overlays ENC `SOUNDG`/`DEPCNT` depth on the satellite imagery, and
5. drops a GRIB wind layer on top.

If that one screen feels good, the project is real and de-risked. The cross-platform
core then *emerges from working code* rather than upfront architecture.

## License

Undecided — see [ADR-0003](docs/decisions/0003-license-posture.md). Posture:
open-source now, preserve the option to commercialize later. The hard rule that falls
out of that: **Helm's own code stays GPL-free** (no OpenCPN source in the core), so an
S-52 chart engine is either rebuilt on permissive GDAL/PROJ or kept as an arm's-length
optional component. Recommended license: **BSL 1.1** (source-available now,
auto-converts to Apache-2.0).

## Provenance

The product definition was produced by a 13-agent research → architecture → design →
adversarial-verification → synthesis workflow (~662k tokens). The full raw output is
preserved verbatim at [docs/research/workflow-raw-output.json](docs/research/workflow-raw-output.json);
a readable digest is in [docs/research/README.md](docs/research/README.md).
