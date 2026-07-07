// SAT-2 — never-blank pan while ENC tiles fetch.
// Prefetches engine /chart raster tiles around the viewport on debounced moveend and keeps the
// active static basemap visible under enc-chart so panning never exposes a blank frame.
(function () {
  'use strict';

  var ENC_SOURCE = 'enc';
  var FILL_LAYER = 'helm-chart-online-fill';
  var ENC_MINZ = 10;
  var ENC_MAXZ = 17;
  var PREFETCH_MARGIN = 1;
  var PREFETCH_BUDGET = 96;
  var PREFETCH_SEEN_CAP = 4000;
  var DEBOUNCE_MS = 200;

  var SAT_LAYERS = ['googlesat', 'bingsat', 'arcgis', 'satellite', 'sat'];
  var ALL_STATIC = ['navionics', 'googlesat', 'bingsat', 'arcgis'];

  var prefetchSeen = Object.create(null);
  var prefetchSeenN = 0;
  var moveDebounce = null;
  var hookBound = false;
  var opportunisticFill = false;

  function lon2tileX(lon, n) { return Math.floor((lon + 180) / 360 * n); }
  function lat2tileY(lat, n) {
    var r = lat * Math.PI / 180;
    return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n);
  }

  function encOn() {
    return window.HelmEncLayers ? window.HelmEncLayers.isOn('enc-chart') : true;
  }

  function offlineActive() {
    return !!(window.HelmBasemapPrefs && window.HelmBasemapPrefs.offlinePackId());
  }

  function userSetOnlineFill() {
    try {
      return window.HelmStore && window.HelmStore.keys().indexOf('ui.onlineFill') >= 0;
    } catch (e) { return false; }
  }

  function layerVisible(map, id) {
    try {
      return !!(map.getLayer(id) && map.getLayoutProperty(id, 'visibility') !== 'none');
    } catch (e) { return false; }
  }

  function activeStaticLayer(map) {
    for (var i = 0; i < ALL_STATIC.length; i++) {
      if (layerVisible(map, ALL_STATIC[i])) return ALL_STATIC[i];
    }
    return null;
  }

  function activeSatLayer(map) {
    for (var i = 0; i < SAT_LAYERS.length; i++) {
      if (layerVisible(map, SAT_LAYERS[i])) return SAT_LAYERS[i];
    }
    return null;
  }

  function sourceIdForLayer(layerId) {
    if (layerId === 'satellite') return 'sat';
    return layerId;
  }

  function boundsFromStyle(map, sourceId) {
    try {
      var style = map.getStyle();
      var src = style && style.sources && style.sources[sourceId];
      return src && src.bounds ? src.bounds.slice(0, 4) : null;
    } catch (e) { return null; }
  }

  function pointInBounds(center, b) {
    if (!b || !center) return true;
    var lng = center.lng != null ? center.lng : center.lon;
    var lat = center.lat;
    return lng >= b[0] && lng <= b[2] && lat >= b[1] && lat <= b[3];
  }

  function warmTile(url) {
    try { var img = new Image(); img.decoding = 'async'; img.src = url; } catch (e) {}
  }

  function prefetchEnc(map) {
    if (!map || !encOn() || offlineActive()) return 0;
    var tmpl = window.HelmEncTileProfile ? window.HelmEncTileProfile.tileUrl()
      : (window.HelmEndpoint && window.HelmEndpoint.tileTemplate());
    if (!tmpl) return 0;
    var bounds;
    try { bounds = map.getBounds(); } catch (e) { return 0; }
    if (!bounds) return 0;
    var z = Math.round(map.getZoom());
    if (z < ENC_MINZ) z = ENC_MINZ;
    else if (z > ENC_MAXZ) z = ENC_MAXZ;
    var W = bounds.getWest(), E = bounds.getEast(), N = bounds.getNorth(), S = bounds.getSouth();
    var budget = PREFETCH_BUDGET;
    var warmed = 0;
    var zooms = [z];
    if (z + 1 <= ENC_MAXZ) zooms.push(z + 1);
    if (z - 1 >= ENC_MINZ) zooms.push(z - 1);
    for (var zi = 0; zi < zooms.length && budget > 0; zi++) {
      var zz = zooms[zi], n = Math.pow(2, zz);
      var x0 = lon2tileX(W, n) - PREFETCH_MARGIN, x1 = lon2tileX(E, n) + PREFETCH_MARGIN;
      var y0 = lat2tileY(N, n) - PREFETCH_MARGIN, y1 = lat2tileY(S, n) + PREFETCH_MARGIN;
      for (var x = x0; x <= x1 && budget > 0; x++) {
        var tx = ((x % n) + n) % n;
        for (var y = y0; y <= y1 && budget > 0; y++) {
          if (y < 0 || y >= n) continue;
          var key = zz + '/' + tx + '/' + y;
          if (prefetchSeen[key]) continue;
          prefetchSeen[key] = 1;
          prefetchSeenN++;
          budget--;
          warmed++;
          warmTile(tmpl.replace('{z}', String(zz)).replace('{x}', String(tx)).replace('{y}', String(y)));
        }
      }
    }
    if (prefetchSeenN > PREFETCH_SEEN_CAP) { prefetchSeen = Object.create(null); prefetchSeenN = 0; }
    return warmed;
  }

  function ensureBasemapUnderEnc(map) {
    if (!map || !encOn() || offlineActive()) return false;
    if (activeStaticLayer(map)) return false;
    if (window.HelmBasemapPrefs) window.HelmBasemapPrefs.restoreStatic(map);
    return true;
  }

  function setFillLayerVisible(map, on) {
    try {
      if (map.getLayer(FILL_LAYER)) map.setLayoutProperty(FILL_LAYER, 'visibility', on ? 'visible' : 'none');
    } catch (e) {}
  }

  function syncOpportunisticFill(map) {
    if (!map || !encOn() || offlineActive() || userSetOnlineFill()) {
      if (opportunisticFill) { opportunisticFill = false; setFillLayerVisible(map, false); }
      return opportunisticFill;
    }
    if (!activeSatLayer(map)) {
      if (opportunisticFill) { opportunisticFill = false; setFillLayerVisible(map, false); }
      return opportunisticFill;
    }
    var layerId = activeStaticLayer(map) || activeSatLayer(map);
    var b = boundsFromStyle(map, sourceIdForLayer(layerId));
    var center;
    try { center = map.getCenter(); } catch (e) { return opportunisticFill; }
    var outside = !!(b && center && !pointInBounds(center, b));
    if (outside && !opportunisticFill) {
      opportunisticFill = true;
      setFillLayerVisible(map, true);
    } else if (!outside && opportunisticFill) {
      opportunisticFill = false;
      setFillLayerVisible(map, false);
    }
    return opportunisticFill;
  }

  function tick(map) {
    ensureBasemapUnderEnc(map);
    prefetchEnc(map);
    syncOpportunisticFill(map);
  }

  function onMove() {
    var map = window.map;
    if (!map) return;
    ensureBasemapUnderEnc(map);
    syncOpportunisticFill(map);
  }

  function onMoveEnd() {
    var map = window.map;
    if (!map) return;
    if (moveDebounce) clearTimeout(moveDebounce);
    moveDebounce = setTimeout(function () {
      moveDebounce = null;
      tick(map);
    }, DEBOUNCE_MS);
  }

  function bind(map) {
    if (!map || hookBound) return;
    hookBound = true;
    map.on('move', onMove);
    map.on('moveend', onMoveEnd);
    map.on('zoomend', onMoveEnd);
    map.on('sourcedata', function (e) {
      if (!e || e.sourceId !== ENC_SOURCE || e.isSourceLoaded) return;
      ensureBasemapUnderEnc(map);
    });
    if (map.isStyleLoaded && map.isStyleLoaded()) tick(map);
    else map.on('load', function () { tick(map); });
  }

  window.HelmEncPanPrefetch = {
    bind: bind,
    prefetchEnc: prefetchEnc,
    ensureBasemapUnderEnc: ensureBasemapUnderEnc,
    syncOpportunisticFill: syncOpportunisticFill,
    activeStaticLayer: activeStaticLayer,
    pointInBounds: pointInBounds,
    boundsFromStyle: boundsFromStyle,
    ENC_MINZ: ENC_MINZ,
    ENC_MAXZ: ENC_MAXZ,
    _test: {
      resetPrefetchSeen: function () { prefetchSeen = Object.create(null); prefetchSeenN = 0; },
      resetOpportunistic: function () { opportunisticFill = false; }
    }
  };
})();
