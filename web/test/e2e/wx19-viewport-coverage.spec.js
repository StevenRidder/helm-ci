const { test, expect } = require('@playwright/test');

const SCENE_LAYERS = ['wind', 'gust', 'rain', 'temp', 'sst', 'clouds', 'waves', 'swell', 'pressure', 'cape', 'current'];
const VECTOR_LAYERS = new Set(['wind', 'current']);
const VALID_TIME = '2026-07-01T00:00:00Z';
const VALID_TIME_ID = '20260701T000000Z';
const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
);

function coverage() {
  return {
    bbox: { crossesAntimeridian: true, west: 172, south: -26, east: -144, north: -5 },
    crs: 'OGC:CRS84',
    global: false,
    regionId: 'fiji',
    wrap: 'antimeridian',
  };
}

function rampFor(layer) {
  if (layer === 'rain') return [[0, [40, 80, 190, 0]], [10, [40, 180, 255, 0.9]]];
  if (layer === 'temp' || layer === 'sst') return [[0, [50, 100, 220, 0.7]], [32, [240, 90, 50, 0.9]]];
  return [[0, [98, 113, 183, 0.7]], [10, [52, 171, 151, 0.85]], [30, [232, 130, 50, 0.95]]];
}

function preparedLayer(layer) {
  const base = `/bundles/open-meteo/latest/fiji/layers/${layer}`;
  const out = {
    id: layer,
    kind: VECTOR_LAYERS.has(layer) ? 'vector' : 'scalar',
    unit: layer === 'pressure' ? 'hPa' : layer === 'temp' || layer === 'sst' ? '°C' : 'kn',
    range: { min: 0, max: layer === 'pressure' ? 1040 : 80, unit: 'mock' },
    ramp: rampFor(layer),
    fieldTiles: {
      minzoom: 0,
      maxzoom: 6,
      tileSize: 256,
      urlTemplate: `${base}/scalar/{validTimeId}/{z}/{x}/{y}.png`,
    },
  };
  if (VECTOR_LAYERS.has(layer)) {
    out.vectorField = {
      components: ['u', 'v'],
      u: { scale: 1, offset: -40, urlTemplate: `${base}/vector/{validTimeId}/u/{z}/{x}/{y}.png` },
      v: { scale: 1, offset: -40, urlTemplate: `${base}/vector/{validTimeId}/v/{z}/{x}/{y}.png` },
    };
  }
  return out;
}

function preparedManifest() {
  return {
    schema: 'helm.env.bundle.v1',
    bundleId: 'open-meteo/latest/fiji',
    encoding: 'helm-wxv1',
    generatedAt: VALID_TIME,
    coverage: coverage(),
    run: {
      mode: 'model-run-cache',
      runTime: VALID_TIME,
      validTimes: [VALID_TIME],
      frameIdByValidTime: { [VALID_TIME]: VALID_TIME_ID },
      frames: 1,
    },
    frames: [{ validTime: VALID_TIME, validTimeId: VALID_TIME_ID, isLatest: true }],
    cachePolicy: { cacheOnlyReplay: true, upstreamFetchesAllowedDuringGesture: false, ttlSeconds: 10800 },
    cacheState: { state: 'fresh', offlineReady: true, serveStale: true, materializedAt: VALID_TIME },
    layers: Object.fromEntries(SCENE_LAYERS.map((layer) => [layer, preparedLayer(layer)])),
  };
}

function bundleIndex() {
  return {
    schema: 'helm.env.bundle.index.v1',
    generatedAt: VALID_TIME,
    bundles: [{
      id: 'open-meteo/latest/fiji',
      kind: 'environmental-bundle',
      schema: 'helm.env.bundle.v1',
      manifest: '/bundles/open-meteo/latest/fiji/manifest.json',
      coverage: coverage(),
      layers: SCENE_LAYERS,
      validTimes: [VALID_TIME],
      runTime: VALID_TIME,
      cacheOnlyReplay: true,
      offlineReady: true,
      cacheState: { state: 'fresh', offlineReady: true },
    }],
  };
}

function gatewayManifest(layer) {
  return {
    encoding: 'helm-wxv1',
    bits: 24,
    tileSize: 256,
    layer,
    unit: layer === 'pressure' ? 'hPa' : layer === 'temp' || layer === 'sst' ? '°C' : 'kn',
    kind: 'scalar',
    scale: 1,
    offset: 0,
    nodata_alpha: 0,
    has_alpha: true,
    minzoom: 0,
    maxzoom: 7,
    bbox: [-180, -85, 180, 85],
    global: true,
    vmin: 0,
    vmax: layer === 'pressure' ? 1040 : 80,
    ramp: rampFor(layer),
    source: 'open-meteo',
    model: 'Open-Meteo mock global tile fallback',
    fetchedAt: VALID_TIME,
    times: null,
    frames: null,
    tiles_template: '{z}/{x}/{y}.png',
  };
}

function velocityPayload() {
  const header = { parameterNumber: 2, nx: 2, ny: 2, lo1: 120, la1: 20, lo2: 250, la2: -40, dx: 130, dy: 60 };
  return [
    { header, data: [1, 1, 1, 1] },
    { header: { ...header, parameterNumber: 3 }, data: [0, 0, 0, 0] },
  ];
}

async function installMockGateway(page) {
  const materialize = [];
  await page.route(/https?:\/\/(?:127\.0\.0\.1|localhost):8093\/.*/, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === '/health') {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, service: 'helm-wx' }) });
    }
    if (path === '/bundles/index.json') {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(bundleIndex()) });
    }
    if (path === '/bundles/open-meteo/latest/fiji/manifest.json') {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(preparedManifest()) });
    }
    if (path === '/bundles/open-meteo/latest/materialize') {
      materialize.push(url.toString());
      return route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, manifest: `/bundles/open-meteo/latest/${url.searchParams.get('region')}/manifest.json` }),
      });
    }
    if (/^\/bundles\/open-meteo\/latest\/fiji\/layers\/.+\.png$/.test(path)) {
      return route.fulfill({ contentType: 'image/png', body: PNG_1X1 });
    }
    const manifest = path.match(/^\/([^/]+)\/manifest\.json$/);
    if (manifest && SCENE_LAYERS.includes(manifest[1])) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(gatewayManifest(manifest[1])) });
    }
    if (/^\/velocity\/(wind|current)$/.test(path)) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(velocityPayload()) });
    }
    if (new RegExp(`^\\/(${SCENE_LAYERS.join('|')})(?:\\/t\\d+)?\\/\\d+\\/\\d+\\/\\d+\\.png$`).test(path)) {
      return route.fulfill({ contentType: 'image/png', body: PNG_1X1 });
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: true, path }) });
  });
  return materialize;
}

async function boot(page, hash) {
  await page.addInitScript(() => {
    try { localStorage.clear(); sessionStorage.clear(); } catch (e) {}
  });
  await page.goto(`/${hash}`);
  await expect(page).toHaveTitle(/Helm/);
  await page.waitForFunction(
    () => !!window.map && window.map.isStyleLoaded && window.map.isStyleLoaded() && !!window.HelmWxControls && !!window.HelmWxScene,
    null,
    { timeout: 30000 }
  );
  await page.waitForSelector('.ri[data-rail="weather"]', { timeout: 10000 });
}

async function clickRail(page, rail) {
  const box = await page.locator(`.ri[data-rail="${rail}"]`).boundingBox();
  expect(box, `${rail} rail button has a visible box`).toBeTruthy();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

async function clickLayer(page, layer) {
  await page.locator(`#wx button[data-wx="${layer}"]`).click();
  await page.waitForFunction((expected) => window.__activeWx === expected, layer, { timeout: 10000 });
}

async function wxState(page) {
  return page.evaluate(() => ({
    active: window.__activeWx,
    zoom: window.map && window.map.getZoom(),
    bounds: window.map && window.map.getBounds().toArray(),
    sceneLayer: !!(window.map && window.map.getLayer('helm-wx-scene')),
    gribLayer: !!(window.map && window.map.getLayer('helm-wx-grib')),
    sceneStatus: window.HelmWxScene && window.HelmWxScene.status && window.HelmWxScene.status(),
    coverageBadge: (document.querySelector('#helm-wx-coverage-status') || {}).textContent || '',
  }));
}

test('WX-19 revalidates prepared coverage on zoom-out and falls back to full-view gateway tiles', async ({ page }) => {
  test.setTimeout(90000);
  const materialize = await installMockGateway(page);
  await boot(page, '#7/-17.68169/177.38424');
  await clickRail(page, 'weather');
  await clickLayer(page, 'wind');

  await page.waitForFunction(
    () => window.map && window.map.getLayer('helm-wx-scene') && !window.map.getLayer('helm-wx-grib'),
    null,
    { timeout: 20000 }
  );
  expect((await wxState(page)).sceneLayer).toBe(true);

  await page.evaluate(() => window.map.jumpTo({ center: [177.38424, -17.68169], zoom: 4.21 }));

  await page.waitForFunction(
    () => window.map && !window.map.getLayer('helm-wx-scene') && window.map.getLayer('helm-wx-grib') &&
      /partial coverage/.test((document.querySelector('#helm-wx-coverage-status') || {}).textContent || ''),
    null,
    { timeout: 20000 }
  );
  const state = await wxState(page);
  expect(state.sceneLayer).toBe(false);
  expect(state.gribLayer).toBe(true);
  expect(state.coverageBadge).toContain('partial coverage');
  expect(materialize.length).toBeGreaterThan(0);
  expect(materialize[0]).toContain('/bundles/open-meteo/latest/materialize');
});

test('WX-19 wide viewport does not use the boxed Fiji prepared renderer for any scene layer', async ({ page }) => {
  test.setTimeout(120000);
  await installMockGateway(page);
  await boot(page, '#4.21/-17.48045/-179.2142');
  await clickRail(page, 'weather');

  for (const layer of SCENE_LAYERS) {
    await clickLayer(page, layer);
    await page.waitForFunction(
      () => window.map && window.map.getLayer('helm-wx-grib') && !window.map.getLayer('helm-wx-scene') &&
        /partial coverage/.test((document.querySelector('#helm-wx-coverage-status') || {}).textContent || ''),
      null,
      { timeout: 20000 }
    );
    const state = await wxState(page);
    expect(state.active).toBe(layer);
    expect(state.gribLayer).toBe(true);
    expect(state.sceneLayer).toBe(false);
    expect(state.coverageBadge).toContain('partial coverage');
  }
});
