// INTAKE-5 e2e: Chart Library panel against a stubbed helm-packd chart-intake seam.
// Covers the four spec bullets: folder add/list/rescan, region-group tabs,
// per-chart info with CAT-1 freshness + honest badges, and the first-run empty
// state. Backend endpoints (/chart-index, /chart-roots, /catalog, /rescan) are
// page.route stubs on the same :9101 port convention as offline4-pack-selector.
const { test, expect } = require('@playwright/test');

const PORT = 9101;
const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg==',
  'base64'
);

const DEFAULT_ROOT = { id: 'root-def4567890abcdef', label: 'Default charts', default: true, added_at: '2026-07-01T00:00:00Z', status: 'available' };
const ADDED_ROOT = { id: 'root-add4567890abcdef', label: 'ChartLocker', default: false, added_at: '2026-07-13T00:00:00Z', status: 'available' };

function chart(id, relative, type, ext, group, extra) {
  const filename = relative.split('/').pop();
  return Object.assign({
    id, root_id: DEFAULT_ROOT.id, relative_path: relative, filename, group,
    chart_type: type, extension: ext, size_bytes: 4 * 1048576, modified_at: '2026-07-10T00:00:00Z',
    validation: { status: 'valid', code: 'ok', message: 'ok' }, warnings: []
  }, extra || {});
}

const LAGOON = chart('chart-lagoon0000000000', 'FIJI/lagoon.mbtiles', 'tile_pack', '.mbtiles', 'FIJI', { bbox: [178, -18, 179, -17] });
const REEF = chart('chart-reef000000000000', 'TONGA/reef.pmtiles', 'tile_pack', '.pmtiles', 'TONGA', { bbox: [184, -22, 185, -21] });
const CELL = chart('chart-cell000000000000', 'cell.000', 'enc', '.000', '.', {
  update_count: 1, latest_update: 1,
  validation: { status: 'error', code: 'contents_extension_mismatch', message: 'file declares .000 but has no ISO 8211 leader' }
});
const PASSAGE = chart('chart-passage000000000', 'FIJI/passage.geojson', 'overlay', '.geojson', 'FIJI', { bbox: [178.1, -17.9, 178.3, -17.7] });
const HARBOR = chart('chart-harbor0000000000', 'harbor.mbtiles', 'tile_pack', '.mbtiles', '.', { root_id: ADDED_ROOT.id });

function indexDoc(roots, charts) {
  const invalid = charts.filter((c) => c.validation.status === 'error').length;
  return {
    schema: 'helm.chart_intake.index.v1', indexer_version: 1,
    generated_at: '2026-07-13T00:00:00Z', fingerprint: 'sha256:e2e-fixture',
    status: invalid ? 'error' : 'ok',
    chart_count: charts.length, invalid_count: invalid, warning_count: 0,
    roots: roots.map((r) => ({
      id: r.id, label: r.label, default: !!r.default, status: r.status,
      chart_count: charts.filter((c) => c.root_id === r.id).length,
      group_count: new Set(charts.filter((c) => c.root_id === r.id).map((c) => c.group)).size
    })),
    charts, warnings: []
  };
}

const CATALOG = {
  lagoon: {
    id: 'lagoon', name: 'lagoon', title: 'Fiji Lagoon', kind: 'chart', container: 'mbtiles',
    format: 'png', extension: 'png', type: 'raster', minzoom: 0, maxzoom: 14,
    bounds: '178,-18,179,-17', bounds_array: [178, -18, 179, -17], size_bytes: 4194304,
    license: 'local-user-owned', staleness: { status: 'stale', age_days: 45 }
  },
  reef: {
    id: 'reef', name: 'reef', title: 'Tonga Reef', kind: 'chart', container: 'pmtiles',
    format: 'png', extension: 'png', type: 'raster', minzoom: 0, maxzoom: 12,
    bounds: '184,-22,185,-21', bounds_array: [184, -22, 185, -21], size_bytes: 1048576,
    license: 'local-user-owned', staleness: { status: 'fresh', age_days: 2 }
  }
};

// Stateful stub: POST /chart-roots flips to the "added" fixture set so the
// panel's auto-refresh observes the registration like a real daemon.
function installRoutes(page, options) {
  const opts = options || {};
  const stub = { added: false, posts: [], rescans: 0 };
  const CORS = {
    'access-control-allow-origin': '*',
    'access-control-allow-headers': 'Range, Content-Type',
    'access-control-allow-methods': 'GET, HEAD, POST, OPTIONS'
  };
  const json = (route, body, status) => {
    // fetch() preflights the JSON POSTs exactly like against the real daemon.
    if (route.request().method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: CORS });
    }
    return route.fulfill({
      status: status || 200,
      headers: Object.assign({ 'content-type': 'application/json' }, CORS),
      body: JSON.stringify(body)
    });
  };
  const host = new RegExp(`https?://[^/]+:${PORT}`);

  page.route(new RegExp(`${host.source}/chart-index$`), (route) => {
    if (opts.empty) return json(route, indexDoc([DEFAULT_ROOT], []));
    const charts = stub.added ? [LAGOON, PASSAGE, REEF, CELL, HARBOR] : [LAGOON, PASSAGE, REEF, CELL];
    const roots = stub.added ? [DEFAULT_ROOT, ADDED_ROOT] : [DEFAULT_ROOT];
    return json(route, indexDoc(roots, charts));
  });
  page.route(new RegExp(`${host.source}/chart-roots$`), (route) => {
    if (route.request().method() === 'POST') {
      stub.posts.push(JSON.parse(route.request().postData() || '{}'));
      stub.added = true;
      return json(route, {
        schema: 'helm.chart_intake.roots.v1', status: 'ok', changed: true,
        root: { id: ADDED_ROOT.id, label: ADDED_ROOT.label, default: false, added_at: ADDED_ROOT.added_at, status: 'available' },
        packs: 3, fingerprint: 'fp-2'
      });
    }
    const roots = (opts.empty || !stub.added) ? [DEFAULT_ROOT] : [DEFAULT_ROOT, ADDED_ROOT];
    return json(route, { schema: 'helm.chart_intake.roots.v1', roots, source: 'file' });
  });
  page.route(new RegExp(`${host.source}/rescan$`), (route) => {
    if (route.request().method() === 'POST') stub.rescans += 1;
    return json(route, { schema: 'helm.chart_index.rescan.v1', status: 'ok', changed: false, packs: 2, fingerprint: 'fp-1' });
  });
  page.route(new RegExp(`${host.source}/catalog$`), (route) => json(route, opts.empty ? {} : CATALOG));
  page.route(new RegExp(`${host.source}/layer-manifest$`), (route) => json(route, {
    schema: 'helm.layer.manifest.v1', layers: [],
    enc: { expected: ['depare', 'depcnt', 'soundg'], present: [], missing: ['depare', 'depcnt', 'soundg'] }
  }));
  // Everything else on the pack port (tiles, health) -> tiny PNG / empty ok.
  page.route(new RegExp(`${host.source}/(?!chart-index$|chart-roots$|rescan$|catalog$|layer-manifest$).+`), (route) => {
    route.fulfill({ status: 200, headers: { 'content-type': 'image/png', 'access-control-allow-origin': '*' }, body: PNG_1X1 });
  });
  return stub;
}

async function bootAndOpen(page) {
  await page.goto(`/?basemapPort=${PORT}#9/-17.75/178.12`);
  await expect(page).toHaveTitle(/Helm/);
  // Gate on our own globals, not map.isStyleLoaded (flaky offline locally).
  await page.waitForFunction(() => {
    if (!window.HelmChartLibrary || !window.HelmShell || !window.HelmShell.panel) return false;
    const h = window.HelmShell.panel('helm-chart-library');
    return !!(h && h.el && h.el());
  }, null, { timeout: 20000 });
  await page.evaluate(() => window.HelmShell.panel('helm-chart-library').open());
  await expect(page.locator('#helm-chart-library')).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} });
});

test('library lists roots, groups, and per-chart honesty from the intake seam', async ({ page }) => {
  installRoutes(page);
  await bootAndOpen(page);
  const panel = page.locator('#helm-chart-library');

  // Roots section: the registered folder with its counts, no filesystem paths anywhere.
  await expect(panel.locator('.helm-chartlib-root')).toContainText('Default charts');
  await expect(panel.locator('.helm-chartlib-root')).toContainText('4 charts');
  expect(await panel.innerHTML()).not.toContain('/private/');

  // Region groups surface as tabs (OpenCPN Chart Groups analog) incl. top-level.
  const tabs = panel.locator('.helm-chartlib-tab');
  await expect(tabs).toHaveText(['All', 'FIJI', 'TONGA', 'Top level']);

  // Per-chart info: type + CAT-1 staleness join, honest invalid + not-served notes.
  const rows = panel.locator('.helm-chartlib-row');
  await expect(rows).toHaveCount(4);
  await expect(rows.filter({ hasText: 'lagoon.mbtiles' })).toContainText('stale · 45d old');
  await expect(rows.filter({ hasText: 'reef.pmtiles' })).toContainText('fresh');
  await expect(rows.filter({ hasText: 'cell.000' })).toContainText('invalid: contents_extension_mismatch');
  await expect(rows.filter({ hasText: 'passage.geojson' })).toContainText('indexed, not yet served');

  // Layout: the filename column must survive the narrow drawer — the action
  // side wraps below instead of flex-starving the title to zero width.
  const titleWidths = await panel.locator('.helm-chartlib-main b').evaluateAll(
    (els) => els.map((el) => el.getBoundingClientRect().width)
  );
  expect(Math.min(...titleWidths)).toBeGreaterThan(40);

  // Group tab filters the list to the region the customer is in.
  await panel.locator('.helm-chartlib-tab', { hasText: 'FIJI' }).click();
  await expect(panel.locator('.helm-chartlib-row')).toHaveCount(2);
  await expect(panel.locator('.helm-chartlib-row').first()).toContainText('lagoon.mbtiles');
});

test('add folder registers a root over HTTP and the library refreshes', async ({ page }) => {
  const stub = installRoutes(page);
  await bootAndOpen(page);
  const panel = page.locator('#helm-chart-library');

  await panel.locator('input[name="path"]').fill('/boat/ChartLocker');
  await panel.locator('input[name="label"]').fill('ChartLocker');
  await panel.locator('[data-chartlib-add] button[type="submit"]').click();

  await expect(panel.locator('.helm-chartlib-notice')).toContainText('registered “ChartLocker”');
  expect(stub.posts).toEqual([{ path: '/boat/ChartLocker', label: 'ChartLocker' }]);

  // The panel refetched: new root row + its chart appear without a reload.
  await expect(panel.locator('.helm-chartlib-root')).toHaveCount(2);
  await expect(panel.locator('.helm-chartlib-root').nth(1)).toContainText('ChartLocker');
  await expect(panel.locator('.helm-chartlib-row', { hasText: 'harbor.mbtiles' })).toBeVisible();

  // Unregister goes back through the seam (files stay put by contract).
  await panel.locator(`[data-chartlib-remove="${ADDED_ROOT.id}"]`).click();
  await expect(panel.locator('.helm-chartlib-notice')).toContainText('unregistered');
});

test('rescan button hits POST /rescan and reports the daemon result', async ({ page }) => {
  const stub = installRoutes(page);
  await bootAndOpen(page);
  const panel = page.locator('#helm-chart-library');
  await panel.locator('[data-chartlib-rescan]').click();
  await expect(panel.locator('.helm-chartlib-notice')).toContainText('rescan: 2 packs, no change');
  expect(stub.rescans).toBe(1);
});

test('Show activates the joined catalog pack via the offline-packs owner', async ({ page }) => {
  installRoutes(page);
  await bootAndOpen(page);
  const panel = page.locator('#helm-chart-library');
  await panel.locator('.helm-chartlib-row', { hasText: 'lagoon.mbtiles' })
    .locator('[data-chartlib-show]').click();
  await expect.poll(() => page.evaluate(() => ({
    activeId: window.HelmOfflinePacks && window.HelmOfflinePacks.state.activeId,
    stored: window.HelmStore ? window.HelmStore.get('offline.activePack', null) : null
  })), { timeout: 10000 }).toMatchObject({ activeId: 'lagoon', stored: 'lagoon' });
  await expect(panel.locator('.helm-chartlib-notice')).toContainText('Fiji Lagoon');
});

test('first-run empty state prompts to add a chart folder', async ({ page }) => {
  installRoutes(page, { empty: true });
  await bootAndOpen(page);
  const panel = page.locator('#helm-chart-library');
  await expect(panel.locator('.helm-chartlib-empty')).toHaveAttribute('data-empty-kind', 'first-run');
  await expect(panel.locator('.helm-chartlib-empty')).toContainText('No charts in the library yet.');
  await expect(panel.locator('.helm-chartlib-empty')).toContainText('nothing is moved or renamed');
  await expect(panel.locator('[data-chartlib-add] input[name="path"]')).toBeVisible();
});
