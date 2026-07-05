// AIS flag country tooltip — hover title on the emoji flag in the tap card (ais-meta + ais-inspector).
const { test, expect } = require('@playwright/test');
const { boot, bootAis } = require('./_helpers');

const US_MMSI = 366123456;
const NZ_MMSI = 512000000;
const start = process.env.HELM_E2E_URL ? bootAis : boot;

test.describe('AIS flag country tooltip', () => {
  test('HelmAisMeta resolves MMSI MID to country name', async ({ page }) => {
    await start(page);
    const meta = await page.evaluate(() => ({
      us: window.HelmAisMeta.countryName(366123456),
      nz: window.HelmAisMeta.countryName(512000000),
      title: window.HelmAisMeta.flagTitleAttr(366123456),
      unknown: window.HelmAisMeta.countryName(999000000),
    }));
    expect(meta.us).toBe('United States');
    expect(meta.nz).toBe('New Zealand');
    expect(meta.title).toBe(' title="United States"');
    expect(meta.unknown).toBe('');
  });

  test('AIS tap card flag span carries the country title attribute', async ({ page }) => {
    await start(page);
    await page.evaluate(({ mmsi }) => {
      window.openAisCard({ mmsi, name: 'TEST VESSEL', sog: 5, cog: 90, cpaValid: false }, { x: 220, y: 180 });
    }, { mmsi: US_MMSI });
    const flag = page.locator('.helm-ais-card span[title="United States"]');
    await expect(flag).toBeVisible();
    await expect(flag).toHaveAttribute('title', 'United States');
  });

  test('New Zealand MMSI shows New Zealand on the card flag', async ({ page }) => {
    await start(page);
    await page.evaluate(({ mmsi }) => {
      window.openAisCard({ mmsi, name: 'KIWI', sog: 3, cog: 180, cpaValid: false }, { x: 220, y: 180 });
    }, { mmsi: NZ_MMSI });
    await expect(page.locator('.helm-ais-card span[title="New Zealand"]')).toBeVisible();
  });
});
