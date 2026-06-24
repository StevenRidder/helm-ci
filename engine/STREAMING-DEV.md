# Streaming dev runbook — local == remote

The decoupled service from [../docs/STREAMING-API.md](../docs/STREAMING-API.md), built as a
testable vertical slice. The point of this increment: the client behaves **identically**
whether the engine is on this MacBook (localhost) or on a Mac mini / Raspberry Pi across the
cabin (a LAN IP) — because there is no "local mode," only a resolved address.

## Pieces

| File | Role |
|------|------|
| [web/server-endpoint.js](../web/server-endpoint.js) | **The resolver.** One place that turns "where's the engine" into a URL. Address comes from `?server=`, then the page's own host, then `127.0.0.1`. Scheme mirrors the page (https→wss). This module *is* the local/remote transparency. |
| [web/nav-client.js](../web/nav-client.js) | Robust WS client: snapshot/delta merge, **age watchdog** (LIVE<3s / LAGGING 3–10s / STALE>10s — judged on frame age, not socket state), reconnect+resume, honest staleness (never fakes position), sim fallback. |
| [mock-engine.js](mock-engine.js) | Dependency-free stand-in for the engine's **network surface** — one origin (default `0.0.0.0:8090`): WS `/nav` (snapshot+delta @ 2 Hz + ping), `GET /chart/{z}/{x}/{y}.png` (immutable-cached stand-in tile), `/health`, `/catalog`. Lets us build + prove the client without the heavy C++ build. |
| [stream-smoke.js](stream-smoke.js) | Dependency-free contract test. |

## Run

```bash
node engine/mock-engine.js                 # one origin on 0.0.0.0:8090
node engine/stream-smoke.js                # → localhost:8090   (the "local" path)
node engine/stream-smoke.js 192.168.1.x 8090   # → LAN IP        (the "remote" path — same code)
```

Both smoke runs pass identically — that equivalence is the deliverable.

## Verify in the browser (on a machine with network for the basemap)

```bash
node engine/mock-engine.js                 # terminal 1
cd web && python3 -m http.server 5173      # terminal 2
```

- **Local:** open `http://localhost:5173` → cockpit shows **LIVE** nav from the mock; the data
  badge title shows the resolved origin (`localhost:5173`). The translucent-blue stand-in ENC
  tiles render (the real engine renders true S-52 here).
- **Remote (the proof):** from an **iPad/iPhone on the same WiFi**, open
  `http://<this-mac-LAN-ip>:5173`. Identical behavior — same code, addressed remotely. The
  resolver derives the engine host from the page host, so no config changes.
- **Staleness is honest:** kill the mock (Ctrl-C). The badge goes **LAGGING → STALE → OFFLINE**
  and the instruments grey out — it never keeps showing the last fix as if it were live.
  Restart the mock and the client reconnects and resumes on its own.
- **Override:** `http://localhost:5173/?server=192.168.1.50:8090` forces a specific engine
  (when the UI is served separately from the engine).

## What's real vs. mocked

- **Real & reusable now:** `server-endpoint.js`, `nav-client.js` — these ship as-is against the
  real engine. The client already accepts the engine's current **legacy full-frame** shape
  (a frame with no `t`) as well as snapshot/delta, so it works against today's `helm-engine`
  unchanged.
- **Mocked:** `mock-engine.js` stands in for the engine's network surface only. It is **not**
  navigation and renders no real charts.

## Next increment (engine side)

Teach the real engine ([README.md](README.md)) to serve this contract: one TLS origin, emit
`snapshot`+`delta`+`seq`+`ping` instead of the full 1 Hz blob, bind a configurable host
(default localhost, flag to open to the LAN), immutable tile cache headers + HTTP/2, then
Bonjour (`_helm._tcp`) and TOFU pairing. That's an **appended engine patch** (`0004+`), leaving
the existing patch series untouched. See [../docs/STREAMING-API.md](../docs/STREAMING-API.md) §8.
