// TOOLS-1 — measure tool upgraded to keepable, editable, persisted planning lines.
// Drives the tool via map.fire('click') + ⏎ to finish, and the public api (window.__helmMeasure).
// Covers: finished lines are kept, multiple coexist, they survive closing the tool AND a reload,
// an unfinished line is dropped on close, and clearAll wipes them.
const { test, expect } = require('@playwright/test');
const { boot } = require('./_helpers');

const tap = (page, lng, lat) => page.evaluate(({ lng, lat }) => {
  const m = window.map; m.fire('click', { lngLat: { lng, lat }, point: m.project([lng, lat]), originalEvent: {} });
}, { lng, lat });
// the api's `lines` IS what build() renders, so count() reflects what's drawn on the chart
const renderedLines = (page) => page.evaluate(() => window.__helmMeasure.count());
const count = (page) => page.evaluate(() => window.__helmMeasure.count());
const stored = (page) => page.evaluate(() => (window.HelmStore.get('measure.lines', []) || []).length);

test.describe('TOOLS-1 — measure: keepable, editable, persisted lines', () => {
  test('finished lines are kept, multiple coexist, survive closing the tool AND a reload', async ({ page }) => {
    await boot(page);
    await page.evaluate(() => { window.HelmStore.set('measure.lines', []); window.map.jumpTo({ center: [0, 0], zoom: 5 }); window.__helmMeasure.setActive(true); });

    await tap(page, 0.10, 0.10); await tap(page, 0.30, 0.10); await page.keyboard.press('Enter');   // line 1
    expect(await count(page), 'line 1 saved on finish').toBe(1);

    await tap(page, 0.10, -0.20); await tap(page, 0.30, -0.20); await page.keyboard.press('Enter'); // line 2 (far away)
    expect(await count(page), 'multiple lines coexist').toBe(2);
    expect(await renderedLines(page), 'both drawn').toBe(2);
    expect(await stored(page), 'persisted to HelmStore').toBe(2);

    await page.evaluate(() => window.__helmMeasure.setActive(false));   // close the tool
    expect(await page.evaluate(() => window.__helmMeasure.active())).toBe(false);
    expect(await renderedLines(page), 'KEPT on the chart after closing the tool').toBe(2);

    await page.reload(); await boot(page);                              // reload
    expect(await stored(page), 'still persisted after reload').toBe(2);
    expect(await renderedLines(page), 'restored on the chart after reload').toBe(2);
  });

  test('an unfinished line is dropped on close; clearAll wipes saved lines', async ({ page }) => {
    await boot(page);
    await page.evaluate(() => { window.HelmStore.set('measure.lines', []); window.map.jumpTo({ center: [20, 20], zoom: 6 }); window.__helmMeasure.setActive(true); });

    await tap(page, 20.0, 20.0);                                        // a single point, not finished
    expect(await count(page)).toBe(1);
    await page.evaluate(() => window.__helmMeasure.setActive(false));
    expect(await count(page), 'unfinished 1-point line dropped on close').toBe(0);

    await page.evaluate(() => window.__helmMeasure.setActive(true));
    await tap(page, 20.0, 20.0); await tap(page, 20.2, 20.1); await page.keyboard.press('Enter');
    expect(await count(page)).toBe(1);
    await page.evaluate(() => window.__helmMeasure.clearAll());
    expect(await count(page)).toBe(0);
    expect(await stored(page)).toBe(0);
  });
});
