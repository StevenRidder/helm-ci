// Manual/regression proof: real NOAA ENC depth-on-sat at Dinner Key, Miami.
// Requires helm-server with US5MIABB + ~/.helm/data depth extract on HELM_E2E_URL.
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { clickRail, bootHarbour } = require('./_harbour-helpers');

const ENABLED = !!process.env.HELM_MIAMI_PROOF;
const HASH = process.env.HELM_MIAMI_HASH || '#14/25.706/-80.224';
const OUT = process.env.HELM_MIAMI_EVIDENCE_DIR || '/tmp/helm-miami-dinner-key';

test.skip(!ENABLED, 'Set HELM_MIAMI_PROOF=1 and point HELM_E2E_URL at Miami helm-server.');

test('Dinner Key depth-on-sat over satellite with US5MIABB ENC depth', async ({ page }) => {
  fs.mkdirSync(OUT, { recursive: true });
  await bootHarbour(page, { hash: HASH, waitRendererStatus: false });
  await clickRail(page, 'layers');
  await page.locator('[data-fusion-preset="depth-on-sat"]').click();
  await page.waitForTimeout(2500);

  const state = await page.evaluate(() => ({
    preset: window.HelmFusionPresets && HelmFusionPresets.readActive(),
    satVis: window.map.getLayer('googlesat')
      ? window.map.getLayoutProperty('googlesat', 'visibility')
      : 'missing',
    depareVis: window.map.getLayer('depare-fill')
      ? window.map.getLayoutProperty('depare-fill', 'visibility')
      : 'missing',
    encVis: window.map.getLayer('enc-chart')
      ? window.map.getLayoutProperty('enc-chart', 'visibility')
      : 'missing',
    depthHits: window.map.queryRenderedFeatures(undefined, {
      layers: ['depare-fill', 'depcnt-line', 'soundg-text'].filter(id => window.map.getLayer(id))
    }).length,
    center: window.map.getCenter().toArray(),
    zoom: window.map.getZoom(),
    depthProv: window.HelmEncDepthSources && HelmEncDepthSources.status
      ? window.HelmEncDepthSources.status()
      : null
  }));

  expect(state.preset).toBe('depth-on-sat');
  expect(state.satVis, 'satellite basemap stays visible under the depth vectors').toBe('visible');
  expect(state.depareVis).toBe('visible');
  expect(state.encVis).toBe('none');
  expect(state.depthProv && state.depthProv.mode).toBe('enc');
  expect(state.depthProv && state.depthProv.cell).toBe('US5MIABB');
  expect(state.depthHits, 'Miami ENC depth should render over satellite at Dinner Key').toBeGreaterThan(0);

  await page.screenshot({ path: path.join(OUT, 'miami-dinner-key-depth-on-sat.png'), fullPage: false });
  fs.writeFileSync(path.join(OUT, 'state.json'), JSON.stringify(state, null, 2));
});
