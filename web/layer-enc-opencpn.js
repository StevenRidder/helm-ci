// LAYER-5: OpenCPN engine PNG is the runtime symbol authority for aids/navaids on satellite.
// Icon Forge clean-room SVG swap is deferred — this module documents and surfaces that contract.
(function (global) {
  'use strict';

  var ENC_LAYER = 'enc-chart';
  var SYMBOL_AUTHORITY = 'opencpn-engine-png';
  var SAT_BASEMAPS = { googlesat: 1, bingsat: 1, arcgis: 1, satellite: 1, sat: 1 };

  function activeSatelliteBasemap(map) {
    if (!map || !map.getStyle) return null;
    var layers = map.getStyle().layers || [];
    for (var i = 0; i < layers.length; i++) {
      var id = layers[i].id;
      if (!SAT_BASEMAPS[id]) continue;
      try {
        if (map.getLayoutProperty(id, 'visibility') !== 'none') return id;
      } catch (e) {}
    }
    return null;
  }

  function encVisible(map) {
    try {
      if (!map.getLayer(ENC_LAYER)) return false;
      return map.getLayoutProperty(ENC_LAYER, 'visibility') !== 'none';
    } catch (e) {
      return false;
    }
  }

  function tileTemplate() {
    try {
      var ep = global.HelmEndpoint;
      return ep && ep.tileTemplate && ep.tileTemplate();
    } catch (e) {
      return null;
    }
  }

  function status(map) {
    map = map || global.map;
    var sat = activeSatelliteBasemap(map);
    return {
      schema: 'helm.layer.enc_opencpn.v1',
      symbol_authority: SYMBOL_AUTHORITY,
      icon_forge_deferred: true,
      enc_layer: ENC_LAYER,
      enc_visible: encVisible(map),
      satellite_basemap: sat,
      fused_on_satellite: !!(sat && encVisible(map)),
      tile_template: tileTemplate()
    };
  }

  function summary(map) {
    var st = status(map);
    if (!st.enc_visible) return { mode: 'hidden', detail: 'enc-chart off', css: 'warn' };
    if (st.fused_on_satellite) {
      return { mode: 'fused', detail: 'OpenCPN PNG on ' + st.satellite_basemap, css: 'ok' };
    }
    return { mode: 'on', detail: 'OpenCPN PNG · ' + SYMBOL_AUTHORITY, css: 'ok' };
  }

  global.HelmLayerEncOpenCPN = {
    ENC_LAYER: ENC_LAYER,
    SYMBOL_AUTHORITY: SYMBOL_AUTHORITY,
    status: status,
    summary: summary
  };
})(typeof window !== 'undefined' ? window : global);
