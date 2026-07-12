// QA-L-3: layer toggle matrix regression. Exercises the ENC-1 depare/depcnt/soundg/enc-chart
// checkboxes, the FUSE-1 fusion presets, and the ENC-3 ?profile=depth|aids|standard resolver
// together across combinations, in SIM mode against the base style (no engine/ENC data needed —
// the depare-fill/depcnt-line/soundg-text/enc-chart layers are always present in style.json).
// Runs unconditionally in CI (no HELM_* opt-in flag) alongside the other default web-e2e specs.
const { test, expect } = require('@playwright/test');
const { bootHarbour, clickRail, attachHarbourDiagnostics } = require('./_harbour-helpers');

const ENC_KEYS = ['depare', 'depcnt', 'soundg', 'enc-chart'];
const ENC_LAYER_IDS = {
  depare: 'depare-fill',
  depcnt: 'depcnt-line',
  soundg: 'soundg-text',
  'enc-chart': 'enc-chart'
};

async function toggleLayers(page, patch) {
  return page.evaluate((patch) => {
    const results = {};
    Object.keys(patch).forEach((key) => {
      const el = document.querySelector('input[data-enc-layer="' + key + '"]');
      if (!el) { results[key] = 'missing'; return; }
      el.checked = patch[key];
      el.dispatchEvent(new Event('change', { bubbles: true }));
      results[key] = 'ok';
    });
    return results;
  }, patch);
}

async function readLayerState(page) {
  return page.evaluate(({ ids }) => {
    const vis = {};
    Object.keys(ids).forEach((key) => {
      const id = ids[key];
      vis[key] = window.map.getLayer(id) ? window.map.getLayoutProperty(id, 'visibility') || 'visible' : 'missing';
    });
    return {
      visibility: vis,
      checkboxes: Object.keys(ids).reduce((acc, key) => {
        const el = document.querySelector('input[data-enc-layer="' + key + '"]');
        acc[key] = el ? el.checked : null;
        return acc;
      }, {}),
      profile: window.HelmEncTileProfile ? window.HelmEncTileProfile.resolve() : undefined
    };
  }, { ids: ENC_LAYER_IDS });
}

function expectedVisibility(patch) {
  const out = {};
  ENC_KEYS.forEach((key) => { out[key] = patch[key] === false ? 'none' : 'visible'; });
  return out;
}

test.describe('QA-L-3 layer toggle matrix', () => {
  test('every ENC-1 checkbox combo drives the matching MapLibre layer visibility + ENC-3 profile', async ({ page }) => {
    const diag = { console: [], pageErrors: [], failedRequests: [] };
    attachHarbourDiagnostics(page, diag);

    await bootHarbour(page, { waitRendererStatus: false });
    await clickRail(page, 'layers');

    // Baseline: everything defaults on.
    const initial = await readLayerState(page);
    expect(initial.visibility).toEqual(expectedVisibility({}));

    const matrix = [
      { depare: false },
      { depare: true, depcnt: false },
      { depcnt: true, soundg: false },
      { soundg: true, 'enc-chart': false },
      { 'enc-chart': true, depare: false, depcnt: false, soundg: false },
      { depare: true, depcnt: true, soundg: true, 'enc-chart': true },
      { depare: false, depcnt: false, soundg: false, 'enc-chart': false }
    ];

    let applied = {};
    for (const patch of matrix) {
      const toggled = await toggleLayers(page, patch);
      expect(toggled, `toggle result for ${JSON.stringify(patch)}`).toEqual(
        Object.keys(patch).reduce((acc, k) => { acc[k] = 'ok'; return acc; }, {})
      );
      applied = Object.assign({}, applied, patch);
      const state = await readLayerState(page);
      expect(state.visibility, `visibility after ${JSON.stringify(patch)}`).toEqual(expectedVisibility(applied));
      expect(state.checkboxes, `checkbox state after ${JSON.stringify(patch)}`).toEqual(
        ENC_KEYS.reduce((acc, k) => { acc[k] = applied[k] !== false; return acc; }, {})
      );

      const depthOn = applied.depare !== false || applied.depcnt !== false || applied.soundg !== false;
      const expectedProfile = applied['enc-chart'] === false ? null : (depthOn ? 'aids' : 'standard');
      expect(state.profile, `ENC-3 profile after ${JSON.stringify(patch)}`).toBe(expectedProfile);
    }

    expect(diag.pageErrors, 'no uncaught page errors while toggling layers').toEqual([]);
    expect(diag.console.filter(m => /TypeError|ReferenceError|Unhandled/i.test(m)), 'no fatal console errors while toggling layers').toEqual([]);
  });

  test('fusion presets apply their declared basemap + ENC combo and keep ENC-3 in sync', async ({ page }) => {
    const diag = { console: [], pageErrors: [], failedRequests: [] };
    attachHarbourDiagnostics(page, diag);

    await bootHarbour(page, { waitRendererStatus: false });
    await clickRail(page, 'layers');

    const presetIds = await page.evaluate(() => window.HelmFusionPresets ? window.HelmFusionPresets.IDS : []);
    expect(presetIds, 'FUSE-1 preset ids are registered').toEqual(
      expect.arrayContaining(['depth-on-sat', 'standard-enc', 'sat-only', 'passage-prep'])
    );

    for (const id of presetIds) {
      await page.locator(`[data-fusion-preset="${id}"]`).click();
      await page.waitForFunction((pid) => window.HelmFusionPresets.readActive() === pid, id, { timeout: 5000 });

      const result = await page.evaluate(({ id, ids }) => {
        const preset = window.HelmFusionPresets.PRESETS[id];
        const vis = {};
        Object.keys(ids).forEach((key) => {
          const layerId = ids[key];
          vis[key] = window.map.getLayer(layerId) ? window.map.getLayoutProperty(layerId, 'visibility') || 'visible' : 'missing';
        });
        return {
          preset,
          visibility: vis,
          activeBasemapRadio: document.querySelector('input[name="basemap"]:checked') ? document.querySelector('input[name="basemap"]:checked').dataset.base : null,
          profile: window.HelmEncTileProfile.resolve()
        };
      }, { id, ids: ENC_LAYER_IDS });

      const expectedVis = {};
      ENC_KEYS.forEach((key) => { expectedVis[key] = result.preset.enc[key] === false ? 'none' : 'visible'; });
      expect(result.visibility, `preset ${id} layer visibility`).toEqual(expectedVis);
      expect(result.activeBasemapRadio, `preset ${id} basemap radio`).toBe(result.preset.basemap);

      const depthOn = result.preset.enc.depare !== false || result.preset.enc.depcnt !== false || result.preset.enc.soundg !== false;
      const expectedProfile = result.preset.enc['enc-chart'] === false ? null : (depthOn ? 'aids' : 'standard');
      expect(result.profile, `preset ${id} ENC-3 profile`).toBe(expectedProfile);
    }

    expect(diag.pageErrors, 'no uncaught page errors while cycling fusion presets').toEqual([]);
  });
});
