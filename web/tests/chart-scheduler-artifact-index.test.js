// SCHED-3 unit test: artifact index resolver maps tiles to packet URLs.
// Run: node web/tests/chart-scheduler-artifact-index.test.js
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const index = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'data', 'render-artifact-index-us5ga2bc.json'), 'utf8'));

function loadIndexModule() {
  const ctx = { console, fetch: null };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(
    path.join(__dirname, '..', 'chart-scheduler-artifact-index.js'), 'utf8'), ctx);
  return ctx;
}

async function main() {
  let pass = 0;
  async function ok(name, fn) {
    try {
      await fn();
      pass++;
      console.log('  ok - ' + name);
    } catch (e) {
      console.error('  FAIL - ' + name + ': ' + e.message);
      process.exitCode = 1;
    }
  }

  await ok('load ingests index and resolves server + static URLs', async () => {
    const ctx = loadIndexModule();
    ctx.fetch = (url) => Promise.resolve({
      ok: true,
      json: () => Promise.resolve(index)
    });
    const idx = new ctx.HelmChartSchedulerArtifactIndex({ indexUrl: '/artifact/index.json' });
    const loaded = await idx.load();
    assert.strictEqual(loaded.cell_id, 'US5GA2BC');
    assert.strictEqual(idx.lookup({ z: 11, x: 560, y: 839 }).packet_sha256.length, 64);
    assert.strictEqual(idx.urlForTile({ z: 11, x: 560, y: 839 }), '/artifact/11/560/839.json');
  });

  await ok('static fallback uses committed artifact_url paths', async () => {
    const ctx = loadIndexModule();
    ctx.fetch = (url) => Promise.resolve({
      ok: url.includes('data/'),
      status: url.includes('data/') ? 200 : 404,
      json: () => Promise.resolve(index)
    });
    const idx = new ctx.HelmChartSchedulerArtifactIndex({
      indexUrl: '/artifact/index.json',
      staticFallbackUrl: 'data/render-artifact-index-us5ga2bc.json'
    });
    await idx.load();
    const url = idx.urlForTile({ z: 12, x: 1120, y: 1678 });
    assert.strictEqual(url, 'data/artifacts/us5ga2bc/z12/x1120/y1678.json');
    assert.strictEqual(idx.snapshot().use_server_urls, false);
  });

  await ok('lookup returns null for tiles outside pyramid', async () => {
    const ctx = loadIndexModule();
    ctx.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(index) });
    const idx = new ctx.HelmChartSchedulerArtifactIndex({ indexUrl: '/artifact/index.json' });
    await idx.load();
    assert.strictEqual(idx.lookup({ z: 16, x: 0, y: 0 }), null);
  });

  console.log('\n' + pass + ' passed');
}

main();
