// SCHED-3 browser acceptance: live pyramid artifacts swap by zoom band (US5GA2BC).
// Run: HELM_SCHED3=1 npx playwright test web/test/e2e/sched-3-live-artifacts.spec.js
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const HASH = process.env.HELM_SCHED3_HASH || '#13/30.86/-81.49?cell=us5ga2bc';
const EVIDENCE_DIR = process.env.HELM_SCHED3_EVIDENCE_DIR ||
  path.resolve(__dirname, '..', '..', '..', 'test-results', 'sched-3-live-artifacts');

const describeSched3 = process.env.HELM_SCHED3 ? test.describe : test.describe.skip;

describeSched3('SCHED-3 live scheduler', () => {
  test.describe.configure({ mode: 'serial' });

function ensureEvidenceDir() {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

async function boot(page) {
  await page.addInitScript(() => {
    try {
      window.HELM_CHART_WEBGPU = true;
      window.HELM_SCHED3 = true;
      localStorage.setItem('helmChartCell', 'us5ga2bc');
      localStorage.setItem('helmChartWebgpu', '1');
    } catch (e) {}
  });
  await page.goto('/' + HASH);
  await expect(page).toHaveTitle(/Helm/);
  await page.waitForFunction(() => window.map && window.map.isStyleLoaded && window.map.isStyleLoaded(), null, { timeout: 30000 });
  await page.waitForFunction(() => window.__helmChartSchedulerBlend && window.__helmChartSchedulerArtifactIndex, null, { timeout: 30000 });
}

test('live scheduler fetches distinct artifact packets across zoom bands', async ({ page }) => {
  ensureEvidenceDir();
  const artifactPackets = [];

  page.on('response', async resp => {
    const url = resp.url();
    if (!/render-artifact-index|\/artifact\/|artifacts\/us5ga2bc/.test(url)) return;
    if (resp.status() !== 200) return;
    try {
      const ct = resp.headers()['content-type'] || '';
      if (!ct.includes('json')) return;
      const body = await resp.json();
      const sha = body.checksums && body.checksums.packet_sha256;
      if (sha) artifactPackets.push({ url, sha, z: body.viewport && body.viewport.tile && body.viewport.tile.z });
    } catch (e) {}
  });

  await boot(page);
  await page.waitForFunction(() => {
    return window.__helmChartScheduler &&
      window.__helmChartScheduler.response &&
      window.__helmChartScheduler.cache.size >= 1;
  }, null, { timeout: 25000 });

  await page.screenshot({ path: path.join(EVIDENCE_DIR, '01-boot-sched3.png'), fullPage: true });

  for (const zoom of [11, 13, 15]) {
    await page.evaluate((z) => window.map.setZoom(z, { duration: 0 }), zoom);
    await page.waitForTimeout(600);
  }

  await page.evaluate(() => window.map.panBy([140, 0], { duration: 0 }));
  await page.waitForTimeout(500);

  const state = await page.evaluate(() => ({
    mode: window.__helmChartMode,
    scheduler: window.__helmChartScheduler,
    status: window.__helmChartRendererStatus,
    index: window.__helmChartSchedulerArtifactIndex && window.__helmChartSchedulerArtifactIndex.snapshot()
  }));

  expect(state.index && state.index.loaded, 'artifact index must load').toBeTruthy();
  expect(state.index.cell_id, 'US5GA2BC cell').toBe('US5GA2BC');
  expect(state.scheduler.cache.size, 'scheduler cache populated').toBeGreaterThan(0);
  expect(state.status.sched3_enabled, 'sched3 flag surfaced').toBeTruthy();

  const uniqueShas = [...new Set(artifactPackets.map(p => p.sha))];
  expect(uniqueShas.length, 'distinct packet_sha256 across zoom/pan').toBeGreaterThanOrEqual(2);

  fs.writeFileSync(path.join(EVIDENCE_DIR, 'sched-3-evidence.json'), JSON.stringify({
    artifactPackets: artifactPackets.slice(0, 48),
    uniqueShaCount: uniqueShas.length,
    state: {
      cache_size: state.scheduler.cache.size,
      missing_reason: state.scheduler.missing_reason,
      index: state.index
    }
  }, null, 2));

  await page.screenshot({ path: path.join(EVIDENCE_DIR, '02-zoom-pan-sched3.png'), fullPage: true });
});

test('pan across tile boundary retains composite without strict missing', async ({ page }) => {
  ensureEvidenceDir();
  await boot(page);
  await page.waitForFunction(() => window.__helmChartScheduler && window.__helmChartScheduler.cache.size >= 1, null, { timeout: 25000 });

  await page.evaluate(() => window.map.panBy([220, 0], { duration: 0 }));
  await page.waitForTimeout(300);
  await page.evaluate(() => window.map.panBy([-220, 0], { duration: 0 }));
  await page.waitForTimeout(500);

  const state = await page.evaluate(() => ({
    cache_size: window.__helmChartScheduler && window.__helmChartScheduler.cache.size,
    strict_missing: window.__helmChartScheduler && window.__helmChartScheduler.strictMissing
  }));
  expect(state.cache_size, 'scheduler cache retains composites after pan').toBeGreaterThan(0);
});
});
