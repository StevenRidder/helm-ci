/*
 * Helm — integrations/temporal.js   ·   maplibre-gl-temporal-control (mug-jp)
 * --------------------------------------------------------------------------
 * A ready-made time slider + play/pause that animates a stack of layers by
 * fading them in/out frame-by-frame. We feed it Helm's LOCAL rain-forecast
 * stack (data/field-rain-t0..N.json + data/forecast.json) rendered as image
 * overlays — a real temporal animation over real Helm data that shows the
 * control we'd reuse across every weather layer's time dimension.
 *
 * OFFLINE-FIRST: no RainViewer, no CDN — every frame comes from local pipeline
 * output and is colourised client-side. If online, the same control trivially
 * accepts a live nowcast source instead; nothing here requires the network.
 *
 * NOTE: the plugin only toggles opacity of layers that ALREADY exist (it never
 * calls addSource/addLayer). So we add each frame's image source + raster layer
 * here (hidden at opacity 0) and pass it specs whose paint carries the *visible*
 * opacity the control restores when a frame becomes active.
 *
 * https://github.com/mug-jp/maplibre-gl-temporal-control
 */
import TemporalControl from 'maplibre-gl-temporal-control';

let control = null;
let layerIds = [];

function lerp(a, b, t) { return a + (b - a) * t; }
function colorAt(stops, v) {
  if (v <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (v <= stops[i][0]) {
      const a = stops[i - 1], b = stops[i], t = (v - a[0]) / (b[0] - a[0] || 1), ca = a[1], cb = b[1];
      return [Math.round(lerp(ca[0], cb[0], t)), Math.round(lerp(ca[1], cb[1], t)), Math.round(lerp(ca[2], cb[2], t))];
    }
  }
  return stops[stops.length - 1][1];
}

// Render a scalar field (nx*ny grid) to a colourised PNG data URL. Low values
// fade to transparent so the precip reads as an overlay (raster-resampling
// 'linear' on the layer smooths the coarse grid).
function fieldToDataURL(field) {
  const { nx, ny, values, stops, vmin, vmax } = field;
  const cv = document.createElement('canvas'); cv.width = nx; cv.height = ny;
  const g = cv.getContext('2d'), img = g.createImageData(nx, ny), span = (vmax - vmin) || 1;
  for (let k = 0; k < nx * ny; k++) {
    const v = values[k], c = colorAt(stops, v), a = Math.max(0, Math.min(1, (v - vmin) / span));
    img.data[k * 4] = c[0]; img.data[k * 4 + 1] = c[1]; img.data[k * 4 + 2] = c[2];
    img.data[k * 4 + 3] = Math.round(255 * a);
  }
  g.putImageData(img, 0, 0);
  return cv.toDataURL();
}

export async function enable(map, ctx) {
  if (control) return;
  const fc = await fetch('data/forecast.json').then(r => r.ok ? r.json() : null).catch(() => null);
  const hours = (fc && fc.hours) || 12;

  const frames = [];
  for (let i = 0; i < hours; i++) {
    const field = await fetch(`data/field-rain-t${i}.json`).then(r => r.ok ? r.json() : null).catch(() => null);
    if (!field) continue;
    const id = `helm-temporal-rain-${i}`, srcId = `${id}-src`;
    const coords = [[field.west, field.north], [field.east, field.north], [field.east, field.south], [field.west, field.south]];
    if (!map.getSource(srcId)) map.addSource(srcId, { type: 'image', url: fieldToDataURL(field), coordinates: coords });
    if (!map.getLayer(id)) {
      // add hidden; the control fades the active frame up to its paint opacity
      map.addLayer({ id, type: 'raster', source: srcId,
        paint: { 'raster-opacity': 0, 'raster-resampling': 'linear', 'raster-fade-duration': 0 } }, ctx.beforeId);
    }
    layerIds.push(id);
    const t = fc && fc.times && fc.times[i];
    frames.push({
      title: t ? new Date(t + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `+${i}h`,
      layers: [{ id, type: 'raster', paint: { 'raster-opacity': 0.75 } }],
    });
  }

  if (!frames.length) { ctx.notify('No local rain frames found — run the pipeline', 'warn'); return; }
  control = new TemporalControl(frames, { interval: 500, position: 'top-right' });
  map.addControl(control);
  ctx.notify('Temporal control — local rain forecast stack (offline), press play', 'ok');
}

export function disable(map) {
  if (control) { try { map.removeControl(control); } catch (e) { /* noop */ } control = null; }
  layerIds.forEach(id => { if (map.getLayer(id)) map.removeLayer(id); if (map.getSource(id + '-src')) map.removeSource(id + '-src'); });
  layerIds = [];
}
