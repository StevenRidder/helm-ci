/*
 * Helm — integrations/temporal.js   ·   maplibre-gl-temporal-control (mug-jp)
 * --------------------------------------------------------------------------
 * A ready-made time slider + play/pause that animates a stack of layers by
 * fading them in/out frame-by-frame. We feed it the RainViewer precipitation
 * nowcast (past frames + forecast), giving a real temporal animation that
 * complements radar.js and shows the control we'd reuse across every weather
 * layer's time dimension.
 *
 * NOTE: the plugin only toggles opacity of layers that ALREADY exist (it never
 * calls addSource/addLayer). So we add each frame's raster source+layer here
 * (hidden at opacity 0) and pass it specs whose paint carries the *visible*
 * opacity the control restores when a frame becomes active.
 *
 * https://github.com/mug-jp/maplibre-gl-temporal-control
 */
import TemporalControl from 'maplibre-gl-temporal-control';

let control = null;
let layerIds = [];

export async function enable(map, ctx) {
  if (control) return;
  let index;
  try {
    index = await fetch('https://api.rainviewer.com/public/weather-maps.json').then(r => r.json());
  } catch (e) {
    ctx.notify('Temporal demo needs RainViewer (network) — offline?', 'warn');
    return;
  }
  const host = index.host;
  const frames = [...(index.radar.past || []), ...(index.radar.nowcast || [])];
  if (!frames.length) { ctx.notify('No radar frames available right now', 'warn'); return; }

  const temporalFrames = frames.map(f => {
    const id = `helm-temporal-${f.time}`;
    const srcId = `${id}-src`;
    if (!map.getSource(srcId)) {
      map.addSource(srcId, {
        type: 'raster',
        tiles: [`${host}${f.path}/256/{z}/{x}/{y}/4/1_1.png`],
        tileSize: 256,
        attribution: 'RainViewer',
      });
    }
    if (!map.getLayer(id)) {
      // add hidden; the control fades the active frame up to its paint opacity
      map.addLayer({ id, type: 'raster', source: srcId, paint: { 'raster-opacity': 0 } }, ctx.beforeId);
    }
    layerIds.push(id);
    return { title: new Date(f.time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
             layers: [{ id, type: 'raster', paint: { 'raster-opacity': 0.7 } }] };
  });

  control = new TemporalControl(temporalFrames, { interval: 500, position: 'top-right' });
  map.addControl(control);
  ctx.notify('Temporal control wired to RainViewer nowcast — press play', 'ok');
}

export function disable(map) {
  if (control) { try { map.removeControl(control); } catch (e) { /* noop */ } control = null; }
  layerIds.forEach(id => { if (map.getLayer(id)) map.removeLayer(id); if (map.getSource(id + '-src')) map.removeSource(id + '-src'); });
  layerIds = [];
}
