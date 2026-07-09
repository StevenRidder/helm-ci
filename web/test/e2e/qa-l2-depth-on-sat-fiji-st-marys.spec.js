// QA-L-2: depth-on-sat fusion preset screenshot proof at Fiji + St Marys (US5GA2BC).
//
// Proof bar (both legs): depth vectors must come from an ENC extract via /user-data/
// (HelmEncDepthSources.status().mode === 'enc') AND queryRenderedFeatures must return
// depth features at the viewport. Toggle/visibility screenshots alone are NOT proof —
// the bundled demo depth is Key West and renders nothing at Fiji or St Marys.
//
// Fiji (mock packd, CI-safe): HELM_QAL2=1 HELM_OFFLINE20_MOCK_PACKD=1 — serve.py serves
//   the committed fixtures/fiji-depth-userdata/ as /user-data/ (HELM_USER_DATA_ROOT is set
//   by playwright.qa-l2.config.js webServer), exercising the real client extract-preference
//   path. Route mocks can NOT stand in here: MapLibre fetches geojson from its worker,
//   which bypasses page.route.
// St Marys (live helm-server): HELM_QAL2=1 HELM_HARBOUR_E2E=1 — real US5GA2BC extract.
// Miami US regression twin (real NOAA ENC): scripts/verify-miami-dinner-key-depth-on-sat.sh
// Headed Chrome locally: HELM_QAL2_HEADED=1 (see playwright.qa-l2.config.js)
//
// Full private-stack proof: scripts/verify-qa-l2-depth-on-sat.sh
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const {
  clickRail,
  bootHarbour,
  fetchCatalogEncCenter
} = require('./_harbour-helpers');

const ENABLED = !!process.env.HELM_QAL2;
const MOCK_PACKD = process.env.HELM_OFFLINE20_MOCK_PACKD === '1';
const HARBOUR = !!process.env.HELM_HARBOUR_E2E;
const PACKD_ORIGIN = process.env.HELM_OFFLINE20_PACKD_URL || 'http://127.0.0.1:9141';
const PACKD_PORT = new URL(PACKD_ORIGIN).port || '9141';
const FIJI_HASH = process.env.HELM_QAL2_FIJI_HASH || '#9/-17.75/178.12';
const ST_MARYS_HASH = process.env.HELM_QAL2_ST_MARYS_HASH || '#13/30.862/-81.487';
const EVIDENCE_DIR = process.env.HELM_QAL2_EVIDENCE_DIR || '';
const OUT = path.join(path.resolve(__dirname, '..', '..'), 'test-results', 'qa-l2-e2e');

test.skip(!ENABLED, 'Set HELM_QAL2=1 to run the depth-on-sat Fiji/St Marys proof.');

function asJsonText(obj) {
  return JSON.stringify(obj, null, 2);
}

function localOnly(urlText) {
  const u = new URL(urlText);
  if (u.protocol === 'blob:' || u.protocol === 'data:') return true;
  return ['127.0.0.1', 'localhost', '[::1]', '::1'].includes(u.hostname);
}

function evidencePath(name) {
  const dir = EVIDENCE_DIR || OUT;
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, name);
}

async function screenshot(page, name) {
  await page.screenshot({ path: evidencePath(name), fullPage: false });
}

function mockCatalog(baseURL) {
  return {
    'fiji-sat': {
      id: 'fiji-sat',
      title: 'Fiji offline satellite PMTiles',
      kind: 'raster',
      container: 'pmtiles',
      format: 'png',
      minzoom: 0,
      maxzoom: 9,
      bounds_array: [176.8, -19.2, 180.0, -16.0],
      pmtiles_url: new URL('/data/fiji-sat.pmtiles', baseURL).href,
      source_info: { label: 'repo Fiji satellite fixture', license: 'test fixture' },
      freshness: { status: 'fixture' },
      inspection: {
        mode: 'raster_metadata',
        semantic_objects: 'unavailable',
        tap_action: 'show_pack_source_metadata',
        message: 'Satellite raster pixels only; nautical objects require a sidecar layer.'
      }
    }
  };
}

function packdRoutePattern(pathname, suffix = '') {
  return new RegExp(`^https?://(?:127\\.0\\.0\\.1|localhost|\\[::1\\]):${PACKD_PORT}${pathname}${suffix}$`);
}

// The committed Fiji-viewport depth fixture (web/test/fixtures/fiji-depth-userdata/) is
// served by serve.py as /user-data/, driving the REAL client path: enc-depth-sources.js
// prefers user-data over the bundled Key West demo, and actual depth vectors render over
// the offline satellite. The cell id is deliberately a fixture name so nobody mistakes it
// for real Fiji ENC coverage.
const FIJI_FIXTURE_CELL = 'FJ-FIXTURE-BLIGH-WATER';

async function applyDepthOnSat(page) {
  await clickRail(page, 'layers');
  await page.locator('[data-fusion-preset="depth-on-sat"]').click();
  await page.waitForTimeout(900);
}

// Wait for depth vectors to actually paint before asserting — geojson sources load async
// and slow CI boxes can reach the assertion before the first depth frame renders.
async function waitForRenderedDepth(page) {
  await page.waitForFunction(
    () => window.map.queryRenderedFeatures(undefined, {
      layers: ['depare-fill', 'depcnt-line'].filter(id => window.map.getLayer(id))
    }).length > 0,
    null,
    { timeout: 20000 }
  );
}

async function collectDepthOnSatState(page) {
  return page.evaluate(() => ({
    preset: window.HelmFusionPresets && HelmFusionPresets.describe('depth-on-sat'),
    active: window.HelmFusionPresets && HelmFusionPresets.readActive(),
    satVis: (() => {
      if (window.map.getLayer('helm-offline-active-pack')) {
        const vis = window.map.getLayoutProperty('helm-offline-active-pack', 'visibility');
        if (vis !== 'none') return 'offline-pack';
      }
      if (window.map.getLayer('googlesat')) {
        return window.map.getLayoutProperty('googlesat', 'visibility') || 'visible';
      }
      return 'missing';
    })(),
    offlinePack: window.HelmOfflinePacks && window.HelmOfflinePacks.state.activeId,
    encVis: window.map.getLayer('enc-chart')
      ? window.map.getLayoutProperty('enc-chart', 'visibility')
      : 'missing',
    depareVis: window.map.getLayer('depare-fill')
      ? window.map.getLayoutProperty('depare-fill', 'visibility')
      : 'missing',
    depcntVis: window.map.getLayer('depcnt-line')
      ? window.map.getLayoutProperty('depcnt-line', 'visibility')
      : 'missing',
    soundgVis: window.map.getLayer('soundg-text')
      ? window.map.getLayoutProperty('soundg-text', 'visibility')
      : 'missing',
    depthHits: window.map.queryRenderedFeatures(undefined, {
      layers: ['depare-fill', 'depcnt-line', 'soundg-text'].filter(id => window.map.getLayer(id))
    }).length,
    depthProv: window.HelmEncDepthSources && HelmEncDepthSources.status
      ? HelmEncDepthSources.status()
      : null,
    fused: window.HelmLayerEncOpenCPN && HelmLayerEncOpenCPN.status()
  }));
}

function expectDepthOnSatState(state, opts) {
  opts = opts || {};
  expect(state.preset && state.preset.id).toBe('depth-on-sat');
  expect(state.active).toBe('depth-on-sat');
  expect(state.depareVis).toBe('visible');
  expect(state.encVis).toBe('none');
  expect(state.fused && state.fused.fused_on_satellite, 'depth-on-sat keeps aids off satellite').toBe(false);
  if (opts.requireSatellite) {
    expect(['visible', 'offline-pack'].includes(state.satVis), 'satellite basemap or offline pack visible').toBeTruthy();
  }
}

// The QA-L-2 proof bar: provenance says ENC extract, and depth features actually painted.
function expectRenderedEncDepth(state, opts) {
  opts = opts || {};
  expect(state.depthProv && state.depthProv.mode,
    'depth vectors come from an ENC extract (user-data), not the bundled Key West demo').toBe('enc');
  if (opts.cell) {
    expect(state.depthProv.cell, 'depth extract cell matches the expected ENC').toBe(opts.cell);
  }
  expect(state.depthHits,
    'depth features actually render over the satellite basemap at the viewport').toBeGreaterThan(0);
}

test.describe('QA-L-2 — depth-on-sat Fiji', () => {
  test('fusion preset over offline Fiji satellite captures screenshot proof', async ({ page, baseURL }) => {
    test.skip(!MOCK_PACKD, 'Set HELM_OFFLINE20_MOCK_PACKD=1 for Fiji mock-packd proof.');

    const externalRequests = [];
    await page.route('**/*', route => {
      const url = route.request().url();
      if (!localOnly(url)) {
        externalRequests.push(url);
        return route.abort('blockedbyclient');
      }
      if (/\/\/(?:127\.0\.0\.1|localhost):8091\//.test(url)) {
        return route.abort('blockedbyclient');
      }
      return route.continue();
    });

    await page.route(packdRoutePattern('/catalog'), route => route.fulfill({
      contentType: 'application/json',
      body: asJsonText(mockCatalog(baseURL))
    }));
    await page.route(packdRoutePattern('/layers'), route => route.fulfill({
      contentType: 'application/json',
      body: asJsonText({ schema: 'helm.layer_inventory.v1', layers: [] })
    }));
    await page.route(packdRoutePattern('/bundle', '(?:[?#].*)?'), route => route.fulfill({
      contentType: 'application/json',
      body: asJsonText({ schema: 'helm.region_bundle.manifest.v1', summary: { packs: 1, mode: 'mock' } })
    }));
    await page.route(packdRoutePattern('/prefetch', '(?:[?#].*)?'), route => route.fulfill({
      contentType: 'application/json',
      body: asJsonText({ schema: 'helm.prefetch.manifest.v1', totals: { bytes: 0, mode: 'mock' } })
    }));

    await page.goto('/?offline20=1&basemapPort=' + new URL(PACKD_ORIGIN).port + FIJI_HASH);
    await expect(page).toHaveTitle(/Helm/);
    await page.waitForFunction(
      () => !!window.map && typeof window.map.isStyleLoaded === 'function' &&
        window.map.isStyleLoaded() && !!window.HelmOfflinePacks && !!window.HelmFusionPresets,
      null,
      { timeout: 30000 }
    );

    await page.evaluate(() => window.HelmShell.panel('helm-offline-packs').open());
    await page.waitForFunction(
      () => window.HelmOfflinePacks.state.packs.some(p => /fiji/i.test(`${p.id || ''} ${p.title || ''}`)),
      null,
      { timeout: 10000 }
    );
    await page.evaluate(() => {
      const pack = window.HelmOfflinePacks.state.packs.find(p => /fiji/i.test(`${p.id || ''} ${p.title || ''}`));
      window.HelmOfflinePacks.activate(pack.id, { fit: false });
    });
    await page.waitForFunction(() => !!window.map.getLayer('helm-offline-active-pack'));
    await page.waitForTimeout(800);

    await applyDepthOnSat(page);
    await waitForRenderedDepth(page);
    const state = await collectDepthOnSatState(page);
    expectDepthOnSatState(state, { requireSatellite: true });
    expect(state.offlinePack, 'Fiji offline satellite pack stays active under depth-on-sat').toMatch(/fiji/i);
    expect(state.preset.offline_pack, 'preset reports offline pack context').toBe(true);
    expectRenderedEncDepth(state, { cell: FIJI_FIXTURE_CELL });
    expect(state.depthProv.layers && state.depthProv.layers.depare,
      'depare source swapped to the user-data fixture').toBe('user');

    await screenshot(page, 'qa-l2-01-fiji-depth-on-sat.png');
    fs.writeFileSync(evidencePath('qa-l2-fiji-state.json'), asJsonText(state));
    expect(externalRequests, 'Fiji proof blocks internet requests').toEqual([]);
  });
});

test.describe('QA-L-2 — depth-on-sat St Marys', () => {
  test('fusion preset at US5GA2BC harbour captures screenshot proof', async ({ page, request }) => {
    test.skip(!HARBOUR, 'Set HELM_HARBOUR_E2E=1 and start helm-server for St Marys proof.');

    const enc = await fetchCatalogEncCenter(request);
    test.skip(enc.cellId !== 'US5GA2BC', 'live server must load US5GA2BC for St Marys depth-on-sat proof');

    await bootHarbour(page, { hash: ST_MARYS_HASH });
    await applyDepthOnSat(page);
    await waitForRenderedDepth(page);
    const state = await collectDepthOnSatState(page);

    expectDepthOnSatState(state, { requireSatellite: true });
    expect(state.satVis).toBe('visible');
    expectRenderedEncDepth(state, { cell: enc.cellId });

    await screenshot(page, 'qa-l2-02-st-marys-depth-on-sat.png');
    fs.writeFileSync(evidencePath('qa-l2-st-marys-state.json'), asJsonText({ enc, state }));
  });
});
