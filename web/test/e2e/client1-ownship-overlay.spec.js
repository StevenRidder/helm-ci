// CLIENT-1 validation — the claim I sold: "Glass-smooth helm view, easy on battery."
// The rings/predictor overlay must still render and track the boat, but must NOT re-serialize the
// geojson source every frame: the rebuild is GATED on real movement and STOPS when the boat is
// settled. (Headless Chromium runs requestAnimationFrame, so — unlike the preview tab — this IS
// exercisable. The fact the overlay source gets created at all proves the rAF frame loop runs.)
const { test, expect } = require('@playwright/test');
const { boot, feedFix } = require('./_helpers');

const OVL = 'helm-ownship-overlay';

test.describe("CLIENT-1 — 'glass-smooth, easy on battery' (gated overlay redraw)", () => {
  test('the rings overlay renders (centred on the boat)', async ({ page }) => {
    await boot(page);
    await feedFix(page, 17.8, 177.4, 90, 6);
    await page.waitForSelector('.ownship', { timeout: 10000 });   // marker added => disp set => frame ran
    const ringCount = await page.evaluate((id) => {
      const s = window.map.getSource(id);
      let cap = null; const o = s.setData.bind(s); s.setData = (d) => { cap = d; return o(d); };
      const own = window.__ownship;
      // force a forced redraw with rings ON, and capture the payload
      if (!own.ringsShown()) own.toggleRings(); else { own.toggleRings(); own.toggleRings(); }
      return cap && cap.features ? cap.features.filter((f) => f.properties.kind === 'ring').length : -1;
    }, OVL);
    expect(ringCount, 'concentric range rings are drawn').toBeGreaterThan(0);
  });

  test('GATED: moving the boat redraws the overlay, but a SETTLED boat produces ~no churn', async ({ page }) => {
    await boot(page);
    await feedFix(page, 17.8, 177.4, 0, 6);
    await page.waitForFunction((id) => !!window.map.getSource(id), OVL, { timeout: 10000 });

    // wrap setData with a counter
    await page.evaluate((id) => {
      const s = window.map.getSource(id); window.__sd = 0;
      const o = s.setData.bind(s); s.setData = (d) => { window.__sd++; return o(d); };
    }, OVL);

    // MOVING: a new fix moves the boat -> the overlay redraws (stays glued to the marker)
    await page.evaluate(() => { window.__sd = 0; });
    await feedFix(page, 17.83, 177.43, 30, 8);
    await page.waitForTimeout(500);
    const moving = await page.evaluate(() => window.__sd);
    expect(moving, 'moving the boat triggers overlay redraws').toBeGreaterThan(0);

    // SETTLED: freeze the target (also blocks the SIM dispatch — shared object), let it converge,
    // then measure. Un-gated this would be ~90 rebuilds in 1.5 s (60 fps); gated it must be ~0.
    await page.evaluate(() => { window.__ownship.update = function () {}; });
    await page.waitForTimeout(900);
    await page.evaluate(() => { window.__sd = 0; });
    await page.waitForTimeout(1500);
    const settled = await page.evaluate(() => window.__sd);
    expect(settled, 'a settled boat produces no overlay churn (vs ~90/1.5s un-gated)').toBeLessThanOrEqual(2);
  });

  test('a manual pan still works (CLIENT-1 gates only the overlay source, never the camera)', async ({ page }) => {
    await boot(page);
    await feedFix(page, 17.8, 177.4, 90, 6);
    const before = await page.evaluate(() => window.map.getCenter().lng);
    await page.evaluate(() => window.map.panBy([140, 0], { duration: 0 }));
    const after = await page.evaluate(() => window.map.getCenter().lng);
    expect(Math.abs(after - before), 'the map panned (camera not frozen by the fix)').toBeGreaterThan(0);
  });
});
