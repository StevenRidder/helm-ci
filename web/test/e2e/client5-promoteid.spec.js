// CLIENT-5 validation — stable AIS feature ids. The `ais` source is promoteId:'mmsi' so each target's
// feature.id == its MMSI: a stable id for tap hit-testing and (future) incremental updates / feature-state.
const { test, expect } = require('@playwright/test');
const { boot } = require('./_helpers');

test.describe('CLIENT-5 — stable AIS feature ids (promoteId: mmsi)', () => {
  test('the ais source declares promoteId: mmsi', async ({ page }) => {
    await boot(page);
    const src = await page.evaluate(() => window.map.getStyle().sources.ais);
    expect(src.promoteId, 'ais promoteId = mmsi').toBe('mmsi');
  });

  test('promoteId surfaces mmsi as feature.id', async ({ page }) => {
    await boot(page);
    await page.evaluate(() => {
      window.map.jumpTo({ center: [177.4, -17.8], zoom: 10 });
      window.map.getSource('ais').setData({
        type: 'FeatureCollection',
        features: [{ type: 'Feature', properties: { mmsi: 244660000, name: 'TESTBOAT' },
          geometry: { type: 'Point', coordinates: [177.4, -17.8] } }],
      });
    });
    await page.waitForFunction(
      () => window.map.querySourceFeatures('ais').some((x) => x.properties && x.properties.mmsi === 244660000),
      null, { timeout: 8000 });
    const idIsMmsi = await page.evaluate(() => {
      const f = window.map.querySourceFeatures('ais').find((x) => x.properties && x.properties.mmsi === 244660000);
      return !!f && String(f.id) === '244660000';
    });
    expect(idIsMmsi, 'feature.id === mmsi (promoteId active)').toBe(true);
  });
});
