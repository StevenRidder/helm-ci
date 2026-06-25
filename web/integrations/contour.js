/*
 * Helm — integrations/contour.js   ·   depth contours from a DEM
 * --------------------------------------------------------------------------
 * Depth/terrain contour lines — the off-the-shelf replacement for our
 * hand-rolled isolines.js (marching squares + polyline stitching).
 *
 * TWO production paths, same DEM:
 *
 *  1. PRE-BAKED (default here): contours generated at build time
 *     (pipeline/gen_demo_data.py · marching squares over the DEM) and shipped as
 *     web/data/depth-contours.geojson. This is how ENC charts carry depth
 *     contours (DEPCNT): vectors, not computed per frame — reliable, offline,
 *     label-ready, and no runtime DEM decode. Best for a fixed on-device chart.
 *
 *  2. RUNTIME (maplibre-contour, kept below, commented): decode a Terrarium DEM
 *     and march on the fly in a Worker. Best for live or third-party DEMs you
 *     don't control at build time (e.g. a pressure field for weather isobars).
 *     See https://github.com/onthegomap/maplibre-contour
 */
// import mlcontour from 'maplibre-contour';   // runtime path — see note above

const SRC = 'helm-contours', LINE = 'helm-contour-line', LBL = 'helm-contour-label';

export async function enable(map, ctx) {
  if (map.getLayer(LINE)) {
    [LINE, LBL].forEach(id => map.setLayoutProperty(id, 'visibility', 'visible'));
    return;
  }

  if (!map.getSource(SRC)) {
    map.addSource(SRC, {
      type: 'geojson',
      data: ctx.contourUrl || 'data/depth-contours.geojson',
      attribution: 'Helm offline depth contours · NOT FOR NAVIGATION',
    });
  }

  // index lines (every 25 m) heavier + labelled; intermediate lines thin.
  map.addLayer({
    id: LINE, type: 'line', source: SRC,
    paint: {
      'line-color': '#2f6f8f',
      'line-width': ['interpolate', ['linear'], ['zoom'],
        9, ['match', ['get', 'level'], 1, 0.9, 0.4],
        14, ['match', ['get', 'level'], 1, 2.0, 0.9]],
      'line-opacity': 0,
      'line-opacity-transition': { duration: 500 },
    },
  }, ctx.beforeId);
  requestAnimationFrame(() => { if (map.getLayer(LINE)) map.setPaintProperty(LINE, 'line-opacity', 0.7); });

  map.addLayer({
    id: LBL, type: 'symbol', source: SRC,
    filter: ['==', ['get', 'level'], 1],   // label the index contours
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 220,
      'text-field': ['concat', ['to-string', ['get', 'depth_m']], ' m'],
      'text-font': ['Open Sans Regular'],
      'text-size': 10,
    },
    paint: { 'text-color': '#cfe9f4', 'text-halo-color': '#0d131b', 'text-halo-width': 1.2 },
  }, ctx.beforeId);

  ctx.notify('Depth contours (pre-baked from DEM) — replaces isolines.js', 'ok');
}

export function disable(map) {
  [LINE, LBL].forEach(id => { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none'); });
}
