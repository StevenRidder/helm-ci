// FUSE-2 — North Star fused-map layer z-order lint.
// Draw order is bottom-first (manifest merge order). Bands: basemap → enc → overlays → weather → nav.
// Run: node web/tests/fuse-2-layer-order.test.js
const fs = require('fs'), path = require('path'), assert = require('assert');

const STYLE_DIR = path.join(__dirname, '..', 'style');
const man = JSON.parse(fs.readFileSync(path.join(STYLE_DIR, 'manifest.json'), 'utf8'));

const merged = JSON.parse(fs.readFileSync(path.join(STYLE_DIR, man.base), 'utf8'));
merged.layers = merged.layers || [];
for (const f of man.fragments) {
  const frag = JSON.parse(fs.readFileSync(path.join(STYLE_DIR, f), 'utf8'));
  merged.layers.push(...(frag.layers || []));
}

// Canonical draw stack for helm-northstar-fused-map (bottom → top).
const BUCKETS = [
  {
    name: 'basemap',
    ids: [
      'ocean', 'helm-chart-online-fill',
      'navionics', 'googlesat', 'bingsat', 'arcgis', 'satellite', 'charts'
    ]
  },
  {
    name: 'enc',
    ids: ['enc-chart', 'depare-fill', 'depcnt-line', 'soundg-text']
  },
  {
    name: 'overlays',
    ids: ['route-line', 'openseamap-seamarks']
  },
  {
    name: 'weather',
    ids: ['wind-arrows']
  },
  {
    name: 'nav',
    ids: [
      'whereto-ring', 'whereto-rank',
      'places-cluster', 'places-cluster-count', 'places-halo', 'places-icon', 'places-label',
      'ais-vessels', 'ais-label',
      'saved-halo', 'saved-icon', 'saved-label'
    ]
  }
];

const EXPECTED = BUCKETS.reduce(function (acc, b) { return acc.concat(b.ids); }, []);
const actual = merged.layers.map(function (l) { return l.id; });

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

ok('merged style layer ids match the FUSE-2 contract', function () {
  assert.deepStrictEqual(actual, EXPECTED, 'layer order drift — update manifest fragments or this contract intentionally');
});

ok('each FUSE-2 band is a contiguous block in draw order', function () {
  var pos = Object.create(null);
  actual.forEach(function (id, i) { pos[id] = i; });
  BUCKETS.forEach(function (bucket, bi) {
    var idxs = bucket.ids.map(function (id) { return pos[id]; });
    var min = Math.min.apply(null, idxs);
    var max = Math.max.apply(null, idxs);
    assert.strictEqual(max - min + 1, bucket.ids.length,
      bucket.name + ' layers must stay contiguous (got spread indices)');
    if (bi > 0) {
      var prev = BUCKETS[bi - 1];
      var prevMax = Math.max.apply(null, prev.ids.map(function (id) { return pos[id]; }));
      assert.ok(min > prevMax, bucket.name + ' must paint above ' + prev.name);
    }
  });
});

ok('manifest fragment order matches band boundaries', function () {
  assert.deepStrictEqual(man.fragments, [
    'helm-chart-basemaps.json',
    'helm-chart-depth.json',
    'helm-route-line.json',
    'helm-layer-seamarks.json',
    'helm-wx-wind.json',
    'helm-place-whereto.json',
    'helm-place-poi.json',
    'helm-ais-targets.json',
    'helm-place-saved.json'
  ]);
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - fuse-2-layer-order: ' + pass + ' groups passed');
