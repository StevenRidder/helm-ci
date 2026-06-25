/*
 * Helm — integrations/ais-deck.js   ·   deck.gl (@deck.gl/mapbox)
 * --------------------------------------------------------------------------
 * AIS at scale. The style.json renders a handful of vessels as symbol layers —
 * fine for the sample, but hundreds/thousands of targets (icons + CPA colour +
 * density) is deck.gl's home turf. We composite a MapboxOverlay over MapLibre
 * and draw the fleet as a ScatterplotLayer + an optional HeatmapLayer.
 *
 * Seed from Helm's REAL AIS sample (data/ais-sample.geojson) and, to make the
 * "at scale" point feel real, synthesize a dense fleet AROUND those real targets
 * (~2,000) — all offline, no live feed required. Swap in a live AIS stream and
 * the layers are unchanged.
 *
 * https://deck.gl  ·  https://deck.gl/docs/api-reference/mapbox/mapbox-overlay
 */
import { MapboxOverlay } from '@deck.gl/mapbox';
import { ScatterplotLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';

let overlay = null;
const TARGET = 2000;

async function fleet(ctx) {
  let real = [];
  try {
    const fc = await fetch('data/ais-sample.geojson').then(r => r.ok ? r.json() : null);
    if (fc && fc.features) real = fc.features
      .filter(f => f.geometry && f.geometry.type === 'Point')
      .map(f => ({ position: f.geometry.coordinates.slice(0, 2), cpa: f.properties.cpa ?? 5, sog: f.properties.sog ?? 0, real: true }));
  } catch (e) { /* offline fallback below */ }

  const out = real.slice();
  const seeds = real.length ? real.map(r => r.position) : [ctx.region.center];
  for (let i = out.length; i < TARGET; i++) {
    const s = seeds[i % seeds.length], r = Math.random();
    out.push({
      position: [s[0] + (Math.random() - 0.5) * 0.8, s[1] + (Math.random() - 0.5) * 0.6],
      cpa: r < 0.04 ? Math.random() * 0.2 : r < 0.12 ? 0.2 + Math.random() * 0.3 : 1 + Math.random() * 5,
      sog: +(Math.random() * 18).toFixed(1),
    });
  }
  return { data: out, realCount: real.length };
}

const colorByCpa = d => d.cpa < 0.2 ? [228, 86, 79] : d.cpa < 0.5 ? [242, 180, 65] : [91, 192, 255];

export async function enable(map, ctx) {
  const { data, realCount } = await fleet(ctx);
  const layers = [
    new HeatmapLayer({
      id: 'helm-ais-heat', data, getPosition: d => d.position, getWeight: 1,
      radiusPixels: 40, intensity: 1, threshold: 0.05, opacity: 0.35,
    }),
    new ScatterplotLayer({
      id: 'helm-ais-scatter', data, getPosition: d => d.position,
      getFillColor: colorByCpa, getRadius: 60, radiusMinPixels: 2, radiusMaxPixels: 6,
      stroked: true, getLineColor: [13, 19, 27], lineWidthMinPixels: 0.5, pickable: true,
    }),
  ];
  if (!overlay) { overlay = new MapboxOverlay({ interleaved: true, layers }); map.addControl(overlay); }
  else overlay.setProps({ layers });
  ctx.notify(`deck.gl: ${realCount} real + ${data.length - realCount} synthetic AIS targets at scale`, 'ok');
}

export function disable(map) {
  if (overlay) { overlay.setProps({ layers: [] }); }
}
