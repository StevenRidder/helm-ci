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
 * DEMO_COG points at geomatico's public demo GeoTIFF; swap it for any COG
 * (e.g. a GFS field exported with `gdal_translate -of COG`). If it 404s the
 * layer simply doesn't draw — non-fatal.
 *
 * https://github.com/geomatico/maplibre-cog-protocol
 */
import { cogProtocol } from '@geomatico/maplibre-cog-protocol';

const SRC = 'helm-cog', LYR = 'helm-cog';
// Public geomatico demo COG — used only if no local file is available.
const DEMO_COG = 'cog://https://geomatico.github.io/maplibre-cog-protocol/sample/dem.tif#color:BrewerSpectral9,0,4000';
let protocolReady = false;

// Local depth GeoTIFF (pipeline/make_geotiff.py), single-band float32, colorized
// client-side by the #color: fragment — the value-encoded-file pattern, offline.
// Production: a true COG (gdal_translate -of COG) streamed via HTTP range reads.
function localCog() {
  return 'cog://' + new URL('data/key-west-depth.tif', location.href).href +
    '#color:BrewerSpectral9,-120,5';
}

export async function enable(map, ctx) {
  if (!protocolReady) { ctx.maplibregl.addProtocol('cog', cogProtocol); protocolReady = true; }
  if (map.getLayer(LYR)) { map.setLayoutProperty(LYR, 'visibility', 'visible'); return; }

  // Prefer the local depth COG; fall back to the public demo if it's missing.
  let url = ctx.cogUrl || localCog();
  try {
    const probe = await fetch('data/key-west-depth.tif', { method: 'GET', headers: { Range: 'bytes=0-3' } });
    if (!probe.ok) throw new Error(String(probe.status));
  } catch (e) { url = DEMO_COG; }

  map.addSource(SRC, { type: 'raster', url, tileSize: 256 });
  map.addLayer({ id: LYR, type: 'raster', source: SRC, paint: { 'raster-opacity': 0.8 } }, ctx.beforeId);
  ctx.notify('COG depth overlay via cog:// protocol (no tiler)', 'ok');
}

export function disable(map) {
  if (map.getLayer(LYR)) map.setLayoutProperty(LYR, 'visibility', 'none');
}
