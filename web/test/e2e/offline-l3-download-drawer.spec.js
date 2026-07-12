// OFFLINE-L-3: the download drawer's sat-first live size estimate.
//
// Lasso an area -> GET helm-packd /bundle?profile=sat_first -> render the real size estimate and a
// per-layer breakdown. The point of this task is an HONEST estimate: when there is no satellite
// basemap for the area (missing_basemap) or the pack server is unreachable, the drawer says so —
// it never shows a fabricated number. helm-packd is mocked on the basemap port via page.route.
const { test, expect } = require('@playwright/test');

const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
  'base64'
);
const FIJI_BBOX = [178.0, -18.0, 178.5, -17.5];
const MB = 1024 * 1024;

function satFirstBundle() {
  return {
    schema: 'helm.region_bundle.manifest.v1',
    profile: 'sat_first',
    id: 'local-region',
    title: 'Local Region Bundle',
    summary: { roles: { basemap: 1, depth: 1 }, prefetch_tiles: 1280, estimated_bytes: 47 * MB },
    components: [
      {
        id: 'pack:fiji-sat', pack_id: 'fiji-sat', role: 'basemap', primary: true,
        kind: 'satellite', type: 'raster', container: 'pmtiles', title: 'Fiji offline satellite',
        prefetch: { tile_count: 1180, estimated_bytes: 44 * MB }
      },
      {
        id: 'depth:fiji-depare', dataset_id: 'fiji-depare', role: 'depth', title: 'Fiji depth',
        prefetch: { tile_count: 100, estimated_bytes: 3 * MB }
      }
    ]
  };
}

function json(body, status) {
  return {
    status: status || 200,
    headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*' },
    body: JSON.stringify(body)
  };
}

async function boot(page) {
  await page.addInitScript(() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} });
  // Registered first => lowest precedence: any pack-port request that isn't catalog/bundle is a tile.
  await page.route(/https?:\/\/[^/]+:9101\//, route => route.fulfill({
    status: 200, headers: { 'content-type': 'image/png', 'access-control-allow-origin': '*' }, body: PNG_1X1
  }));
  await page.route(/\/chart\/\d+\/\d+\/\d+\.png$/, route => route.fulfill({
    status: 200, headers: { 'content-type': 'image/png' }, body: PNG_1X1
  }));
  await page.route(/https?:\/\/[^/]+:9101\/catalog$/, route => route.fulfill(json({
    'fiji-sat': {
      id: 'fiji-sat', title: 'Fiji offline satellite', kind: 'satellite', type: 'raster',
      container: 'pmtiles', format: 'jpg', minzoom: 0, maxzoom: 14,
      bounds_array: [176.8, -19.2, 180.0, -16.0], size_bytes: 2450000000, license: 'test-fixture'
    }
  })));
  await page.goto('/?basemapPort=9101#9/-17.75/178.12');
  await expect(page).toHaveTitle(/Helm/);
  // The download drawer mounts independently of the map (we drive setBbox directly, not "use current
  // view"), so gate only on the drawer being ready — no dependency on live basemap/style loading.
  await page.waitForFunction(() => !!window.HelmDownloadDrawer, null, { timeout: 20000 });
}

async function openDrawer(page) {
  await page.locator('[data-rail="download"]').click();
  await expect(page.locator('#drawer-download')).toBeVisible();
}

test('renders a live sat-first size estimate from the pack server /bundle', async ({ page }) => {
  await boot(page);
  let requested = '';
  await page.route(/https?:\/\/[^/]+:9101\/bundle/, route => {
    requested = route.request().url();
    return route.fulfill(json(satFirstBundle()));
  });
  await openDrawer(page);
  await page.evaluate(b => window.HelmDownloadDrawer.setBbox(b), FIJI_BBOX);

  const est = page.locator('[data-testid="dl-estimate"]');
  await expect(est).toContainText('47 MB');     // from summary.estimated_bytes
  await expect(est).toContainText('tiles');
  await expect(est).not.toContainText('unavailable');

  const breakdown = page.locator('[data-testid="dl-breakdown"]');
  await expect(breakdown).toContainText('★');           // primary basemap marker
  await expect(breakdown).toContainText('satellite');
  await expect(breakdown).toContainText('depth');
  await expect(page.locator('[data-testid="dl-error"]')).toBeHidden();

  // handoff command builds the sat-first manifest (OFFLINE-L-2 bakes the tiles)
  await expect(page.locator('.dl-cmd')).toContainText('region_bundle.py');
  await expect(page.locator('.dl-cmd')).toContainText('--profile sat_first');

  // the request actually asked packd for the sat-first profile over the lassoed bbox
  expect(requested).toContain('profile=sat_first');
  expect(requested).toContain('bbox=178');
});

test('shows an honest missing_basemap error instead of a fabricated estimate', async ({ page }) => {
  await boot(page);
  await page.route(/https?:\/\/[^/]+:9101\/bundle/, route => route.fulfill(json({
    error: 'missing_basemap',
    message: 'missing_basemap: sat-first bundle requires a basemap component',
    profile: 'sat_first'
  }, 422)));
  await openDrawer(page);
  await page.evaluate(b => window.HelmDownloadDrawer.setBbox(b), FIJI_BBOX);

  const err = page.locator('[data-testid="dl-error"]');
  await expect(err).toBeVisible();
  await expect(err).toHaveAttribute('data-error-code', 'missing_basemap');
  await expect(err).toContainText(/satellite/i);
  await expect(err).toContainText('OFFLINE-L-2');

  const est = page.locator('[data-testid="dl-estimate"]');
  await expect(est).toContainText('unavailable');
  await expect(est).not.toContainText('MB');           // no fake number
});

test('fails loud when the pack server is unreachable (no silent estimate)', async ({ page }) => {
  await boot(page);
  await page.route(/https?:\/\/[^/]+:9101\/bundle/, route => route.abort());
  await openDrawer(page);
  await page.evaluate(b => window.HelmDownloadDrawer.setBbox(b), FIJI_BBOX);

  const err = page.locator('[data-testid="dl-error"]');
  await expect(err).toBeVisible();
  await expect(err).toHaveAttribute('data-error-code', 'packd_unreachable');
  await expect(err).toContainText(/pack server/i);
  await expect(page.locator('[data-testid="dl-estimate"]')).toContainText('unavailable');
});

test('keeps the legacy single-source fetch_tiles.py handoff', async ({ page }) => {
  await boot(page);
  await openDrawer(page);
  await page.evaluate(() => window.HelmDownloadDrawer.setSource('noaa'));
  await page.evaluate(b => window.HelmDownloadDrawer.setBbox(b), FIJI_BBOX);

  await expect(page.locator('.dl-cmd')).toContainText('fetch_tiles.py');
  await expect(page.locator('[data-testid="dl-estimate"]')).toContainText('tiles');
  await expect(page.locator('[data-testid="dl-error"]')).toBeHidden();
});
