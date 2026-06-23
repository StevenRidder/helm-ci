/*
 * Helm — isolines.js
 * Contour lines (e.g. pressure isobars) from a scalar field via marching squares,
 * rendered as MapLibre line + label layers — Windy's isobars.
 *
 * API:
 *   const iso = HelmIsolines(map, { beforeId: 'route-line' });
 *   iso.load('data/field-pressure.json', { interval: 4 });   // Promise
 *   iso.setVisible(true|false);
 */
(function (global) {
  'use strict';
  var SRC = 'helm-iso', LBL = 'helm-iso-lbl';

  // marching-squares segments per case (bits: tl=8 tr=4 br=2 bl=1). Edges: T R B Lf.
  var CASES = {
    1: [['Lf', 'B']], 2: [['B', 'R']], 3: [['Lf', 'R']], 4: [['T', 'R']],
    5: [['T', 'Lf'], ['B', 'R']], 6: [['T', 'B']], 7: [['T', 'Lf']],
    8: [['T', 'Lf']], 9: [['T', 'B']], 10: [['T', 'R'], ['B', 'Lf']],
    11: [['T', 'R']], 12: [['Lf', 'R']], 13: [['B', 'R']], 14: [['Lf', 'B']]
  };

  function contour(field, interval) {
    var nx = field.nx, ny = field.ny, v = field.values;
    var dx = (field.east - field.west) / (nx - 1), dy = (field.north - field.south) / (ny - 1);
    function lon(gx) { return field.west + gx * dx; }
    function lat(gy) { return field.north - gy * dy; }
    var lines = [], labels = [], seg = 0;
    var lo = Math.ceil(field.vmin / interval) * interval;
    for (var L = lo; L <= field.vmax; L += interval) {
      for (var j = 0; j < ny - 1; j++) {
        for (var i = 0; i < nx - 1; i++) {
          var tl = v[j * nx + i], tr = v[j * nx + i + 1];
          var bl = v[(j + 1) * nx + i], br = v[(j + 1) * nx + i + 1];
          var idx = (tl >= L ? 8 : 0) | (tr >= L ? 4 : 0) | (br >= L ? 2 : 0) | (bl >= L ? 1 : 0);
          var segs = CASES[idx];
          if (!segs) continue;
          var pt = {
            T: function () { return [lon(i + (L - tl) / (tr - tl || 1e-9)), lat(j)]; },
            B: function () { return [lon(i + (L - bl) / (br - bl || 1e-9)), lat(j + 1)]; },
            Lf: function () { return [lon(i), lat(j + (L - tl) / (bl - tl || 1e-9))]; },
            R: function () { return [lon(i + 1), lat(j + (L - tr) / (br - tr || 1e-9))]; }
          };
          for (var s = 0; s < segs.length; s++) {
            var a = pt[segs[s][0]](), b = pt[segs[s][1]]();
            lines.push({ type: 'Feature', properties: { level: L },
                         geometry: { type: 'LineString', coordinates: [a, b] } });
            if ((seg++ % 16) === 0) {
              labels.push({ type: 'Feature', properties: { level: L },
                            geometry: { type: 'Point', coordinates: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2] } });
            }
          }
        }
      }
    }
    return { lines: { type: 'FeatureCollection', features: lines },
             labels: { type: 'FeatureCollection', features: labels } };
  }

  function HelmIsolines(map, opts) {
    if (!(this instanceof HelmIsolines)) return new HelmIsolines(map, opts);
    this.map = map;
    this.beforeId = (opts && opts.beforeId) || null;
  }

  HelmIsolines.prototype.load = function (url, opts) {
    var self = this, interval = (opts && opts.interval) || 4;
    return fetch(url).then(function (r) { return r.json(); }).then(function (field) {
      var c = contour(field, interval), map = self.map;
      if (map.getSource(SRC)) {
        map.getSource(SRC).setData(c.lines);
        map.getSource(LBL).setData(c.labels);
        map.setLayoutProperty(SRC, 'visibility', 'visible');
        map.setLayoutProperty(LBL, 'visibility', 'visible');
      } else {
        var before = (self.beforeId && map.getLayer(self.beforeId)) ? self.beforeId : undefined;
        map.addSource(SRC, { type: 'geojson', data: c.lines });
        map.addSource(LBL, { type: 'geojson', data: c.labels });
        map.addLayer({ id: SRC, type: 'line', source: SRC,
          paint: { 'line-color': 'rgba(255,255,255,0.55)', 'line-width': 0.9 } }, before);
        map.addLayer({ id: LBL, type: 'symbol', source: LBL,
          layout: { 'text-field': ['to-string', ['get', 'level']], 'text-font': ['Open Sans Regular'],
                    'text-size': 10, 'symbol-placement': 'point', 'text-allow-overlap': false },
          paint: { 'text-color': '#fff', 'text-halo-color': 'rgba(13,19,27,0.85)', 'text-halo-width': 1.2 } }, before);
      }
      return field;
    }).catch(function (e) { console.warn('[HelmIsolines] failed', e && e.message); return null; });
  };

  HelmIsolines.prototype.setVisible = function (v) {
    var vis = v ? 'visible' : 'none';
    if (this.map.getLayer(SRC)) this.map.setLayoutProperty(SRC, 'visibility', vis);
    if (this.map.getLayer(LBL)) this.map.setLayoutProperty(LBL, 'visibility', vis);
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = HelmIsolines;
  else global.HelmIsolines = HelmIsolines;
})(typeof window !== 'undefined' ? window : this);
