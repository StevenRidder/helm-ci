/*
 * Helm — depth-contours.js   ·   PRODUCTION depth/terrain contours
 * --------------------------------------------------------------------------
 * Off-thread contour lines from a terrain-RGB DEM, via maplibre-contour
 * (onthegomap). This is the production adoption that retires the hand-rolled
 * marching-squares isolines.js: instead of stitching segments on the main
 * thread, maplibre-contour tiles + contours the DEM in a Web Worker.
 *
 * OFFLINE-FIRST: the DEM is the LOCAL terrarium tile set baked by
 * pipeline/fetch_dem.py into web/data/dem/{z}/{x}/{y}.png. No CDN at runtime —
 * works on a boat with no internet. Terrarium encodes bathymetry (negative
 * elevations) as well as land, so this draws real depth contours under the
 * chart and fills in continuously where the ENC depcnt vectors aren't loaded.
 *
 * ESM (imported lazily from index.html the first time the toggle is switched
 * on) so neither maplibre-contour nor its worker cost anything until used.
 *
 * https://github.com/onthegomap/maplibre-contour
 */
import mlcontour from 'maplibre-contour';

const DEM = 'helm-dem-src', CONT = 'helm-depth-contours';
const LINE = 'helm-depth-contour-line', LBL = 'helm-depth-contour-label';
let demSource = null;

// Local terrarium DEM baked by the pipeline. Same {z}/{x}/{y} contract a CDN
// would use, but served from the app's own origin — offline by default.
const LOCAL_DEM = 'data/dem/{z}/{x}/{y}.png';

export async function enable(map, ctx = {}) {
  const maplibregl = ctx.maplibregl || window.maplibregl;
  const beforeId = (ctx.beforeId && map.getLayer(ctx.beforeId)) ? ctx.beforeId : undefined;

  if (map.getLayer(LINE)) {                       // re-enable: just show
    [LINE, LBL].forEach(id => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', 'visible'));
    return;
  }

  if (!demSource) {
    demSource = new mlcontour.DemSource({
      url: LOCAL_DEM,
      encoding: 'terrarium',
      maxzoom: 13,                                // DEM is baked to z13; over-zoom past that
      worker: true,
    });
    demSource.setupMaplibre(maplibregl);
  }

  map.addSource(CONT, {
    type: 'vector',
    tiles: [demSource.contourProtocolUrl({
      // metres. Thin line every 5 m, bold index line every 25 m — tuned for the
      // shallow Key West shelf; deepen the steps for open-ocean DEMs.
      thresholds: { 9: [20, 100], 10: [10, 50], 11: [10, 50], 12: [5, 25], 13: [5, 25] },
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
      'line-width': ['match', ['get', 'level'], 1, 1.2, 0.5],   // index lines heavier
      'line-opacity': 0.6,
    },
  }, beforeId);

  map.addLayer({
    id: LBL, type: 'symbol', source: CONT, 'source-layer': 'contours',
    filter: ['>', ['get', 'level'], 0],            // label index lines only
    layout: {
      'symbol-placement': 'line',
      'text-field': ['concat', ['number-format', ['abs', ['get', 'ele']], {}], ' m'],
      'text-font': ['Noto Sans Regular'],
      'text-size': 10,
    },
    paint: { 'text-color': '#1e5066', 'text-halo-color': '#fff', 'text-halo-width': 1.1 },
  }, beforeId);
}

export function disable(map) {
  [LINE, LBL].forEach(id => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', 'none'));
}
