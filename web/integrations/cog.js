/*
 * Helm — integrations/cog.js   ·   maplibre-cog-protocol (geomatico)
 * --------------------------------------------------------------------------
 * Load a Cloud Optimized GeoTIFF straight into MapLibre via a `cog://` custom
 * protocol — no tiler, no mbtiles repack, just HTTP range reads off a static
 * .tif. This is the cheap path for BOTH halves of Helm: GRIB->COG is a one-step
 * GDAL convert (weather), and depth/imagery COGs stream the same way.
 *
 * The protocol also supports a `#color:...` URL fragment that colorizes a
 * value-encoded single-band COG client-side (the Mercator-style idea, applied
 * to a file instead of a tile pyramid).
 *
 * TWO requirements verified the hard way, both true of any real COG host:
 *   - the COG must be EPSG:3857 (Web Mercator). geotiff.js reads a 4326 file's
 *     coords AS METRES and lands it at the wrong place. pipeline/make_geotiff.py
 *     authors data/key-west-depth.tif in 3857.
 *   - the server must support HTTP Range requests (206). geotiff.js streams the
 *     COG with ranges; a server that returns the full file (e.g. a bare
 *     python -m http.server) errors "Server responded with full file".
 *
 * Local default below is that 3857 depth COG; swap for any COG (e.g. a GFS field
 * exported with `gdal_translate -of COG`). If it 404s the layer simply doesn't
 * draw — non-fatal.
 *
 * https://github.com/geomatico/maplibre-cog-protocol
 */
import { cogProtocol } from '@geomatico/maplibre-cog-protocol';

const SRC = 'helm-cog', LYR = 'helm-cog';
// Public geomatico demo COG — used only if no local file is available.
const DEMO_COG = 'cog://https://geomatico.github.io/maplibre-cog-protocol/sample/dem.tif#color:BrewerSpectral9,0,4000';
let protocolReady = false;

// Local depth GeoTIFF (pipeline/make_geotiff.py), single-band float32, colorized
// client-side by the #color: fragment — the value-encoded-file pattern, offline.
// Production: a true COG (gdal_translate -of COG) streamed via HTTP range reads.
function localCog() {
  return 'cog://' + new URL('data/key-west-depth.tif', location.href).href +
    '#color:BrewerSpectral9,-120,5';
}

export async function enable(map, ctx) {
  if (!protocolReady) { ctx.maplibregl.addProtocol('cog', cogProtocol); protocolReady = true; }
  if (map.getLayer(LYR)) { map.setLayoutProperty(LYR, 'visibility', 'visible'); return; }

  // Prefer the local depth COG; fall back to the public demo if it's missing.
  let url = ctx.cogUrl || localCog();
  try {
    const probe = await fetch('data/key-west-depth.tif', { method: 'GET', headers: { Range: 'bytes=0-3' } });
    if (!probe.ok) throw new Error(String(probe.status));
  } catch (e) { url = DEMO_COG; }

  map.addSource(SRC, { type: 'raster', url, tileSize: 256 });
  map.addLayer({ id: LYR, type: 'raster', source: SRC,
    paint: { 'raster-opacity': 0, 'raster-opacity-transition': { duration: 500 } } }, ctx.beforeId);
  requestAnimationFrame(() => { if (map.getLayer(LYR)) map.setPaintProperty(LYR, 'raster-opacity', 0.8); });
  ctx.notify('COG depth overlay via cog:// protocol (no tiler)', 'ok');
}

export function disable(map) {
  if (map.getLayer(LYR)) map.setLayoutProperty(LYR, 'visibility', 'none');
}


/* ============================================================================================
 * WX-10 — VALUE-ENCODED (Mercator) weather tiles.
 * --------------------------------------------------------------------------------------------
 * The depth-COG path above streams ONE static value-encoded COG. This section is the general
 * weather contract: a Web-Mercator XYZ pyramid of value-encoded tiles (pipeline/make_value_tiles.py,
 * encoding "helm-wxv1" in web/wx-value-codec.js) decoded + colourised CLIENT-SIDE via a custom
 * `helmwx://` MapLibre protocol — and the SAME tiles answer a deterministic sample(lat,lon,t) probe
 * (the face ROUTING-3's spacetime probe and AI-5's layer sample() consume). One source of truth:
 * the heatmap you see and the number the probe reads are decoded from identical pixels.
 *
 * Honesty (docs/VISION.md): NODATA pixels (alpha<128) are transparent and sample as a null value
 * with a "verify locally" note — Helm never fakes a value to fill a gap; every sample carries its
 * model name + valid-time + horizon/confidence so a consumer can show provenance.
 * ============================================================================================ */

const WXP = 'helmwx';                  // custom protocol scheme: helmwx://<setId>/<frame>/{z}/{x}/{y}
const WX_SRC = 'helm-wx-grib', WX_LYR = 'helm-wx-grib';
const RAW_CACHE_MAX = 96;              // bound decoded-tile memory (per set)
let wxProtoReady = false;
let wxActiveKey = null;
const wxSets = Object.create(null);    // setId -> { cfg, baseDir, rawCache:Map<string,{values,w,h}|null>, order:[] }
let _transparent = null;

function codec() { return (typeof globalThis !== 'undefined' ? globalThis : self).HelmWxCodec; }
function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas'); c.width = w; c.height = h; return c;
}
async function decodeImageData(blob) {
  const bmp = await createImageBitmap(blob);
  const cv = makeCanvas(bmp.width, bmp.height), cx = cv.getContext('2d', { willReadFrequently: true });
  cx.drawImage(bmp, 0, 0);
  const id = cx.getImageData(0, 0, bmp.width, bmp.height);
  if (bmp.close) bmp.close();
  return id;
}
async function transparentTile() {
  if (_transparent) return _transparent;
  const cv = makeCanvas(256, 256);     // a fully-transparent tile (no data here)
  _transparent = await createImageBitmap(cv);
  return _transparent;
}
function effFrame(cfg, frame) {                 // the clamped, in-range frame index (used for BOTH key + path)
  if (!cfg.times || !cfg.times.length) return null;
  return Math.max(0, Math.min(cfg.times.length - 1, frame | 0));
}
function touch(set, key) {                       // move-to-end → true LRU recency on a hit
  const i = set.order.indexOf(key);
  if (i >= 0) set.order.splice(i, 1);
  set.order.push(key);
}

// Fetch + decode ONE raw value tile into a flat values grid (NaN = NODATA). Cached per set so the
// colourising protocol and the sample() probe share decoded pixels. In-flight requests are de-duped
// (a worldline of probe points hitting the same tile fetches once). A genuine absence (HTTP 404 =
// outside the baked pyramid) is cached as a real gap; a TRANSIENT failure (offline/abort) is NOT
// cached, so connectivity recovery re-probes instead of poisoning the region with false "no data".
async function wxFetchRaw(set, frame, z, x, y, signal) {
  const f = effFrame(set.cfg, frame);
  const key = f + '/' + z + '/' + x + '/' + y;
  if (set.rawCache.has(key)) { touch(set, key); return set.rawCache.get(key); }
  if (set.inflight.has(key)) return set.inflight.get(key);
  const sub = f == null ? '' : 't' + f + '/';
  const url = set.baseDir + sub + z + '/' + x + '/' + y + '.png';
  const p = (async () => {
    let tile = null, cacheable = true;
    try {
      const r = await fetch(url, signal ? { signal } : undefined);
      if (r.ok) {
        const id = await decodeImageData(await r.blob());
        const C = codec(), cfg = set.cfg, d = id.data, n = id.width * id.height;
        const values = new Float64Array(n);
        for (let i = 0; i < n; i++) {
          const v = C.decodeRGBA(d[i * 4], d[i * 4 + 1], d[i * 4 + 2], d[i * 4 + 3], cfg.scale, cfg.offset);
          values[i] = v == null ? NaN : v;   // NODATA -> NaN (bilinear + colourise treat as a gap)
        }
        tile = { values, w: id.width, h: id.height };
      } else if (r.status !== 404) {
        cacheable = false;                     // 5xx/etc — transient, allow a later retry
      }                                        // 404 → genuine absence (outside the pyramid) → cache the gap
    } catch (e) {
      cacheable = false;                       // offline / AbortError — transient, do not poison the cache
    }
    set.inflight.delete(key);
    if (cacheable) {
      set.rawCache.set(key, tile); set.order.push(key);
      while (set.order.length > RAW_CACHE_MAX) { const ev = set.order.shift(); if (set.order.indexOf(ev) < 0) set.rawCache.delete(ev); }
    }
    return tile;
  })();
  set.inflight.set(key, p);
  return p;
}

// The custom protocol: MapLibre asks for helmwx://setId/frame/z/x/y; we fetch the raw value tile,
// decode each pixel's value, paint it through the layer's colour ramp, and hand back the image.
// MapLibre 5.x passes (requestParameters, abortController); we thread the abort signal so stale
// tiles (fast pan / frame scrub) stop fetching + decoding.
async function wxProtocol(params, abortController) {
  const m = /^helmwx:\/\/([^/]+)\/(\d+)\/(\d+)\/(\d+)\/(\d+)/.exec(params.url);
  if (!m) { if (!wxProtocol._warned) { wxProtocol._warned = true; console.warn('[helmwx] malformed tile url: ' + params.url); } return { data: await transparentTile() }; }
  const set = wxSets[m[1]];
  if (!set) return { data: await transparentTile() };
  let tile;
  try { tile = await wxFetchRaw(set, +m[2], +m[3], +m[4], +m[5], abortController && abortController.signal); }
  catch (e) { if (e && e.name === 'AbortError') throw e; return { data: await transparentTile() }; }
  if (!tile) return { data: await transparentTile() };
  const C = codec(), ramp = set.cfg.ramp, vals = tile.values;
  const cv = makeCanvas(tile.w, tile.h), cx = cv.getContext('2d');
  const img = cx.createImageData(tile.w, tile.h), d = img.data;
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i];
    if (v == null || !isFinite(v)) { d[i * 4 + 3] = 0; continue; }   // NODATA -> transparent
    const c = C.rampColor(ramp, v);
    d[i * 4] = c[0]; d[i * 4 + 1] = c[1]; d[i * 4 + 2] = c[2]; d[i * 4 + 3] = c[3];
  }
  cx.putImageData(img, 0, 0);
  return { data: await createImageBitmap(cv) };
}

function provenanceClass(source) {
  // docs/SPACETIME-PROBE.md LayerSample.source ∈ open|owned|rag|nfl|engine (+ extensions). Public
  // weather MODELS (GFS/ECMWF/ICON/Open-Meteo) are 'open'. The synthetic offline demo is NOT a real
  // feed — it must NOT share the trusted-model 'open' class, so it gets its own 'synthetic' token
  // (a consumer that only trusts the known enum fails closed on it). The authoritative not-for-nav
  // signal is the explicit `notForNavigation` flag below.
  return source === 'demo-synthetic' ? 'synthetic' : 'open';
}
const SOURCE_URL = {
  'open-meteo': 'https://open-meteo.com', 'gfs': 'https://nomads.ncep.noaa.gov',
  'ecmwf-ifs': 'https://www.ecmwf.int/en/forecasts/datasets/open-data', 'icon': 'https://opendata.dwd.de',
};
const NFN = /NOT FOR NAVIGATION/i;
function layerSample(cfg, value, frame, note) {
  const validTime = cfg.times && cfg.times.length ? cfg.times[Math.max(0, Math.min(cfg.times.length - 1, frame | 0))] : null;
  const notForNav = cfg.source === 'demo-synthetic' || NFN.test(cfg.model || '') || NFN.test(cfg.disclaimer || '');
  return {
    layer: cfg.layer, value: value == null ? null : Math.round(value * 100) / 100, unit: cfg.unit,
    source: provenanceClass(cfg.source),
    sourceRef: { title: cfg.model || cfg.source, url: SOURCE_URL[cfg.source] || null, provenance: cfg.source },
    // freshness = data-age (when the model was issued/fetched), NOT the forecast valid-time — those
    // are separate fields per SPACETIME-PROBE.md. validTime is returned distinctly below.
    freshness: cfg.fetchedAt || (cfg.source === 'demo-synthetic' ? 'synthetic' : 'forecast'),
    confidence: cfg.confidence || 'fair', horizon: cfg.horizon || null,
    validTime: validTime, encoding: cfg.encoding,
    notForNavigation: notForNav, disclaimer: cfg.disclaimer || undefined,
    note: note || (value == null ? 'no data here — verify locally' : undefined),
  };
}

// PUBLIC — enable a value-encoded weather tile set. ctx: { maplibregl, manifestUrl, beforeId?,
// opacity?, frame?, notify? }. Returns the resolved manifest (or null on load failure — surfaced,
// never silently empty).
export async function enableWxTiles(map, ctx) {
  const C = codec();
  if (!C) { ctx.notify && ctx.notify('weather value-codec not loaded (web/wx-value-codec.js)', 'warn'); return null; }
  if (!wxProtoReady) { ctx.maplibregl.addProtocol(WXP, wxProtocol); wxProtoReady = true; }
  let cfg;
  try {
    const r = await fetch(ctx.manifestUrl);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    cfg = await r.json();
  } catch (e) {
    ctx.notify && ctx.notify('weather tiles unavailable: ' + (e.message || e), 'warn');
    return null;
  }
  if (cfg.encoding !== C.ENCODING) {            // a contract bump must fail loud, not mis-decode silently
    ctx.notify && ctx.notify('unsupported tile encoding "' + cfg.encoding + '" (need ' + C.ENCODING + ')', 'warn');
    return null;
  }
  const setId = cfg.layer || 'wx';
  wxSets[setId] = { cfg, baseDir: ctx.manifestUrl.replace(/manifest\.json$/, ''), rawCache: new Map(), inflight: new Map(), order: [] };
  wxActiveKey = setId;
  const frame = ctx.frame | 0;
  const opacity = Math.max(0, Math.min(1, ctx.opacity == null ? 0.82 : ctx.opacity));
  disableWxTiles(map, true);
  map.addSource(WX_SRC, {
    type: 'raster', tiles: ['helmwx://' + setId + '/' + frame + '/{z}/{x}/{y}'],
    tileSize: 256, minzoom: cfg.minzoom || 0, maxzoom: cfg.maxzoom || 7, bounds: cfg.bbox,
    attribution: 'Helm value-encoded weather · ' + (cfg.model || cfg.source),
  });
  map.addLayer({
    id: WX_LYR, type: 'raster', source: WX_SRC,
    paint: { 'raster-opacity': opacity, 'raster-resampling': 'linear', 'raster-fade-duration': 0 },
  }, (ctx.beforeId && map.getLayer(ctx.beforeId)) ? ctx.beforeId : undefined);
  ctx.notify && ctx.notify('Value-encoded ' + setId + ' tiles (' + (cfg.model || cfg.source) + ') — decoded client-side', 'ok');
  return cfg;
}

export function disableWxTiles(map, keep) {
  if (map.getLayer(WX_LYR)) map.removeLayer(WX_LYR);
  if (map.getSource(WX_SRC)) map.removeSource(WX_SRC);
  if (!keep) wxActiveKey = null;
}
export function setWxOpacity(map, o) {
  if (map.getLayer(WX_LYR)) map.setPaintProperty(WX_LYR, 'raster-opacity', Math.max(0, Math.min(1, o)));
}
export function setWxFrame(map, frame) {
  if (!wxActiveKey) return;
  const set = wxSets[wxActiveKey], src = map.getSource(WX_SRC);
  const f = set ? (effFrame(set.cfg, frame) ?? 0) : (frame | 0);   // clamp so the URL frame matches the cache key
  if (src && src.setTiles) src.setTiles(['helmwx://' + wxActiveKey + '/' + f + '/{z}/{x}/{y}']);
}

// PUBLIC PROBE — the deterministic weather sample face (ROUTING-3 / AI-5). Returns a LayerSample
// (docs/SPACETIME-PROBE.md): { layer, value, unit, source, sourceRef, freshness, confidence,
// horizon, validTime, note? }. value is DECODED from the value tiles (never invented); null +
// "verify locally" when the point is outside coverage or NODATA.
//   NOTE on argument order: this honours the doc contract sample(lat, lon, t) — lat FIRST — which
//   differs from web/wind-layer.js's sample(lon, lat). Documented so AI-5/AI-17 standardise on one.
export async function sampleWx(lat, lon, t, opts) {
  const C = codec(); if (!C) return null;
  const setId = (opts && opts.layer) || wxActiveKey;
  const set = wxSets[setId];
  if (!set) return null;                                  // no active value-tile layer
  const cfg = set.cfg, b = cfg.bbox;                      // [w,s,e,n]
  const frame = cfg.times ? C.pickFrame(cfg.times, t) : 0;
  // lon coverage handles an antimeridian-crossing bbox (west > east, e.g. around 180° near Fiji).
  const lonIn = b[0] <= b[2] ? (lon >= b[0] && lon <= b[2]) : (lon >= b[0] || lon <= b[2]);
  if (!lonIn || lat < b[1] || lat > b[3]) return layerSample(cfg, null, frame, 'outside coverage — verify locally');
  const z = C.sampleZoom(cfg, cfg.maxzoom);
  const p = C.lonLatToPixel(lon, lat, z, cfg.tileSize || 256);
  const tile = await wxFetchRaw(set, frame, z, p.x, p.y);
  if (!tile) return layerSample(cfg, null, frame, 'no data here — verify locally');
  const v = C.bilinear(tile.values, tile.w, tile.h, p.px, p.py);
  return layerSample(cfg, (v == null || !isFinite(v)) ? null : v, frame);
}

// Active set introspection (for the panel readout / legend).
export function activeWx() { const s = wxSets[wxActiveKey]; return s ? s.cfg : null; }
