# Helm — canonical port map (binding convention)

> **One screen to watch: `:8080`.** Everything else is either a fixed dependency it needs, or an
> agent's private scratch you should never look at. This file is the rule, not a suggestion: if your
> service binds a **production** port below, you *will* blank Steve's chart on the live boat. It has
> already happened once (the WX met-ocean gateway grabbed `:8091` and every basemap went black —
> see board task **WX-15**). Don't be the next one.

---

## Production stack — ALWAYS up; agents must NEVER bind these

| Port | Service | Process / run | Serves |
|------|---------|---------------|--------|
| **8080** | one-origin boat screen | `helm-server`, built from `main`, run from `~/.helm/live/` | **the integrated `main` view Steve watches** — the web UI + `/nav` WebSocket + S-52 chart tiles (`/chart/{z}/{x}/{y}.png`) + `/health` + `/catalog`, all on one origin |
| **8090** | data backend | `backend/` (FastAPI, `uvicorn`) | real weather (Open-Meteo) + the community feed. `web/server-endpoint.js` defaults here. |
| **8091** | basemap tile server | `python3 pipeline/mbtiles_server.py 8091` | the owned chart packs — **Navionics** + Google/Bing/ArcGIS satellite — straight from the Fiji `.mbtiles`, as XYZ raster |

How the basemaps reach a LAN device: `web/style.json` hard-codes `localhost:8091` for the four
basemap sources; `web/index.html`'s `transformRequest` rewrites the **host** of every `:8091`
request to the page origin, so the iPad/phone on the boat WiFi loads charts from the Mac (not from
its own `localhost`). The port stays `8091`. The S-52 ENC tiles and `/nav` are same-origin on
`:8080`. **If a chart goes blank, one of these three is down — start there.**

### Live `:8080` deploy

The live binary + web live at `~/.helm/live/helm-server` and `~/.helm/live/web`. To publish merged
`main`, rebuild `helm-server` from `main` and copy it + the current `web/` there, then restart with:

```
HELM_BIND=0.0.0.0 HELM_PORT=8080 HELM_HDG_OFFSET=180 HELM_TILES_NO_WARMUP=1 \
HELM_CONFIG=~/.helm HELM_WEB_ROOT=~/.helm/live/web HELM_ENC=<cell>.000 \
DYLD_LIBRARY_PATH=/opt/homebrew/opt/wxwidgets@3.2/lib:/opt/homebrew/opt/libarchive/lib \
~/.helm/live/helm-server
```

The UI is served `Cache-Control: no-cache` so a browser never pins a stale page; tiles stay
`immutable`. (`~/.helm/live` is a one-time detached process — no launchd supervisor — so it stays
dead after a kill until relaunched.)

---

## Agent dev / scratch — pick your OWN high port; never the three above

| Agent | Scratch port |
|-------|-------------|
| CLIENT | 8077 |
| WX | 8092 (the met-ocean gateway moved here off `:8091` — WX-15) |
| AIS | 9000 (retired; was an integration-preview port) |
| anyone else | any free `80xx` / `90xx` of your own — **just not 8080 / 8090 / 8091** |

Run your branch on your scratch port for testing. When it merges to `main`, whoever owns the live
deploy rebuilds `:8080` from `main` and the integrated result appears there. **Steve only ever opens
`:8080` — never an agent scratch port.**

---

## The rule, in three lines

1. "Done" means **merged to git `main`** — not "running on my port." A port only *serves* `main`.
2. **Never bind `8080` / `8090` / `8091` for dev.** They are the boat. Binding one blanks the chart.
3. Watch exactly one port: **`:8080`.** If it's wrong, a production service is down — not your branch.
