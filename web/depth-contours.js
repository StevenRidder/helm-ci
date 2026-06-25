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
// ABSOLUTE url on purpose: maplibre-contour fetches DEM tiles inside a Web Worker,
// which has no document base and can't resolve a relative path (it throws
// "Failed to parse URL"). Resolve against the page origin so the worker can fetch.
const LOCAL_DEM = new URL('data/dem/', document.baseURI).href + '{z}/{x}/{y}.png';

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
      maxzoom: 12,                                // DEM is baked to z12; maplibre-contour over-zooms past that
      worker: true,
    });
    demSource.setupMaplibre(maplibregl);
  }

  map.addSource(CONT, {
    type: 'vector',
    tiles: [demSource.contourProtocolUrl({
      // metres, per display zoom — coarse contours when zoomed out (regional, only the
      // big bathymetric steps) through fine ones near the anchorage. [minor, index].
      thresholds: {
        6: [500, 2000], 7: [200, 1000], 8: [100, 500],
        9: [50, 250], 10: [50, 250], 11: [20, 100], 12: [5, 25],
      },
      subsampleBelow: 13,     // bilinearly upsample the DEM before contouring -> smooth curves, not stair-steps
      elevationKey: 'ele',
      levelKey: 'level',
      contourLayer: 'contours',
    })],
    // Generate at the DEM's native zooms (z6-12) only — maplibre-contour's DEM over-zoom
    // returns empty past ~1 level. For closer display zooms MapLibre over-zooms the z12
    // contour VECTOR tiles natively, so lines stay present (and crisp — vector geometry,
    // not pixels) at ANY zoom.
    maxzoom: 12,
  });

  map.addLayer({
    id: LINE, type: 'line', source: CONT, 'source-layer': 'contours',
    layout: { 'line-join': 'round', 'line-cap': 'round' },   // smooth the corners
    paint: {
      'line-color': '#46a0c4',                               // brighter teal — reads on dark-water satellite
      'line-width': ['interpolate', ['linear'], ['zoom'],    // thinner zoomed out, heavier zoomed in; index lines bolder
        8,  ['match', ['get', 'level'], 1, 0.8, 0.4],
        14, ['match', ['get', 'level'], 1, 1.7, 0.8]],
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 6, 0.4, 11, 0.7, 14, 0.85],
      'line-blur': 0.4,                                       // soften residual marching-squares stair-steps
    },
  }, beforeId);

  map.addLayer({
    id: LBL, type: 'symbol', source: CONT, 'source-layer': 'contours',
    minzoom: 11,                                   // labels only once they're readable
    filter: ['>', ['get', 'level'], 0],            // label index lines only
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 220,
      'text-field': ['concat', ['number-format', ['abs', ['get', 'ele']], {}], ' m'],
      'text-font': ['Noto Sans Regular'],
      'text-size': 10,
    },
    paint: { 'text-color': '#bfe2f0', 'text-halo-color': 'rgba(13,19,27,0.85)', 'text-halo-width': 1.1 },
  }, beforeId);
}

export function disable(map) {
  [LINE, LBL].forEach(id => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', 'none'));
}
