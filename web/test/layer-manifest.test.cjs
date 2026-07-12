// Unit test for web/layer-manifest.js (LAYER-2 client loader: manifest -> MapLibre overlay tier).
// Pure logic (tier resolution, format classification, url guard, layer specs) + the applyManifest
// flow against a fake MapLibre map. No browser, no network. Auto-joins web/test/run.mjs.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

// Minimal MapLibre stand-in: records sources/layers and their draw order + beforeId anchor.
function FakeMap(present) {
  this.sources = Object.create(null);
  this.layers = Object.create(null);
  this.order = [];
  const self = this;
  (present || []).forEach(function (id) { self.layers[id] = { id: id }; self.order.push(id); });
}
FakeMap.prototype.getSource = function (id) { return this.sources[id] || null; };
FakeMap.prototype.addSource = function (id, spec) {
  if (this.sources[id]) throw new Error('source exists: ' + id);
  this.sources[id] = spec;
};
FakeMap.prototype.removeSource = function (id) { delete this.sources[id]; };
FakeMap.prototype.getLayer = function (id) { return this.layers[id] || null; };
FakeMap.prototype.addLayer = function (spec, before) {
  if (this.layers[spec.id]) throw new Error('layer exists: ' + spec.id);
  if (before != null && this.order.indexOf(before) === -1) throw new Error('before layer missing: ' + before);
  this.layers[spec.id] = spec;
  spec.__before = before;
  if (before != null) this.order.splice(this.order.indexOf(before), 0, spec.id);
  else this.order.push(spec.id);
};
FakeMap.prototype.removeLayer = function (id) {
  delete this.layers[id];
  const i = this.order.indexOf(id);
  if (i !== -1) this.order.splice(i, 1);
};

function load() {
  const win = {};
  const sandbox = { window: win, console: { log: function () {}, warn: function () {} }, Promise: Promise };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'layer-manifest.js'), 'utf8'), sandbox, { filename: 'layer-manifest.js' });
  return win.HelmLayerManifest;
}

// FUSE-2 layers present on the test map (one per band).
const FUSE2 = ['ocean', 'navionics', 'enc-chart', 'depare-fill', 'route-line', 'wind-arrows', 'ais-vessels'];

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

const M = load();

// --- tierBeforeId: overlays insert below the lowest present layer of the next band up ---
{
  const map = new FakeMap(FUSE2);
  ok(M.tierBeforeId(map, 'basemap') === 'enc-chart', 'basemap tier anchors before enc band (enc-chart)');
  ok(M.tierBeforeId(map, 'enc') === 'route-line', 'enc tier anchors before overlay band (route-line)');
  ok(M.tierBeforeId(map, 'overlay') === 'wind-arrows', 'overlay tier anchors before weather band (wind-arrows)');
  ok(M.tierBeforeId(map, 'weather') === 'ais-vessels', 'weather tier anchors before nav band (ais-vessels)');
  ok(M.tierBeforeId(map, 'nav') === undefined, 'nav tier has no anchor (paints on top)');
  ok(M.tierBeforeId(map, 'bogus') === 'wind-arrows', 'unknown tier defaults to overlay band anchor');
}

// --- tierBeforeId is resilient to a sparse style (skips absent band layers) ---
{
  const sparse = new FakeMap(['navionics', 'ais-vessels']);   // no enc/overlay/weather layers
  ok(M.tierBeforeId(sparse, 'basemap') === 'ais-vessels', 'basemap falls through absent bands to nav');
  ok(M.tierBeforeId(sparse, 'weather') === 'ais-vessels', 'weather falls through to nav');
}

// --- slug + isPublicUrl ---
{
  ok(M.slug('Owned Anchorage #2!') === 'owned-anchorage-2', 'slug sanitizes to helm-<epic>-safe id');
  ok(M.isPublicUrl('/user-data/layers/x.geojson') === true, 'accepts server route');
  ok(M.isPublicUrl('data/notes.geojson') === true, 'accepts app-relative path');
  ok(M.isPublicUrl('https://tiles.example/x.json') === true, 'accepts absolute http(s)');
  ok(M.isPublicUrl('/Users/steve/.helm/secret.geojson') === false, 'refuses private FS root');
  ok(M.isPublicUrl('file:///etc/passwd') === false, 'refuses file: url');
  ok(M.isPublicUrl('../../etc/passwd') === false, 'refuses path traversal');
  ok(M.isPublicUrl('C:\\\\Users\\\\x') === false, 'refuses windows path');
  ok(M.isPublicUrl('') === false && M.isPublicUrl(null) === false, 'refuses empty/non-string');
}

// --- classify: geojson supported; packs/bundles deferred (named); unknown unsupported ---
{
  ok(M.classify({ format: 'geojson' }).supported === true, 'geojson supported');
  ok(M.classify({ format: 'GeoJSON' }).supported === true, 'format is case-insensitive');
  const p = M.classify({ format: 'pmtiles' });
  ok(p.supported === false && /deferred-to-offline-packs/.test(p.reason), 'pmtiles deferred to offline-packs');
  ok(/deferred-to-wx-grid/.test(M.classify({ format: 'environmental-bundle' }).reason), 'env-bundle deferred to wx-grid');
  ok(M.classify({ format: 'xyz' }).reason === 'unsupported-format', 'unknown format unsupported');
}

// --- layerSpecs: kind -> maplibre type, namespaced ids, degraded dimming ---
{
  const pts = M.layerSpecs({ id: 'anchor notes', kind: 'points', url: 'x' });
  ok(pts.length === 1 && pts[0].type === 'circle' && pts[0].id === 'helm-layer-anchor-notes', 'points -> circle, namespaced id');
  ok(pts[0].source === 'helm-layer-anchor-notes-src', 'layer bound to namespaced source');
  ok(pts[0].paint['circle-opacity'] === 0.9, 'fresh points at full opacity');

  const lines = M.layerSpecs({ id: 'route', kind: 'lines', url: 'x' });
  ok(lines[0].type === 'line', 'lines -> line');

  const poly = M.layerSpecs({ id: 'zone', kind: 'polygons', url: 'x' });
  ok(poly.length === 2 && poly[0].type === 'fill' && poly[1].type === 'line', 'polygons -> fill + outline');
  ok(poly[0].id === 'helm-layer-zone-fill' && poly[1].id === 'helm-layer-zone-outline', 'polygon layer ids namespaced');

  const stale = M.layerSpecs({ id: 'old', kind: 'lines', url: 'x', freshness: { status: 'stale' } });
  ok(stale[0].paint['line-opacity'] === 0.4, 'stale line rendered dimmed');
  ok(Array.isArray(stale[0].paint['line-dasharray']), 'stale line rendered dashed');
  ok(pts[0].metadata['helm:layer'].id === 'anchor notes', 'layer carries manifest metadata for inspection');
}

// --- applyManifest: mixed manifest routes each entry correctly ---
function mixedManifest() {
  return {
    schema: 'helm.layer.manifest.v1',
    layers: [
      { id: 'owned-anchorage-notes', kind: 'points', format: 'geojson', tier: 'overlay', url: '/user-data/layers/anchorages.geojson', freshness: { status: 'ok' } },
      { id: 'depare', kind: 'polygons', format: 'geojson', tier: 'enc', url: '/user-data/enc/depare.geojson' },            // base-owned -> skip
      { id: 'fiji-sat', kind: 'raster', format: 'pmtiles', tier: 'basemap', url: '/user-data/packs/fiji.pmtiles' },        // deferred
      { id: 'leaky', kind: 'points', format: 'geojson', tier: 'overlay', url: '/Users/steve/.helm/secret.geojson' },       // rejected
      { id: 'stale-notes', kind: 'lines', format: 'geojson', tier: 'overlay', url: 'data/notes.geojson', freshness: { status: 'stale' } } // degraded
    ]
  };
}
{
  const map = new FakeMap(FUSE2);
  const s = M.applyManifest(map, mixedManifest());
  ok(s.loaded.length === 1 && s.loaded[0].id === 'owned-anchorage-notes', 'one fresh geojson overlay loaded');
  ok(s.degraded.length === 1 && s.degraded[0].id === 'stale-notes', 'stale geojson loaded as degraded');
  ok(s.skipped.length === 2, 'base-owned + deferred skipped');
  ok(s.rejected.length === 1 && s.rejected[0].id === 'leaky', 'private-url entry rejected');
  ok(s.errors.length === 0, 'no errors on well-formed manifest');
  ok(!!map.getLayer('helm-layer-owned-anchorage-notes'), 'overlay layer added to map');
  ok(!!map.getSource('helm-layer-owned-anchorage-notes-src'), 'overlay source added to map');
  ok(map.layers['helm-layer-owned-anchorage-notes'].__before === 'wind-arrows', 'overlay inserted into its FUSE-2 band');
  ok(!map.getLayer('helm-layer-depare-fill') && !map.getLayer('helm-layer-fiji-sat'), 'skipped entries drew nothing');
}

// --- idempotent re-load: clear() removes prior layers, re-apply yields the same result ---
{
  const map = new FakeMap(FUSE2);
  M.applyManifest(map, mixedManifest());
  const before = Object.keys(map.layers).length;
  const s2 = M.applyManifest(map, mixedManifest());
  ok(Object.keys(map.layers).length === before, 're-load does not duplicate layers');
  ok(s2.loaded.length === 1 && s2.degraded.length === 1, 're-load reports the same overlays');
  M.clear(map);
  ok(!map.getLayer('helm-layer-owned-anchorage-notes') && !map.getSource('helm-layer-owned-anchorage-notes-src'), 'clear() removes our layers + sources');
}

// --- malformed manifest fails loud (named signal), never throws ---
{
  const map = new FakeMap(FUSE2);
  const s = M.applyManifest(map, { schema: 'helm.layer.manifest.v1' });   // no layers[]
  ok(s.errors.length >= 1, 'malformed manifest surfaces an error');
  ok(M.status().lastError && M.status().lastError.reason === 'malformed-manifest', 'lastError records the malformed signal');
}

// --- fetch paths: 404 => empty (not an error); ok => applied; network throw => loud, no reject ---
function fakeRes(opts) {
  return { ok: opts.ok, status: opts.status || (opts.ok ? 200 : 500), json: function () { return Promise.resolve(opts.body); } };
}
async function asyncTests() {
  const map = new FakeMap(FUSE2);
  const okFetch = function () { return Promise.resolve(fakeRes({ ok: true, body: mixedManifest() })); };
  const s1 = await M.load(map, { fetch: okFetch });
  ok(s1.loaded.length === 1 && s1.degraded.length === 1, 'load() applies a fetched manifest');

  const map2 = new FakeMap(FUSE2);
  const notFound = function () { return Promise.resolve(fakeRes({ ok: false, status: 404 })); };
  const s2 = await M.load(map2, { fetch: notFound });
  ok(s2.loaded.length === 0 && s2.errors.length === 0, '404 manifest => empty, no error (chart keeps rendering)');

  const map3 = new FakeMap(FUSE2);
  const boom = function () { return Promise.reject(new Error('network down')); };
  const s3 = await M.load(map3, { fetch: boom });
  ok(s3.errors.length === 1 && /network down/.test(s3.errors[0].message), 'network failure surfaced as a named error, load() still resolves');
}

asyncTests().then(function () {
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}).catch(function (e) {
  console.error('async tests threw:', e);
  process.exit(1);
});
