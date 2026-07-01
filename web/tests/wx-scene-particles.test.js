// WX-25 fail-loud unit test: particle-path health is a real, surfaced signal —
// data-reason offs warn (once per transition) and flag the badge; intentional
// offs don't. Run: node web/tests/wx-scene-particles.test.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const assert = require('assert');

const code = fs.readFileSync(path.join(__dirname, '..', 'wx-scene.js'), 'utf8');
const warns = [];
const win = {
  console: { warn: (...a) => warns.push(a.join(' ')), log: () => {}, info: () => {}, error: () => {} },
  setTimeout, clearTimeout, setInterval, clearInterval,
  document: { getElementById: () => null, createElement: () => ({ style: {} }), body: { appendChild: () => {} } }
};
win.window = win;
vm.runInContext(code, vm.createContext(win));
const S = win.HelmWxScene;

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

ok('data-reason off is surfaced in state + warns once per transition', () => {
  warns.length = 0;
  S._setParticleState(false, 'outside-coverage');
  assert.strictEqual(S.state.particles.active, false);
  assert.strictEqual(S.state.particles.reason, 'outside-coverage');
  S._setParticleState(false, 'outside-coverage');            // same reason -> no repeat spam
  assert.strictEqual(warns.filter(w => w.includes('particles OFF')).length, 1);
  S._setParticleState(false, 'no-vector-data');              // new reason -> new warn
  assert.strictEqual(warns.filter(w => w.includes('particles OFF')).length, 2);
  assert.ok(warns[0].includes('outside-coverage') && warns[0].includes('retries'));
});

ok('recovery clears the warning state', () => {
  S._setParticleState(true, 'ok');
  assert.strictEqual(S.state.particles.active, true);
  assert.strictEqual(S.state.particles.reason, 'ok');
  assert.strictEqual(S._particleWarn({ particles: S.state.particles }), false);
});

ok('particleWarn flags data reasons, not scalar-only layers', () => {
  assert.strictEqual(S._particleWarn({ particles: { active: false, reason: 'outside-coverage' } }), true);
  assert.strictEqual(S._particleWarn({ particles: { active: false, reason: 'build-failed: boom' } }), true);
  assert.strictEqual(S._particleWarn({ particles: { active: false, reason: 'no-vector-field' } }), false);  // rain etc: normal
  assert.strictEqual(S._particleWarn({ particles: null }), false);
});

ok('particleMsg is specific, and build errors pass through verbatim', () => {
  assert.ok(/outside prepared bundle/.test(S._particleMsg('outside-coverage')));
  assert.ok(/no vector data/.test(S._particleMsg('no-vector-data')));
  assert.strictEqual(S._particleMsg('build-failed: tex alloc'), 'build-failed: tex alloc');
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - wx-scene-particles: ' + pass + ' groups passed');
