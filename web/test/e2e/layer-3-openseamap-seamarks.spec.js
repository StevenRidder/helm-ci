// LAYER-3: OpenSeaMap seamarks overlay (ODbL attribution). Static raster overlay in the
// FUSE-2 "overlay" band (web/style/helm-layer-seamarks.json), toggled by index.html's
// generic data-layer checkbox handler. Real tiles.openseamap.org requests are intercepted
// so this runs offline/deterministically in CI.
const { test, expect } = require('@playwright/test');
const { bootHarbour, clickRail, attachHarbourDiagnostics } = require('./_harbour-helpers');

test('OpenSeaMap seamarks overlay is off by default, toggles on, and carries ODbL attribution', async ({ page }) => {
  const diag = { console: [], pageErrors: [], failedRequests: [] };
  attachHarbourDiagnostics(page, diag);

  const seamarkRequests = [];
  await page.route('https://tiles.openseamap.org/**', (route) => {
    seamarkRequests.push(route.request().url());
    route.fulfill({
      contentType: 'image/png',
      body: Buffer.from('89504e470d0a1a0a', 'hex')
    });
  });

  await bootHarbour(page, { waitRendererStatus: false });

  const initial = await page.evaluate(() => ({
    hasLayer: !!window.map.getLayer('openseamap-seamarks'),
    visibility: window.map.getLayer('openseamap-seamarks')
      ? window.map.getLayoutProperty('openseamap-seamarks', 'visibility')
      : 'missing',
    tiles: window.map.getSource('openseamap-seamarks') && window.map.getSource('openseamap-seamarks').tiles,
    checked: document.querySelector('input[data-layer="openseamap-seamarks"]').checked
  }));
  expect(initial.hasLayer, 'openseamap-seamarks layer is present in the merged style').toBe(true);
  expect(initial.visibility, 'seamarks overlay defaults to hidden (internet-dependent)').toBe('none');
  expect(initial.tiles).toEqual(['https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png']);
  expect(initial.checked, 'checkbox reflects the hidden default').toBe(false);

  await clickRail(page, 'layers');
  await page.locator('input[data-layer="openseamap-seamarks"]').click();

  await page.waitForFunction(
    () => window.map.getLayoutProperty('openseamap-seamarks', 'visibility') === 'visible',
    null,
    { timeout: 5000 }
  );

  await expect.poll(() => seamarkRequests.length, {
    message: 'toggling the overlay on should fetch OpenSeaMap seamark tiles',
    timeout: 10000
  }).toBeGreaterThan(0);
  expect(seamarkRequests[0]).toMatch(/^https:\/\/tiles\.openseamap\.org\/seamark\/\d+\/\d+\/\d+\.png$/);

  const attribution = await page.locator('.maplibregl-ctrl-attrib').innerText();
  expect(attribution).toContain('OpenSeaMap seamarks');
  expect(attribution).toContain('ODbL');

  // Toggle back off — layer stays registered, just hidden again.
  await page.locator('input[data-layer="openseamap-seamarks"]').click();
  await page.waitForFunction(
    () => window.map.getLayoutProperty('openseamap-seamarks', 'visibility') === 'none',
    null,
    { timeout: 5000 }
  );

  expect(diag.pageErrors, 'no uncaught page errors while toggling the seamarks overlay').toEqual([]);
});
