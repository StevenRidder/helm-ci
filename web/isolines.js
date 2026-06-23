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

  // Stitch marching-squares 2-point segments into continuous polylines by
  // walking shared endpoints (adjacent cells produce identical edge points).
  function key(p) { return p[0].toFixed(5) + ',' + p[1].toFixed(5); }
  function stitch(segs) {
    var ends = {};               // point key -> [{si, e}]
    for (var si = 0; si < segs.length; si++)
      for (var e = 0; e < 2; e++) {
        var k = key(segs[si][e]);
        (ends[k] || (ends[k] = [])).push({ si: si, e: e });
      }
    var used = new Array(segs.length); var polys = [];
    function grow(poly, fwd) {
      for (;;) {
        var tip = fwd ? poly[poly.length - 1] : poly[0];
        var cands = ends[key(tip)] || [], nx = null;
        for (var c = 0; c < cands.length; c++) if (!used[cands[c].si]) { nx = cands[c]; break; }
        if (!nx) break;
        used[nx.si] = true;
        var other = segs[nx.si][nx.e === 0 ? 1 : 0];
        if (fwd) poly.push(other); else poly.unshift(other);
      }
    }
    for (var s = 0; s < segs.length; s++) {
      if (used[s]) continue;
      used[s] = true;
      var poly = [segs[s][0], segs[s][1]];
      grow(poly, true); grow(poly, false);
      polys.push(poly);
    }
    return polys;
  }
  // Chaikin corner-cutting -> smooth flowing curves (Windy-like isobars).
  function chaikin(pts, iters) {
    for (var it = 0; it < iters; it++) {
      if (pts.length < 3) break;
      var out = [pts[0]];
      for (var i = 0; i < pts.length - 1; i++) {
        var a = pts[i], b = pts[i + 1];
        out.push([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25]);
        out.push([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75]);
      }
      out.push(pts[pts.length - 1]);
      pts = out;
    }
    return pts;
  }

  function contour(field, interval) {
    var nx = field.nx, ny = field.ny, v = field.values;
    var dx = (field.east - field.west) / (nx - 1), dy = (field.north - field.south) / (ny - 1);
    function lon(gx) { return field.west + gx * dx; }
    function lat(gy) { return field.north - gy * dy; }
    var lines = [], labels = [];
    var lo = Math.ceil(field.vmin / interval) * interval;
    for (var L = lo; L <= field.vmax; L += interval) {
      var segs = [];
      for (var j = 0; j < ny - 1; j++) {
        for (var i = 0; i < nx - 1; i++) {
          var tl = v[j * nx + i], tr = v[j * nx + i + 1];
          var bl = v[(j + 1) * nx + i], br = v[(j + 1) * nx + i + 1];
          var idx = (tl >= L ? 8 : 0) | (tr >= L ? 4 : 0) | (br >= L ? 2 : 0) | (bl >= L ? 1 : 0);
          var cs = CASES[idx];
          if (!cs) continue;
          var pt = {
            T: function () { return [lon(i + (L - tl) / (tr - tl || 1e-9)), lat(j)]; },
            B: function () { return [lon(i + (L - bl) / (br - bl || 1e-9)), lat(j + 1)]; },
            Lf: function () { return [lon(i), lat(j + (L - tl) / (bl - tl || 1e-9))]; },
            R: function () { return [lon(i + 1), lat(j + (L - tr) / (br - tr || 1e-9))]; }
          };
          for (var s = 0; s < cs.length; s++) segs.push([pt[cs[s][0]](), pt[cs[s][1]]()]);
        }
      }
      // stitch -> smooth -> one feature per continuous isobar, one label at its midpoint
      var polys = stitch(segs);
      for (var p = 0; p < polys.length; p++) {
        if (polys[p].length < 3) continue;             // drop tiny stubs
        var sm = chaikin(polys[p], 3);
        lines.push({ type: 'Feature', properties: { level: L },
                     geometry: { type: 'LineString', coordinates: sm } });
        if (polys[p].length >= 5) {
          var mid = sm[Math.floor(sm.length / 2)];
          labels.push({ type: 'Feature', properties: { level: L },
                        geometry: { type: 'Point', coordinates: mid } });
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
