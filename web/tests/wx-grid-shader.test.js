// WX-33 unit test: the WGSL specialization in wx-grid-scene.js is string surgery —
// pin that the emitted shader is well-formed before a GPU ever sees it.
// Run: node web/tests/wx-grid-shader.test.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const assert = require('assert');

const win = { console, setTimeout, clearTimeout };
win.window = win;
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'wx-grid-scene.js'), 'utf8'), vm.createContext(win));

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

const src = win.HelmWxGrid._test.buildShader();

ok('specialized taps exist and generic template is gone', () => {
  assert.ok(src.includes('fn tapA('), 'tapA present');
  assert.ok(src.includes('fn tapB('), 'tapB present');
  assert.ok(src.includes('fn sampleFrame('), 'dispatch present');
  assert.ok(!src.includes('fn tap(t:'), 'generic tap removed');
  assert.ok(!src.includes('fA_or'), 'placeholder resolved');
});

ok('taps reference their own frame textures', () => {
  const tapA = src.slice(src.indexOf('fn tapA('), src.indexOf('fn tapB('));
  const tapB = src.slice(src.indexOf('fn tapB('), src.indexOf('fn sampleFrame('));
  assert.ok(/textureLoad\(fA,/.test(tapA) && !/textureLoad\(fB,/.test(tapA), 'tapA loads fA only');
  assert.ok(/textureLoad\(fB,/.test(tapB) && !/textureLoad\(fA,/.test(tapB), 'tapB loads fB only');
});

ok('shader keeps the contract semantics markers', () => {
  assert.ok(src.includes('mix(a.xy, b.xy, u.frac)'), 'values lerped before colourization');
  assert.ok(src.includes('c.rgb*alpha, alpha'), 'premultiplied output');
  assert.ok(src.includes('1e29'), 'NODATA sentinel honoured');
  assert.ok(src.includes('u.opacity*valid'), 'opacity scales alpha only, invalid -> transparent');
});

ok('balanced braces (rough syntax sanity)', () => {
  const open = (src.match(/{/g) || []).length, close = (src.match(/}/g) || []).length;
  assert.strictEqual(open, close, 'brace balance ' + open + '/' + close);
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - wx-grid-shader: ' + pass + ' groups passed');
