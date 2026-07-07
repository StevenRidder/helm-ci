// ENC-1 — canonical toggles for depare / depcnt / soundg / enc-chart on the sat-first fused map.
// Maps S-57 layer keys to legacy MapLibre ids, persists via HelmStore, and keeps the WebGPU ENC
// artifact in sync with the enc-chart checkbox (user off must hide GPU + MapLibre fallback).
(function () {
  'use strict';

  var STORE_KEY = 'ui.encLayers';
  var LAYERS = {
    depare: { mapIds: ['depare-fill'], defaultOn: true },
    depcnt: { mapIds: ['depcnt-line'], defaultOn: true },
    soundg: { mapIds: ['soundg-text'], defaultOn: true },
    'enc-chart': { mapIds: ['enc-chart'], defaultOn: true, webgpu: true }
  };
  var KEYS = ['depare', 'depcnt', 'soundg', 'enc-chart'];

  function defaults() {
    var o = Object.create(null);
    KEYS.forEach(function (k) { o[k] = LAYERS[k].defaultOn; });
    return o;
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

  function writeState(state) {
    if (!window.HelmStore) return false;
    return window.HelmStore.set(STORE_KEY, state);
  }

  function chartArtifact() {
    return window.__helmChartArtifact || null;
  }

  function checkbox(key) {
    return document.querySelector('input[data-enc-layer="' + key + '"]');
  }

  function setMapVisibility(map, layerId, visible) {
    if (!map) return;
    try {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
    } catch (e) {}
  }

  function applyEncChart(map, visible) {
    var art = chartArtifact();
    if (art && art.setVisible) {
      try { art.setVisible(visible); } catch (e) {}
    }
    setMapVisibility(map, 'enc-chart', visible);
  }

  function applyLayer(map, key, visible, opts) {
    opts = opts || {};
    var def = LAYERS[key];
    if (!def) return false;
    visible = !!visible;
    if (key === 'enc-chart') applyEncChart(map, visible);
    else def.mapIds.forEach(function (id) { setMapVisibility(map, id, visible); });
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
    return state;
  }

  function bind(map) {
    if (!map) return;
    document.querySelectorAll('input[data-enc-layer]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        applyLayer(map, cb.dataset.encLayer, cb.checked, { persist: true });
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
    defaults: defaults,
    readState: readState,
    applyLayer: applyLayer,
    applyAll: applyAll,
    restore: restore,
    bind: bind,
    isOn: isOn,
    mapLayerId: mapLayerId
  };
})();
