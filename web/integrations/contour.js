/*
 * Helm — integrations/contour.js   ·   maplibre-contour (onthegomap)
 * --------------------------------------------------------------------------
 * On-the-fly contour lines from a terrain-RGB DEM, computed in a worker. This
 * is the off-the-shelf replacement for our hand-rolled isolines.js (marching
 * squares + polyline stitching): point it at a value-encoded DEM and get
 * labelled isolines for free.
 *
 * We use the public Terrarium DEM (AWS open data), which encodes BATHYMETRY
 * (negative elevations) as well as land — so around Key West this draws real
 * depth contours under the chart. For weather isobars, feed it a pressure
 * field exported as terrain-RGB instead (same code path).
 *
 * https://github.com/onthegomap/maplibre-contour
 */
import mlcontour from 'maplibre-contour';

const DEM = 'helm-dem', CONT = 'helm-contours', LINE = 'helm-contour-line', LBL = 'helm-contour-label';
let demSource = null;

export async function enable(map, ctx) {
  if (map.getLayer(LINE)) {
    [LINE, LBL].forEach(id => map.setLayoutProperty(id, 'visibility', 'visible'));
    return;
  }
  if (!demSource) {
    demSource = new mlcontour.DemSource({
      url: 'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png',
      encoding: 'terrarium',
      maxzoom: 13,
      worker: true,
    });
    demSource.setupMaplibre(ctx.maplibregl);
  }

  map.addSource(CONT, {
    type: 'vector',
    tiles: [demSource.contourProtocolUrl({
      // metres. Thin lines every 10 m, bold (an index line) every 50 m.
      thresholds: { 10: [10, 50], 11: [10, 50], 12: [5, 25], 13: [5, 25], 14: [5, 25] },
      elevationKey: 'ele',
      levelKey: 'level',
      contourLayer: 'contours',
    })],
    maxzoom: 15,
  });

  map.addLayer({
    id: LINE, type: 'line', source: CONT, 'source-layer': 'contours',
    paint: {
      'line-color': '#2f6f8f',
      'line-width': ['match', ['get', 'level'], 1, 1.1, 0.5],
      'line-opacity': 0.65,
    },
  }, ctx.beforeId);

  map.addLayer({
    id: LBL, type: 'symbol', source: CONT, 'source-layer': 'contours',
    filter: ['>', ['get', 'level'], 0],
    layout: {
      'symbol-placement': 'line',
      'text-field': ['concat', ['number-format', ['abs', ['get', 'ele']], {}], ' m'],
      'text-font': ['Open Sans Regular'],
      'text-size': 10,
    },
    paint: { 'text-color': '#1e5066', 'text-halo-color': '#fff', 'text-halo-width': 1.1 },
  }, ctx.beforeId);

  ctx.notify('Contours from DEM (worker) — replaces isolines.js', 'ok');
}

export function disable(map) {
  [LINE, LBL].forEach(id => { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none'); });
}
