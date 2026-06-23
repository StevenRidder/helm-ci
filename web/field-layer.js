/*
 * Helm — field-layer.js
 * The Windy "color overlay": a smooth, interpolated heatmap of a scalar weather field
 * (wind speed, rain, temp, wave height, ...), rendered as a MapLibre `image` source with
 * linear resampling. It sits ABOVE the basemap and BELOW the chart/route/AIS overlays and
 * the animated particle canvas — so particles ride on top, exactly like Windy.
 *
 * Data: web/data/field-<layer>.json from pipeline/fetch_weather.py:
 *   { layer, unit, nx, ny, west, north, east, south, vmin, vmax,
 *     stops: [[value,[r,g,b(,a)]], ...], values: [nx*ny, row-major NW->SE] }
 *
 * API:
 *   const wx = HelmField(map, { beforeId: 'route-line', opacity: 0.8 });
 *   wx.load('data/field-wind.json');   // Promise; sets wx.current to the field
 *   wx.setVisible(true|false);  wx.clear();
 */
(function (global) {
  'use strict';
  var SRC = 'helm-wxfield', LYR = 'helm-wxfield';

  function lerp(a, b, t) { return a + (b - a) * t; }

  function colorAt(stops, v) {
    if (v <= stops[0][0]) return stops[0][1];
    for (var i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        var a = stops[i - 1], b = stops[i];
        var t = (v - a[0]) / (b[0] - a[0] || 1);
        var ca = a[1], cb = b[1];
        return [
          Math.round(lerp(ca[0], cb[0], t)),
          Math.round(lerp(ca[1], cb[1], t)),
          Math.round(lerp(ca[2], cb[2], t)),
          lerp(ca.length > 3 ? ca[3] : 1, cb.length > 3 ? cb[3] : 1, t)
        ];
      }
    }
    var last = stops[stops.length - 1][1];
    return [last[0], last[1], last[2], last.length > 3 ? last[3] : 1];
  }

  // Bilinear-sample the grid at fractional (fx in [0,nx-1], fy in [0,ny-1]).
  function sample(vals, nx, ny, fx, fy) {
    var x0 = Math.floor(fx), y0 = Math.floor(fy);
    var x1 = Math.min(nx - 1, x0 + 1), y1 = Math.min(ny - 1, y0 + 1);
    var gx = fx - x0, gy = fy - y0;
    var v00 = vals[y0 * nx + x0], v10 = vals[y0 * nx + x1];
    var v01 = vals[y1 * nx + x0], v11 = vals[y1 * nx + x1];
    return lerp(lerp(v00, v10, gx), lerp(v01, v11, gx), gy);
  }

  function fieldToDataURL(field) {
    var nx = field.nx, ny = field.ny, vals = field.values, stops = field.stops;
    var up = 8;                                  // upsample for a silky gradient
    var W = Math.max(2, (nx - 1) * up), H = Math.max(2, (ny - 1) * up);
    var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d');
    var img = ctx.createImageData(W, H), d = img.data;
    for (var y = 0; y < H; y++) {
      var fy = y / (H - 1) * (ny - 1);
      for (var x = 0; x < W; x++) {
        var fx = x / (W - 1) * (nx - 1);
        var c = colorAt(stops, sample(vals, nx, ny, fx, fy));
        var o = (y * W + x) * 4;
        d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; d[o + 3] = Math.round((c[3] == null ? 1 : c[3]) * 255);
      }
    }
    ctx.putImageData(img, 0, 0);
    return cv.toDataURL('image/png');
  }

  function HelmField(map, opts) {
    if (!(this instanceof HelmField)) return new HelmField(map, opts);
    this.map = map;
    this.opts = opts || {};
    this.opacity = this.opts.opacity == null ? 0.8 : this.opts.opacity;
    this.beforeId = this.opts.beforeId || null;
    this.current = null;
  }

  HelmField.prototype.load = function (url, opts) {
    var self = this;
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url);
      return r.json();
    }).then(function (field) {
      if (opts && opts.stops) field.stops = opts.stops;   // palette override (e.g. the Windy wind ramp)
      self.current = field;
      var coords = [[field.west, field.north], [field.east, field.north],
                    [field.east, field.south], [field.west, field.south]];
      var dataURL = fieldToDataURL(field);
      var map = self.map;
      if (map.getSource(SRC)) {
        map.getSource(SRC).updateImage({ url: dataURL, coordinates: coords });
        map.setLayoutProperty(LYR, 'visibility', 'visible');
      } else {
        map.addSource(SRC, { type: 'image', url: dataURL, coordinates: coords });
        var before = (self.beforeId && map.getLayer(self.beforeId)) ? self.beforeId : undefined;
        map.addLayer({
          id: LYR, type: 'raster', source: SRC,
          paint: { 'raster-opacity': self.opacity, 'raster-resampling': 'linear', 'raster-fade-duration': 0 }
        }, before);
      }
      return field;
    }).catch(function (e) {
      console.warn('[HelmField] could not load', url, e && e.message);
      throw e;   // propagate — never silently swallow a failed weather load
    });
  };

  HelmField.prototype.setOpacity = function (o) {
    this.opacity = Math.max(0, Math.min(1, o));
    if (this.map.getLayer(LYR)) this.map.setPaintProperty(LYR, 'raster-opacity', this.opacity);
  };
  HelmField.prototype.setVisible = function (v) {
    if (this.map.getLayer(LYR)) this.map.setLayoutProperty(LYR, 'visibility', v ? 'visible' : 'none');
  };
  HelmField.prototype.clear = function () { this.setVisible(false); this.current = null; };

  if (typeof module !== 'undefined' && module.exports) module.exports = HelmField;
  else global.HelmField = HelmField;
})(typeof window !== 'undefined' ? window : this);
