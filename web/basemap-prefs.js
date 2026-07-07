// SAT-1 — remember the user's last static basemap (Navionics / Google / Bing / ArcGIS).
// Offline PMTiles packs use offline-packs.js (offline.activePack). Static choice is stored
// in HelmStore as ui.basemap and restored on cold load when no offline pack is active.
(function () {
  'use strict';

  var STORE_KEY = 'ui.basemap';
  var BASEMAPS = ['navionics', 'googlesat', 'bingsat', 'arcgis'];
  var DEFAULT = 'navionics';

  function valid(id) {
    return BASEMAPS.indexOf(id) >= 0;
  }

  function offlinePackId() {
    try {
      if (window.HelmOfflinePacks && window.HelmOfflinePacks.state && window.HelmOfflinePacks.state.activeId) {
        return window.HelmOfflinePacks.state.activeId;
      }
      return window.HelmStore ? window.HelmStore.get('offline.activePack', null) : null;
    } catch (e) {
      return null;
    }
  }

  function applyStatic(map, pick, opts) {
    opts = opts || {};
    if (!valid(pick)) pick = DEFAULT;
    document.querySelectorAll('input[name="basemap"]').forEach(function (rb) {
      rb.checked = rb.dataset.base === pick;
    });
    var m = map || window.map;
    if (m) {
      BASEMAPS.forEach(function (id) {
        try {
          if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', id === pick ? 'visible' : 'none');
        } catch (e) {}
      });
    }
    if (opts.persist && window.HelmStore) window.HelmStore.set(STORE_KEY, pick);
    return pick;
  }

  function restoreStatic(map) {
    if (offlinePackId()) return null;
    var saved = window.HelmStore ? window.HelmStore.get(STORE_KEY, DEFAULT) : DEFAULT;
    return applyStatic(map, saved, { persist: false });
  }

  function bind(map) {
    if (!map) return;
    document.querySelectorAll('input[name="basemap"]').forEach(function (rb) {
      rb.addEventListener('change', function () {
        if (!rb.checked) return;
        applyStatic(map, rb.dataset.base, { persist: true });
      });
    });
    var run = function () { restoreStatic(map); };
    if (map.isStyleLoaded && map.isStyleLoaded()) run();
    else map.on('load', run);
  }

  window.HelmBasemapPrefs = {
    BASEMAPS: BASEMAPS,
    DEFAULT: DEFAULT,
    storeKey: STORE_KEY,
    applyStatic: applyStatic,
    restoreStatic: restoreStatic,
    bind: bind,
    offlinePackId: offlinePackId
  };
})();
