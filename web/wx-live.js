// wx-live.js — fetch-on-pan LIVE weather (screen-filling sampled mode).  WX epic · weather-ux.
// ----------------------------------------------------------------------------------------------
// The legacy weather overlay paints one fixed-bbox image around your start point, so zooming out
// shows a tiny rectangle. This mode instead fetches Open-Meteo for WHATEVER IS IN VIEW and repaints
// when the view escapes the fetched field — so weather fills the screen everywhere you look.
//
// IMPORTANT: this is not Windy's global GRIB tile backend. It is real live Open-Meteo data sampled
// over the visible bbox, colour-ramped/interpolated into one georeferenced image, and cached. The
// baked Tier-2 value tiles are the structural path for true tile-pyramid pan/zoom.
//
// HONESTY: weather is fetched live; if the network is unreachable (offshore / no link), Helm keeps
// the last known good field at its true geographic bbox and marks it stale. It never fabricates or
// stretches a field to fill the gap (docs/VISION.md). For offline coverage, bake Tier-2 tiles.
(function () {
  'use strict';
  var FORECAST = 'https://api.open-meteo.com/v1/forecast';
  var MARINE = 'https://marine-api.open-meteo.com/v1/marine';
  var SRC = 'helm-wx-live', LYR = 'helm-wx-live';
  var CACHE_KEY = 'helm.wx.live.cache.v1';
  var CACHE_TTL_MS = 30 * 60 * 1000;
  var RATE_LIMIT_BACKOFF_MS = 15 * 60 * 1000;
  var MAX_CACHE = 8;

  // layer -> Open-Meteo current variable + display unit + colour ramp (knots/°C/hPa/… ). Mirrors
  // pipeline/fetch_weather.py so Live and the pipeline agree. Marine layers use Open-Meteo's
  // dedicated marine endpoint; sea cells can honestly remain NODATA near land.
  var LAYERS = {
    wind:     { v: 'wind_speed_10m', dir: 'wind_direction_10m', unit: 'kn', stops: [[0,[98,113,183]],[5,[57,131,168]],[10,[52,171,151]],[16,[123,183,80]],[22,[225,200,60]],[30,[232,130,50]],[40,[214,70,74]],[55,[150,60,150]]] },
    gust:     { v: 'wind_gusts_10m', unit: 'kn', stops: [[0,[56,189,248]],[10,[45,212,191]],[20,[250,204,21]],[30,[249,115,22]],[42,[239,68,68]],[60,[217,33,154]]] },
    rain:     { v: 'precipitation', unit: 'mm', stops: [[0,[80,160,220,0]],[0.2,[90,180,255,0.55]],[2,[40,120,235,0.8]],[6,[120,90,235,0.85]],[15,[175,60,200,0.9]]] },
    temp:     { v: 'temperature_2m', unit: '°C', stops: [[-10,[70,90,200]],[0,[80,180,235]],[10,[70,200,130]],[20,[245,205,60]],[30,[240,120,40]],[42,[210,40,40]]] },
    clouds:   { v: 'cloud_cover', unit: '%', stops: [[0,[150,170,190,0]],[40,[200,210,222,0.4]],[80,[235,240,246,0.75]],[100,[250,252,255,0.9]]] },
    pressure: { v: 'pressure_msl', unit: 'hPa', stops: [[980,[120,80,200]],[1000,[80,160,230]],[1013,[120,205,140]],[1025,[240,200,80]],[1040,[230,110,55]]] },
    cape:     { v: 'cape', unit: 'J/kg', stops: [[0,[56,160,200,0]],[300,[120,200,120,0.5]],[1000,[245,205,60,0.8]],[2500,[240,120,40,0.9]],[4000,[220,40,40,0.95]]] },
    waves:    { endpoint: MARINE, v: 'wave_height', unit: 'm', stops: [[0,[56,120,190]],[0.5,[45,170,190]],[1.5,[65,195,135]],[3,[230,205,70]],[5,[235,125,55]],[8,[195,45,75]]] },
    swell:    { endpoint: MARINE, v: 'swell_wave_height', unit: 'm', stops: [[0,[65,105,175]],[0.5,[55,155,195]],[1.5,[70,190,145]],[3,[225,195,70]],[5,[225,110,60]],[8,[175,50,120]]] },
    sst:      { endpoint: MARINE, v: 'sea_surface_temperature', unit: '°C', stops: [[0,[70,95,190]],[10,[60,165,210]],[20,[65,195,135]],[26,[235,205,70]],[31,[230,100,45]],[36,[185,35,65]]] },
    current:  { endpoint: MARINE, v: 'ocean_current_velocity', dir: 'ocean_current_direction', direction: 'to', unit: 'kn', stops: [[0,[60,105,175]],[0.25,[45,155,195]],[0.75,[55,190,145]],[1.5,[225,205,70]],[2.5,[230,120,55]],[4,[190,45,80]]] },
  };
  function supports(layer) { return !!LAYERS[layer]; }

  var st = { map: null, on: false, layer: 'wind', token: 0, field: null, velocity: null,
             particles: true, notify: function () {}, moveHandler: null, endHandler: null,
             debounce: null, abort: null, lastKey: '', requestCount: 0, phase: 'off', opacity: 0.72,
             cache: Object.create(null), cacheOrder: [], cacheLoaded: false, cacheHits: 0,
             lastError: '', backoffUntil: 0, forceFetch: false, imageUrl: '', imageShift: null };

  function codec() { return window.HelmWxCodec; }
  function layerCache() { return window.HelmLayerCache; }
  function services() { return window.HelmServices || null; }
  function layerEndpointKind(layer) { return LAYERS[layer] && LAYERS[layer].endpoint === MARINE ? 'marine' : 'forecast'; }
  function providerInfo() {
    var S = services();
    if (S && S.publicWeatherProvider) return S.publicWeatherProvider();
    return { label: 'Open-Meteo Free', scope: 'openmeteo:free' };
  }
  function providerLabel() { return providerInfo().label || 'Open-Meteo'; }
  function providerScope() {
    var S = services();
    return S && S.providerScope ? S.providerScope() : (providerInfo().scope || 'openmeteo:free');
  }
  function cacheScope() { return st.layer + ':' + (st.model || 'gfs_seamless') + ':' + providerScope(); }
  function fieldBbox(field) { return field ? [field.west, field.south, field.east, field.north] : null; }

  function now() { return Date.now ? Date.now() : +new Date(); }

  function cacheStorage() {
    try { return window.localStorage || null; } catch (_) { return null; }
  }

  function loadCache() {
    if (st.cacheLoaded) return;
    st.cacheLoaded = true;
    var ls = cacheStorage(); if (!ls) return;
    try {
      var raw = ls.getItem(CACHE_KEY); if (!raw) return;
      var saved = JSON.parse(raw), t = now();
      (saved.entries || []).forEach(function (entry) {
        if (!entry || !entry.key || !entry.field || !entry.savedAt) return;
        if (t - entry.savedAt > CACHE_TTL_MS) return;
        st.cache[entry.key] = entry;
        st.cacheOrder.push(entry.key);
      });
    } catch (_) {
      try { ls.removeItem(CACHE_KEY); } catch (__) {}
    }
  }

  function saveCache() {
    var ls = cacheStorage(); if (!ls) return;
    try {
      var entries = st.cacheOrder.map(function (key) { return st.cache[key]; }).filter(Boolean);
      ls.setItem(CACHE_KEY, JSON.stringify({ version: 1, entries: entries }));
    } catch (_) {}
  }

  function pruneCache() {
    var t = now();
    st.cacheOrder = st.cacheOrder.filter(function (key) {
      var entry = st.cache[key];
      if (!entry || t - entry.savedAt > CACHE_TTL_MS) { delete st.cache[key]; return false; }
      return true;
    });
    while (st.cacheOrder.length > MAX_CACHE) delete st.cache[st.cacheOrder.shift()];
  }

  function remember(key, field, velocity) {
    if (!field) return;
    loadCache();
    field.savedAt = now();
    var entry = { key: key, layer: st.layer, model: st.model, savedAt: field.savedAt,
                  field: field, velocity: velocity || null };
    if (!st.cache[key]) st.cacheOrder.push(key);
    st.cache[key] = entry;
    pruneCache();
    saveCache();
    var LC = layerCache();
    if (LC) {
      try {
        LC.put({
          layerId: 'weather.live',
          scope: cacheScope(),
          cacheKey: key,
          kind: 'raster-field',
          bbox: fieldBbox(field),
          source: providerLabel(),
          model: st.model || 'gfs_seamless',
          ttlMs: CACHE_TTL_MS,
          payload: { field: field, velocity: velocity || null }
        });
      } catch (_) {}
    }
  }

  function findCached(map) {
    var LC = layerCache(), view = map ? viewport(map) : null;
    if (LC) {
      var rec = LC.getBest('weather.live', { scope: cacheScope(), bbox: view });
      if (rec && rec.payload && rec.payload.field) {
        return {
          key: rec.cacheKey, layer: st.layer, model: st.model,
          savedAt: rec.fetchedAtMs || rec.storedAt || now(),
          field: rec.payload.field, velocity: rec.payload.velocity || null,
          shared: true
        };
      }
    }
    loadCache(); pruneCache();
    for (var i = st.cacheOrder.length - 1; i >= 0; i--) {
      var entry = st.cache[st.cacheOrder[i]];
      if (!entry || entry.layer !== st.layer || entry.model !== st.model) continue;
      if (entry.field && covers(entry.field, map)) return entry;
    }
    return null;
  }

  function latestCached() {
    var LC = layerCache();
    if (LC) {
      var rec = LC.getBest('weather.live', { scope: cacheScope(), allowAny: true });
      if (rec && rec.payload && rec.payload.field) {
        return {
          key: rec.cacheKey, layer: st.layer, model: st.model,
          savedAt: rec.fetchedAtMs || rec.storedAt || now(),
          field: rec.payload.field, velocity: rec.payload.velocity || null,
          shared: true
        };
      }
    }
    loadCache(); pruneCache();
    for (var i = st.cacheOrder.length - 1; i >= 0; i--) {
      var entry = st.cache[st.cacheOrder[i]];
      if (entry && entry.layer === st.layer && entry.model === st.model && entry.field) return entry;
    }
    return null;
  }

  function cacheAge(entry) {
    if (!entry || !entry.savedAt) return '';
    var mins = Math.max(0, Math.round((now() - entry.savedAt) / 60000));
    return mins < 1 ? 'just now' : (mins + ' min ago');
  }

  function normalizeLon(lon) {
    var wrapped = ((lon + 180) % 360 + 360) % 360 - 180;
    return wrapped === -180 && lon > 0 ? 180 : wrapped;
  }

  function viewport(map) {
    var b = map.getBounds(), w = b.getWest(), s = b.getSouth(), e = b.getEast(), n = b.getNorth();
    if (e < w) e += 360;
    return [w, Math.max(-85, s), e, Math.min(85, n)];
  }

  // Cover the viewport plus 50% margin on every side. Longitude stays unwrapped for MapLibre
  // image coordinates (so Fiji views can cross 180°); API query longitudes are wrapped in grid().
  // At world scale the request is capped to one 360° revolution, never to an arbitrary local box.
  function viewBbox(map) {
    var v = viewport(map), w = v[0], s = v[1], e = v[2], n = v[3];
    var width = Math.min(360, Math.max(0.01, e - w));
    var height = Math.min(170, Math.max(0.01, n - s));
    var cx = (w + e) / 2, cy = (s + n) / 2;
    var paddedWidth = Math.min(360, width * 2), paddedHeight = Math.min(170, height * 2);
    return [cx - paddedWidth / 2, Math.max(-85, cy - paddedHeight / 2),
            cx + paddedWidth / 2, Math.min(85, cy + paddedHeight / 2)];
  }

  function gridSize(map) {
    var c = map && map.getCanvas ? map.getCanvas() : null;
    var w = c ? c.clientWidth || c.width : 1280, h = c ? c.clientHeight || c.height : 720;
    return {
      nx: Math.max(12, Math.min(22, Math.ceil(w / 95) + 2)),
      ny: Math.max(10, Math.min(18, Math.ceil(h / 95) + 2))
    };
  }

  function covers(field, map) {
    if (!field) return false;
    var v = viewport(map), w = v[0], e = v[2], mid = (w + e) / 2;
    var fieldMid = (field.west + field.east) / 2;
    var shift = Math.round((fieldMid - mid) / 360) * 360;
    w += shift; e += shift;
    if (e - w >= 360 && field.east - field.west >= 360) return field.south <= v[1] && field.north >= v[3];
    return field.west <= w && field.east >= e && field.south <= v[1] && field.north >= v[3];
  }

  // MapLibre image sources do not automatically repeat across wrapped world copies. A field fetched
  // around Fiji can honestly cover a viewport at -175° after a ±360° shift, but if the image source
  // stays anchored at the original 35°..319° copy it renders off-screen. Keep the data bbox stable
  // and shift only the display coordinates to the copy closest to the current viewport.
  function displayShift(field, map) {
    if (!field || !map) return 0;
    var v = viewport(map), viewMid = (v[0] + v[2]) / 2, fieldMid = (field.west + field.east) / 2;
    return Math.round((viewMid - fieldMid) / 360) * 360;
  }

  function imageCoordsForShift(field, shift) {
    return [[field.west + shift, field.north], [field.east + shift, field.north],
            [field.east + shift, field.south], [field.west + shift, field.south]];
  }

  function reanchorImage(map) {
    map = map || st.map;
    if (!map || !st.field || !st.imageUrl || !map.getSource(SRC)) return false;
    var shift = displayShift(st.field, map);
    if (st.imageShift === shift) return true;
    map.getSource(SRC).updateImage({ url: st.imageUrl, coordinates: imageCoordsForShift(st.field, shift) });
    st.imageShift = shift;
    return true;
  }

  function grid(bbox, nx, ny) {
    var lats = [], lons = [], qlat = [], qlon = [];
    for (var j = 0; j < ny; j++) lats.push(bbox[3] - (bbox[3] - bbox[1]) * j / (ny - 1));
    for (var i = 0; i < nx; i++) lons.push(bbox[0] + (bbox[2] - bbox[0]) * i / (nx - 1));
    for (var a = 0; a < lats.length; a++) for (var c = 0; c < lons.length; c++) {
      qlat.push(+lats[a].toFixed(4)); qlon.push(+normalizeLon(lons[c]).toFixed(4));
    }
    return { nx: nx, ny: ny, lats: lats, lons: lons, qlat: qlat, qlon: qlon };
  }

  function url(g, layer, model) {
    var L = LAYERS[layer];
    var vars = L.dir ? (L.v + ',' + L.dir) : L.v;
    var p = 'latitude=' + g.qlat.join(',') + '&longitude=' + g.qlon.join(',') + '&current=' + vars;
    if (layer === 'wind' || layer === 'gust' || layer === 'current') p += '&wind_speed_unit=kn';
    if (L.endpoint === MARINE) p += '&cell_selection=sea';
    else if (model && model !== 'gfs_seamless') p += '&models=' + model;
    var S = services(), kind = layerEndpointKind(layer);
    var endpoint = S && S.weatherEndpoint ? S.weatherEndpoint(kind) : (L.endpoint || FORECAST);
    var raw = endpoint + '?' + p;
    return S && S.withOpenMeteoAuth ? S.withOpenMeteoAuth(raw) : raw;
  }

  // turn Open-Meteo's per-point response into a field-<layer> grid (row-major N->S).
  function toField(nodes, g, layer) {
    var L = LAYERS[layer], vals = [];
    for (var k = 0; k < g.qlat.length; k++) {
      var node = Array.isArray(nodes) ? nodes[k] : nodes;
      var v = node && node.current ? node.current[L.v] : null;
      vals.push(typeof v === 'number' ? v : NaN);
    }
    var valid = vals.filter(function (x) { return isFinite(x); });
    return { layer: layer, unit: L.unit, nx: g.nx, ny: g.ny,
             west: g.lons[0], east: g.lons[g.lons.length - 1], north: g.lats[0], south: g.lats[g.lats.length - 1],
             vmin: valid.length ? Math.min.apply(null, valid) : 0, vmax: valid.length ? Math.max.apply(null, valid) : 1,
             stops: L.stops, values: vals };
  }

  function metToUv(speed, directionFromDeg) {
    var r = directionFromDeg * Math.PI / 180;
    return [-speed * Math.sin(r), -speed * Math.cos(r)];
  }

  function directionToUv(speed, directionDeg, convention) {
    if (convention !== 'to') return metToUv(speed, directionDeg);
    var r = directionDeg * Math.PI / 180;
    return [speed * Math.sin(r), speed * Math.cos(r)];
  }

  function toVelocity(nodes, g, layer) {
    var L = LAYERS[layer]; if (!L || !L.dir) return null;
    var u = [], v = [];
    for (var k = 0; k < g.qlat.length; k++) {
      var node = Array.isArray(nodes) ? nodes[k] : nodes;
      var cur = node && node.current, spd = cur && cur[L.v], dir = cur && cur[L.dir];
      var uv = (typeof spd === 'number' && typeof dir === 'number') ? directionToUv(spd, dir, L.direction) : [NaN, NaN];
      u.push(uv[0]); v.push(uv[1]);
    }
    var header = { nx: g.nx, ny: g.ny, lo1: g.lons[0], la1: g.lats[0],
      lo2: g.lons[g.lons.length - 1], la2: g.lats[g.lats.length - 1],
      dx: (g.lons[g.lons.length - 1] - g.lons[0]) / (g.nx - 1),
      dy: (g.lats[0] - g.lats[g.lats.length - 1]) / (g.ny - 1) };
    return [
      { header: Object.assign({ parameterCategory: 2, parameterNumber: 2 }, header), data: u },
      { header: Object.assign({ parameterCategory: 2, parameterNumber: 3 }, header), data: v }
    ];
  }

  function applyParticles(velocity) {
    var wind = window.__helmWindLayer;
    st.velocity = velocity || null;
    if (!wind) return false;
    if (!st.on || !st.particles || (st.layer !== 'wind' && st.layer !== 'current') || !velocity) {
      wind.setVisible(false);
      if (!velocity) wind.clearData();
      return false;
    }
    var ok = wind.setData(velocity);
    wind.setVisible(ok);
    return ok;
  }

  // PUBLIC (also used by tests): colourise a field full-bleed over its bbox as a MapLibre image source.
  function renderField(map, field) {
    var C = codec(); if (!C) return;
    st.field = field;
    var up = 10, W = Math.max(2, (field.nx - 1) * up), H = Math.max(2, (field.ny - 1) * up);
    var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    var cx = cv.getContext('2d'), img = cx.createImageData(W, H), d = img.data;
    for (var y = 0; y < H; y++) {
      var fy = y / (H - 1) * (field.ny - 1);
      for (var x = 0; x < W; x++) {
        var fx = x / (W - 1) * (field.nx - 1);
        var v = C.bilinear(field.values, field.nx, field.ny, fx, fy);
        var o = (y * W + x) * 4;
        if (v == null || !isFinite(v)) { d[o + 3] = 0; continue; }
        var col = C.rampColor(field.stops, v);
        d[o] = col[0]; d[o + 1] = col[1]; d[o + 2] = col[2]; d[o + 3] = col[3];
      }
    }
    cx.putImageData(img, 0, 0);
    var urlData = cv.toDataURL('image/png');
    st.imageUrl = urlData;
    st.imageShift = displayShift(field, map);
    var coords = imageCoordsForShift(field, st.imageShift);
    if (map.getSource(SRC)) map.getSource(SRC).updateImage({ url: urlData, coordinates: coords });
    else {
      map.addSource(SRC, { type: 'image', url: urlData, coordinates: coords });
      map.addLayer({ id: LYR, type: 'raster', source: SRC, paint: { 'raster-opacity': st.opacity, 'raster-resampling': 'linear', 'raster-fade-duration': 0 } },
        map.getLayer('route-line') ? 'route-line' : undefined);
    }
    publishStatus('ready');
  }

  async function fetchPoints(u, signal) {
    // Test seam for Playwright/localhost automation. Production uses Open-Meteo fetch below.
    if (typeof window.__helmWxLiveFetch === 'function') return window.__helmWxLiveFetch(u, signal);
    var r = await fetch(u, { signal: signal });
    if (!r.ok) {
      var e = new Error('HTTP ' + r.status);
      e.status = r.status;
      try {
        var body = await r.json();
        if (body && body.reason) e.reason = body.reason;
      } catch (_) {}
      throw e;
    }
    return r.json();
  }

  function clearOverlay(map) {
    if (!map) return;
    if (map.getLayer(LYR)) map.removeLayer(LYR);
    if (map.getSource(SRC)) map.removeSource(SRC);
    st.field = null; st.velocity = null; st.imageUrl = ''; st.imageShift = null;
    applyParticles(null);
    publishStatus(st.on ? 'empty' : 'off');
  }

  function status() {
    var view = st.map ? viewport(st.map) : null;
    return {
      on: st.on, phase: st.phase, layer: st.layer, model: st.model,
      field: st.field ? [st.field.west, st.field.south, st.field.east, st.field.north] : null,
      viewport: view, covers: !!(st.field && st.map && covers(st.field, st.map)),
      requests: st.requestCount, opacity: st.opacity, cacheHits: st.cacheHits,
      lastError: st.lastError, backoffUntil: st.backoffUntil, hasField: !!st.field,
      provider: providerInfo()
    };
  }

  function publishStatus(phase) {
    st.phase = phase || st.phase;
    var el = st.map && st.map.getContainer ? st.map.getContainer() : document.getElementById('map');
    if (!el) return;
    var s = status();
    el.dataset.wxLive = s.on ? '1' : '0';
    el.dataset.wxPhase = s.phase;
    el.dataset.wxCovers = s.covers ? '1' : '0';
    el.dataset.wxLayer = s.layer || '';
    el.dataset.wxRequests = String(s.requests);
    el.dataset.wxOpacity = String(s.opacity);
    el.dataset.wxCacheHits = String(s.cacheHits);
    el.dataset.wxError = s.lastError || '';
    el.dataset.wxBackoff = s.backoffUntil ? String(s.backoffUntil) : '';
    el.dataset.wxHasField = s.hasField ? '1' : '0';
    el.dataset.wxProvider = s.provider && s.provider.label ? s.provider.label : '';
    el.dataset.wxProviderScope = s.provider && s.provider.scope ? s.provider.scope : '';
    el.dataset.wxField = s.field ? s.field.map(function (x) { return x.toFixed(3); }).join(',') : '';
    el.dataset.wxViewport = s.viewport ? s.viewport.map(function (x) { return x.toFixed(3); }).join(',') : '';
  }

  function renderCached(entry, why) {
    if (!entry || !entry.field) return false;
    st.cacheHits++;
    renderField(st.map, entry.field);
    var particleOk = applyParticles(entry.velocity || null);
    st.lastError = '';
    st.notify('Live ' + st.layer + (particleOk ? ' + animated particles' : '') +
      ' · cached ' + providerLabel() + ' field (' + (why || cacheAge(entry)) + ')', 'ok');
    return true;
  }

  async function refresh() {
    if (!st.on || !supports(st.layer)) return;
    var force = st.forceFetch;
    st.forceFetch = false;
    if (!force && st.field && covers(st.field, st.map)) {
      reanchorImage(st.map);
      st.lastError = '';
      publishStatus('ready');
      return;
    }
    var cached = force ? null : findCached(st.map);
    if (cached && renderCached(cached)) return;
    if (st.backoffUntil && now() < st.backoffUntil) {
      st.lastKey = ''; st.abort = null;
      st.lastError = 'rate_limited';
      publishStatus(st.field ? (covers(st.field, st.map) ? 'stale' : 'out_of_coverage') : 'empty');
      st.notify(st.field
        ? 'Live weather is rate-limited — showing the last ' + providerLabel() + ' pull as stale.'
        : 'Live weather is rate-limited and no cached field covers this view yet.', 'warn');
      return;
    }
    var bbox = viewBbox(st.map);
    var key = providerScope() + ':' + st.layer + ':' + st.model + ':' + bbox.map(function (x) { return x.toFixed(2); }).join(',');
    if (key === st.lastKey) return;                       // same view+layer -> skip
    st.lastKey = key;

    // Never stretch a field into a new part of the world. Keep the old source at its true bbox
    // while a replacement loads; if it does not cover the view, MapLibre simply will not draw it
    // there, but panning back still shows the last pull.
    if (st.field && !covers(st.field, st.map)) publishStatus('out_of_coverage');

    var size = gridSize(st.map), g = grid(bbox, size.nx, size.ny), my = ++st.token;
    if (st.abort) st.abort.abort();
    var ac = new AbortController(); st.abort = ac;
    st.requestCount++;
    publishStatus('loading');
    st.notify('Fetching live ' + st.layer + ' for this view via ' + providerLabel() + ' …', 'info');
    try {
      var nodes = await fetchPoints(url(g, st.layer, st.model === 'gfs_seamless' ? null : st.model), ac.signal);
      if (my !== st.token || !st.on) return;              // a newer pan superseded this one
      var field = toField(nodes, g, st.layer);
      if (!field.values.some(function (v) { return isFinite(v); })) {
        st.lastKey = ''; st.abort = null; st.lastError = 'no_data';
        publishStatus(st.field ? (covers(st.field, st.map) ? 'stale' : 'out_of_coverage') : 'empty');
        st.notify(st.field ? 'No new live data for this area — keeping the last weather pull as stale.'
          : 'No live data for this area', 'warn');
        return;
      }
      if (!covers(field, st.map)) {
        st.lastKey = ''; st.abort = null; publishStatus('stale');
        scheduleRefresh(0);
        return;
      }
      renderField(st.map, field);
      var velocity = toVelocity(nodes, g, st.layer);
      var particleOk = applyParticles(velocity);
      remember(key, field, velocity);
      st.abort = null;
      st.lastError = '';
      st.notify('Live ' + st.layer + (particleOk ? ' + animated particles' : '') +
        ' · ' + providerLabel() + ' (' + field.nx + '×' + field.ny + ' over view)', 'ok');
    } catch (e) {
      if (e && e.name === 'AbortError') {
        if (st.abort === ac) st.abort = null;
        if (st.lastKey === key) st.lastKey = '';
        publishStatus(st.field && covers(st.field, st.map) ? 'ready' : 'empty');
        return;
      }
      if (my !== st.token || !st.on) return;
      st.lastError = e && e.status === 429 ? 'rate_limited' : (e && e.message ? e.message : 'fetch_failed');
      if (e && e.status === 429) st.backoffUntil = now() + RATE_LIMIT_BACKOFF_MS;
      var fallback = findCached(st.map);
      if (fallback && renderCached(fallback, e && e.status === 429 ? 'rate-limited fallback' : 'offline fallback')) {
        st.lastError = e && e.status === 429 ? 'rate_limited' : (e && e.message ? e.message : 'fetch_failed');
        st.lastKey = ''; st.abort = null; publishStatus('ready');
        st.notify('Live weather provider is unavailable — showing cached ' + providerLabel() + ' field for this view.', 'warn');
        return;
      }
      if (st.field && covers(st.field, st.map)) {
        st.abort = null; st.lastKey = ''; publishStatus('ready');
        st.notify('Live weather provider is unavailable — keeping the current field because it still covers the view.', 'warn');
        return;
      }
      // Honest offline behaviour — never fabricate a field, but never delete a valid last pull
      // merely because the next pull failed.
      st.lastKey = ''; st.abort = null;
      publishStatus(st.field ? (covers(st.field, st.map) ? 'stale' : 'out_of_coverage') : 'empty');
      st.notify(e && e.status === 429
        ? (st.field ? 'Live weather is rate-limited — keeping the last ' + providerLabel() + ' pull as stale.'
          : 'Live weather is rate-limited and no cached field covers this view yet.')
        : (st.field ? 'Live weather needs a connection — keeping the last weather pull as stale.'
          : 'Live weather needs a connection — offline. (Bake Tier-2 tiles for offline coverage.)'), 'warn');
    }
  }

  function scheduleRefresh(delay) {
    clearTimeout(st.debounce);
    st.debounce = setTimeout(refresh, delay);
  }

  function onMove() {
    // A response for the pre-pan viewport must never land after the map has moved. Abort it as soon
    // as movement begins, not 450 ms later when the old implementation finally scheduled refresh.
    if (st.abort) { st.token++; st.abort.abort(); st.abort = null; st.lastKey = ''; }
    if (st.field && covers(st.field, st.map)) {
      clearTimeout(st.debounce);
      reanchorImage(st.map);
      publishStatus('ready');
      return;
    }
    publishStatus(st.field ? 'out_of_coverage' : 'moving');
    scheduleRefresh(220);
  }

  function onMoveEnd() {
    if (st.field && covers(st.field, st.map)) { reanchorImage(st.map); publishStatus('ready'); return; }
    scheduleRefresh(0);
  }

  function enable(map, opts) {
    opts = opts || {};
    st.map = map; st.layer = opts.layer || st.layer; st.model = opts.model || 'gfs_seamless';
    st.particles = opts.particles !== false;
    st.opacity = Math.max(0, Math.min(1, opts.opacity == null ? st.opacity : opts.opacity));
    st.notify = opts.notify || st.notify; st.on = true; st.lastKey = '';
    loadCache();
    if (!st.moveHandler) {
      st.moveHandler = onMove; st.endHandler = onMoveEnd;
      map.on('move', st.moveHandler); map.on('moveend', st.endHandler);
    }
    publishStatus('loading');
    refresh();
  }
  function disable(map) {
    st.on = false; st.token++;
    clearTimeout(st.debounce); st.debounce = null;
    if (st.abort) { st.abort.abort(); st.abort = null; }
    if (st.moveHandler) {
      (map || st.map).off('move', st.moveHandler);
      (map || st.map).off('moveend', st.endHandler);
      st.moveHandler = null; st.endHandler = null;
    }
    clearOverlay(map || st.map); st.lastKey = '';
  }
  function setLayer(layer) { st.layer = layer; st.lastKey = ''; clearOverlay(st.map); if (st.on) refresh(); }
  function setModel(model) { st.model = model; st.lastKey = ''; clearOverlay(st.map); if (st.on) refresh(); }
  function setParticles(on) { st.particles = !!on; applyParticles(st.velocity); }
  function setOpacity(opacity) {
    st.opacity = Math.max(0, Math.min(1, opacity));
    if (st.map && st.map.getLayer(LYR)) st.map.setPaintProperty(LYR, 'raster-opacity', st.opacity);
    publishStatus(st.phase);
  }
  function isEnabled() { return st.on; }
  function sampleAt(lat, lon) {
    var f = st.field, C = codec(); if (!f || !C) return null;
    lon += Math.round(((f.west + f.east) / 2 - lon) / 360) * 360;
    if (lon < f.west || lon > f.east || lat < f.south || lat > f.north) return { value: null, source: 'open', note: 'outside live view' };
    var fx = (lon - f.west) / ((f.east - f.west) || 1) * (f.nx - 1), fy = (f.north - lat) / ((f.north - f.south) || 1) * (f.ny - 1);
    var v = C.bilinear(f.values, f.nx, f.ny, fx, fy);
    return { layer: f.layer, value: (v == null || !isFinite(v)) ? null : Math.round(v * 100) / 100, unit: f.unit, source: 'open', sourceRef: { title: providerLabel() + ' (live)' } };
  }

  window.addEventListener('helm-services-changed', function (e) {
    if (e && e.detail && e.detail.service && e.detail.service !== 'weather.openmeteo') return;
    st.lastKey = '';
    st.backoffUntil = 0;
    st.forceFetch = true;
    publishStatus(st.phase);
    if (st.on) scheduleRefresh(0);
  });

  window.HelmWxLive = { enable: enable, disable: disable, setLayer: setLayer, setModel: setModel,
    setParticles: setParticles, setOpacity: setOpacity, isEnabled: isEnabled,
    sampleAt: sampleAt, renderField: renderField,
    supports: supports, status: status, _toField: toField, _toVelocity: toVelocity,
    _metToUv: metToUv, _directionToUv: directionToUv, _viewBbox: viewBbox,
    _gridSize: gridSize, _grid: grid, _covers: covers, _clearOverlay: clearOverlay };
})();
