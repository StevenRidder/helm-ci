'use strict';
// fuse-3-wx-scrim-toggle.test.cjs — FUSE-3: the weather scrim (web/wx-scrim.js) dim/desaturate is
// opt-out via the #wx-scrim checkbox in the Weather drawer (index.html). DOM-coupled module, so we
// load it in a vm sandbox with a minimal document + fake map, same style as ais-guard.test.cjs.
//   Run: node web/test/fuse-3-wx-scrim-toggle.test.cjs   (exit 0 = all green)
const fs = require('fs'), path = require('path'), vm = require('vm');
const assert = require('assert');

const WEB = path.join(__dirname, '..');

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

function makeCheckbox(checked) {
  return { checked: checked, _onchange: null, addEventListener: function (evt, fn) { if (evt === 'change') this._onchange = fn; } };
}

// Loads a fresh wx-scrim.js instance into its own sandbox. `elements` maps id -> element stub
// (only 'wx-scrim' matters here); omit the key entirely to simulate markup without the checkbox.
function loadScrim(elements) {
  var paints = [];   // { layerId, prop, value } — every setPaintProperty call, in order
  var layers = [
    { id: 'navionics', type: 'raster' },
    { id: 'helm-wx-grid-0', type: 'raster' },   // must never be touched (prefix exclusion)
    { id: 'route-line', type: 'line' },          // non-raster — must never be touched
  ];
  var sandbox = {
    console: console,
    document: {
      readyState: 'complete',
      addEventListener: function () {},
      querySelectorAll: function () { return []; },   // no [data-wx] buttons in this harness
      getElementById: function (id) { return elements[id] || null; },
    },
    map: {
      getStyle: function () { return { layers: layers }; },
      setPaintProperty: function (id, prop, value) { paints.push({ layerId: id, prop: prop, value: value }); },
    },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(WEB, 'wx-scrim.js'), 'utf8'), sandbox, { filename: 'wx-scrim.js' });
  if (!sandbox.HelmWxScrim) throw new Error('wx-scrim.js did not attach window.HelmWxScrim');
  return { sandbox: sandbox, scrim: sandbox.HelmWxScrim, paints: paints };
}

ok('index.html: #wx-scrim checkbox present in the Weather drawer, checked by default', function () {
  var html = fs.readFileSync(path.join(WEB, 'index.html'), 'utf8');
  var drawer = html.slice(html.indexOf('id="drawer-weather"'), html.indexOf('id="drawer-download"'));
  assert.ok(/id="wx-scrim"/.test(drawer), '#wx-scrim checkbox missing from the Weather drawer');
  var m = drawer.match(/<input[^>]*id="wx-scrim"[^>]*>/);
  assert.ok(m, 'could not isolate the #wx-scrim input tag');
  assert.ok(/checked/.test(m[0]), '#wx-scrim must default to checked (dim is the pre-FUSE-3 behaviour)');
});

ok('sw.js still precaches wx-scrim.js', function () {
  assert.ok(/wx-scrim\.js/.test(fs.readFileSync(path.join(WEB, 'sw.js'), 'utf8')));
});

ok('scrim dims when weather is on and the checkbox is checked (default)', function () {
  var h = loadScrim({ 'wx-scrim': makeCheckbox(true) });
  h.sandbox.__activeWx = 'wind';
  h.paints.length = 0;
  h.scrim.reconcile();
  var navPaints = h.paints.filter(function (p) { return p.layerId === 'navionics'; });
  assert.ok(navPaints.length > 0, 'basemap raster should receive paint updates');
  var brightness = navPaints.find(function (p) { return p.prop === 'raster-brightness-max'; });
  assert.strictEqual(brightness.value, 0.42, 'checked + weather-on must apply the dim values');
});

ok('scrim stays off when the checkbox is unchecked, even with weather active', function () {
  var h = loadScrim({ 'wx-scrim': makeCheckbox(false) });
  h.sandbox.__activeWx = 'wind';
  h.paints.length = 0;
  h.scrim.reconcile();
  var navPaints = h.paints.filter(function (p) { return p.layerId === 'navionics'; });
  var brightness = navPaints.find(function (p) { return p.prop === 'raster-brightness-max'; });
  assert.strictEqual(brightness.value, 1, 'unchecked opt-out must keep the chart at normal brightness');
});

ok('toggling the checkbox live re-reconciles without a weather-button click', function () {
  var cb = makeCheckbox(false);
  var h = loadScrim({ 'wx-scrim': cb });
  h.sandbox.__activeWx = 'wind';
  h.scrim.reconcile();   // baseline: unchecked -> normal
  h.paints.length = 0;
  cb.checked = true;
  assert.ok(typeof cb._onchange === 'function', 'wire() must attach a change listener to #wx-scrim');
  cb._onchange();
  var navPaints = h.paints.filter(function (p) { return p.layerId === 'navionics'; });
  var brightness = navPaints.find(function (p) { return p.prop === 'raster-brightness-max'; });
  assert.strictEqual(brightness.value, 0.42, 'checking the box must immediately re-dim');
});

ok('missing checkbox (older markup) preserves always-on-when-active behaviour', function () {
  var h = loadScrim({});   // no 'wx-scrim' key at all
  assert.strictEqual(h.scrim.scrimEnabled(), true, 'scrimEnabled() must fail open when the control is absent');
  h.sandbox.__activeWx = 'rain';
  h.paints.length = 0;
  h.scrim.reconcile();
  var navPaints = h.paints.filter(function (p) { return p.layerId === 'navionics'; });
  var brightness = navPaints.find(function (p) { return p.prop === 'raster-brightness-max'; });
  assert.strictEqual(brightness.value, 0.42);
});

ok('weather raster (helm-wx- prefix) is never touched, checkbox state notwithstanding', function () {
  var h = loadScrim({ 'wx-scrim': makeCheckbox(true) });
  h.sandbox.__activeWx = 'wind';
  h.paints.length = 0;
  h.scrim.reconcile();
  assert.strictEqual(h.paints.filter(function (p) { return p.layerId === 'helm-wx-grid-0'; }).length, 0,
    'the active weather raster itself must never be dimmed');
  assert.strictEqual(h.paints.filter(function (p) { return p.layerId === 'route-line'; }).length, 0,
    'non-raster layers must never be touched');
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - fuse-3-wx-scrim-toggle: ' + pass + ' groups passed');
