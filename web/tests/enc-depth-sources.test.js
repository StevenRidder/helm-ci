// Unit smoke for web/enc-depth-sources.js (ENC-4 user-data depth preference).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function load(fetchImpl, getImpl) {
  const heads = new Set([
    'user-data/depare.geojson', 'user-data/depcnt.geojson', 'user-data/soundg.geojson',
    'user-data/depth-provenance.json'
  ]);
  const getFn = getImpl || function (url) {
    if (url === 'user-data/depth-provenance.json') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ source: 'enc', cell: 'US5FL4CR' })
      });
    }
    return Promise.resolve({ ok: false });
  };
  const fetchFn = fetchImpl || function (url, init) {
    if (init && init.method === 'HEAD') return Promise.resolve({ ok: heads.has(url) });
    if (url === 'user-data/depth-provenance.json') return getFn(url);
    return Promise.resolve({ ok: heads.has(url) });
  };
  const win = { fetch: fetchFn, document: { getElementById: () => null } };
  const sandbox = { window: win, document: win.document, console, fetch: fetchFn };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'enc-depth-sources.js'), 'utf8'), sandbox, { filename: 'enc-depth-sources.js' });
  return win;
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const win = load();
  const style = {
    sources: {
      depare: { type: 'geojson', data: 'data/depare.geojson' },
      depcnt: { type: 'geojson', data: 'data/depcnt.geojson' },
      soundg: { type: 'geojson', data: 'data/soundg.geojson' }
    }
  };
  win.HelmEncDepthSources.preferUserDepthData(style).then(function (st) {
    ok(style.sources.depare.data === 'user-data/depare.geojson', 'depare prefers user-data');
    ok(style.sources.soundg.data === 'user-data/soundg.geojson', 'soundg prefers user-data');
    ok(st.mode === 'enc' && st.cell === 'US5FL4CR', 'status mode enc with cell');
    ok(win.HelmEncDepthSources.summary().mode === 'enc', 'summary enc');
  });
}

{
  const win = load(function (url, init) {
    if (init && init.method === 'HEAD') return Promise.resolve({ ok: false });
    return Promise.resolve({ ok: false });
  });
  const style = { sources: { depare: { type: 'geojson', data: 'data/depare.geojson' } } };
  win.HelmEncDepthSources.preferUserDepthData(style).then(function (st) {
    ok(style.sources.depare.data === 'data/depare.geojson', 'falls back to demo data/');
    ok(st.mode === 'demo', 'status mode demo');
    ok(win.HelmEncDepthSources.summary().css === 'warn', 'demo summary warns');
  });
}

setTimeout(function () {
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
}, 50);
