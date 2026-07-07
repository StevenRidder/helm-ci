// Unit smoke for web/fusion-presets.js (FUSE-1 fusion presets).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadFusion(opts) {
  opts = opts || {};
  const vis = {};
  const encState = { depare: true, depcnt: true, soundg: true, 'enc-chart': true };
  const win = {
    map: {
      layers: [
        { id: 'googlesat' }, { id: 'navionics' }, { id: 'depare-fill' }, { id: 'depcnt-line' },
        { id: 'soundg-text' }, { id: 'enc-chart' }, { id: 'route-line' }, { id: 'ais-symbols' }
      ],
      getStyle() { return { layers: this.layers }; },
      getLayer(id) { return this.layers.find(l => l.id === id) ? { id } : null; },
      setLayoutProperty(id, prop, val) {
        if (prop === 'visibility') vis[id] = val;
      }
    },
    HelmStore: null,
    HelmBasemapPrefs: {
      offlinePackId: () => opts.offlinePack || null,
      applyStatic(map, pick, o) {
        win._basemap = pick;
        win._basemapPersist = !!(o && o.persist);
        return pick;
      }
    },
    HelmEncLayers: {
      KEYS: ['depare', 'depcnt', 'soundg', 'enc-chart'],
      defaults() { return { depare: true, depcnt: true, soundg: true, 'enc-chart': true }; },
      applyAll(map, state, o) {
        Object.assign(encState, state);
        win._encPersist = !!(o && o.persist);
      },
      readState() { return Object.assign({}, encState); }
    },
    HelmLayerEncOpenCPN: {
      status() {
        return {
          fused_on_satellite: win._basemap === 'googlesat' && encState['enc-chart']
        };
      }
    },
    document: {
      buttons: [
        { dataset: { fusionPreset: 'depth-on-sat' }, classList: { _on: false, toggle(k, v) { this._on = v; } }, setAttribute() {} },
        { dataset: { fusionPreset: 'standard-enc' }, classList: { _on: false, toggle(k, v) { this._on = v; } }, setAttribute() {} },
        { dataset: { fusionPreset: 'sat-only' }, classList: { _on: false, toggle(k, v) { this._on = v; } }, setAttribute() {} },
        { dataset: { fusionPreset: 'passage-prep' }, classList: { _on: false, toggle(k, v) { this._on = v; } }, setAttribute() {} }
      ],
      overlayBoxes: {
        'route-line': { checked: false },
        ais: { checked: false }
      },
      querySelectorAll(sel) {
        if (sel === '[data-fusion-preset]') return this.buttons;
        return [];
      },
      querySelector(sel) {
        const m = sel.match(/data-layer="([^"]+)"/);
        return m ? this.overlayBoxes[m[1]] : null;
      }
    }
  };
  const store = new Map();
  win.HelmStore = {
    get(k, d) {
      const v = store.get('helm.' + k);
      return v == null ? d : JSON.parse(v);
    },
    set(k, v) {
      store.set('helm.' + k, JSON.stringify(v));
      return true;
    }
  };

  const sandbox = { window: win, document: win.document, console };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'fusion-presets.js'), 'utf8'), sandbox, { filename: 'fusion-presets.js' });
  return { win, vis, encState, store };
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const { win, encState } = loadFusion();
  const d = win.HelmFusionPresets.apply(win.map, 'depth-on-sat', { persist: true });
  ok(win._basemap === 'googlesat', 'depth-on-sat picks satellite basemap');
  ok(encState.depare === true && encState['enc-chart'] === false, 'depth-on-sat enables depth not aids');
  ok(d && d.id === 'depth-on-sat', 'describe returns preset id');
  ok(win.HelmStore.get('ui.fusionPreset', null) === 'depth-on-sat', 'persists active preset');
}

{
  const { win, encState } = loadFusion();
  win.HelmFusionPresets.apply(win.map, 'sat-only', { persist: true });
  ok(encState.depare === false && encState['enc-chart'] === false, 'sat-only turns all ENC off');
}

{
  const { win, encState } = loadFusion();
  win.HelmFusionPresets.apply(win.map, 'standard-enc', { persist: false });
  ok(win._basemap === 'navionics', 'standard-enc picks navionics');
  ok(encState['enc-chart'] === true, 'standard-enc keeps enc-chart on');
}

{
  const { win, vis } = loadFusion();
  win.HelmFusionPresets.apply(win.map, 'passage-prep', { persist: false });
  ok(vis['route-line'] === 'visible', 'passage-prep shows route overlay');
}

{
  const { win } = loadFusion({ offlinePack: 'fiji-sat' });
  win.HelmFusionPresets.apply(win.map, 'depth-on-sat', { persist: false });
  ok(win._basemap == null, 'offline pack active: preset skips static basemap switch');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
