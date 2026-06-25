# Runbook — build & run Helm on macOS, then verify

**Audience:** an engineer or agent on a Mac who wants to build the engine, run the whole stack,
and **see/verify** the features. Self-contained — assumes no prior context.

**What you're building (today):** Helm is currently a **C++ engine** (reuses OpenCPN's nav core +
S-52 renderer, headless) + a **web client** (`web/`, MapLibre). The engine streams live nav over a
WebSocket and serves S-52 chart tiles over HTTP; the web client consumes both. The native
SwiftUI/Xcode app from the PRD **does not exist yet** — "build in Xcode" here means building the
C++ engine with the Xcode toolchain (CLI, or an optional generated Xcode project) and running the
web client. macOS only (the tiler renders via CoreGraphics on the main thread).

> Source of truth for the build is `engine/bootstrap.sh` (pinned OpenCPN + patch series, no
> hand-editing a clone). This doc wraps it with data setup, run, and a verification checklist.

---

## 0. TL;DR

```bash
# 1. prerequisites (once)
brew install wxwidgets@3.2 gpatch cmake gdal node python3
sudo xcodebuild -license accept                      # or: sudo xcode-select -s /Library/Developer/CommandLineTools

# 2. build the engine (clones OpenCPN @ pin, patches, builds helm-engine + helm-tiles)
engine/bootstrap.sh                                   # ~10-20 min first run; binaries in /tmp/helm-opencpn/build/cli

# 3. get a chart (free NOAA ENC) and lay it where the tiler looks
mkdir -p /tmp/ENC_ROOT && unzip ~/Downloads/US5FL96M.zip -d /tmp/ENC_ROOT   # any US5/US4/US3 cell(s)

# 4. run the three processes (separate terminals)
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  /tmp/helm-opencpn/build/cli/helm-engine                              # nav WS  ws://127.0.0.1:8081
HELM_ENC_ROOT=/tmp/ENC_ROOT \
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  /tmp/helm-opencpn/build/cli/helm-tiles                               # tiles   http://127.0.0.1:8082
cd web && python3 -m http.server 8080                                  # client  http://localhost:8080

# 5. open the client
open http://localhost:8080
```

Then jump to **§5 Verification**.

---

## 1. Prerequisites

| Tool | Why | Install |
|---|---|---|
| **Xcode CLT / Xcode** | C/C++ toolchain (clang) | `xcode-select --install`; if a full Xcode is active, run `sudo xcodebuild -license accept` |
| **wxWidgets 3.2** | OpenCPN dependency — **must be 3.2** (3.3 removed `wxNode`) | `brew install wxwidgets@3.2` |
| **GNU patch (`gpatch`)** | OpenCPN's bundled-lib build patch uses GNU syntax; macOS BSD `patch` fails | `brew install gpatch` |
| **CMake** | build system | `brew install cmake` |
| **GDAL** | depth-on-satellite extraction (`extract_depth.sh`) | `brew install gdal` |
| **node** | quick WS/JS checks | `brew install node` |
| **python3** | serve `web/` | preinstalled / `brew install python3` |

`bootstrap.sh` checks each and **fails loud** with the exact fix if one is missing (including the
"Xcode license not accepted" trap, which it auto-works-around via Command Line Tools).

---

## 2. Get chart data

### 2a. ENC cells (required for charts)
Free, US public domain: <https://www.charts.noaa.gov/ENCs/ENCs.shtml>. Download one or more `.000`
cells and unzip them under a root folder:

```bash
mkdir -p /tmp/ENC_ROOT
# unzip each cell so you end up with e.g. /tmp/ENC_ROOT/US5FL96M/US5FL96M.000
```

- **Multi-cell quilting:** put several cells of the **same area at different scales** (e.g. a US3
  coastal, US4 approach, US5 harbour) under `/tmp/ENC_ROOT`. The tiler loads all of them and
  picks the zoom-appropriate one per tile.
- The tiler reads `$HELM_ENC_ROOT` (folder, recursive) or a single `.000` path as `argv[1]`;
  default `/tmp/ENC_ROOT`.

### 2b. Depth-on-satellite vector overlay (optional but recommended)
Extract depth features from a cell into GeoJSON the client overlays on the satellite:

```bash
pipeline/extract_depth.sh /tmp/ENC_ROOT/US5FL96M/US5FL96M.000   # -> web/data/{depare,depcnt,soundg}.geojson
```

(These files are gitignored — they're generated. Without them the depth layers are simply empty;
the **engine's** S-52 tiles still show depth.)

### 2c. Weather (optional)
```bash
bash pipeline/build.sh        # wind + places + forecast into web/data/ (Open-Meteo, no key)
```

---

## 3. Build the engine

### 3a. Primary path — the bootstrap (recommended)
```bash
engine/bootstrap.sh                 # clone@pin -> patch -> overlay cli/ -> cmake build helm targets
engine/bootstrap.sh --smoke         # ...and render one tile to prove the chart path end-to-end
engine/bootstrap.sh --clean         # nuke the clone and start fresh
```
Outputs (default `HELM_OCPN_DIR=/tmp/helm-opencpn`):
```
/tmp/helm-opencpn/build/cli/helm-engine     # nav-state WebSocket server (:8081)
/tmp/helm-opencpn/build/cli/helm-tiles      # S-52 chart-tile HTTP server (:8082)
```
First build clones + builds OpenCPN's libs — **10–20 min**. Rebuilds are incremental.

> **⚠️ `helm-server` is NOT built by bootstrap (ENGINE-12).** The one-origin binary — nav WS + tiles +
> `/health` + `/catalog` + static UI on **one port (:8080)**, which `.claude/run-helm-server.sh` and
> `.claude/launch.json` exec — is complete in `helm_server.cpp` but missing from the bootstrap target
> list. A clean bootstrap produces **no** `helm-server`. Build it explicitly:
> `cmake --build /tmp/helm-opencpn/build --target helm-server -j`. Otherwise use the two separate
> binaries (helm-engine + helm-tiles) below. See [../CLAUDE.md](../CLAUDE.md).

### 3b. Optional — open it in Xcode
CMake can emit an Xcode project instead of the default build:
```bash
# after bootstrap.sh has cloned + patched once (so /tmp/helm-opencpn exists & is patched):
cmake -S /tmp/helm-opencpn -B /tmp/helm-opencpn/build-xcode -G Xcode \
  -DwxWidgets_CONFIG_EXECUTABLE=/opt/homebrew/opt/wxwidgets@3.2/bin/wx-config-3.2 \
  -DOCPN_BUILD_TEST=OFF
open /tmp/helm-opencpn/build-xcode/*.xcodeproj
```
In Xcode, pick the **`helm-engine`** or **`helm-tiles`** scheme and Build/Run. (The C++ engine,
not a SwiftUI app — there is no app target yet.) For day-to-day work the CLI build in 3a is faster.

---

## 4. Run

Three processes. The web client auto-detects the engine and falls back to a built-in simulator
when it's absent, so you can run the client alone first.

```bash
# A) nav engine — streams nav state @1Hz, listens for NMEA/AIS on TCP 10110, optional SignalK
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  /tmp/helm-opencpn/build/cli/helm-engine                      # add a GPX: helm-engine route.gpx  (or HELM_ROUTE=...)
# expect: "nav-state WebSocket: ws://127.0.0.1:8081" and "AIS: OpenCPN AisDecoder live"

# B) chart tiles — multi-cell, zoom-quilted, NODTA-transparent
HELM_ENC_ROOT=/tmp/ENC_ROOT \
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  /tmp/helm-opencpn/build/cli/helm-tiles
# expect: "loaded N ENC cell(s)…" and "NODTA no-data colour = rgb(…) -> transparent"

# C) web client
cd web && python3 -m http.server 8080 && open http://localhost:8080
```

Sanity checks without a browser:
```bash
node engine/wsclient-test.js                                   # prints 3 nav frames from the engine
curl -s -o /tmp/t.png -w '%{http_code}\n' http://127.0.0.1:8082/chart/12/1120/1756.png   # 200 + a PNG
```

### Feed test boat data (drives AIS, CPA, instruments)
The engine listens on **TCP 10110**. Replay the bundled AIS fixture:
```bash
cat engine/test/fixtures/ais_sample.nmea | nc 127.0.0.1 10110
# or live position too: pipe RMC/DPT/MWV/HDT sentences from your own NMEA source/multiplexer
```
SignalK instead: `HELM_SIGNALK=ws://pi.local:3000/signalk/v1/stream?subscribe=self helm-engine`.

---

## 5. Verification — what to look for

Top-left **data-source badge**: `LIVE` (real position), `ENGINE · SIM POS` (engine up, demo
position), `SIM` (no engine), `ENGINE LOST` (engine dropped — readings stale).

| # | Feature | How to drive it | Pass = you see |
|---|---|---|---|
| 1 | **Live nav** | run engine (B) | instruments (SOG/COG/depth/wind/pos), route inspector (ETA/DTG/XTE), own-ship marker moving |
| 2 | **Charts (quilt)** | run tiles + Layers → "S-52 charts (engine)" | real S-52 (soundings/depth/contours); **pan & zoom stays seamless**, right detail per zoom; tiles log per request |
| 3 | **Depth-on-satellite** | Layers → Satellite **on** + S-52 on (engine NODTA-transparent), or run §2b then toggle "Depth shading/contours/soundings" | chart composites **over** the imagery (no grey blanket); shallow soundings **warm/red**, deep light |
| 4 | **Globe** | zoom all the way out | Earth as a **sphere** (curvature), flattening to the chart as you zoom in |
| 5 | **AIS** | `nc … < ais_sample.nmea` (see §4) | vessel triangles from the **live** feed; tap one → name/MMSI/class/SOG/COG/HDG/range/brg/CPA/**TCPA** |
| 6 | **CPA alarm + COLREGs** | feed an AIS target on a closing course | red **collision-risk banner** with give-way/stand-on + the maneuver (e.g. "alter to STARBOARD, pass astern"), intercept line + pulsing ring on the target |
| 7 | **Measure tool** | left rail → ruler icon, click points | dashed rubber-band, per-leg **range + bearing °T** labels, cumulative HUD; ⌫ undo, dbl-click/Esc finish |
| 8 | **Live route line** | `helm-engine your.gpx` | drawn magenta route **matches the loaded GPX** and the inspector; active leg highlighted brighter |
| 9 | **Weather** | run §2c, Weather drawer | wind particles + scalar layers + forecast scrubber |
| 10 | **Day/Dusk/Night** | top-bar toggle | basemap reskins |

---

## 6. Troubleshooting / known gotchas

- **`wx-config not executable`** → `brew install wxwidgets@3.2`, or set `WX_CONFIG=/opt/homebrew/opt/wxwidgets@3.2/bin/wx-config-3.2`. Must be **3.2**, not 3.3.
- **Every compile fails / "Xcode license"** → `sudo xcodebuild -license accept` or `sudo xcode-select -s /Library/Developer/CommandLineTools`. (bootstrap auto-falls-back to CLT.)
- **`patch` errors during OpenCPN configure** → `brew install gpatch` (GNU patch). bootstrap shims it onto PATH.
- **engine/tiles run but `dyld: library not loaded`** → set `DYLD_LIBRARY_PATH` to the wxwidgets@3.2 + libarchive lib dirs (see §4).
- **tiles: "no ENC (*.000) cells under …"** → put cells under `/tmp/ENC_ROOT` or set `HELM_ENC_ROOT`.
- **tiles: blank/transparent everywhere** → expected outside cell coverage; check the cell extent in the startup log; confirm the tile z/x/y overlaps it.
- **no-data stays grey (not transparent)** → look for `NODTA no-data colour = … -> transparent` in the tiles log; if it says "NODTA colour unavailable", depth-on-satellite compositing falls back to opaque (still renders, just no see-through).
- **ENC tiles missing in the browser, basemap fine** → MapLibre's image-request pool can be starved by a slow/blocked basemap; with a reachable basemap the ENC tiles load (sandbox-only issue, not a product bug).
- **globe looks wrong / weather particles misplaced when zoomed way out** → the MapLibre **v5** globe is new; the custom WebGL weather layers (`wind-layer.js` etc.) may need a globe-aware tweak at world zoom. It's cosmetic at ocean-overview scale and guarded so it can't break the base map; revert by pinning `maplibre-gl@4.7.1` in `web/index.html` if needed.
- **AIS/CPA never appears** → those are **engine-driven** (real CPA/TCPA). In pure `SIM` mode (no engine) only the static AIS sample shows and no CPA alarm fires — feed AIS on TCP 10110 with the engine running.

---

## 7. What this runbook can and can't prove

- **Can:** that the engine builds, serves real S-52 tiles + live nav, and that the client renders
  charts, AIS w/ TCPA, CPA+COLREGs alarm, measure tool, live route, depth-on-satellite, and globe.
- **Can't yet:** there is **no native SwiftUI app** (PRD Phase 1+); iOS/iPad are future. And the
  full S-52 conditional-symbology / CM93 / encrypted-chart coverage and OpenCPN's decades of
  messy-real-cell hardening are **not** matched (see [CHART-QUILTING.md](CHART-QUILTING.md) §5).

*Cross-references: [engine/README.md](../engine/README.md), [engine/VENDORING.md](../engine/VENDORING.md),
[TRACER-BULLET.md](../TRACER-BULLET.md), [CHART-QUILTING.md](CHART-QUILTING.md),
[FEATURE-AUDIT.md](FEATURE-AUDIT.md).*
