// WX-19 regression: prepared weather tile fetches must wrap x across the antimeridian.
// Run: node web/tests/wx-scene-antimeridian.test.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const code = fs.readFileSync(path.join(__dirname, '..', 'wx-scene.js'), 'utf8');
const ctx = { window: {}, console, setTimeout, clearTimeout, setInterval, clearInterval,
  Date, Math, Object, Array, Promise, isFinite, parseInt, parseFloat,
  Blob: function () {}, fetch: function () { return Promise.resolve(); } };
ctx.window.HelmWxCodec = require(path.join(__dirname, '..', 'wx-value-codec.js'));
vm.createContext(ctx);
vm.runInContext(code, ctx);
const S = ctx.window.HelmWxScene;

let pass = 0, fail = 0;
function eq(name, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log((ok ? '  PASS ' : '  FAIL ') + name + (ok ? '' : '  got=' + JSON.stringify(got) + ' want=' + JSON.stringify(want)));
  ok ? pass++ : fail++;
}
function ok(name, cond) { console.log((cond ? '  PASS ' : '  FAIL ') + name); cond ? pass++ : fail++; }

eq('x=64 at z6 wraps to x=0', S._wrapTileX(6, 64), 0);
eq('x=66 at z6 wraps to x=2', S._wrapTileX(6, 66), 2);
eq('x=-1 at z6 wraps to x=63', S._wrapTileX(6, -1), 63);
eq('x=128 at z7 wraps to x=0', S._wrapTileX(7, 128), 0);

// Live Fiji view from the regression: bounds are continuous 159E..194E, crossing 180.
const tiles = S._wrappedTilesForBbox(6, [159.32796028182182, -27.14590165782444, 194.39441971818175, -7.695932095481245]);
const xs = Array.from(new Set(tiles.map(t => t.x))).sort((a, b) => a - b);
eq('continuous 159E..194E bbox fetches wrapped x tiles', xs, [0, 1, 2, 60, 61, 62, 63]);
ok('no impossible z6 x>=64 requests remain', tiles.every(t => t.x >= 0 && t.x < 64));

const nearManifest = { coverage: { bbox: {
  west: 157.4, east: -162.6, south: -32.6, north: -2.6, crossesAntimeridian: true
} } };
eq('wide transient view clips to antimeridian bundle coverage',
  S._clipViewToCoverage(nearManifest, 90, -60, 220, 20),
  { west: 157.4, south: -32.6, east: 197.4, north: -2.6 });
eq('inside antimeridian view remains continuous',
  S._clipViewToCoverage(nearManifest, 159, -27, 194, -8),
  { west: 159, south: -27, east: 194, north: -8 });

console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
