// wx-live.js — fetch-on-pan LIVE weather (the Windy-style full-bleed mode).  WX epic · weather-ux.
// ----------------------------------------------------------------------------------------------
// The legacy weather overlay paints one fixed-bbox image around your start point, so zooming out
// shows a tiny rectangle. This mode instead fetches Open-Meteo for WHATEVER IS IN VIEW and repaints
// (debounced) as you pan — so weather fills the screen everywhere you look, the way Windy does.
//
// HONESTY: weather is fetched live; if the network is unreachable (offshore / no link) it surfaces
// a clear notice and renders NOTHING — it never fabricates a field to fill the gap (docs/VISION.md).
// Provenance is always Open-Meteo (named); for offline coverage, bake Tier-2 tiles for your area.
(function () {
  'use strict';
  var FORECAST = 'https://api.open-meteo.com/v1/forecast';
  var SRC = 'helm-wx-live', LYR = 'helm-wx-live';

  // layer -> Open-Meteo current variable + display unit + colour ramp (knots/°C/hPa/… ). Mirrors
  // pipeline/fetch_weather.py so Live and the pipeline agree. Marine layers (waves/swell/sst/current)
  // use a different endpoint and stay on Standard for now.
  var LAYERS = {
    wind:     { v: 'wind_speed_10m', unit: 'kn', stops: [[0,[98,113,183]],[5,[57,131,168]],[10,[52,171,151]],[16,[123,183,80]],[22,[225,200,60]],[30,[232,130,50]],[40,[214,70,74]],[55,[150,60,150]]] },
    gust:     { v: 'wind_gusts_10m', unit: 'kn', stops: [[0,[56,189,248]],[10,[45,212,191]],[20,[250,204,21]],[30,[249,115,22]],[42,[239,68,68]],[60,[217,33,154]]] },
    rain:     { v: 'precipitation', unit: 'mm', stops: [[0,[80,160,220,0]],[0.2,[90,180,255,0.55]],[2,[40,120,235,0.8]],[6,[120,90,235,0.85]],[15,[175,60,200,0.9]]] },
    temp:     { v: 'temperature_2m', unit: '°C', stops: [[-10,[70,90,200]],[0,[80,180,235]],[10,[70,200,130]],[20,[245,205,60]],[30,[240,120,40]],[42,[210,40,40]]] },
    clouds:   { v: 'cloud_cover', unit: '%', stops: [[0,[150,170,190,0]],[40,[200,210,222,0.4]],[80,[235,240,246,0.75]],[100,[250,252,255,0.9]]] },
    pressure: { v: 'pressure_msl', unit: 'hPa', stops: [[980,[120,80,200]],[1000,[80,160,230]],[1013,[120,205,140]],[1025,[240,200,80]],[1040,[230,110,55]]] },
    cape:     { v: 'cape', unit: 'J/kg', stops: [[0,[56,160,200,0]],[300,[120,200,120,0.5]],[1000,[245,205,60,0.8]],[2500,[240,120,40,0.9]],[4000,[220,40,40,0.95]]] },
  };
  function supports(layer) { return !!LAYERS[layer]; }

  var st = { map: null, on: false, layer: 'wind', token: 0, field: null, notify: function () {}, handler: null, debounce: null, lastKey: '' };

  function codec() { return window.HelmWxCodec; }

  // The grid covers the VIEWPORT + a 50% margin on each side, so the rendered field runs PAST the
  // visible edges (fills the screen with REAL fetched data — not a box, and not a stretched raster).
  function viewBbox(map) {
    var b = map.getBounds(), w = b.getWest(), s = b.getSouth(), e = b.getEast(), n = b.getNorth();
    var mw = (e - w) * 0.5, mh = (n - s) * 0.5;
    return [Math.max(-180, w - mw), Math.max(-84, s - mh), Math.min(180, e + mw), Math.min(84, n + mh)];
  }
  function covers(field, map) {                            // does the rendered overlay still span the view?
    if (!field) return false;
    var b = map.getBounds();
    return field.west <= b.getWest() && field.east >= b.getEast() && field.south <= b.getSouth() && field.north >= b.getNorth();
  }
  function clearLayer(map) { if (map.getLayer(LYR)) map.removeLayer(LYR); if (map.getSource(SRC)) map.removeSource(SRC); st.field = null; }

  function grid(bbox, nx, ny) {
    var lats = [], lons = [], qlat = [], qlon = [];
    for (var j = 0; j < ny; j++) lats.push(bbox[3] - (bbox[3] - bbox[1]) * j / (ny - 1));
    for (var i = 0; i < nx; i++) lons.push(bbox[0] + (bbox[2] - bbox[0]) * i / (nx - 1));
    for (var a = 0; a < lats.length; a++) for (var c = 0; c < lons.length; c++) { qlat.push(+lats[a].toFixed(4)); qlon.push(+lons[c].toFixed(4)); }
    return { nx: nx, ny: ny, lats: lats, lons: lons, qlat: qlat, qlon: qlon };
  }

  function url(g, layer, model) {
    var L = LAYERS[layer];
    var p = 'latitude=' + g.qlat.join(',') + '&longitude=' + g.qlon.join(',') + '&current=' + L.v;
    if (layer === 'wind' || layer === 'gust') p += '&wind_speed_unit=kn';
    if (model && model !== 'gfs_seamless') p += '&models=' + model;
    return FORECAST + '?' + p;
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
    var coords = [[field.west, field.north], [field.east, field.north], [field.east, field.south], [field.west, field.south]];
    if (map.getSource(SRC)) map.getSource(SRC).updateImage({ url: urlData, coordinates: coords });
    else {
      map.addSource(SRC, { type: 'image', url: urlData, coordinates: coords });
      map.addLayer({ id: LYR, type: 'raster', source: SRC, paint: { 'raster-opacity': 0.72, 'raster-resampling': 'linear', 'raster-fade-duration': 0 } },
        map.getLayer('route-line') ? 'route-line' : undefined);
    }
  }

  async function fetchPoints(u, signal) {
    var r = await fetch(u, { signal: signal });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  async function refresh() {
    if (!st.on || !supports(st.layer)) return;
    var bbox = viewBbox(st.map);
    var key = st.layer + ':' + bbox.map(function (x) { return x.toFixed(2); }).join(',');
    if (key === st.lastKey && covers(st.field, st.map)) return;   // same view + overlay still covers it -> skip
    st.lastKey = key;
    var g = grid(bbox, 12, 12), my = ++st.token;
    var ac = new AbortController();
    st.notify('Fetching live ' + st.layer + ' for this view …', 'info');
    try {
      var nodes = await fetchPoints(url(g, st.layer, st.model === 'gfs_seamless' ? null : st.model), ac.signal);
      if (my !== st.token || !st.on) return;              // a newer pan superseded this one
      var field = toField(nodes, g, st.layer);
      if (!field.values.some(function (v) { return isFinite(v); })) { clearLayer(st.map); st.notify('No live data for this area', 'warn'); return; }
      renderField(st.map, field);
      st.notify('Live ' + st.layer + ' · Open-Meteo, this view', 'ok');
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      // honest offline behaviour — never fabricate a field, and don't leave a stale overlay in the
      // wrong place: if what's rendered no longer covers the view, drop it.
      if (!covers(st.field, st.map)) clearLayer(st.map);
      st.notify('Live weather needs a connection — offline. (Standard mode shows your cached local field.)', 'warn');
    }
  }

  function onMove() { clearTimeout(st.debounce); st.debounce = setTimeout(refresh, 450); }

  function enable(map, opts) {
    opts = opts || {};
    st.map = map; st.layer = opts.layer || st.layer; st.model = opts.model || 'gfs_seamless';
    st.notify = opts.notify || st.notify; st.on = true; st.lastKey = '';
    if (!st.handler) { st.handler = onMove; map.on('moveend', st.handler); }
    refresh();
  }
  function disable(map) {
    st.on = false;
    if (st.handler) { (map || st.map).off('moveend', st.handler); st.handler = null; }
    var m = map || st.map; if (m) { if (m.getLayer(LYR)) m.removeLayer(LYR); if (m.getSource(SRC)) m.removeSource(SRC); }
    st.field = null; st.lastKey = '';
  }
  function setLayer(layer) { st.layer = layer; st.lastKey = ''; if (st.on) refresh(); }
  function setModel(model) { st.model = model; st.lastKey = ''; if (st.on) refresh(); }
  function sampleAt(lat, lon) {
    var f = st.field, C = codec(); if (!f || !C) return null;
    if (lon < f.west || lon > f.east || lat < f.south || lat > f.north) return { value: null, source: 'open', note: 'outside live view' };
    var fx = (lon - f.west) / ((f.east - f.west) || 1) * (f.nx - 1), fy = (f.north - lat) / ((f.north - f.south) || 1) * (f.ny - 1);
    var v = C.bilinear(f.values, f.nx, f.ny, fx, fy);
    return { layer: f.layer, value: (v == null || !isFinite(v)) ? null : Math.round(v * 100) / 100, unit: f.unit, source: 'open', sourceRef: { title: 'Open-Meteo (live)' } };
  }

  window.HelmWxLive = { enable: enable, disable: disable, setLayer: setLayer, setModel: setModel, sampleAt: sampleAt, renderField: renderField, supports: supports, _toField: toField, _viewBbox: viewBbox, _grid: grid };
})();
