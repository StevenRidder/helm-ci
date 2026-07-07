// ENC-1/2 — canonical toggles + per-layer opacity for depare / depcnt / soundg / enc-chart.
// Maps S-57 layer keys to legacy MapLibre ids, persists via HelmStore, and keeps the WebGPU ENC
// artifact in sync with the enc-chart checkbox (user off must hide GPU + MapLibre fallback).
(function () {
  'use strict';

  var STORE_KEY = 'ui.encLayers';
  var OPACITY_STORE_KEY = 'ui.encLayerOpacity';
  var LAYERS = {
    depare: { mapIds: ['depare-fill'], defaultOn: true, paint: 'fill-opacity' },
    depcnt: { mapIds: ['depcnt-line'], defaultOn: true, paint: 'line-opacity' },
    soundg: { mapIds: ['soundg-text'], defaultOn: true, paint: 'text-opacity' },
    'enc-chart': { mapIds: ['enc-chart'], defaultOn: true, webgpu: true, paint: 'raster-opacity' }
  };
  var KEYS = ['depare', 'depcnt', 'soundg', 'enc-chart'];
  var basePaint = Object.create(null);

  function defaults() {
    var o = Object.create(null);
    KEYS.forEach(function (k) { o[k] = LAYERS[k].defaultOn; });
    return o;
  }

  function opacityDefaults() {
    var o = Object.create(null);
    KEYS.forEach(function (k) { o[k] = 100; });
    return o;
  }

  function clampPct(pct) {
    var n = Number(pct);
    if (!isFinite(n)) return 100;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function readState() {
    var base = defaults();
    if (!window.HelmStore) return base;
    try {
      var saved = window.HelmStore.get(STORE_KEY, base);
      if (!saved || typeof saved !== 'object') return base;
      KEYS.forEach(function (k) {
        if (typeof saved[k] === 'boolean') base[k] = saved[k];
      });
    } catch (e) {}
    return base;
  }

  function readOpacityState() {
    var base = opacityDefaults();
    if (!window.HelmStore) return base;
    try {
      var saved = window.HelmStore.get(OPACITY_STORE_KEY, base);
      if (!saved || typeof saved !== 'object') return base;
      KEYS.forEach(function (k) {
        if (saved[k] != null) base[k] = clampPct(saved[k]);
      });
    } catch (e) {}
    return base;
  }

  function writeState(state) {
    if (!window.HelmStore) return false;
    return window.HelmStore.set(STORE_KEY, state);
  }

  function writeOpacityState(state) {
    if (!window.HelmStore) return false;
    return window.HelmStore.set(OPACITY_STORE_KEY, state);
  }

  function chartArtifact() {
    return window.__helmChartArtifact || null;
  }

  function checkbox(key) {
    return document.querySelector('input[data-enc-layer="' + key + '"]');
  }

  function opacitySlider(key) {
    return document.querySelector('input[data-enc-opacity="' + key + '"]');
  }

  function setMapVisibility(map, layerId, visible) {
    if (!map) return;
    try {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
    } catch (e) {}
  }

  function captureBasePaint(map, key) {
    if (basePaint[key] != null) return basePaint[key];
    var def = LAYERS[key];
    if (!def || !map) return 1;
    var prop = def.paint;
    var val = 1;
    def.mapIds.some(function (id) {
      try {
        if (!map.getLayer(id)) return false;
        var p = map.getPaintProperty(id, prop);
        if (p != null) { val = p; return true; }
      } catch (e) {}
      return false;
    });
    basePaint[key] = val;
    return val;
  }

  function scalePaint(base, factor) {
    if (base == null) return factor;
    if (typeof base === 'number') return base * factor;
    if (Array.isArray(base)) return ['*', base, factor];
    return factor;
  }

  function applyEncChartGpuOpacity(pct) {
    var art = chartArtifact();
    if (!art || !art.getGpuLayer) return;
    try {
      var gpu = art.getGpuLayer();
      if (gpu && gpu.canvas) gpu.canvas.style.opacity = String(clampPct(pct) / 100);
    } catch (e) {}
  }

  function applyOpacity(map, key, pct, opts) {
    opts = opts || {};
    var def = LAYERS[key];
    if (!def || !map) return false;
    pct = clampPct(pct);
    var factor = pct / 100;
    var paintVal = scalePaint(captureBasePaint(map, key), factor);
    def.mapIds.forEach(function (id) {
      try {
        if (map.getLayer(id)) map.setPaintProperty(id, def.paint, paintVal);
      } catch (e) {}
    });
    if (key === 'enc-chart') applyEncChartGpuOpacity(pct);
    var slider = opacitySlider(key);
    if (slider) slider.value = String(pct);
    if (opts.persist) {
      var state = readOpacityState();
      state[key] = pct;
      writeOpacityState(state);
    }
    return true;
  }

  function getOpacity(key) {
    var slider = opacitySlider(key);
    if (slider) return clampPct(slider.value);
    return readOpacityState()[key];
  }

  function restoreOpacity(map) {
    var state = readOpacityState();
    KEYS.forEach(function (k) {
      applyOpacity(map, k, state[k], { persist: false });
    });
    return state;
  }

  function applyEncChart(map, visible) {
    var art = chartArtifact();
    if (art && art.setVisible) {
      try { art.setVisible(visible); } catch (e) {}
    }
    setMapVisibility(map, 'enc-chart', visible);
    if (visible) applyOpacity(map, 'enc-chart', getOpacity('enc-chart'), { persist: false });
  }

  function applyLayer(map, key, visible, opts) {
    opts = opts || {};
    var def = LAYERS[key];
    if (!def) return false;
    visible = !!visible;
    if (key === 'enc-chart') applyEncChart(map, visible);
    else {
      def.mapIds.forEach(function (id) { setMapVisibility(map, id, visible); });
      if (visible) applyOpacity(map, key, getOpacity(key), { persist: false });
    }
    var cb = checkbox(key);
    if (cb) cb.checked = visible;
    if (opts.persist) {
      var state = readState();
      state[key] = visible;
      writeState(state);
    }
    return true;
  }

  function isOn(key) {
    var cb = checkbox(key);
    if (cb) return cb.checked;
    return !!readState()[key];
  }

  function applyAll(map, state, opts) {
    KEYS.forEach(function (k) {
      applyLayer(map, k, state[k] !== false, Object.assign({}, opts, { persist: false }));
    });
    if (opts && opts.persist) writeState(state);
  }

  function restore(map) {
    var state = readState();
    applyAll(map, state, { persist: false });
    restoreOpacity(map);
    return state;
  }

  function bind(map) {
    if (!map) return;
    document.querySelectorAll('input[data-enc-layer]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        applyLayer(map, cb.dataset.encLayer, cb.checked, { persist: true });
      });
    });
    document.querySelectorAll('input[data-enc-opacity]').forEach(function (sl) {
      sl.addEventListener('input', function () {
        applyOpacity(map, sl.dataset.encOpacity, sl.value, { persist: true });
      });
    });
    var run = function () { restore(map); };
    if (map.isStyleLoaded && map.isStyleLoaded()) run();
    else map.on('load', run);
  }

  function mapLayerId(key) {
    var def = LAYERS[key];
    return def && def.mapIds.length ? def.mapIds[0] : null;
  }

  window.HelmEncLayers = {
    KEYS: KEYS,
    LAYERS: LAYERS,
    storeKey: STORE_KEY,
    opacityStoreKey: OPACITY_STORE_KEY,
    defaults: defaults,
    opacityDefaults: opacityDefaults,
    readState: readState,
    readOpacityState: readOpacityState,
    applyLayer: applyLayer,
    applyOpacity: applyOpacity,
    applyAll: applyAll,
    restore: restore,
    restoreOpacity: restoreOpacity,
    bind: bind,
    isOn: isOn,
    getOpacity: getOpacity,
    mapLayerId: mapLayerId
  };
})();
