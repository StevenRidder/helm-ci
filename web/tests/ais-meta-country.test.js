// AIS flag country tooltip — MID -> ISO -> display name.
// Run: node web/tests/ais-meta-country.test.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const assert = require('assert');

function loadMeta(extra) {
  const code = fs.readFileSync(path.join(__dirname, '..', 'ais-meta.js'), 'utf8');
  const win = Object.assign({ console }, extra || {});
  win.window = win;
  vm.runInContext(code, vm.createContext(win));
  return win.HelmAisMeta;
}

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

ok('US MMSI resolves to United States', () => {
  const m = loadMeta();
  assert.strictEqual(m.countryCode(366123456), 'US');
  assert.strictEqual(m.countryName(366123456), 'United States');
  assert.match(m.flagTitleAttr(366123456), /title="United States"/);
});

ok('NZ MMSI resolves to New Zealand', () => {
  const m = loadMeta();
  assert.strictEqual(m.countryName(512000000), 'New Zealand');
});

ok('unknown MID yields empty country + no title attr', () => {
  const m = loadMeta();
  assert.strictEqual(m.countryName(999000000), '');
  assert.strictEqual(m.flagTitleAttr(999000000), '');
});

console.log('\n' + pass + ' passed');
