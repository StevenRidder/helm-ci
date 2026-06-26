# basemap-fill — online-fill underlay tile cache (CHART-16)

A standalone, **clean-IP** caching reverse-proxy that serves licensed online satellite
tiles for the **online-fill underlay** — the layer that sits *beneath* the offline MBTiles
charts and fills the gaps (the missing z16 in every Fiji pack, anything past the pack's
zoom, and everywhere outside the Fiji bbox). Where the owned charts have tiles, they paint
on top and the fill is hidden; where they don't, the satellite shows instead of dark ocean.

Permissive **stdlib only** — no GPL, no OpenCPN (ADR-0006/0009). Part of the post-GPL data
plane, beside [`services/wx`](../wx). Holds the upstream URL server-side so the browser only
ever talks to this origin.

## Run

```sh
sh services/basemap-fill/run.sh      # :8095, cache in ~/.helm/basemap-fill-cache
```

Bind is `0.0.0.0` so an iPad/phone on the boat LAN loads the same fill from this Mac
(`index.html`'s `transformRequest` rewrites the `:8095` host like it does `:8091`).

> **Port:** `:8095`. Do **NOT** use `:8091` — that's `pipeline/mbtiles_server.py` (the offline
> basemap server). See WX-15.

## API

| Route | Returns |
|---|---|
| `GET /basemap/{source}/{z}/{x}/{y}.{ext}` | tile bytes (cache-first) |
| `GET /health` | `{"ok":true}` |
| `GET /stats` | `{"cached_tiles":N,"sources":[...]}` |

`source` is `eox` (production) or `esri` (dev/alt only — paid ToS). MapLibre requests
`{z}/{x}/{y}`; both upstreams address `{z}/{y}/{x}`, handled internally.

## Cache policy (world-class, no size cap)

- **cache-first** — a cached tile serves instantly, even with no internet.
- **stale-while-revalidate** — older than `HELM_FILL_REFRESH_DAYS` (default 30) → a
  *background* conditional GET (`If-None-Match` via stored ETag) refreshes it; the response
  never waits. Satellite mosaics update ~annually, so this keeps tiles current without churn.
- **serve-stale-on-outage** — upstream down/timeout → serve any cached bytes; if none, `204`
  transparent (fail-safe: the dark ocean shows, never a 5xx/spinner/broken tile).
- **no eviction** (Mac mini / iOS, not a Pi). Roadmap: byte-budget + route-pin for tiny devices.

## Env

| var | default | |
|---|---|---|
| `HELM_FILL_PORT` | `8095` | listen port |
| `HELM_FILL_CACHE` | `~/.helm/basemap-fill-cache` | disk cache root |
| `HELM_FILL_REFRESH_DAYS` | `30` | background-revalidate age |
| `HELM_FILL_TIMEOUT` | `12` | upstream fetch timeout (s) |

## Production source

**EOX Sentinel-2 cloudless** (`s2cloudless-2023`, global, ~10 m, CC-BY-4.0) — matches Helm's
existing offline `sat` pack credit, and (unlike MapTiler/Mapbox) its license permits the
server-side caching + offline persistence this design depends on. Attribution:
*"Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH"*.

## Roadmap

Fold into a content-agnostic `services/wx` cache (parameterize `OrderedTileCache` `ext`+`subdir`
+ `ignore_ttl`) so weather + basemap fill share one cache tier; add the CLIENT-11 service-worker
browser tier for LAN companions; byte-budget + route-pin ("download this passage") for small disks.
