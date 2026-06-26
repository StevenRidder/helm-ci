# Runbook - Build, Run, and Verify Helm on macOS

**Audience:** an engineer or alpha tester on macOS who wants to build the
headless engine, run the web client, and verify the current one-origin stack.

**What you are building today:** a C++ `helm-server` that reuses OpenCPN's
`model/` navigation core and S-52/S-57 renderer headlessly, plus the browser
client in `web/`. The server owns `/nav`, `/chart/{z}/{x}/{y}.png`, `/health`,
`/catalog`, and the static UI on one HTTP/WebSocket origin.

There is no SwiftUI/iOS native client yet. The browser is the reference client.

## Live-Port Warning

In shared development environments, `:8080` may be reserved for a stable live
instance and must not be killed or replaced by agents. The examples below use
private port `9001`. On your own machine you can choose another port, but using
a private port keeps the habit safe.

## 0. TL;DR

```bash
# 1. Prerequisites, once.
brew install wxwidgets@3.2 gpatch cmake gdal node python3
sudo xcodebuild -license accept

# 2. Build the one-origin engine. First run may take 10-20 minutes.
engine/bootstrap.sh

# 3. Optional but recommended: put a NOAA ENC cell where the default demo expects it.
mkdir -p /tmp/ENC_ROOT
# unzip a free NOAA ENC so you have, for example:
# /tmp/ENC_ROOT/US5FL96M/US5FL96M.000

# 4. Run a private one-origin server.
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib
HELM_PORT=9001 \
HELM_WEB_ROOT="$PWD/web" \
HELM_CONFIG="$(mktemp -d)" \
HELM_TILES_NO_WARMUP=1 \
  /tmp/helm-opencpn/build/cli/helm-server

# 5. Open the client.
open http://127.0.0.1:9001/
```

The UI will load even without live vessel data. To see live movement, feed NMEA or
configure a SignalK/NMEA connection as described below.

## 1. Prerequisites

| Tool | Why | Install |
|---|---|---|
| Xcode CLT / Xcode | C/C++ toolchain | `xcode-select --install`; if full Xcode is active, run `sudo xcodebuild -license accept` |
| wxWidgets 3.2 | OpenCPN dependency; 3.3 is not compatible | `brew install wxwidgets@3.2` |
| GNU patch (`gpatch`) | OpenCPN bundled-lib patches require GNU patch | `brew install gpatch` |
| CMake | build system | `brew install cmake` |
| GDAL | optional depth extraction pipeline | `brew install gdal` |
| node | smoke tests and WebSocket checks | `brew install node` |
| python3 | helper scripts | macOS/Homebrew Python |

`engine/bootstrap.sh` checks prerequisites and fails with the specific fix when
something is missing.

## 2. Chart and Weather Data

### NOAA ENC Cells

Free US ENC cells are available from NOAA:
<https://www.charts.noaa.gov/ENCs/ENCs.shtml>

Unzip one or more cells under `/tmp/ENC_ROOT`, for example:

```bash
mkdir -p /tmp/ENC_ROOT
# unzip US5FL96M.zip so this exists:
# /tmp/ENC_ROOT/US5FL96M/US5FL96M.000
```

`helm-server` reads a single ENC from `HELM_ENC`, defaulting to
`/tmp/ENC_ROOT/US5FL96M/US5FL96M.000`. If no ENC is present, the server still
starts and the UI still loads, but chart tiles for that demo cell will be empty
or unavailable.

### Depth-on-Satellite GeoJSON

Optional overlay extraction:

```bash
pipeline/extract_depth.sh /tmp/ENC_ROOT/US5FL96M/US5FL96M.000
```

This writes generated GeoJSON under `web/data/`. Without these files, the
browser depth overlays are empty; the S-52 engine tiles still render if `HELM_ENC`
points at a valid cell.

### Weather

```bash
bash pipeline/build.sh
```

This builds demo/public-data weather layers into `web/data/`.

## 3. Build

```bash
engine/bootstrap.sh
```

The bootstrap clones the pinned OpenCPN source into `/tmp/helm-opencpn`, applies
Helm's maintained patch series, overlays Helm's new CLI sources, and builds the
Helm targets, including:

```text
/tmp/helm-opencpn/build/cli/helm-server
/tmp/helm-opencpn/build/cli/helm-engine
/tmp/helm-opencpn/build/cli/helm-tiles
/tmp/helm-opencpn/build/cli/helm-tides-smoke
```

`helm-server` is the normal product path. `helm-engine` and `helm-tiles` remain
useful lower-level split-process debugging tools.

To rebuild from scratch:

```bash
engine/bootstrap.sh --clean
```

To run the bootstrap's smoke check on a private port:

```bash
engine/bootstrap.sh --smoke
```

## 4. Run the One-Origin Server

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib

HELM_PORT=9001 \
HELM_WEB_ROOT="$PWD/web" \
HELM_CONFIG="$(mktemp -d)" \
HELM_TILES_NO_WARMUP=1 \
HELM_ENC=/tmp/ENC_ROOT/US5FL96M/US5FL96M.000 \
  /tmp/helm-opencpn/build/cli/helm-server
```

Open:

```bash
open http://127.0.0.1:9001/
```

Sanity checks:

```bash
curl -s http://127.0.0.1:9001/health
curl -s http://127.0.0.1:9001/catalog
curl -s -o /tmp/helm-tile.png -w '%{http_code}\n' \
  http://127.0.0.1:9001/chart/12/1120/1756.png
```

## 5. Feed Boat Data

The server seeds a local NMEA TCP relay on `127.0.0.1:10110` for first-run
testing. You can send NMEA 0183 sentences to it:

```bash
cat engine/test/fixtures/ais_sample.nmea | nc 127.0.0.1 10110
```

For a real boat, add connections through the UI or provide a persisted
`HELM_CONFIG` with `connections.json`. Supported connection types include TCP
client/server, UDP, SignalK, serial, NMEA 2000 placeholders, and internet AIS
raw NMEA feeds.

For SignalK, configure the connection in the UI or use the persisted connection
file under the selected `HELM_CONFIG` directory.

## 6. Verify End-to-End

After a build, run:

```bash
engine/test-engine.sh
```

It starts private test instances and verifies:

- one-origin `helm-server` framing, `/health`, `/catalog`, UI, and S-52 tiles;
- immutable tile caching and ETag revalidation;
- nav-core per-fix math, source tags, and waypoint auto-advance;
- GPL containment guard;
- offline tide smoke/regression coverage.

## 7. What to Look For in the Browser

| Feature | Pass looks like |
|---|---|
| One-origin UI | `http://127.0.0.1:9001/` serves the browser app |
| Health/catalog | `/health` and `/catalog` return JSON |
| Charts | S-52 chart tiles render when `HELM_ENC` points at a valid NOAA cell |
| Data honesty | missing or stale data is shown as missing/stale, not silently live |
| AIS | AIS targets appear after NMEA/AIS sentences reach the server |
| Routes | route create/save/activate uses the command plane and navobj persistence |
| Weather | generated weather layers appear after `pipeline/build.sh` |

## 8. Troubleshooting

- `wx-config not executable`: install `wxwidgets@3.2` or set `WX_CONFIG`.
- Xcode license errors: run `sudo xcodebuild -license accept`.
- `patch` errors during OpenCPN configure: install `gpatch`.
- `dyld: library not loaded`: set `DYLD_LIBRARY_PATH` as shown above.
- No ENC tiles: set `HELM_ENC` to a valid `.000` file.
- UI loads but no boat movement: feed NMEA/SignalK; the server should not fake a
  live vessel.
- Port conflict: pick another private `HELM_PORT` and, if needed,
  `HELM_RELAY_PORT`.

## 9. Public Alpha Caveat

Helm is pre-alpha navigation software. It is not type-approved ECDIS, not a
primary navigation system, and not a substitute for official charts,
instruments, watchkeeping, or seamanship. See [SAFETY.md](../SAFETY.md),
[LEGAL.md](LEGAL.md), [CLIENT-LICENSE-REGISTER.md](CLIENT-LICENSE-REGISTER.md),
and [PUBLIC-ALPHA-CHECKLIST.md](PUBLIC-ALPHA-CHECKLIST.md) before distributing
a public build.
