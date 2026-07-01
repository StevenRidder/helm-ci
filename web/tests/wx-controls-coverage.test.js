// WX-19 unit test: viewport coverage must be antimeridian-aware and viewport-based.
// Run: node web/tests/wx-controls-coverage.test.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const code = fs.readFileSync(path.join(__dirname, '..', 'wx-controls.js'), 'utf8');

function bounds(w, s, e, n) {
  return { getWest: () => w, getSouth: () => s, getEast: () => e, getNorth: () => n };
}
function map(w, s, e, n, z) {
  return { getBounds: () => bounds(w, s, e, n), getZoom: () => z };
}

const ctx = {
  window: { addEventListener: function () {} },
  location: { protocol: 'http:', hostname: 'localhost' },
  document: {
    readyState: 'loading',
    addEventListener: function () {},
    getElementById: function () { return null; },
    createElement: function () { return { style: {}, appendChild: function () {} }; },
    body: { appendChild: function () {} },
  },
  console, setTimeout, clearTimeout, Math, Array, Object, String, Number,
  encodeURIComponent, decodeURIComponent, Promise,
  fetch: function () { return Promise.resolve({ ok: false }); },
};
vm.createContext(ctx);
vm.runInContext(code, ctx);
const T = ctx.window.HelmWxControls._test;

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  console.log((cond ? '  PASS ' : '  FAIL ') + name + (cond || !detail ? '' : '  ' + detail));
  cond ? pass++ : fail++;
}

const fiji = { west: 172, east: -144, south: -26, north: -5, crossesAntimeridian: true };
const z4View = { west: -245.429, east: -112.999, south: -39.476, north: 16.724 };
const rep = T.coverageReportForBbox(fiji, z4View);
ok('Fiji prepared bbox does NOT cover the wide z4 viewport', rep.coversView === false, JSON.stringify(rep));
ok('coverage report names missing edges', rep.missing.indexOf('west') >= 0 && rep.missing.indexOf('east') >= 0 && rep.missing.indexOf('south') >= 0 && rep.missing.indexOf('north') >= 0, JSON.stringify(rep.missing));
ok('Fiji bbox is normalized into the viewport longitude frame', Math.round(rep.coverage.west) === -188 && Math.round(rep.coverage.east) === -144, JSON.stringify(rep.coverage));

const wide = { west: 110, east: -100, south: -50, north: 25, crossesAntimeridian: true };
ok('Wider basin bbox covers the same z4 viewport', T.coverageReportForBbox(wide, z4View).coversView === true);

const plan = T.quantizeViewForMaterialize(map(-245.429, -39.476, -112.999, 16.724, 4.2));
ok('materialize plan crosses antimeridian for the z4 Fiji view', plan.e < plan.w, JSON.stringify(plan));
ok('materialize plan requests low-zoom overview through z5', plan.maxzoom === 5, JSON.stringify(plan));
ok('materialize URL uses the prepared-bundle endpoint', /\/bundles\/open-meteo\/latest\/materialize\?/.test(T.materializeUrl(plan)));

console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
