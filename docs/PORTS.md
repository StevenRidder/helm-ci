# Helm Port Map

Use private development ports while testing Helm. Do not assume another developer's
machine, boat server, or demo process is safe to stop or replace.

## Common Ports

| Port | Service | Notes |
|------|---------|-------|
| 8080 | Default `helm-server` port | Product default only. In shared environments this may already be reserved. |
| 8090 | Optional backend service | Weather, places, and community/LLM prototype endpoints. |
| 8091 | Optional BYO MBTiles server | Local raster packs served by `pipeline/mbtiles_server.py`. Packs are not committed. **Reserved for basemaps — other services must NOT bind it.** |
| 8093 | Optional weather gateway | `services/wx` value-tile gateway (Open-Meteo). Must use :8093, never :8091 (WX-15). |
| 8095 | Optional basemap-fill proxy | Online Sentinel-2 fill/cache service. |
| 9001+ | Private development servers | Recommended for local agent/test runs. |

## Public-Alpha Rule

Run examples on a private port:

```bash
scripts/start-helm.sh --port 8080 --weather --fill
```

For BYO MBTiles, point the helper at a local directory:

```bash
HELM_MBTILES_DIR="$HOME/Charts/mbtiles" \
  python3 pipeline/mbtiles_server.py 8091
```

Commercial, proprietary, or personally acquired chart packs must stay local and
must not be committed to this repository.
