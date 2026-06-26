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

Pre-alpha. Holds the product definition, architecture, research, the canonical UI, and the
**first real code** — a reusable data pipeline + a MapLibre prototype
(see [TRACER-BULLET.md](TRACER-BULLET.md)). **Phase 1 of the build plan is proven** — *both* reuse halves run headless on a Mac: OpenCPN's
`model/` nav core ([spike/opencpn-headless/](spike/opencpn-headless/)) **and** its S-52 ENC renderer
([spike/opencpn-headless/chart-render/](spike/opencpn-headless/chart-render/), which rendered a real
NOAA cell to a PNG with no GUI). **Phase 2 is underway**: the [Helm Engine](engine/) drives OpenCPN's real `Routeman` headless and streams
nav state over a WebSocket the cockpit consumes, **and** serves real S-52 ENC chart tiles over HTTP that
render in the UI — so the web app now shows OpenCPN's actual charts under live, OpenCPN-computed nav.
See [docs/OPENCPN-REUSE.md](docs/OPENCPN-REUSE.md).

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
| [SAFETY.md](SAFETY.md) | Alpha navigation disclaimer - supplemental aid only, not primary navigation |
| [docs/VISION.md](docs/VISION.md) | The north-star UX study — what world-class & AI-native looks like |
| [docs/SPACETIME-PROBE.md](docs/SPACETIME-PROBE.md) | The keystone primitive — any layer, any point in space/time, fused into one narratable slice |
| [docs/WEATHER-ROUTING.md](docs/WEATHER-ROUTING.md) | Spacetime weather engine — forecast follows the boat; easy routing; LLM guardrails |
| [docs/BRIEFINGS.md](docs/BRIEFINGS.md) | Living briefings — "along the way" + "once I get there", on a continuously-updating timeline |
| [docs/PUBLIC-ALPHA-CHECKLIST.md](docs/PUBLIC-ALPHA-CHECKLIST.md) | Public-alpha release gate, licensing posture, and Cruisers Forum sharing plan |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Shared C++ core + native Apple UIs + hybrid renderer |
| [docs/STREAMING-API.md](docs/STREAMING-API.md) | Boat server ↔ iOS thin clients — the world-class streaming/API contract |
| [docs/CHART-PIPELINE.md](docs/CHART-PIPELINE.md) | On-demand tiler + depth-on-satellite |
| [docs/WEATHER.md](docs/WEATHER.md) | Own-GRIB overlay + Windy + PredictWind |
| [docs/WEATHER-DATA.md](docs/WEATHER-DATA.md) | Data sources — Windy's models are public; we use the same |
| [docs/OPENCPN-REUSE.md](docs/OPENCPN-REUSE.md) | Read OpenCPN file-by-file: reuse its nav core; the new plan |
| [docs/FEATURE-AUDIT.md](docs/FEATURE-AUDIT.md) | **Client feature audit** — what's wired vs missing, benchmarked feature-by-feature against OpenCPN, pro MFDs, and iOS apps |
| [docs/CHART-QUILTING.md](docs/CHART-QUILTING.md) | Multi-cell S-52 tiler → quilting; where OpenCPN's quilt code falls short vs ours |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | **Build & run on macOS** — bootstrap the engine, run the stack, feature-by-feature verification checklist |
| [docs/integrations/noforeignland.md](docs/integrations/noforeignland.md) | NoForeignLand + community-places overlay scope |
| [TRACER-BULLET.md](TRACER-BULLET.md) | **The first code** — run the pipeline + prototype |
| [pipeline/](pipeline/) | Reusable engine: tiler · depth · wind |
| [web/](web/) | MapLibre prototype + shared `style.json` |
| [docs/LEGAL.md](docs/LEGAL.md) | Source licensing tiers — **read before touching a tile** |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phases 0–3 |
| [docs/decisions/](docs/decisions/) | Architecture decision records (ADRs) |
| [docs/mockups/](docs/mockups/) | UI mockups (macOS / iPad / iPhone) |

Internal business strategy, raw research artifacts, live-machine notes, and local
operator configuration are intentionally kept out of the public repository.

## Navigation Safety

Helm is pre-alpha marine navigation software. It is not certified, not
type-approved ECDIS, not carriage-compliant, and not a substitute for official
charts, notices, instruments, watchkeeping, or seamanship. Treat it as a
supplemental evaluation tool only.

Read [SAFETY.md](SAFETY.md) before running Helm, sharing screenshots, posting a
demo, or inviting testers.

## Quick Start

The current public-alpha path is the one-origin `helm-server`: it serves the
browser UI, `/nav`, `/chart`, `/catalog`, and `/health` on one private port.

```bash
brew install wxwidgets@3.2 gpatch cmake gdal node python3
engine/bootstrap.sh

export DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib
HELM_PORT=9001 \
HELM_WEB_ROOT="$PWD/web" \
HELM_CONFIG="$(mktemp -d)" \
HELM_TILES_NO_WARMUP=1 \
  /tmp/helm-opencpn/build/cli/helm-server

open http://127.0.0.1:9001/
```

Use [docs/RUNBOOK.md](docs/RUNBOOK.md) for NOAA ENC setup, NMEA/SignalK input,
and end-to-end verification. In the shared development environment, do not use
`:8080`; use a private development port instead.

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

Multi-license — see [LICENSE](LICENSE), [LICENSE.BSL](LICENSE.BSL), and
[ADR-0010](docs/decisions/0010-distribution-and-packaging-posture.md).

- **OpenCPN-derived engine work:** GPLv2-or-later, source-visible, and kept in a
  separate boat-server process behind the HTTP/WebSocket protocol boundary.
- **Helm-authored web/backend/pipeline/docs:** Business Source License 1.1
  today, with personal boat use, self-hosting, internal use, modification,
  redistribution, non-commercial use, and contribution allowed now. It converts
  to Apache-2.0 on the change date.
- **Reserved use:** offering Helm as a competing hosted or managed commercial
  service before the BSL change date.

BSL is source-available, not OSI open source. The paid/commercial distribution
path is still gated on IP counsel; see [docs/LEGAL.md](docs/LEGAL.md) and
[docs/PUBLIC-ALPHA-CHECKLIST.md](docs/PUBLIC-ALPHA-CHECKLIST.md).
