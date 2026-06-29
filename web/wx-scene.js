// wx-scene.js — WX-19 Environmental Scene renderer.  Phase 1: scalar field from the WX-17/18 bundle.
// ------------------------------------------------------------------------------------------------
// Replaces the old per-renderer soup (field-layer/wx-live/cog image paths) with ONE scene that reads
// the prepared model-run bundle (helm.env.bundle.v1).
//
// CONTRACT-ONLY COUPLING — this is why the planned Python->C++ backend port is invisible here:
//   • we read the prepared-bundle MANIFEST and use ITS urlTemplates / lod / ramp / coverage — we
//     hardcode no endpoint paths and no provider behaviour;
//   • tiles are helm-wxv1 value rasters decoded by HelmWxCodec and coloured by HelmWxRamp (CLIENT-14,
//     so field + particles + probe agree by construction; the manifest ramp wins via setManifestRamp);
//   • LOD / overzoom / parent-fallback / no-blank-edge come from the raster source's min/maxzoom
//     (CLIENT-22 discipline) — MapLibre scales prepared parent/native tiles, never blanks inside coverage;
//   • NO upstream fetch on the gesture path: we only ever GET prepared bundle tiles (the gateway stamps
//     X-Helm-Upstream-Fetch: 0). Materialize/refresh is the gateway's job, not the renderer's.
//
// Phase 2 adds vector particles (wind/current) from the same bundle uv tiles; phase 3 adds time
// interpolation + last-good + stale/missing + probe; phase 4 swaps in the WebGPU render path.
(function (global) {
  'use strict';

  var PROTO = 'helmscene';                      // helmscene://<sceneKey>/{z}/{x}/{y}
  var SRC = 'helm-wx-scene', LYR = 'helm-wx-scene';
  var DEFAULT_SVC = (typeof location !== 'undefined') ? (location.protocol + '//' + location.hostname + ':8093') : '';
  var log = (global.HelmLog && HelmLog.scope) ? HelmLog.scope('wx-scene') : console;

  var scenes = {};          // sceneKey -> { template (abs url with {z}/{x}/{y}), layer, scale, offset }
  var protoBound = false;
  var bmpWarned = false;
  var state = { map: null, region: null, layer: null, validTimeId: null, manifest: null, opacity: 0.82 };

  function svc() { return global.HELM_WX_SERVICE || DEFAULT_SVC; }
  function codec() { return global.HelmWxCodec; }
  function ramp() { return global.HelmWxRamp; }

  // ---- canvas + degrade-safe transparent fallback (mirrors the cog.js createImageBitmap fix) ------
  function makeCanvas(w, h) {
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
    var c = document.createElement('canvas'); c.width = w; c.height = h; return c;
  }
  var _blankP = null;
  function transparentBitmap() {                // 1x1 transparent -> MapLibre keeps the parent tile (no blank)
    if (!_blankP) { try { _blankP = createImageBitmap(makeCanvas(1, 1)); } catch (e) { _blankP = Promise.reject(e); } }
    return _blankP.then(function (b) { return { data: b }; }, function () { return { data: new Uint8Array() }; });
  }
  function bmpFail(e) {
    if (bmpWarned) return; bmpWarned = true;
    (log.warn || console.warn).call(log, '[wx-scene] tile colourise failed; transparent fallback: ' + ((e && e.message) || e));
  }

  // ---- helm-wxv1 value tile -> colourised ImageBitmap (per-pixel decode + shared ramp) ------------
  function colorize(buf, layer, scale, offset) {
    return createImageBitmap(new Blob([buf], { type: 'image/png' })).then(function (img) {
      var w = img.width || 256, h = img.height || 256;
      if (!w || !h) return transparentBitmap();
      var cv = makeCanvas(w, h), ctx = cv.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(img, 0, 0);
      if (img.close) try { img.close(); } catch (e) {}
      var src;
      try { src = ctx.getImageData(0, 0, w, h); } catch (e) { return transparentBitmap(); }
      var out = ctx.createImageData(w, h), sd = src.data, od = out.data, C = codec(), R = ramp();
      for (var i = 0; i < sd.length; i += 4) {
        var v = C.decodeRGBA(sd[i], sd[i + 1], sd[i + 2], sd[i + 3], scale, offset);
        if (v == null) { od[i + 3] = 0; continue; }      // NODATA -> transparent (honest gap, never invented)
        var c = R.rampColor(layer, v);
        od[i] = c[0]; od[i + 1] = c[1]; od[i + 2] = c[2]; od[i + 3] = c[3];
      }
      ctx.putImageData(out, 0, 0);
      return createImageBitmap(cv).then(function (bmp) { return { data: bmp }; });
    });
  }

  // ---- custom protocol handler: MapLibre substitutes {z}/{x}/{y}, then calls us per tile -----------
  function tileHandler(params, abortController) {
    var rest = params.url.slice((PROTO + '://').length);
    var m = rest.match(/^([^/]+)\/(\d+)\/(\d+)\/(\d+)/);
    if (!m) return transparentBitmap();
    var sc = scenes[m[1]];
    if (!sc) return transparentBitmap();
    var url = sc.template.replace('{z}', m[2]).replace('{x}', m[3]).replace('{y}', m[4]);
    var signal = abortController && abortController.signal;
    return fetch(url, { signal: signal }).then(function (r) {
      if (r.status === 404) return transparentBitmap();   // missing tile inside declared coverage -> parent shows
      if (!r.ok) throw new Error('wx-scene tile HTTP ' + r.status);
      return r.arrayBuffer().then(function (buf) {
        return colorize(buf, sc.layer, sc.scale, sc.offset).catch(function (e) { bmpFail(e); return transparentBitmap(); });
      });
    });
  }
  function ensureProtocol() {
    if (protoBound || !global.maplibregl || !maplibregl.addProtocol) return;
    try { maplibregl.addProtocol(PROTO, tileHandler); } catch (e) { if (!/already|exist|regist/i.test(String(e && e.message))) throw e; }
    protoBound = true;
  }

  // ---- manifest: the renderer's source of truth (drives URLs/LOD/ramp/coverage; port-agnostic) -----
  function manifestUrl(region) { return svc() + '/bundles/open-meteo/latest/' + encodeURIComponent(region) + '/manifest.json'; }
  function loadManifest(region) {
    return fetch(manifestUrl(region), { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('bundle manifest HTTP ' + r.status + ' — materialize region "' + region + '" first');
      return r.json();
    });
  }
  function layerCfg(manifest, layer) { return (manifest && manifest.layers && manifest.layers[layer]) || {}; }
  function frameId(manifest, isoTime) {
    var map = (manifest && manifest.run && manifest.run.frameIdByValidTime) || {};
    if (isoTime && map[isoTime]) return map[isoTime];
    var ids = Object.keys(map).map(function (k) { return map[k]; });
    return ids.length ? ids[0] : 'latest';
  }
  function scaleOffsetFor(manifest, layer) {
    var L = layerCfg(manifest, layer), rng = L.range || (L.fieldTiles && L.fieldTiles.range) || {};
    return codec().scaleOffset(rng.min, rng.max);
  }
  function lodRange(manifest, layer) {
    var ft = layerCfg(manifest, layer).fieldTiles || {};
    if (ft.minzoom != null && ft.maxzoom != null) return { minzoom: ft.minzoom, maxzoom: ft.maxzoom };
    var lv = (manifest.lod && manifest.lod.levels) || {}, los = [], his = [];
    Object.keys(lv).forEach(function (k) { if (isFinite(lv[k].minzoom)) los.push(lv[k].minzoom); if (isFinite(lv[k].maxzoom)) his.push(lv[k].maxzoom); });
    return { minzoom: los.length ? Math.min.apply(null, los) : 0, maxzoom: his.length ? Math.max.apply(null, his) : 8 };
  }
  function coverageBounds(manifest) {
    var b = (manifest.coverage || {}).bbox;
    if (!b || b.crossesAntimeridian) return null;          // wrap-crossing coverage -> let MapLibre wrap (no bounds clamp)
    return [b.west, b.south, b.east, b.north];
  }
  function tileTemplateAbs(manifest, layer, vtId) {
    var ft = layerCfg(manifest, layer).fieldTiles || {};
    var tpl = ft.urlTemplate || '';                        // e.g. /bundles/open-meteo/latest/fiji/layers/wind/scalar/{validTimeId}/{z}/{x}/{y}.png
    return svc() + tpl.replace('{validTimeId}', vtId);     // leaves {z}/{x}/{y} for MapLibre
  }

  function beforeId(m) { return m.getLayer('route-line') ? 'route-line' : (m.getLayer('enc-chart') ? 'enc-chart' : undefined); }
  function remove() {
    var m = state.map; if (!m) return;
    try { if (m.getLayer(LYR)) m.removeLayer(LYR); } catch (e) {}
    try { if (m.getSource(SRC)) m.removeSource(SRC); } catch (e) {}
  }

  // ---- public API --------------------------------------------------------------------------------
  // enableScalar(map, { region, layer, isoTime, opacity }) -> Promise<{layer,validTimeId,lod,bounds,unit,ramp}>
  function enableScalar(map, opts) {
    opts = opts || {};
    state.map = map; ensureProtocol();
    var region = opts.region || state.region || 'fiji';
    var layer = opts.layer || 'wind';
    return loadManifest(region).then(function (manifest) {
      state.manifest = manifest; state.region = region; state.layer = layer;
      var L = layerCfg(manifest, layer);
      if (L.ramp && ramp() && ramp().setManifestRamp) ramp().setManifestRamp(layer, L.ramp);   // CLIENT-14: field/particles/probe agree
      var vtId = frameId(manifest, opts.isoTime); state.validTimeId = vtId;
      var so = scaleOffsetFor(manifest, layer), lod = lodRange(manifest, layer), bounds = coverageBounds(manifest);
      var key = region + '|' + layer + '|' + vtId;
      scenes[key] = { template: tileTemplateAbs(manifest, layer, vtId), layer: layer, scale: so.scale, offset: so.offset };
      remove();
      var src = { type: 'raster', tiles: [PROTO + '://' + key + '/{z}/{x}/{y}'], tileSize: 256, minzoom: lod.minzoom, maxzoom: lod.maxzoom };
      if (bounds) src.bounds = bounds;
      map.addSource(SRC, src);
      map.addLayer({
        id: LYR, type: 'raster', source: SRC,
        paint: { 'raster-opacity': (opts.opacity != null ? opts.opacity : state.opacity), 'raster-resampling': 'linear', 'raster-fade-duration': 280 }
      }, beforeId(map));
      return { layer: layer, validTimeId: vtId, lod: lod, bounds: bounds, unit: L.unit || '', ramp: L.ramp || null };
    });
  }
  function setOpacity(o) { state.opacity = o; try { if (state.map && state.map.getLayer(LYR)) state.map.setPaintProperty(LYR, 'raster-opacity', o); } catch (e) {} }

  // ============================ PHASE 2: vector particles =========================================
  // Animate wind/current particles from the PREPARED bundle uv tiles (not the gesture-fetching
  // /velocity endpoint) — same bundle/time/coverage as the scalar colour field. We decode the uv
  // component tiles and sample them onto a regular lat/lon grid (mercator-correct: we sample at
  // lat/lon points, reading the right mercator pixel), then feed the existing GPU particle engine
  // (window.__helmWind). Colour stays on the scalar field (Windy-style: coloured field + pale streaks).
  var VGRID_NX = 80, VGRID_NY = 60;             // velocity sample-grid resolution over the viewport
  var pState = { on: false, layer: null, moveHandler: null, debounce: null, token: 0 };
  var valueTileCache = {};                      // url -> Promise<{w,h,vals(Float32, NaN=NODATA)}|null>

  function fetchValueTile(url, scale, offset) {
    if (valueTileCache[url]) return valueTileCache[url];
    var p = fetch(url).then(function (r) {
      if (r.status === 404) return null;
      if (!r.ok) throw new Error('uv tile HTTP ' + r.status);
      return r.arrayBuffer().then(function (buf) {
        return createImageBitmap(new Blob([buf], { type: 'image/png' })).then(function (img) {
          var w = img.width || 256, h = img.height || 256, cv = makeCanvas(w, h), cx = cv.getContext('2d', { willReadFrequently: true });
          cx.drawImage(img, 0, 0); if (img.close) try { img.close(); } catch (e) {}
          var d = cx.getImageData(0, 0, w, h).data, vals = new Float32Array(w * h), C = codec();
          for (var i = 0, j = 0; i < d.length; i += 4, j++) {
            var v = C.decodeRGBA(d[i], d[i + 1], d[i + 2], d[i + 3], scale, offset);
            vals[j] = (v == null ? NaN : v);     // honest NODATA -> NaN (not finite -> particle won't advect)
          }
          return { w: w, h: h, vals: vals };
        });
      });
    }).catch(function () { return null; });
    valueTileCache[url] = p; return p;
  }
  function sampleTileSet(tiles, lon, lat, z) {
    var C = codec(), p = C.lonLatToPixel(lon, lat, z, 256), g = tiles[p.x + '/' + p.y];
    if (!g || !g.vals) return NaN;
    var v = C.bilinear(g.vals, g.w, g.h, p.px, p.py);
    return (v == null ? NaN : v);
  }
  function assign(a, b) { for (var k in b) if (b.hasOwnProperty(k)) a[k] = b[k]; return a; }

  // Assemble the GRIB-JSON velocity array (u,v components) the particle engine ingests.
  function buildVelocity(layer) {
    var m = state.map, manifest = state.manifest, C = codec();
    var vf = layerCfg(manifest, layer).vectorField;
    if (!m || !vf || !vf.u || !vf.v) return Promise.resolve(null);
    var lod = lodRange(manifest, layer);
    var z = Math.max(lod.minzoom, Math.min(lod.maxzoom, Math.round(m.getZoom())));
    var b = m.getBounds(), W = b.getWest(), E = b.getEast(), S = b.getSouth(), N = b.getNorth();
    var cov = (manifest.coverage || {}).bbox;
    if (cov && !cov.crossesAntimeridian) { W = Math.max(W, cov.west); E = Math.min(E, cov.east); S = Math.max(S, cov.south); N = Math.min(N, cov.north); }
    if (!(E > W && N > S)) return Promise.resolve(null);          // viewport doesn't overlap coverage
    var vt = state.validTimeId, list = C.tilesForBbox(z, [W, S, E, N]);
    var uTpl = svc() + vf.u.urlTemplate.replace('{validTimeId}', vt);
    var vTpl = svc() + vf.v.urlTemplate.replace('{validTimeId}', vt);
    function url(tpl, t) { return tpl.replace('{z}', t.z).replace('{x}', t.x).replace('{y}', t.y); }
    function gather(tpl, so) {
      return Promise.all(list.map(function (t) {
        return fetchValueTile(url(tpl, t), so.scale, so.offset).then(function (g) { return { k: t.x + '/' + t.y, g: g }; });
      })).then(function (rows) { var mp = {}; rows.forEach(function (r) { if (r.g) mp[r.k] = r.g; }); return mp; });
    }
    return Promise.all([gather(uTpl, vf.u), gather(vTpl, vf.v)]).then(function (sets) {
      var uT = sets[0], vT = sets[1], NX = VGRID_NX, NY = VGRID_NY, us = new Array(NX * NY), vs = new Array(NX * NY), any = false;
      for (var j = 0; j < NY; j++) {
        var lat = N - (N - S) * (j / (NY - 1));
        for (var i = 0; i < NX; i++) {
          var lon = W + (E - W) * (i / (NX - 1));
          var u = sampleTileSet(uT, lon, lat, z), v = sampleTileSet(vT, lon, lat, z);
          us[j * NX + i] = u; vs[j * NX + i] = v;
          if (u === u && v === v) any = true;                     // NaN !== NaN
        }
      }
      if (!any) return null;
      var hdr = { nx: NX, ny: NY, lo1: W, la1: N, lo2: E, la2: S, dx: (E - W) / (NX - 1), dy: (N - S) / (NY - 1) };
      return [{ header: assign({ parameterNumber: 2 }, hdr), data: us }, { header: assign({ parameterNumber: 3 }, hdr), data: vs }];
    });
  }

  function refreshParticles() {
    var w = global.__helmWind; if (!pState.on || !w) return;
    var tok = ++pState.token;
    buildVelocity(pState.layer).then(function (vel) {
      if (tok !== pState.token || !pState.on) return;             // a newer move superseded this build
      if (!vel) { try { w.setVisible(false); } catch (e) {} return; }
      w.setData(vel); w.setVisible(true);
    }).catch(function (e) { if (log.warn) log.warn.call(log, '[wx-scene] particle build failed: ' + ((e && e.message) || e)); });
  }
  function onMove() { clearTimeout(pState.debounce); pState.debounce = setTimeout(refreshParticles, 300); }   // refetch from cache only — no upstream
  function startParticles(map, layer) {
    var w = global.__helmWind; if (!w) return Promise.resolve(false);
    pState.on = true; pState.layer = layer;
    if (!pState.moveHandler) { pState.moveHandler = onMove; map.on('moveend', pState.moveHandler); }
    return buildVelocity(layer).then(function (vel) {
      if (vel && pState.on) { w.setData(vel); w.setVisible(true); }
      return !!vel;
    }).catch(function () { return false; });
  }
  function stopParticles() {
    pState.on = false; pState.layer = null; pState.token++;
    var w = global.__helmWind; if (w) try { w.setVisible(false); } catch (e) {}
    if (pState.moveHandler && state.map) { try { state.map.off('moveend', pState.moveHandler); } catch (e) {} pState.moveHandler = null; }
  }

  // Unified entry: scalar colour field + (vector layers) particles, all from the prepared bundle.
  function enable(map, opts) {
    opts = opts || {};
    return enableScalar(map, opts).then(function (info) {
      var L = layerCfg(state.manifest, info.layer);
      if (L.vectorField || L.kind === 'vector') return startParticles(map, info.layer).then(function (ok) { info.particles = ok; return info; });
      stopParticles(); return info;
    });
  }
  function disable() { stopParticles(); remove(); }

  global.HelmWxScene = {
    enable: enable, enableScalar: enableScalar, disable: disable, setOpacity: setOpacity, loadManifest: loadManifest, state: state
  };
})(typeof window !== 'undefined' ? window : this);
