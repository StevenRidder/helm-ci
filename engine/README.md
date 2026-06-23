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

## The contract (`ws://127.0.0.1:8081`, ~1 Hz)
Identical to what `web/nav-source.js` (the sim) emits — the UI prefers the engine, falls back to the
sim when the engine isn't running, with **no code difference** between real and simulated nav:
```json
{ "type":"nav",
  "pos":{"lat":24.45867,"lon":-81.8078}, "posStr":"24°27.5′N · 81°48.5′W",
  "sog":6.1, "cog":15, "hdg":14, "depth":13.2,
  "wind":{"spd":17,"dir":105,"range":"13–25 kt"},
  "active":{ "name":"Route to Marina", "eta":"11:43 PM", "dtg":"6.1 NM", "xte":"0 m",
    "legs":[{"name":"WP2 · sea buoy","brg":"15°","active":true}, …], "nextWp":"WP2 · 1.6 NM" } }
```

## Build & run (against the OpenCPN clone, like the spikes)
```bash
cp helm_engine.cpp /tmp/opencpn/cli/
cat cli-CMakeLists-engine-snippet.txt >> /tmp/opencpn/cli/CMakeLists.txt   # after the helm-spike block
cmake -S /tmp/opencpn -B /tmp/opencpn/build -DwxWidgets_CONFIG_EXECUTABLE=$WX ...   # (see ../spike/opencpn-headless/README.md)
cmake --build /tmp/opencpn/build --target helm-engine --parallel 8
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
  /tmp/opencpn/build/cli/helm-engine        # streams on ws://127.0.0.1:8081
node wsclient-test.js                        # dependency-free check: prints 3 nav frames
```
Then open `web/index.html` (served) — the cockpit picks up the engine automatically
(`window.__navSource === 'engine'`); kill the engine and it falls back to the sim.

## Gotcha found
ixwebsocket **requires** registering a per-socket message callback *inside* the connection callback
(`webSocket.lock()->setOnMessageCallback(...)`), even for a push-only server — omitting it makes the
server reject every connection with "Server callback improperly registered" and reset the socket.

## Built on the same model/ that drives a real boat
Links the identical `ocpn::model-src` proven in [../spike/opencpn-headless/](../spike/opencpn-headless/).

## Next increment
- **S-52 chart-tile HTTP server** — `http://127.0.0.1:8082/chart/{z}/{x}/{y}.png` rendering ENC tiles
  via the proven [chart-render](../spike/opencpn-headless/chart-render/) path → a MapLibre raster
  source. Then the UI shows real S-52 charts under real nav.
- Real position in (SignalK / NMEA) instead of the demo own-ship advance.
- The tides + `UpdateProgress` relocations into the core (see ../docs/OPENCPN-REUSE.md).
