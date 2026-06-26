#!/usr/bin/env python3
"""
helm-wx — the met-ocean / data-layer gateway (clean-IP microservice)
====================================================================
A standalone, permissively-licensed service that turns external weather sources into Helm's
VALUE-ENCODED Mercator tiles on demand — the online counterpart of pipeline/make_value_tiles.py.

WHY IT EXISTS (the architecture, see docs/decisions/0006/0009 + docs/ARCHITECTURE.md):
  • The GPL OpenCPN/S-52 engine is quarantined behind the wire (arm's-length containment). This
    service is the OPPOSITE corner — net-new, clean IP (FastAPI + httpx + Python stdlib only; no GPL,
    no OpenCPN) — a brick in the POST-GPL data plane, not the legacy core.
  • It is the seam where map data layers enter Helm. Today: Open-Meteo. Tomorrow: the S-100 met-ocean
    product specs (S-411 wind/pressure, S-412 waves, S-104 water level, S-111 currents) plug in here,
    beside the planned permissive S-101 chart rebuild. The client never changes — it just consumes
    helm-wxv1 tiles over HTTP.
  • "Fetch once, serve many" (what Windy does): a coarse source grid is fetched per coarse cell and
    cached; every output tile in that cell is baked from it. One client or twenty, panning or zooming,
    we touch Open-Meteo only when we move into a genuinely new area or the cache ages out.

CONTRACT (mirrors web/wx-value-codec.js + pipeline/make_value_tiles.py — "helm-wxv1"):
  GET /{layer}/manifest.json     -> {encoding, scale, offset, ramp, bbox, minzoom, maxzoom, unit, ...}
  GET /{layer}/{z}/{x}/{y}.png   -> 256x256 RGBA; RGB = 24-bit value, A = NODATA mask (0 = no data)
      value = offset + ((R<<16)|(G<<8)|B) * scale     (decoded + colourised client-side by cog.js)
  GET /index.json                -> layer catalogue for the UI picker
  GET /health

HONESTY: never fabricates a value to fill a gap (NODATA stays transparent). On a provider 429/outage
we serve stale cache if we have it, else fail honestly — we do NOT invent weather. NOT FOR NAVIGATION.

Run:  uvicorn app:app --port 8091      (deps: pip install -r requirements.txt)
"""
import asyncio
import json
import math
import os
import hashlib
import struct
import time
import zlib
from typing import Dict, List, Optional, Tuple

import httpx
import numpy as np
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# ------------------------------------------------------------------ config
VMAX24 = 0xFFFFFF
ENCODING = "helm-wxv1"


def _load_dotenv():
    """Load services/wx/.env (gitignored) into the environment if present — so the API key lives in a
    local secret file, never in source/git. Real env vars win (setdefault)."""
    p = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_dotenv()
# Open-Meteo endpoint. With a commercial key (HELM_WX_OPENMETEO_KEY in the ENV/.env — never in source/git)
# we use the customer host + &apikey (1M calls/mo, no daily cap); otherwise the free, daily-capped host.
OPENMETEO_KEY = os.environ.get("HELM_WX_OPENMETEO_KEY", "").strip()
FORECAST = ("https://customer-api.open-meteo.com/v1/forecast" if OPENMETEO_KEY
            else "https://api.open-meteo.com/v1/forecast")
# Marine endpoint (waves/swell/sst/currents) — same key, different host. Marine layers carry marine:True.
MARINE = ("https://customer-marine-api.open-meteo.com/v1/marine" if OPENMETEO_KEY
          else "https://marine-api.open-meteo.com/v1/marine")
KMH2KN = 0.539957
CACHE_DIR = os.environ.get("HELM_WX_CACHE", os.path.join(os.path.dirname(__file__), "cache"))
TTL = int(os.environ.get("HELM_WX_TTL", "1800"))            # a fetched grid / baked tile is reusable for 30 min
COOLDOWN = int(os.environ.get("HELM_WX_COOLDOWN", "300"))   # after a 429 we serve cache only for 5 min
DATA_Z_MAX = int(os.environ.get("HELM_WX_DATA_Z", "7"))     # manifest maxzoom — the client overzooms (scales) beyond
# We fetch SOURCE grids at this COARSE zoom and bake every finer tile from them, so a whole viewport is
# 1–few grid fetches, not one-per-tile ("fetch once, serve many"). Coarser => fewer Open-Meteo calls but
# a softer field; the animated particles carry the fine detail. (The truly world-class fix is GRIB model
# ingestion — one download per run, full resolution, zero per-tile calls — see README "Phase 2".)
FETCH_Z = int(os.environ.get("HELM_WX_FETCH_Z", "5"))
GRID_N = int(os.environ.get("HELM_WX_GRID_N", "12"))        # source-grid resolution per coarse cell (GRID_N x GRID_N pts)
# NOTE: GRID_N**2 points go in ONE Open-Meteo GET; >~150 points overflows the URI (HTTP 414). 12x12=144
# is the safe max (matches web/wx-live.js). Finer detail comes from a finer FETCH_Z (smaller cells), not N.
TILE_MEM_MAX = int(os.environ.get("HELM_WX_TILE_MEM", "400"))
TIMEOUT = float(os.environ.get("HELM_WX_TIMEOUT", "12"))
# Throttle is key-aware: the commercial key (1M/mo) tolerates bursts, so fetch a viewport's cells in
# parallel for a faster first paint; the free tier stays conservative to avoid 429s.
CONCURRENCY = int(os.environ.get("HELM_WX_CONCURRENCY", "6" if OPENMETEO_KEY else "2"))
MIN_INTERVAL = float(os.environ.get("HELM_WX_MIN_INTERVAL", "0.05" if OPENMETEO_KEY else "0.2"))
USER_AGENT = "helm-wx/0.1 (+https://github.com/StevenRidder/Helm; marine chartplotter, cached client)"

# Per-layer config. scale/offset are FIXED per layer (from a sensible physical [vmin,vmax]) so colours
# and decoded values are comparable across EVERY tile and session — like Windy's fixed scales, and
# unlike the offline baker's per-pack min/max. Ramps mirror web/wx-live.js so Live and tiles agree.
LAYERS: Dict[str, dict] = {
    "wind":     {"v": "wind_speed_10m", "dir": "wind_direction_10m", "vector": True, "unit": "kn", "vmin": 0.0, "vmax": 80.0,
                 "stops": [[0, [98, 113, 183]], [5, [57, 131, 168]], [10, [52, 171, 151]], [16, [123, 183, 80]],
                           [22, [225, 200, 60]], [30, [232, 130, 50]], [40, [214, 70, 74]], [55, [150, 60, 150]]]},
    "gust":     {"v": "wind_gusts_10m", "unit": "kn", "vmin": 0.0, "vmax": 100.0,
                 "stops": [[0, [56, 189, 248]], [10, [45, 212, 191]], [20, [250, 204, 21]], [30, [249, 115, 22]],
                           [42, [239, 68, 68]], [60, [217, 33, 154]]]},
    "temp":     {"v": "temperature_2m", "unit": "°C", "vmin": -40.0, "vmax": 50.0,
                 "stops": [[-10, [70, 90, 200]], [0, [80, 180, 235]], [10, [70, 200, 130]], [20, [245, 205, 60]],
                           [30, [240, 120, 40]], [42, [210, 40, 40]]]},
    "pressure": {"v": "pressure_msl", "unit": "hPa", "vmin": 950.0, "vmax": 1050.0,
                 "stops": [[980, [120, 80, 200]], [1000, [80, 160, 230]], [1013, [120, 205, 140]],
                           [1025, [240, 200, 80]], [1040, [230, 110, 55]]]},
    "rain":     {"v": "precipitation", "unit": "mm", "vmin": 0.0, "vmax": 50.0,
                 "stops": [[0, [80, 160, 220, 0]], [0.2, [90, 180, 255, 0.55]], [2, [40, 120, 235, 0.8]],
                           [6, [120, 90, 235, 0.85]], [15, [175, 60, 200, 0.9]]]},
    "clouds":   {"v": "cloud_cover", "unit": "%", "vmin": 0.0, "vmax": 100.0,
                 "stops": [[0, [150, 170, 190, 0]], [40, [200, 210, 222, 0.4]], [80, [235, 240, 246, 0.75]],
                           [100, [250, 252, 255, 0.9]]]},
    "cape":     {"v": "cape", "unit": "J/kg", "vmin": 0.0, "vmax": 4000.0,
                 "stops": [[0, [56, 160, 200, 0]], [300, [120, 200, 120, 0.5]], [1000, [245, 205, 60, 0.8]],
                           [2500, [240, 120, 40, 0.9]], [4000, [220, 40, 40, 0.95]]]},
    # MARINE layers — Open-Meteo Marine API (marine:True). NODATA over land falls out as transparent.
    "sst":      {"v": "sea_surface_temperature", "marine": True, "unit": "°C", "vmin": 0.0, "vmax": 35.0,
                 "stops": [[0, [70, 90, 200]], [10, [80, 180, 235]], [18, [70, 200, 150]], [24, [245, 205, 60]],
                           [30, [240, 120, 40]], [35, [210, 40, 40]]]},
    "waves":    {"v": "wave_height", "marine": True, "unit": "m", "vmin": 0.0, "vmax": 12.0,
                 "stops": [[0, [60, 110, 180, 0.15]], [1, [60, 160, 190, 0.6]], [2.5, [80, 200, 140, 0.8]],
                           [4, [235, 205, 70, 0.85]], [6, [235, 130, 50, 0.9]], [9, [210, 50, 60, 0.95]]]},
    "swell":    {"v": "swell_wave_height", "marine": True, "unit": "m", "vmin": 0.0, "vmax": 10.0,
                 "stops": [[0, [60, 110, 180, 0.15]], [1, [70, 150, 200, 0.6]], [2.5, [90, 190, 160, 0.8]],
                           [4, [230, 200, 80, 0.85]], [6, [230, 120, 60, 0.9]], [8, [200, 50, 70, 0.95]]]},
    "current":  {"v": "ocean_current_velocity", "dir": "ocean_current_direction", "vector": True, "conv": "kmh2kn",
                 "dir_to": True,                            # ocean-current direction is TOWARD (oceanographic), unlike wind (FROM)
                 "marine": True, "unit": "kn", "vmin": 0.0, "vmax": 3.0,   # ocean currents are weak (0–2 kn); vmax 3 + a
                 "stops": [[0, [60, 120, 200, 0.4]], [0.3, [70, 175, 200, 0.65]], [0.8, [90, 200, 150, 0.8]],
                           [1.5, [240, 210, 70, 0.88]], [2.2, [240, 130, 50, 0.92]], [3, [215, 50, 60, 0.95]]]},  # visible low end like Windy
}
MODEL_NAME = "Open-Meteo (GFS-seamless)"
MARINE_MODEL = "Open-Meteo Marine"


def layer_scale_offset(cfg: dict) -> Tuple[float, float]:
    vmin, vmax = float(cfg["vmin"]), float(cfg["vmax"])
    scale = (vmax - vmin) / VMAX24 if vmax > vmin else 1.0
    return scale, vmin


# ------------------------------------------------------------------ web mercator (mirrors make_value_tiles.py)
def lonlat_to_tile(lon: float, lat: float, z: int) -> Tuple[float, float]:
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    lat = max(-85.05112878, min(85.05112878, lat))
    lr = math.radians(lat)
    y = (1.0 - math.log(math.tan(lr) + 1.0 / math.cos(lr)) / math.pi) / 2.0 * n
    return x, y


def pixel_to_lonlat(z: int, xt: int, yt: int, px: float, py: float, size: int = 256) -> Tuple[float, float]:
    n = 2 ** z
    x = xt + px / size
    y = yt + py / size
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def tile_bounds(z: int, xt: int, yt: int) -> Tuple[float, float, float, float]:
    """(west, south, east, north) of tile (z,xt,yt)."""
    w, n = pixel_to_lonlat(z, xt, yt, 0, 0)
    e, s = pixel_to_lonlat(z, xt, yt, 256, 256)
    return w, s, e, n


# ------------------------------------------------------------------ helm-wxv1 encode + PNG (stdlib; mirrors the codec)
def encode_value(v: float, scale: float, offset: float) -> Tuple[int, int, int]:
    n = int(round((v - offset) / (scale if scale > 0 else 1.0)))
    n = 0 if n < 0 else (VMAX24 if n > VMAX24 else n)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def write_png_bytes(buf: bytes, size: int = 256, alpha: bool = True) -> bytes:
    ch = 4 if alpha else 3
    stride = size * ch
    raw = bytearray()
    for row in range(size):
        raw.append(0)                                   # filter type 0 (None)
        raw.extend(buf[row * stride:(row + 1) * stride])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6 if alpha else 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


# ------------------------------------------------------------------ source grid (coarse Open-Meteo data)
class Grid:
    """A coarse NxN field over a bbox: row-major, row0=north, col0=west. Bilinear sample, NODATA-honest."""
    def __init__(self, nx, ny, west, south, east, north, values):
        self.nx, self.ny = nx, ny
        self.west, self.south, self.east, self.north = west, south, east, north
        self.values = values

    def sample(self, lon: float, lat: float) -> Optional[float]:
        fx = (lon - self.west) / ((self.east - self.west) or 1) * (self.nx - 1)
        fy = (self.north - lat) / ((self.north - self.south) or 1) * (self.ny - 1)
        if fx < -0.001 or fx > self.nx - 1 + 0.001 or fy < -0.001 or fy > self.ny - 1 + 0.001:
            return None
        x0 = max(0, min(self.nx - 1, int(math.floor(fx))))
        y0 = max(0, min(self.ny - 1, int(math.floor(fy))))
        x1 = min(self.nx - 1, x0 + 1)
        y1 = min(self.ny - 1, y0 + 1)
        gx, gy = fx - x0, fy - y0
        v = self.values
        v00, v10 = v[y0 * self.nx + x0], v[y0 * self.nx + x1]
        v01, v11 = v[y1 * self.nx + x0], v[y1 * self.nx + x1]
        if None in (v00, v10, v01, v11):
            # nearest valid corner rather than NaN-propagate; fully-missing -> None
            cand = [c for c in (v00, v10, v01, v11) if c is not None]
            if not cand:
                return None
            return cand[0]
        return (v00 * (1 - gx) + v10 * gx) * (1 - gy) + (v01 * (1 - gx) + v11 * gx) * gy


# ------------------------------------------------------------------ caches + provider state
_grids: Dict[str, Tuple[Grid, float]] = {}
_grid_locks: Dict[str, asyncio.Lock] = {}
_tiles: "OrderedTileCache" = None  # set below
_cooldown_until = 0.0
_stats = {"openmeteo_calls": 0, "grid_hits": 0, "tile_hits": 0, "bakes": 0, "cooldowns": 0}
_om_sem: Optional[asyncio.Semaphore] = None       # bounds concurrent Open-Meteo calls (lazy: needs a loop)
_om_last = 0.0                                     # timestamp of the last call (for MIN_INTERVAL spacing)


class OrderedTileCache:
    """Tiny in-memory LRU of baked PNG bytes, mirrored to disk so restarts/offline keep coverage."""
    def __init__(self, cap: int):
        self.cap = cap
        self.mem: Dict[str, Tuple[bytes, float]] = {}
        self.order: List[str] = []

    def _disk(self, key: str) -> str:
        return os.path.join(CACHE_DIR, "tiles", key + ".png")

    def get(self, key: str) -> Optional[bytes]:
        now = time.time()
        v = self.mem.get(key)
        if v and now - v[1] <= TTL:
            return v[0]
        p = self._disk(key)
        try:
            if os.path.exists(p) and now - os.path.getmtime(p) <= TTL:
                data = open(p, "rb").read()
                self.put(key, data, persist=False)
                return data
        except OSError:
            pass
        return None

    def put(self, key: str, data: bytes, persist: bool = True):
        self.mem[key] = (data, time.time())
        self.order.append(key)
        while len(self.mem) > self.cap:
            old = self.order.pop(0)
            self.mem.pop(old, None)
        if persist:
            p = self._disk(key)
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(data)
            except OSError:
                pass


_tiles = OrderedTileCache(TILE_MEM_MAX)


def _coarse_cell(z: int, x: int, y: int) -> Tuple[int, int, int]:
    """The source-grid cell a tile bakes from — its ancestor at the COARSE FETCH_Z, so many tiles share
    one grid fetch ("fetch once, serve many"). At z <= FETCH_Z the tile is its own cell."""
    if z <= FETCH_Z:
        return z, x, y
    d = z - FETCH_Z
    return FETCH_Z, x >> d, y >> d


async def _fetch_grid(layer: str, cz: int, cx: int, cy: int) -> Grid:
    """Fetch ONE coarse Open-Meteo grid over a coarse cell (+small margin). Honest: raises on 429/error."""
    global _cooldown_until
    cfg = LAYERS[layer]
    w, s, e, n = tile_bounds(cz, cx, cy)
    mw, mh = (e - w) * 0.08, (n - s) * 0.08          # small overlap so child-tile edges interpolate cleanly
    w, e = w - mw, e + mw
    s, n = max(-85.0, s - mh), min(85.0, n + mh)
    lats, lons = [], []
    for j in range(GRID_N):
        lats.append(n - (n - s) * j / (GRID_N - 1))
    for i in range(GRID_N):
        lons.append(w + (e - w) * i / (GRID_N - 1))
    qlat, qlon = [], []
    for la in lats:
        for lo in lons:
            qlat.append(round(la, 3))                                      # 3dp keeps the URI short (HTTP 414 guard)
            qlon.append(round(((lo + 180) % 360 + 360) % 360 - 180, 3))   # wrap for the API (antimeridian-safe)
    params = {
        "latitude": ",".join(str(v) for v in qlat),
        "longitude": ",".join(str(v) for v in qlon),
        "current": cfg["v"],
    }
    if OPENMETEO_KEY:
        params["apikey"] = OPENMETEO_KEY
    if layer in ("wind", "gust"):
        params["wind_speed_unit"] = "kn"
    endpoint = MARINE if cfg.get("marine") else FORECAST   # waves/swell/sst/currents come from the Marine API
    # Be a polite client: cap concurrency + space calls, so a viewport's burst of cell-fetches doesn't
    # hammer Open-Meteo (what tripped the 429s before caching+throttling).
    global _om_sem, _om_last
    if _om_sem is None:
        _om_sem = asyncio.Semaphore(CONCURRENCY)
    async with _om_sem:
        gap = MIN_INTERVAL - (time.time() - _om_last)
        if gap > 0:
            await asyncio.sleep(gap)
        _om_last = time.time()
        _stats["openmeteo_calls"] += 1
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(endpoint, params=params)
    if r.status_code == 429:
        _cooldown_until = time.time() + COOLDOWN
        _stats["cooldowns"] += 1
        raise RuntimeError("open-meteo 429 (hourly limit) — cooling down")
    r.raise_for_status()
    nodes = r.json()
    if not isinstance(nodes, list):
        nodes = [nodes]
    conv = cfg.get("conv")
    vals: List[Optional[float]] = []
    for node in nodes:
        cur = (node or {}).get("current") or {}
        v = cur.get(cfg["v"])
        if isinstance(v, (int, float)):
            vals.append(float(v) * KMH2KN if conv == "kmh2kn" else float(v))
        else:
            vals.append(None)                            # NODATA (land for an ocean-only layer) — never faked
    return Grid(GRID_N, GRID_N, lons[0], lats[-1], lons[-1], lats[0], vals)


async def get_grid(layer: str, cz: int, cx: int, cy: int) -> Grid:
    """Cached + deduped coarse grid. Serves stale on cooldown; one fetch per cell feeds many tiles."""
    key = "%s|z%d|%d|%d" % (layer, cz, cx, cy)
    now = time.time()
    hit = _grids.get(key)
    if hit and now - hit[1] <= TTL:
        _stats["grid_hits"] += 1
        return hit[0]
    if now < _cooldown_until:
        if hit:                                       # stale-but-present beats hammering a rate-limited API
            _stats["grid_hits"] += 1
            return hit[0]
        raise RuntimeError("rate-limited (cooldown) and no cached grid")
    lock = _grid_locks.setdefault(key, asyncio.Lock())
    async with lock:                                  # coalesce concurrent identical fetches
        hit = _grids.get(key)
        if hit and time.time() - hit[1] <= TTL:
            return hit[0]
        try:
            grid = await _fetch_grid(layer, cz, cx, cy)
        except Exception:
            if hit:
                return hit[0]                         # any failure -> serve stale if we can
            raise
        _grids[key] = (grid, time.time())
        return grid


# ---------------------------------------------------------------- dense REGIONAL ingestion (Windy parity)
# Fetch a HIGH-RES grid over the boat's region ONCE (batched), cache it, and bake every tile in that
# region from it -> native-resolution (Copernicus ~8 km) detail at EVERY zoom, like Windy's pre-baked CDN.
# Outside the region we fall back to the coarse on-demand path. A boat only needs its own area, and the
# region follows you (re-warm on a schedule). Same Open-Meteo data, no new deps, fits the keyed budget.
REGION_TTL = int(os.environ.get("HELM_WX_REGION_TTL", "10800"))    # 3 h (fields change slowly)
REGION_RES = float(os.environ.get("HELM_WX_REGION_RES", "0.1"))    # ~11 km sampling (~Copernicus native)
_regions: Dict[str, dict] = {}                                     # layer -> {bbox, grid, vel, t}
_region_lock = asyncio.Lock()


def _region_covers(reg, cz, cx, cy) -> bool:
    w, s, e, n = tile_bounds(cz, cx, cy)
    rw, rs, re_, rn = reg["bbox"]
    return rw <= w and re_ >= e and rs <= s and rn >= n


async def _fetch_points(layer: str, qlat, qlon):
    """One batched (<=~140-pt) Open-Meteo request -> list of nodes. Throttled + keyed; raises on 429."""
    global _om_sem, _om_last, _cooldown_until
    cfg = LAYERS[layer]
    cur = cfg["v"] + ("," + cfg["dir"] if cfg.get("dir") else "")
    params = {"latitude": ",".join(str(round(a, 3)) for a in qlat),
              "longitude": ",".join(str(round(((o + 180) % 360 + 360) % 360 - 180, 3)) for o in qlon),
              "current": cur}
    if not cfg.get("marine"):
        params["wind_speed_unit"] = "kn"
    if OPENMETEO_KEY:
        params["apikey"] = OPENMETEO_KEY
    endpoint = MARINE if cfg.get("marine") else FORECAST
    if _om_sem is None:
        _om_sem = asyncio.Semaphore(CONCURRENCY)
    async with _om_sem:
        gap = MIN_INTERVAL - (time.time() - _om_last)
        if gap > 0:
            await asyncio.sleep(gap)
        _om_last = time.time()
        _stats["openmeteo_calls"] += 1
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(endpoint, params=params)
    if r.status_code == 429:
        _cooldown_until = time.time() + COOLDOWN
        raise RuntimeError("open-meteo 429")
    r.raise_for_status()
    nodes = r.json()
    return nodes if isinstance(nodes, list) else [nodes]


async def warm_region(layer: str, w: float, s: float, e: float, n: float, res: float = REGION_RES):
    """Ingest a dense grid over (w,s,e,n) into _regions[layer] — the source for Windy-parity tiles there."""
    cfg = LAYERS[layer]
    conv = cfg.get("conv"); sign = 1.0 if cfg.get("dir_to") else -1.0; D2R = math.pi / 180.0
    nx = max(2, int(round((e - w) / res)) + 1)
    ny = max(2, int(round((n - s) / res)) + 1)
    lats = [n - (n - s) * j / (ny - 1) for j in range(ny)]
    lons = [w + (e - w) * i / (nx - 1) for i in range(nx)]
    pts = [(j, i) for j in range(ny) for i in range(nx)]
    vals: List[Optional[float]] = [None] * (nx * ny)
    us = [0.0] * (nx * ny); vs = [0.0] * (nx * ny)
    BATCH = 140

    async def do_batch(chunk):
        nodes = await _fetch_points(layer, [lats[j] for (j, i) in chunk], [lons[i] for (j, i) in chunk])
        for k, (j, i) in enumerate(chunk):
            c = (nodes[k] or {}).get("current") or {}
            v = c.get(cfg["v"])
            if isinstance(v, (int, float)):
                vv = float(v) * KMH2KN if conv == "kmh2kn" else float(v)
                vals[j * nx + i] = vv
                if cfg.get("dir"):
                    d = c.get(cfg["dir"]); d = float(d) if isinstance(d, (int, float)) else 0.0
                    us[j * nx + i] = sign * vv * math.sin(d * D2R)
                    vs[j * nx + i] = sign * vv * math.cos(d * D2R)

    await asyncio.gather(*[do_batch(pts[b:b + BATCH]) for b in range(0, len(pts), BATCH)])
    reg = {"bbox": (w, s, e, n), "grid": Grid(nx, ny, lons[0], lats[-1], lons[-1], lats[0], vals), "t": time.time()}
    if cfg.get("vector"):
        hdr = {"nx": nx, "ny": ny, "lo1": lons[0], "la1": lats[0], "lo2": lons[-1], "la2": lats[-1],
               "dx": (lons[-1] - lons[0]) / (nx - 1), "dy": (lats[0] - lats[-1]) / (ny - 1)}
        reg["vel"] = [{"header": dict(parameterNumber=2, **hdr), "data": us},
                      {"header": dict(parameterNumber=3, **hdr), "data": vs}]
    _regions[layer] = reg
    # Invalidate this layer's already-baked tiles so they re-bake from the dense grid (else cache wins).
    import shutil
    for k in [k for k in _tiles.order if k.startswith(layer + "/")]:
        _tiles.mem.pop(k, None)
    _tiles.order = [k for k in _tiles.order if not k.startswith(layer + "/")]
    shutil.rmtree(os.path.join(CACHE_DIR, "tiles", layer), ignore_errors=True)
    for k in [k for k in list(_vel) if k.startswith("vel|" + layer + "|")]:
        _vel.pop(k, None)
    return {"layer": layer, "nx": nx, "ny": ny, "points": nx * ny, "res_deg": res, "bbox": [w, s, e, n]}


async def bake_tile(layer: str, z: int, x: int, y: int) -> bytes:
    """Bake (or cache-hit) one helm-wxv1 value tile. PNG bytes, 256x256 RGBA."""
    return await _bake_tile_impl(layer, z, x, y)


def _bake_np(grid: "Grid", lons, lats, scale: float, offset: float):
    """Vectorised bilinear sample + helm-wxv1 encode of a 256x256 tile. Returns (rgba_bytes, any_valid).
    NaN (NODATA — land for ocean layers, gaps) -> alpha 0; never faked."""
    nx, ny = grid.nx, grid.ny
    gv = np.array([np.nan if v is None else v for v in grid.values], dtype=np.float64).reshape(ny, nx)
    ew = (grid.east - grid.west) or 1.0
    ns = (grid.north - grid.south) or 1.0
    fx = np.clip((lons - grid.west) / ew * (nx - 1), 0, nx - 1)
    fy = np.clip((grid.north - lats) / ns * (ny - 1), 0, ny - 1)
    x0 = np.floor(fx).astype(np.intp); x1 = np.minimum(x0 + 1, nx - 1)
    y0 = np.floor(fy).astype(np.intp); y1 = np.minimum(y0 + 1, ny - 1)
    gx = fx - x0; gy = fy - y0
    X0, Y0 = np.meshgrid(x0, y0); X1, Y1 = np.meshgrid(x1, y1)
    GX, GY = np.meshgrid(gx, gy)
    v00 = gv[Y0, X0]; v10 = gv[Y0, X1]; v01 = gv[Y1, X0]; v11 = gv[Y1, X1]
    # NaN-aware bilinear: a NODATA corner (land for an ocean layer) contributes 0 weight, so ocean pixels
    # next to the coast still render from the valid corners; only an all-NODATA cell stays transparent.
    w00 = (1 - GX) * (1 - GY) * (~np.isnan(v00)); w10 = GX * (1 - GY) * (~np.isnan(v10))
    w01 = (1 - GX) * GY * (~np.isnan(v01)); w11 = GX * GY * (~np.isnan(v11))
    den = w00 + w10 + w01 + w11
    num = (np.nan_to_num(v00) * w00 + np.nan_to_num(v10) * w10
           + np.nan_to_num(v01) * w01 + np.nan_to_num(v11) * w11)
    valid = den > 0
    val = num / np.where(valid, den, 1.0)
    s = scale if scale > 0 else 1.0
    n = np.clip(np.round((np.nan_to_num(val) - offset) / s), 0, VMAX24).astype(np.uint32)
    rgba = np.empty((256, 256, 4), dtype=np.uint8)
    rgba[..., 0] = (n >> 16) & 255
    rgba[..., 1] = (n >> 8) & 255
    rgba[..., 2] = n & 255
    rgba[..., 3] = np.where(valid, 255, 0).astype(np.uint8)
    return rgba.tobytes(), bool(valid.any())


async def _bake_tile_impl(layer: str, z: int, x: int, y: int) -> bytes:
    key = "%s/%d/%d/%d" % (layer, z, x, y)
    cached = _tiles.get(key)
    if cached is not None:
        _stats["tile_hits"] += 1
        return cached
    cfg = LAYERS[layer]
    scale, offset = layer_scale_offset(cfg)
    reg = _regions.get(layer)
    if reg and (time.time() - reg["t"]) <= REGION_TTL and _region_covers(reg, z, x, y):
        grid = reg["grid"]                               # dense regional grid covers this TILE -> native detail
    else:
        cz, cx, cy = _coarse_cell(z, x, y)
        grid = await get_grid(layer, cz, cx, cy)
    # Per-column lon, per-row lat (512 mercator unprojects, not 65 536), then VECTORISE the whole 256x256
    # bilinear+encode in numpy (was a multi-second Python loop -> a few ms). NODATA (NaN) stays transparent.
    lons = np.array([pixel_to_lonlat(z, x, y, px + 0.5, 0.0)[0] for px in range(256)])
    lats = np.array([pixel_to_lonlat(z, x, y, 0.0, py + 0.5)[1] for py in range(256)])
    buf, any_valid = _bake_np(grid, lons, lats, scale, offset)
    png = write_png_bytes(buf, 256, alpha=True)
    _stats["bakes"] += 1
    if any_valid:
        _tiles.put(key, png)                          # don't pollute cache with all-NODATA tiles
    return png


def manifest_for(layer: str) -> dict:
    cfg = LAYERS[layer]
    scale, offset = layer_scale_offset(cfg)
    return {
        "encoding": ENCODING, "bits": 24, "tileSize": 256,
        "layer": layer, "unit": cfg["unit"], "kind": "scalar",
        "scale": scale, "offset": offset, "nodata_alpha": 0, "has_alpha": True,
        "minzoom": 0, "maxzoom": DATA_Z_MAX,
        "bbox": [-180.0, -85.0, 180.0, 85.0],         # global — the gateway serves anywhere
        "global": True,                                # tells cog.js NOT to set source bounds (wrap across the dateline)
        "vmin": cfg["vmin"], "vmax": cfg["vmax"], "ramp": cfg["stops"],
        "source": "open-meteo", "model": MARINE_MODEL if cfg.get("marine") else MODEL_NAME,
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "times": None, "frames": None,
        "tiles_template": "{z}/{x}/{y}.png",
        "horizon": "good ~0–7 d; beyond is climatology", "confidence": "fair",
        "disclaimer": "Forecast — cross-reference official sources. NOT FOR NAVIGATION.",
    }


# ------------------------------------------------------------------ FastAPI app
app = FastAPI(title="helm-wx", version="0.1",
              description="Met-ocean / data-layer gateway — value-encoded weather tiles (helm-wxv1).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"ok": True, "service": "helm-wx", "encoding": ENCODING,
            "layers": list(LAYERS.keys()), "cooldown": time.time() < _cooldown_until, "stats": _stats}


@app.get("/index.json")
def index():
    return {"encoding": ENCODING, "layers": {
        k: {"unit": v["unit"], "source": "open-meteo", "model": MARINE_MODEL if v.get("marine") else MODEL_NAME,
            "minzoom": 0, "maxzoom": DATA_Z_MAX, "frames": 1, "manifest": "%s/manifest.json" % k}
        for k, v in LAYERS.items()}}


@app.get("/{layer}/manifest.json")
def manifest(layer: str):
    if layer not in LAYERS:
        return JSONResponse({"error": True, "reason": "unknown layer"}, status_code=404)
    return manifest_for(layer)


# ---- wind VELOCITY for the animated particle layer (leaflet-velocity u/v) — keyed + cached ----------
# The GPU particle layer (web/wind-layer.js) needs u/v, not a scalar tile. We fetch wind speed+direction
# over the (snapped) viewport server-side with the KEY, build u/v, and cache — so particles are live and
# animated everywhere WITHOUT the client ever touching the rate-capped free API or holding the key.
_vel: Dict[str, Tuple[list, float]] = {}
_vel_locks: Dict[str, asyncio.Lock] = {}


def _snap(w, s, e, n, step=2.0):
    fl = lambda x: math.floor(x / step) * step
    ce = lambda x: math.ceil(x / step) * step
    return fl(w), max(-84.0, fl(s)), ce(e), min(84.0, ce(n))


async def _fetch_velocity(layer, w, s, e, n, gn):
    global _cooldown_until, _om_last, _om_sem
    cfg = LAYERS[layer]
    spd_var, dir_var, conv = cfg["v"], cfg["dir"], cfg.get("conv")
    endpoint = MARINE if cfg.get("marine") else FORECAST
    sign = 1.0 if cfg.get("dir_to") else -1.0             # TOWARD (current) -> motion = +dir; FROM (wind) -> negate
    D2R = math.pi / 180.0
    lats = [n - (n - s) * j / (gn - 1) for j in range(gn)]
    lons = [w + (e - w) * i / (gn - 1) for i in range(gn)]
    qlat, qlon = [], []
    for la in lats:
        for lo in lons:
            qlat.append(round(la, 3))
            qlon.append(round(((lo + 180) % 360 + 360) % 360 - 180, 3))
    params = {"latitude": ",".join(str(v) for v in qlat), "longitude": ",".join(str(v) for v in qlon),
              "current": spd_var + "," + dir_var}
    if not cfg.get("marine"):
        params["wind_speed_unit"] = "kn"
    if OPENMETEO_KEY:
        params["apikey"] = OPENMETEO_KEY
    if _om_sem is None:
        _om_sem = asyncio.Semaphore(CONCURRENCY)
    async with _om_sem:
        gap = MIN_INTERVAL - (time.time() - _om_last)
        if gap > 0:
            await asyncio.sleep(gap)
        _om_last = time.time()
        _stats["openmeteo_calls"] += 1
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(endpoint, params=params)
    if r.status_code == 429:
        _cooldown_until = time.time() + COOLDOWN
        raise RuntimeError("open-meteo 429")
    r.raise_for_status()
    nodes = r.json()
    if not isinstance(nodes, list):
        nodes = [nodes]
    us, vs = [], []
    for node in nodes:
        cur = (node or {}).get("current") or {}
        spd = cur.get(spd_var)
        dr = cur.get(dir_var)
        spd = float(spd) if isinstance(spd, (int, float)) else 0.0
        dr = float(dr) if isinstance(dr, (int, float)) else 0.0
        if conv == "kmh2kn":
            spd *= KMH2KN
        us.append(sign * spd * math.sin(dr * D2R))      # wind: FROM (sign=-1); current: TOWARD (sign=+1)
        vs.append(sign * spd * math.cos(dr * D2R))
    hdr = {"nx": gn, "ny": gn, "lo1": lons[0], "la1": lats[0], "lo2": lons[-1], "la2": lats[-1],
           "dx": (lons[-1] - lons[0]) / (gn - 1), "dy": (lats[0] - lats[-1]) / (gn - 1)}
    return [{"header": dict(parameterNumber=2, **hdr), "data": us},
            {"header": dict(parameterNumber=3, **hdr), "data": vs}]


@app.get("/velocity/{layer}")
async def velocity(layer: str, w: float, s: float, e: float, n: float):
    cfg = LAYERS.get(layer)
    if not cfg or not cfg.get("vector"):
        return JSONResponse({"error": True, "reason": "velocity is for vector layers (wind, current)"}, status_code=404)
    if e < w:
        e += 360.0                                       # continuous across the antimeridian
    reg = _regions.get(layer)                            # dense regional particles (Windy parity) if the view is inside
    if reg and reg.get("vel") and (time.time() - reg["t"]) <= REGION_TTL:
        rw, rs, re_, rn = reg["bbox"]
        if rw <= w and re_ >= e and rs <= s and rn >= n:
            return reg["vel"]
    sw, ss, se, sn = _snap(w, s, e, n)                   # snap so nearby pans/zooms reuse one fetch
    key = "vel|%s|%.2f,%.2f,%.2f,%.2f" % (layer, sw, ss, se, sn)
    now = time.time()
    hit = _vel.get(key)
    if hit and now - hit[1] <= TTL:
        return hit[0]
    if now < _cooldown_until and hit:
        return hit[0]
    lock = _vel_locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _vel.get(key)
        if hit and time.time() - hit[1] <= TTL:
            return hit[0]
        try:
            vel = await _fetch_velocity(layer, sw, ss, se, sn, GRID_N)
        except Exception:
            if hit:
                return hit[0]
            return JSONResponse({"error": True, "reason": "velocity unavailable"}, status_code=503)
        _vel[key] = (vel, time.time())
        return vel


@app.get("/warm")
async def warm(layers: str, w: float, s: float, e: float, n: float, res: float = REGION_RES):
    """Dense-ingest a region so its tiles render at native (~Copernicus) resolution — Windy parity.
    e.g. /warm?layers=current,wind&w=170&s=-25&e=185&n=-10"""
    out = []
    async with _region_lock:
        for L in [x.strip() for x in layers.split(",") if x.strip()]:
            if L not in LAYERS:
                out.append({"layer": L, "error": "unknown layer"}); continue
            try:
                out.append(await warm_region(L, w, s, e, n, res))
            except Exception as ex:
                out.append({"layer": L, "error": str(ex)})
    return {"warmed": out}


@app.on_event("startup")
async def _startup_warm():
    """If HELM_WX_WARM_BBOX is set, dense-ingest the boat's region on boot + refresh every REGION_TTL."""
    bbox = os.environ.get("HELM_WX_WARM_BBOX", "").strip()
    if not bbox:
        return
    try:
        w, s, e, n = [float(x) for x in bbox.split(",")]
    except Exception:
        return
    layers = [x.strip() for x in os.environ.get("HELM_WX_WARM_LAYERS", "current,wind").split(",") if x.strip()]

    async def loop():
        while True:
            async with _region_lock:
                for L in layers:
                    if L in LAYERS:
                        try:
                            await warm_region(L, w, s, e, n)
                        except Exception:
                            pass
            await asyncio.sleep(REGION_TTL)
    asyncio.create_task(loop())


@app.get("/{layer}/{z}/{x}/{y}.png")
async def tile(layer: str, z: int, x: int, y: int, request: Request):
    if layer not in LAYERS:
        return PlainTextResponse("unknown layer", status_code=404)
    if z < 0 or z > 22 or x < 0 or y < 0 or x >= 2 ** z or y >= 2 ** z:
        return PlainTextResponse("tile out of range", status_code=404)
    try:
        png = await bake_tile(layer, z, x, y)
    except Exception as e:
        # honest failure: no cache + rate-limited/offline. The client's own fallback handles it.
        return PlainTextResponse("weather unavailable: %s" % e, status_code=503)
    # Mapbox-grade HTTP caching: strong ETag + conditional 304 so the browser/CDN revalidate cheaply
    # (no re-transfer of the ~200 KB PNG when the tile is unchanged) on top of max-age.
    etag = 'W/"%s"' % hashlib.md5(png).hexdigest()
    headers = {"Cache-Control": "public, max-age=%d" % TTL, "ETag": etag, "X-Helm-Encoding": ENCODING}
    inm = request.headers.get("if-none-match")
    if inm and etag in [t.strip() for t in inm.split(",")]:
        return Response(status_code=304, headers=headers)
    return Response(content=png, media_type="image/png", headers=headers)
