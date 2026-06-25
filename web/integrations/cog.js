/*
 * Helm — integrations/cog.js   ·   maplibre-cog-protocol (geomatico)
 * --------------------------------------------------------------------------
 * Load a Cloud Optimized GeoTIFF straight into MapLibre via a `cog://` custom
 * protocol — no tiler, no mbtiles repack, just HTTP range reads off a static
 * .tif. This is the cheap path for BOTH halves of Helm: GRIB->COG is a one-step
 * GDAL convert (weather), and depth/imagery COGs stream the same way.
 *
 * The protocol also supports a `#color:...` URL fragment that colorizes a
 * value-encoded single-band COG client-side (the Mercator-style idea, applied
 * to a file instead of a tile pyramid).
 *
 * OFFLINE-FIRST: DEMO_COG points at a LOCAL value-encoded GeoTIFF baked by
 * pipeline/make_demo_cog.py (a Helm SST field, EPSG:4326) — colourised
 * client-side by the #color fragment, no CDN. Swap it for any COG (e.g. a GFS
 * field exported with `gdal_translate -of COG`, served from the boat-server).
 * If the file is missing the layer simply doesn't draw — non-fatal.
 *
 * https://github.com/geomatico/maplibre-cog-protocol
 */
import { cogProtocol } from '@geomatico/maplibre-cog-protocol';

const SRC = 'helm-cog', LYR = 'helm-cog';
const DEMO_COG = 'cog://data/demo-sst-cog.tif#color:BrewerYlOrRd9,28,33';
let protocolReady = false;

export async function enable(map, ctx) {
  if (!protocolReady) { ctx.maplibregl.addProtocol('cog', cogProtocol); protocolReady = true; }
  if (map.getLayer(LYR)) { map.setLayoutProperty(LYR, 'visibility', 'visible'); return; }

  map.addSource(SRC, { type: 'raster', url: ctx.cogUrl || DEMO_COG, tileSize: 256 });
  map.addLayer({ id: LYR, type: 'raster', source: SRC, paint: { 'raster-opacity': 0.8 } }, ctx.beforeId);
  ctx.notify('COG overlay loaded via cog:// protocol (no tiler)', 'ok');
}

export function disable(map) {
  if (map.getLayer(LYR)) map.setLayoutProperty(LYR, 'visibility', 'none');
}
