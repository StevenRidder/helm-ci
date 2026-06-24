/*
 * Helm — integrations/draw.js   ·   Terra Draw (+ MapLibre adapter)
 * --------------------------------------------------------------------------
 * Two marine jobs, one library:
 *   1. "Draw route"  — sketch/edit a route as a linestring.
 *   2. "Lasso area"  — drag a rectangle; we turn it into a bbox and hand it to
 *      the Download drawer. That IS the "lasso an area -> fetch charts" gesture
 *      from CHART-PIPELINE.md.
 *
 * Terra Draw owns its own GeoJSON source/layers via the adapter, so it sits
 * cleanly beside our style without touching route-line etc.
 *
 * https://github.com/JamesLMilner/terra-draw
 */
import { TerraDraw, TerraDrawLineStringMode, TerraDrawRectangleMode, TerraDrawSelectMode } from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';

let draw = null;

function ensure(map, ctx) {
  if (draw) return draw;
  draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map }),
    modes: [
      new TerraDrawLineStringMode(),
      new TerraDrawRectangleMode(),
      new TerraDrawSelectMode({
        flags: {
          linestring: { feature: { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } } },
          rectangle: { feature: { draggable: true } },
        },
      }),
    ],
  });
  draw.start();

  // When a rectangle is finished, derive its bbox and publish it to the app.
  draw.on('finish', (id) => {
    const f = draw.getSnapshot().find(s => s.id === id);
    if (!f || f.geometry.type !== 'Polygon') return;
    const ring = f.geometry.coordinates[0];
    const xs = ring.map(p => p[0]), ys = ring.map(p => p[1]);
    const bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
      .map(n => +n.toFixed(4));
    window.__helmBbox = bbox;
    window.dispatchEvent(new CustomEvent('helm:bbox', { detail: bbox }));
    ctx.notify(`Area selected — bbox ${bbox.join(', ')}`, 'ok');
  });
  return draw;
}

export function route(map, ctx) { ensure(map, ctx).setMode('linestring'); ctx.notify('Click to draw a route; double-click to finish', 'info'); }
export function lasso(map, ctx) { ensure(map, ctx).setMode('rectangle'); ctx.notify('Drag a rectangle over the area to fetch charts for', 'info'); }
export function select(map, ctx) { ensure(map, ctx).setMode('select'); }

export function disable() {
  if (!draw) return;
  try { draw.setMode('select'); } catch (e) { /* already stopped */ }
}
