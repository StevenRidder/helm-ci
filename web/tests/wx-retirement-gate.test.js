// WX-35 retirement gate — the repo-grep proof, as a test so CI fails LOUDLY if a
// retired weather entrypoint creeps back. Retired by this gate:
//   - wx-live.js (gesture-fetching "Live · fills view" viewport path; zero call sites)
//   - the legacy data/wind.json particle autoload (404'd forever, raced the scene
//     with an empty-but-visible engine)
//   - client-side viewport materialize / hidden gateway substitution (removed by
//     WX-30; this pins them out)
// Prose/comments describing the retirement are allowed; executable references are not.
// Run: node web/tests/wx-retirement-gate.test.js
const fs = require('fs'), path = require('path');
const assert = require('assert');

const WEB = path.join(__dirname, '..');
let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}
const read = f => fs.readFileSync(path.join(WEB, f), 'utf8');
const webFiles = fs.readdirSync(WEB).filter(f => f.endsWith('.js') || f === 'index.html' || f === 'sw.js');

ok('wx-live.js is gone: no file, no script tag, no precache entry, no API calls', () => {
  assert.ok(!fs.existsSync(path.join(WEB, 'wx-live.js')), 'web/wx-live.js must not exist');
  assert.ok(!/<script[^>]*wx-live\.js/.test(read('index.html')), 'no script tag');
  assert.ok(!/wx-live\.js/.test(read('sw.js')), 'no service-worker precache entry');
  for (const f of webFiles) {
    const src = read(f);
    assert.ok(!/HelmWxLive\s*[.(]/.test(src), `executable HelmWxLive reference in ${f}`);
    assert.ok(!/window\.HelmWxLive/.test(src), `window.HelmWxLive reference in ${f}`);
  }
});

ok('legacy data/wind.json particle autoload is retired (scene owns particles)', () => {
  const html = read('index.html');
  assert.ok(!/wind\.load\(/.test(html), 'no legacy wind.load() in index.html');
  assert.ok(!/velUrl/.test(html), 'velUrl helper removed');
  assert.ok(!/data\/wind\.json/.test(html), 'no data/wind.json reference');
});

ok('no client-side viewport materialize or silent gateway substitution entrypoints', () => {
  for (const f of webFiles) {
    const src = read(f);
    assert.ok(!/materializeUrl|quantizeViewForMaterialize/.test(src), `viewport-materialize entrypoint in ${f}`);
    const noComments = src.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
    assert.ok(!/['"]force-cache['"]/.test(noComments), `range-unsafe force-cache in ${f}`);
  }
  // wx-controls' off-edge path must stay fail-loud (disabled plan), never a fetch
  const wc = read('wx-controls.js');
  assert.ok(/disabled:\s*true/.test(wc), 'ensureViewportBundle stays a disabled fail-loud plan');
});

ok('grid path is present and loud (the replacement actually exists)', () => {
  for (const f of ['wx-grid-pack-client.js', 'wx-grid-decode.js', 'wx-grid-scene.js']) {
    assert.ok(fs.existsSync(path.join(WEB, f)), f + ' present');
  }
  const scene = read('wx-grid-scene.js');
  assert.ok(/unsupported_renderer_capability/.test(scene), 'capability failures are loud');
  const sceneCode = scene.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
  assert.ok(!/8093|WX_SERVICE|gatewayFallback/.test(sceneCode), 'grid scene has no gateway/service fallback code');
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - wx-retirement-gate: ' + pass + ' groups passed');
