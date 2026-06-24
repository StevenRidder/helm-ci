# Helm Engine — skeleton (Phase 2)

The C++ engine that links OpenCPN's nav core and serves the Helm UI over localhost. This first
increment is the **nav-state half**: it drives OpenCPN's **real `Routeman` headless** and streams the
live nav state over a WebSocket that the web UI consumes. Verified end-to-end on macOS
(2026-06-23): browser cockpit driven by `model/`-computed nav over the wire.

```
   ┌───────────── helm-engine (C++, GPL) ─────────────┐
   │  links ocpn::model-src  (route · Routeman ·       │
   │     active-nav · auto-advance · tracks · AIS)     │
   │  + ix::WebSocketServer (in-tree libs/IXWebSocket) │
   │  → ws://127.0.0.1:8081   nav state @ 1 Hz         │
   └───────────────────────▲──────────────────────────┘
                            │  (same JSON shape as web/nav-source.js)
   ┌───────────────────────┴──────────────────────────┐
   │  Helm UI (web/index.html): instrument bar +       │
   │  route inspector + ownship marker                 │
   └───────────────────────────────────────────────────┘
```

## What it proves
- OpenCPN's `model/` nav core (`Route` + `Routeman`: `ActivateRoute`, `ActivateNextPoint`
  auto-advance, active waypoint) runs headless **and** feeds a real client.
- The per-fix nav math (BRG / DTW / XTE / ETA — the `gui/`→core "UpdateProgress" relocation) is
  computed engine-side and pushed.
- The UI is fully decoupled: it speaks JSON over a socket, so it runs in a plain browser and the
  engine can be swapped/relocated freely.

## The contract (`ws://<bind>:8081/`, ~1 Hz) — snapshot + delta
On connect, a client gets a full **`snapshot`** (its baseline); thereafter **`delta`** frames carry
only the fields that move, each stamped with a monotonic `seq` + wall-clock `ts`, with a `snapshot`
keyframe every 10th tick so any client resyncs. The full state is identical to what
`web/nav-source.js` (the sim) emits, so the cockpit renders real, simulated, local, and remote nav
through the same code — `web/nav-client.js` merges snapshot/delta and also accepts a legacy full
frame. Full design: [../docs/STREAMING-API.md](../docs/STREAMING-API.md).
```jsonc
// snapshot — full baseline (on connect + keyframe)
{ "t":"snapshot", "seq":11, "ts":1750000000.123, "type":"nav", "posSource":"simulated",
  "sources":{ "pos":"nmea","sog":"nmea","cog":"nmea","hdg":"simulated","depth":"nmea","wind":"simulated" },
  "pos":{"lat":24.45867,"lon":-81.8078}, "posStr":"24°27.5′N · 81°48.5′W",
  "sog":6.1, "cog":15, "hdg":14, "depth":13.2, "wind":{"spd":17,"dir":105,"range":"13–25 kt"},
  "active":{ "name":"Route to Marina","eta":"11:43 PM","dtg":"6.1 NM","xte":"0 m",
    "legs":[{"name":"WP2 · sea buoy","brg":"15°","active":true}], "nextWp":"WP2 · 1.6 NM" } }
// delta — only what changed (wind only every ~5th)
{ "t":"delta", "seq":12, "ts":1750000001.121, "pos":{"lat":24.4589,"lon":-81.8077}, "posStr":"…",
  "sog":6.0, "cog":16, "hdg":15, "depth":13.1,
  "active":{ "dtg":"6.0 NM","xte":"1 m","eta":"11:42 PM","ttg":"59m","vmg":"5.9 kn","nextWp":"WP2 · 1.5 NM" } }
```

## Build & run

The build is reproducible from a pinned OpenCPN + maintained patch series — see
[VENDORING.md](VENDORING.md). `helm_engine.cpp` lives in [`vendor/cli/`](vendor/cli/) and
its target is added by `patches/0003`; do not hand-edit a clone.
```bash
engine/bootstrap.sh                          # clone @ pin → patch → overlay → build all helm targets
# bind is configurable so the SAME engine serves localhost or the boat LAN (iPad/iPhone):
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  HELM_BIND=0.0.0.0 HELM_PORT=8081 \
  "$HELM_OCPN_DIR/build/cli/helm-engine"     # HELM_BIND defaults to 127.0.0.1; 0.0.0.0 exposes it on the LAN
node engine/stream-smoke.js 127.0.0.1 8081 --ws-only   # contract check: snapshot→deltas, seq increasing
node engine/wsclient-test.js                 # legacy dependency-free check: prints 3 nav frames
```
The contract is verified end-to-end against the real `model/` core, **identically over localhost and a
LAN IP** (`stream-smoke … --ws-only`). Then open `web/index.html` (served) — `web/nav-client.js`
resolves the engine address (localhost, or the boat host if you load the UI from it; see
[../docs/STREAMING-API.md](../docs/STREAMING-API.md)) and the cockpit picks it up automatically; kill the
engine and it goes STALE/OFFLINE (never faking position), reconnecting on its own.

## Gotchas found
- ixwebsocket **requires** registering a per-socket message callback *inside* the connection callback
  (`webSocket.lock()->setOnMessageCallback(...)`), even for a push-only server — omitting it makes the
  server reject every connection with "Server callback improperly registered" and reset the socket.
- The connection callback fires **before the WS handshake completes**, so a `send()` from inside it is
  dropped. A new client's `snapshot` baseline must therefore be sent from the nav loop (which only
  iterates `getClients()` once a client is fully connected), tracking who's been seen — not from the
  connection callback.

## Built on the same model/ that drives a real boat
Links the identical `ocpn::model-src` proven in [../spike/opencpn-headless/](../spike/opencpn-headless/).

## S-52 chart-tile server (`helm_tiles.cpp`) ✅
`helm-tiles` loads a NOAA ENC headless (the proven [chart-render](../spike/opencpn-headless/chart-render/)
path) and serves `http://<bind>:8082/chart/{z}/{x}/{y}.png` — per-tile S-52 renders — to a MapLibre
raster source (`enc` in `web/style.json`, the "S-52 charts (engine)" toggle). Verified: real S-52 tiles
(soundings, depth areas, contours, cell boundary) render in the Helm UI. Notes:
- **Configurable bind + immutable caching** (streaming patch): `HELM_BIND` (default 127.0.0.1; 0.0.0.0 for
  the LAN) + `HELM_TILE_PORT`. Tiles are immutable for a cell/scheme, so they're served
  `Cache-Control: public, max-age=31536000, immutable` + an `ETag` and answer `If-None-Match` with 304 —
  a big win when one Pi feeds several iPads (was `no-cache`). Errors are `no-store`, never cached.
- Renders on the **main thread** (CoreGraphics): HTTP worker threads hand each tile to a main-thread job
  queue and wait — see `render_tile` + the `main()` loop.
- Slippy-tile → ViewPort: tile-bbox center + `ppm = 256 / lat_span_m`, `RenderRegionViewOnDC`, then
  `dc.GetSelectedBitmap()` → PNG to memory. Tiles outside the cell return a transparent tile.
- Build: `cmake --build … --target helm-tiles` (clones the chart-spike slice + `ixwebsocket`). Built first-try.
- Sandbox gotcha (not a product bug): network-blocked basemap tiles can saturate MapLibre's image-request
  pool and starve the ENC tiles; with a reachable basemap they load fine.

## Streaming patch — done in this increment
- **Snapshot + delta + seq/ts** on the nav WS (was a full blob every tick); new clients get a snapshot
  baseline, established clients get deltas, keyframe every 10th tick. Verified against the real `model/`
  core, identically over localhost and a LAN IP.
- **Configurable bind** on both servers (`HELM_BIND` / `HELM_PORT` / `HELM_TILE_PORT`) — the server-side
  half of "behaves the same local or remote."
- **Immutable tile caching** (ETag + 304) on `helm-tiles`.

## Next increment
- **One TLS origin + Bonjour + pairing**: merge nav WS + chart HTTP onto one port, add TLS (the in-tree
  `mdns` lib + OpenSSL are already linked), advertise `_helm._tcp`, TOFU pairing. See STREAMING-API.md §5–8.
- **NODTA → transparent**: make the S-52 no-data grey transparent so charts composite *over* satellite.
- **Real position in** (SignalK / NMEA) instead of the demo own-ship advance.
- **lastSeq resume**: use the client's `hello` lastSeq to send only the delta-since, not a full snapshot.
- Align the demo route + ENC cell so the boat rides the S-52 chart; tides + `UpdateProgress` relocations.
