// FUSE-1 — one-tap fusion presets for the sat-first North Star layer cake.
// Applies basemap + ENC toggles (and optional nav overlays) via HelmBasemapPrefs + HelmEncLayers.
(function () {
  'use strict';

  var STORE_KEY = 'ui.fusionPreset';
  var SAT_BASEMAP = 'googlesat';
  var CHART_BASEMAP = 'navionics';

  var PRESETS = {
    'depth-on-sat': {
      label: 'Depth on sat',
      title: 'Satellite basemap with depth shading, contours, and soundings',
      basemap: SAT_BASEMAP,
      enc: { depare: true, depcnt: true, soundg: true, 'enc-chart': false },
      overlays: null
    },
    'standard-enc': {
      label: 'Standard ENC',
      title: 'Navionics chart with full ENC stack',
      basemap: CHART_BASEMAP,
      enc: { depare: true, depcnt: true, soundg: true, 'enc-chart': true },
      overlays: null
    },
    'sat-only': {
      label: 'Sat only',
      title: 'Satellite basemap with all ENC overlays off',
      basemap: SAT_BASEMAP,
      enc: { depare: false, depcnt: false, soundg: false, 'enc-chart': false },
      overlays: null
    },
    'passage-prep': {
      label: 'Passage prep',
      title: 'Satellite + depth + OpenCPN aids + route and AIS for passage planning',
      basemap: SAT_BASEMAP,
      enc: { depare: true, depcnt: true, soundg: true, 'enc-chart': true },
      overlays: { 'route-line': true, ais: true, places: true }
    }
  };

  var IDS = Object.keys(PRESETS);

  function readActive() {
    try {
      var id = window.HelmStore ? window.HelmStore.get(STORE_KEY, null) : null;
      return PRESETS[id] ? id : null;
    } catch (e) {
      return null;
    }
  }

  function writeActive(id) {
    if (!window.HelmStore) return false;
    return window.HelmStore.set(STORE_KEY, id || null);
  }

  function offlinePackActive() {
    return !!(window.HelmBasemapPrefs && window.HelmBasemapPrefs.offlinePackId && window.HelmBasemapPrefs.offlinePackId());
  }

  function applyBasemap(map, pick, opts) {
    opts = opts || {};
    if (!pick) return null;
    if (offlinePackActive() && !opts.forceStatic) return null;
    if (window.HelmBasemapPrefs && window.HelmBasemapPrefs.applyStatic) {
      return window.HelmBasemapPrefs.applyStatic(map, pick, { persist: opts.persist !== false });
    }
    return null;
  }

  function applyEnc(map, enc, opts) {
    if (!enc || !window.HelmEncLayers) return;
    var state = window.HelmEncLayers.defaults();
    window.HelmEncLayers.KEYS.forEach(function (k) {
      if (typeof enc[k] === 'boolean') state[k] = enc[k];
    });
    window.HelmEncLayers.applyAll(map, state, { persist: opts && opts.persist !== false });
    if (window.HelmEncTileProfile) window.HelmEncTileProfile.sync(map);
  }

  function setOverlayVisibility(map, layerId, visible) {
    if (!map || !map.getStyle) return;
    var vis = visible ? 'visible' : 'none';
    map.getStyle().layers.forEach(function (l) {
      if (l.id === layerId || l.id.indexOf(layerId + '-') === 0 || l.id.indexOf('helm-' + layerId + '-') === 0) {
        try { map.setLayoutProperty(l.id, 'visibility', vis); } catch (e) {}
      }
    });
    var cb = document.querySelector('.row input[data-layer="' + layerId + '"]');
    if (cb) cb.checked = !!visible;
  }

  function applyOverlays(map, overlays, opts) {
    if (!overlays || !map) return;
    Object.keys(overlays).forEach(function (id) {
      setOverlayVisibility(map, id, !!overlays[id]);
    });
  }

  function markUi(id) {
    document.querySelectorAll('[data-fusion-preset]').forEach(function (btn) {
      var on = btn.dataset.fusionPreset === id;
      btn.classList.toggle('on', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function apply(map, id, opts) {
    opts = opts || {};
    map = map || window.map;
    var preset = PRESETS[id];
    if (!preset || !map) return null;

    applyBasemap(map, preset.basemap, opts);
    applyEnc(map, preset.enc, opts);
    applyOverlays(map, preset.overlays, opts);

    if (opts.persist !== false) writeActive(id);
    markUi(id);

    if (window.HelmOfflinePacks && window.HelmOfflinePacks.refreshOffline20Strip) {
      try { window.HelmOfflinePacks.refreshOffline20Strip(); } catch (e) {}
    }

    return describe(id, map);
  }

  function describe(id, map) {
    var preset = PRESETS[id];
    if (!preset) return null;
    map = map || window.map;
    var enc = window.HelmEncLayers ? window.HelmEncLayers.readState() : preset.enc;
    var fused = window.HelmLayerEncOpenCPN && map ? window.HelmLayerEncOpenCPN.status(map) : null;
    return {
      schema: 'helm.fusion_preset.v1',
      id: id,
      label: preset.label,
      basemap: preset.basemap,
      offline_pack: offlinePackActive(),
      enc: enc,
      fused_on_satellite: fused && fused.fused_on_satellite,
      overlays: preset.overlays
    };
  }

  function bind(map) {
    if (!map) return;
    document.querySelectorAll('[data-fusion-preset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        apply(map, btn.dataset.fusionPreset, { persist: true });
      });
    });
    var saved = readActive();
    if (saved) markUi(saved);
  }

  window.HelmFusionPresets = {
    STORE_KEY: STORE_KEY,
    PRESETS: PRESETS,
    IDS: IDS,
    readActive: readActive,
    apply: apply,
    describe: describe,
    bind: bind
  };
})();
