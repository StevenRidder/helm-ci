// INTEGRATE-1 browser acceptance: explicit feature flag, visible status, no silent fallback.
// Run: HELM_INTEGRATE1=1 npx playwright test web/test/e2e/integrate-1-chart-renderer.spec.js
const { test, expect } = require('@playwright/test');
const { boot } = require('./_helpers');

test.skip(!process.env.HELM_INTEGRATE1, 'Set HELM_INTEGRATE1=1 to run the chart renderer integration proof.');

test('default boot makes WebGPU the primary renderer with a visible status surface (kill legacy)', async ({ page }) => {
  await boot(page);
  await page.waitForFunction(() => window.__helmChartRendererStatus, null, { timeout: 15000 });

  const status = await page.evaluate(() => window.__helmChartRendererStatus);
  // Default-on (INTEGRATE-1 "kill legacy"): the WebGPU path is enabled with no opt-in.
  expect(status.feature_flag.enabled).toBe(true);
  // WebGPU is primary where the browser supports it; any fallback must carry a real capability
  // reason (never a silent or "disabled" opt-in gate) so we can see if the new path works.
  if (status.active_renderer === 'maplibre') {
    expect(status.fallback_reason.length).toBeGreaterThan(0);
    expect(status.fallback_reason.toLowerCase()).not.toContain('disabled');
  } else {
    expect(status.active_renderer).toBe('webgpu');
  }

  await expect(page.locator('#chart-renderer-badge')).toBeVisible();

  await page.locator('.ri[data-rail="settings"]').click();
  await expect(page.locator('#chart-renderer-settings-host')).toContainText('WebGPU nautical renderer');
  await expect(page.locator('#chart-renderer-flag')).toBeChecked();
});

test('explicit opt-out (helmChartWebgpu=0) shows the visible MapLibre legacy fallback', async ({ page }) => {
  await page.addInitScript(() => {
    try { window.localStorage.setItem('helmChartWebgpu', '0'); } catch (e) {}
  });
  await boot(page);
  await page.waitForFunction(() => window.__helmChartRendererStatus, null, { timeout: 15000 });

  const status = await page.evaluate(() => window.__helmChartRendererStatus);
  expect(status.feature_flag.enabled).toBe(false);
  expect(status.active_renderer).toBe('maplibre');
  expect(status.fallback_reason.length).toBeGreaterThan(0);
  await expect(page.locator('#chart-renderer-badge-txt')).toHaveText('ENC');
});

test('status panel reports renderer schema and chart epoch after artifact load', async ({ page }) => {
  await page.addInitScript(() => {
    try { window.localStorage.setItem('helmChartWebgpu', '1'); } catch (e) {}
  });
  await boot(page);
  await page.waitForFunction(() => {
    return window.__helmChartRendererStatus &&
      window.__helmChartRendererStatus.artifact &&
      window.__helmChartRendererStatus.artifact.schema_version;
  }, null, { timeout: 20000 });

  await page.locator('.ri[data-rail="helm-client-health"]').click();
  const panel = page.locator('#helm-client-health');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('Chart Renderer');
  await expect(panel).toContainText('helm.render.artifact.v1');
  await expect(panel).toContainText('synthetic-chart-1@2026-06-28');
});
