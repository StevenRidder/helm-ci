// ENC-3 — resolve ?profile=depth|aids|standard for enc-chart MapLibre tiles from layer toggles.
(function () {
  'use strict';

  var ENC_SOURCE = 'enc';

  function depthLayersOn(state) {
    if (!state) return false;
    return state.depare !== false || state.depcnt !== false || state.soundg !== false;
  }

  function resolve(state) {
    if (window.HelmEncLayers && !state) state = window.HelmEncLayers.readState();
    if (!state || state['enc-chart'] === false) return null;
    if (depthLayersOn(state)) return 'aids';
    return 'standard';
  }

  function tileUrl(profile) {
    if (!window.HelmEndpoint || !window.HelmEndpoint.tileTemplate) return null;
    var p = profile != null ? profile : resolve();
    if (!p || p === 'standard') return window.HelmEndpoint.tileTemplate();
    return window.HelmEndpoint.tileTemplate({ profile: p });
  }

  function sync(map) {
    if (!map) return false;
    var profile = resolve();
    if (!profile) return false;
    var url = tileUrl(profile);
    if (!url) return false;
    try {
      var src = map.getSource(ENC_SOURCE);
      if (!src || !src.setTiles) return false;
      src.setTiles([url]);
      return true;
    } catch (e) { return false; }
  }

  function bind(map) {
    if (!map) return;
    var run = function () { sync(map); };
    document.querySelectorAll('input[data-enc-layer]').forEach(function (cb) {
      cb.addEventListener('change', run);
    });
    var once = function () { run(); };
    if (map.isStyleLoaded && map.isStyleLoaded()) once();
    else map.on('load', once);
  }

  window.HelmEncTileProfile = {
    depthLayersOn: depthLayersOn,
    resolve: resolve,
    tileUrl: tileUrl,
    sync: sync,
    bind: bind
  };
})();
