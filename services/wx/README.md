# helm-wx — met-ocean / data-layer gateway

A standalone, **clean-IP** microservice that turns external weather sources into Helm's
value-encoded Mercator tiles **on demand** — the online counterpart of
[`pipeline/make_value_tiles.py`](../../pipeline/make_value_tiles.py).

## Why it's its own service (not in the C++ engine)

Helm's GPL OpenCPN/S-52 core is quarantined behind the wire (arm's-length containment —
ADR-0006 / ADR-0009). This service is the **opposite corner**: net-new, permissively licensed
(FastAPI + httpx + Python stdlib — **no GPL, no OpenCPN**), a brick in the **post-GPL data plane**.

It's the seam where map data layers enter Helm:

- **Today** → Open-Meteo (free, no key).
- **Next** → the **S-100 met-ocean** product specs plug in here unchanged for the client:
  S-411 (wind/pressure), S-412 (waves), S-104 (water level), S-111 (surface currents) — sitting
  beside the planned permissive **S-101** chart rebuild.

The client never changes — it just consumes `helm-wxv1` tiles over HTTP. Swap the fetcher behind
the same tile contract and you've migrated a data layer off the legacy core.

## "Fetch once, serve many" (what Windy does)

A coarse **source grid** is fetched per coarse Mercator cell and cached; every output tile in that
cell is baked from it. One client or twenty, panning or zooming — we touch Open-Meteo only when we
move into a genuinely new area or the cache ages out (default 30 min). On a provider `429`/outage we
serve stale cache if we have it, else fail honestly. **We never fabricate a value to fill a gap**
(NODATA stays transparent). **NOT FOR NAVIGATION.**

## Contract — `helm-wxv1` (mirrors `web/wx-value-codec.js`)

```
GET /index.json                -> layer catalogue for the UI picker
GET /{layer}/manifest.json     -> {encoding, scale, offset, ramp, bbox, minzoom, maxzoom, unit, ...}
GET /{layer}/{z}/{x}/{y}.png   -> 256x256 RGBA; RGB = 24-bit value, A = NODATA mask (0 = no data)
GET /health
```

`value = offset + ((R<<16)|(G<<8)|B) * scale` — decoded + colourised **client-side** by
[`web/integrations/cog.js`](../../web/integrations/cog.js) (`helmwx://` protocol). `scale`/`offset`
are **fixed per layer** so colours and values are comparable across every tile and session.

Layers: `wind, gust, temp, pressure, rain, clouds, cape` (forecast API) + `sst, waves, swell, current` (Marine API).

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --port 8091
# point the client at  http://<host>:8091/{layer}/manifest.json
```

### Open-Meteo API key (commercial)

The free tier is non-commercial + daily-capped. For production / heavy use, set a commercial key — the
service then uses `customer-api.open-meteo.com` (1M+ calls/mo, no daily cap). Put it in a **gitignored**
`services/wx/.env` (never commit it):

```
HELM_WX_OPENMETEO_KEY=your-key-here
```

`app.py` loads `.env` on startup (real env vars override it). Without a key it falls back to the free host.

Env knobs: `HELM_WX_CACHE` (dir), `HELM_WX_TTL` (s, default 1800), `HELM_WX_COOLDOWN` (s after a 429,
default 300), `HELM_WX_DATA_Z` (manifest maxzoom, default 7), `HELM_WX_FETCH_Z` (coarse source-grid zoom,
default 5), `HELM_WX_GRID_N` (source-grid resolution, default 12), `HELM_WX_CONCURRENCY` / `HELM_WX_MIN_INTERVAL`
(outbound throttle).

## Test

```bash
python3 test_wx.py        # offline — bakes, round-trips bake->PNG->decode->value, checks caching
```
