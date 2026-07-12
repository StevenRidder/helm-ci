// LAYER-2 — Client loader: helm.layer.manifest.v1 -> MapLibre overlay tier.
//
// Fetches GET /layer-manifest (served by helm-packd / pipeline/mbtiles_server.py, LAYER-1) and
// injects each user overlay as a runtime MapLibre source + layer, inserted into its FUSE-2 draw
// band (basemap -> enc -> overlay -> weather -> nav) via `beforeId` so it paints at the top of its
// band WITHOUT owning official chart z-order (see docs/proposals/interfaces/layer-manifest-v1.md).
//
// Scope (v1): renders `geojson` overlays. Pack/tile/bundle formats (pmtiles/mbtiles/png/env-bundle)
// stay owned by their dedicated client modules (offline-packs.js, wx-grid) and are skipped here with
// a NAMED, visible reason -- never a silent drop. Interface Failure Rules honored: private paths are
// refused, a missing/empty manifest never fails chart rendering, and stale/out-of-coverage layers
// render dimmed AND report their status (console + HelmLayerManifest.status()).
(function () {
  'use strict';

  var MANIFEST_URL = '/layer-manifest';
  var SCHEMA = 'helm.layer.manifest.v1';
  var ID_PREFIX = 'helm-layer-';          // every source/layer id we add is namespaced helm-layer-*
  var DEFAULT_TIER = 'overlay';
  var DEFAULT_COLOR = '#5bc0ff';

  // FUSE-2 draw bands, bottom -> top. Mirror of web/SHELL.md + web/tests/fuse-2-layer-order.test.js.
  // A tier-T overlay inserts just below the lowest present layer of the next band up.
  var BANDS = [
    { tier: 'basemap', ids: ['ocean', 'helm-chart-online-fill', 'navionics', 'googlesat', 'bingsat', 'arcgis', 'satellite', 'charts'] },
    { tier: 'enc',     ids: ['enc-chart', 'depare-fill', 'depcnt-line', 'soundg-text'] },
    { tier: 'overlay', ids: ['route-line'] },
    { tier: 'weather', ids: ['wind-arrows'] },
    { tier: 'nav',     ids: ['whereto-ring', 'whereto-rank', 'places-cluster', 'places-cluster-count', 'places-halo', 'places-icon', 'places-label', 'ais-vessels', 'ais-label', 'saved-halo', 'saved-icon', 'saved-label'] }
  ];

  // Manifest ids already drawn by the base style / dedicated modules -- never double-draw these.
  var BASE_OWNED = { 'depare': 1, 'depcnt': 1, 'soundg': 1, 'enc-chart': 1, 'depare-fill': 1, 'depcnt-line': 1, 'soundg-text': 1 };

  // Formats owned by another client module -> deferred (named, not hidden).
  var DEFERRED = {
    'pmtiles': 'offline-packs.js', 'mbtiles': 'offline-packs.js', 'raster': 'offline-packs.js',
    'png': 'offline-packs.js', 'jpg': 'offline-packs.js', 'jpeg': 'offline-packs.js',
    'environmental-bundle': 'wx-grid', 'env-bundle': 'wx-grid', 'helm.env.bundle.v1': 'wx-grid'
  };

  // freshness statuses that render degraded (dimmed + reported). 'ok'/'unknown' render normally.
  var DEGRADED = { 'stale': 1, 'expired': 1, 'out-of-coverage': 1, 'out_of_coverage': 1, 'missing': 1, 'error': 1 };

  var state = { tracked: [], summary: null, lastError: null };
  var cmdRegistered = false;

  function win() { return (typeof window !== 'undefined') ? window : null; }

  function warn(msg) {
    var w = win();
    try { if (w && w.HelmLog && w.HelmLog.warn) { w.HelmLog.warn(msg); return; } } catch (e) {}
    try { console.warn(msg); } catch (e2) {}
  }
  function info(msg) {
    var w = win();
    try { if (w && w.HelmLog && w.HelmLog.info) { w.HelmLog.info(msg); return; } } catch (e) {}
    try { console.log(msg); } catch (e2) {}
  }

  function slug(id) {
    return String(id == null ? '' : id).toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'layer';
  }

  function sourceId(entry) { return ID_PREFIX + slug(entry && entry.id) + '-src'; }

  // Defense in depth: the server strips private paths, but never trust a filesystem path client-side.
  function isPublicUrl(url) {
    if (typeof url !== 'string') return false;
    var u = url.trim();
    if (!u) return false;
    if (u.indexOf('\\') !== -1) return false;             // Windows separator
    if (/^[a-z]:[\\/]/i.test(u)) return false;            // C:\ or C:/
    if (u.indexOf('..') !== -1) return false;             // path traversal
    if (/^file:/i.test(u)) return false;                  // file: URL
    if (/^\/(Users|home|root|private)\//i.test(u)) return false;  // obvious private FS roots
    if (/^https?:\/\//i.test(u)) return true;             // absolute http(s)
    if (u.indexOf('//') === 0) return true;               // protocol-relative
    if (u.charAt(0) === '/') return true;                 // server route, e.g. /user-data/...
    return /^[\w.\-]/.test(u);                            // app-relative, e.g. data/notes.geojson
  }

  function tierIndex(tier) {
    var t = String(tier || '').toLowerCase(), i;
    for (i = 0; i < BANDS.length; i++) if (BANDS[i].tier === t) return i;
    for (i = 0; i < BANDS.length; i++) if (BANDS[i].tier === DEFAULT_TIER) return i;
    return 0;
  }

  function normTier(entry) {
    var t = String((entry && entry.tier) || '').toLowerCase();
    for (var i = 0; i < BANDS.length; i++) if (BANDS[i].tier === t) return t;
    return DEFAULT_TIER;
  }

  // beforeId anchor: the lowest present layer of any band strictly above `tier`.
  // undefined => nothing above is present => append on top of the stack.
  function tierBeforeId(map, tier) {
    if (!map || typeof map.getLayer !== 'function') return undefined;
    for (var b = tierIndex(tier) + 1; b < BANDS.length; b++) {
      var ids = BANDS[b].ids;
      for (var i = 0; i < ids.length; i++) {
        try { if (map.getLayer(ids[i])) return ids[i]; } catch (e) {}
      }
    }
    return undefined;
  }

  function freshnessStatus(entry) {
    var f = entry && entry.freshness;
    if (f && typeof f === 'object' && typeof f.status === 'string') return f.status.toLowerCase();
    if (typeof f === 'string') return f.toLowerCase();
    return 'unknown';
  }
  function isDegraded(entry) { return !!DEGRADED[freshnessStatus(entry)]; }

  // geojson => supported here. Pack/tile/bundle formats => deferred to their owner module (named).
  function classify(entry) {
    var fmt = String((entry && entry.format) || '').toLowerCase();
    if (fmt === 'geojson' || fmt === 'json') return { supported: true, format: 'geojson', reason: '' };
    if (DEFERRED[fmt]) return { supported: false, format: fmt, reason: 'deferred-to-' + DEFERRED[fmt] };
    return { supported: false, format: fmt || 'unknown', reason: 'unsupported-format' };
  }

  function layerColor(entry) {
    if (entry && typeof entry.color === 'string') return entry.color;
    var src = entry && entry.source;
    if (src && typeof src.color === 'string') return src.color;
    return DEFAULT_COLOR;
  }

  function sourceSpec(entry) {
    if (!classify(entry).supported) return null;
    var spec = { type: 'geojson', data: entry.url };
    var src = entry && entry.source;
    var attr = src && (src.attribution || src.label);
    if (attr) spec.attribution = String(attr);
    if (entry && entry.promoteId) spec.promoteId = entry.promoteId;
    return spec;
  }

  // Pure: MapLibre layer spec(s) for one manifest entry. points->circle, lines->line,
  // polygons->fill+outline. Degraded (stale/out-of-coverage) layers render dimmed + dashed.
  function layerSpecs(entry) {
    var id = slug(entry && entry.id);
    var srcId = ID_PREFIX + id + '-src';
    var kind = String((entry && entry.kind) || '').toLowerCase();
    var color = layerColor(entry);
    var degraded = isDegraded(entry);
    var meta = {
      'helm:layer': {
        id: entry && entry.id, tier: normTier(entry), degraded: degraded,
        freshness: freshnessStatus(entry), inspection: (entry && entry.inspection) || null
      }
    };
    function withBase(spec) { spec.source = srcId; spec.metadata = meta; return spec; }

    if (kind === 'lines' || kind === 'line') {
      var linePaint = { 'line-color': color, 'line-width': 1.6, 'line-opacity': degraded ? 0.4 : 0.9 };
      if (degraded) linePaint['line-dasharray'] = [2, 2];
      return [withBase({ id: ID_PREFIX + id, type: 'line', paint: linePaint })];
    }
    if (kind === 'polygons' || kind === 'polygon' || kind === 'fill') {
      var outPaint = { 'line-color': color, 'line-width': 1.2, 'line-opacity': degraded ? 0.4 : 0.85 };
      if (degraded) outPaint['line-dasharray'] = [2, 2];
      return [
        withBase({ id: ID_PREFIX + id + '-fill', type: 'fill', paint: { 'fill-color': color, 'fill-opacity': degraded ? 0.12 : 0.28 } }),
        withBase({ id: ID_PREFIX + id + '-outline', type: 'line', paint: outPaint })
      ];
    }
    // default: points -> circle
    return [withBase({
      id: ID_PREFIX + id, type: 'circle',
      paint: {
        'circle-radius': 5, 'circle-color': color,
        'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.2,
        'circle-opacity': degraded ? 0.4 : 0.9, 'circle-stroke-opacity': degraded ? 0.4 : 1
      }
    })];
  }

  // Add one manifest entry to the map. Returns a status record (never throws).
  function addEntry(map, entry) {
    var result = { id: entry && entry.id, added: false, srcId: null, layerIds: [], tier: normTier(entry), status: 'ok', reason: '' };
    if (!entry || entry.id == null || entry.id === '') { result.status = 'skipped'; result.reason = 'missing-id'; return result; }
    if (BASE_OWNED[String(entry.id).toLowerCase()]) { result.status = 'skipped'; result.reason = 'base-owned'; return result; }
    var cls = classify(entry);
    if (!cls.supported) { result.status = 'skipped'; result.reason = cls.reason; return result; }
    if (!isPublicUrl(entry.url)) {
      result.status = 'rejected'; result.reason = 'non-public-url';
      warn('[layer-manifest] refused non-public url for "' + entry.id + '": ' + entry.url);
      return result;
    }
    if (!map || typeof map.addLayer !== 'function') { result.status = 'error'; result.reason = 'no-map'; return result; }

    var srcId = sourceId(entry);
    result.srcId = srcId;
    try {
      if (!(map.getSource && map.getSource(srcId))) map.addSource(srcId, sourceSpec(entry));
    } catch (e) {
      result.status = 'error'; result.reason = 'addSource:' + (e && e.message);
      warn('[layer-manifest] addSource ' + srcId + ' failed: ' + (e && e.message));
      return result;
    }

    var before = tierBeforeId(map, result.tier);
    layerSpecs(entry).forEach(function (spec) {
      try {
        if (map.getLayer && map.getLayer(spec.id)) { result.layerIds.push(spec.id); return; }
        try { map.addLayer(spec, before); } catch (e) { map.addLayer(spec); }  // anchor may be absent
        result.layerIds.push(spec.id);
      } catch (e2) {
        warn('[layer-manifest] addLayer ' + spec.id + ' failed: ' + (e2 && e2.message));
      }
    });

    result.added = result.layerIds.length > 0;
    if (result.added && isDegraded(entry)) {
      result.status = 'degraded'; result.reason = 'freshness:' + freshnessStatus(entry);
      warn('[layer-manifest] layer "' + entry.id + '" is ' + freshnessStatus(entry) + ' (rendered dimmed)');
    }
    return result;
  }

  // Remove every layer/source we previously added (idempotent re-load).
  function clear(map) {
    if (map && typeof map.getLayer === 'function') {
      state.tracked.forEach(function (t) {
        (t.layerIds || []).forEach(function (lid) {
          try { if (map.getLayer(lid)) map.removeLayer(lid); } catch (e) {}
        });
        try { if (map.getSource && map.getSource(t.srcId)) map.removeSource(t.srcId); } catch (e2) {}
      });
    }
    state.tracked = [];
  }

  function applyManifest(map, manifest) {
    var summary = { schema: manifest && manifest.schema, loaded: [], degraded: [], skipped: [], rejected: [], errors: [] };
    if (!manifest || !Array.isArray(manifest.layers)) {
      state.lastError = { reason: 'malformed-manifest', message: 'manifest.layers is not an array' };
      summary.errors.push(state.lastError);
      warn('[layer-manifest] malformed manifest: layers[] missing or not an array');
      state.summary = summary;
      return summary;
    }
    if (manifest.schema && manifest.schema !== SCHEMA) {
      warn('[layer-manifest] unexpected schema "' + manifest.schema + '" (expected ' + SCHEMA + '); best-effort load');
    }
    clear(map);
    manifest.layers.forEach(function (entry) {
      var r = addEntry(map, entry);
      if (r.added) {
        state.tracked.push({ srcId: r.srcId, layerIds: r.layerIds });
        (r.status === 'degraded' ? summary.degraded : summary.loaded).push(r);
      } else if (r.status === 'rejected') summary.rejected.push(r);
      else if (r.status === 'error') summary.errors.push(r);
      else summary.skipped.push(r);
    });
    state.lastError = null;
    state.summary = summary;
    info('[layer-manifest] loaded ' + (summary.loaded.length + summary.degraded.length) +
      ' overlay layer(s); skipped ' + summary.skipped.length + ', rejected ' + summary.rejected.length +
      ', errors ' + summary.errors.length);
    return summary;
  }

  function fetchManifest(fetchFn) {
    var w = win();
    var f = fetchFn || (w && typeof w.fetch === 'function' ? w.fetch.bind(w) : (typeof fetch === 'function' ? fetch : null));
    if (!f) return Promise.reject(new Error('no fetch available'));
    return Promise.resolve(f(MANIFEST_URL, { cache: 'no-store' })).then(function (res) {
      if (!res) throw new Error('empty response');
      if (!res.ok) {
        // 404 => manifest not served / no user overlays. A normal empty state, not a failure.
        if (res.status === 404) return { schema: SCHEMA, layers: [], _absent: true };
        var err = new Error('layer-manifest HTTP ' + res.status);
        err.httpStatus = res.status;
        throw err;
      }
      return res.json();
    });
  }

  // Fetch + apply. Fails LOUD (named signal) but never rejects/throws -- a broken or missing manifest
  // must not break chart rendering (interface Failure Rule). No fake-green fallback.
  function load(map, opts) {
    opts = opts || {};
    var w = win();
    map = map || (w && w.map) || null;
    return fetchManifest(opts.fetch).then(function (manifest) {
      return applyManifest(map, manifest);
    }).catch(function (e) {
      state.lastError = { reason: 'load-failed', message: e && e.message };
      warn('[layer-manifest] load failed: ' + (e && e.message));
      var summary = { schema: null, loaded: [], degraded: [], skipped: [], rejected: [], errors: [state.lastError] };
      state.summary = summary;
      return summary;
    });
  }

  function registerReloadCommand() {
    if (cmdRegistered) return;
    var w = win();
    if (!w || !w.HelmShell || typeof w.HelmShell.registerCommand !== 'function') return;
    try {
      w.HelmShell.registerCommand({
        id: 'helm-layer-reload-manifest', epic: 'LAYER',
        title: 'Reload user overlay layers', subtitle: 'Re-fetch /layer-manifest',
        keywords: ['layer', 'manifest', 'overlay', 'reload'], group: 'Layers',
        run: function (ctx) { load((ctx && ctx.map) || (win() && win().map)); }
      });
      cmdRegistered = true;
    } catch (e) {}
  }

  function bind(map) {
    var w = win();
    map = map || (w && w.map) || null;
    if (!map) return;
    var run = function () { registerReloadCommand(); load(map); };
    if (map.isStyleLoaded && map.isStyleLoaded()) run();
    else if (map.once) map.once('load', run);
    else if (map.on) map.on('load', run);
  }

  function status() {
    return {
      summary: state.summary,
      lastError: state.lastError,
      trackedLayers: state.tracked.reduce(function (n, t) { return n + (t.layerIds ? t.layerIds.length : 0); }, 0)
    };
  }

  var api = {
    MANIFEST_URL: MANIFEST_URL, SCHEMA: SCHEMA, ID_PREFIX: ID_PREFIX, DEFAULT_TIER: DEFAULT_TIER, BANDS: BANDS,
    slug: slug, sourceId: sourceId, isPublicUrl: isPublicUrl, tierIndex: tierIndex, normTier: normTier,
    tierBeforeId: tierBeforeId, freshnessStatus: freshnessStatus, isDegraded: isDegraded,
    classify: classify, sourceSpec: sourceSpec, layerSpecs: layerSpecs, addEntry: addEntry,
    clear: clear, applyManifest: applyManifest, fetchManifest: fetchManifest, load: load, bind: bind, status: status
  };
  if (win()) win().HelmLayerManifest = api;

  // Self-wire to the real map once it exists (mirrors offline-packs.js CLIENT-22 deferral). Guarded
  // so the module stays inert when loaded head-less in a unit test (no setTimeout in the vm sandbox).
  if (win() && typeof setTimeout === 'function') {
    (function waitForMap(attempt) {
      if (win().map && typeof win().map.on === 'function') { bind(win().map); return; }
      if ((attempt || 0) < 150) setTimeout(function () { waitForMap((attempt || 0) + 1); }, 100);
    })(0);
  }
})();
