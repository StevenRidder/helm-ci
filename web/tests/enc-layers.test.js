// Unit smoke for web/enc-layers.js (ENC-1 layer toggles).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadEncLayers(lsMap, artifact) {
  const vis = {};
  const win = {
    map: {
      layers: { 'depare-fill': true, 'depcnt-line': true, 'soundg-text': true, 'enc-chart': true },
      getLayer(id) { return this.layers[id] ? { id: id } : null; },
      setLayoutProperty(id, prop, val) {
        if (prop === 'visibility') vis[id] = val;
      }
    },
    __helmChartArtifact: artifact || null,
    HelmStore: null,
    document: {
      boxes: {
        depare: { dataset: { encLayer: 'depare' }, checked: true },
        depcnt: { dataset: { encLayer: 'depcnt' }, checked: true },
        soundg: { dataset: { encLayer: 'soundg' }, checked: true },
        'enc-chart': { dataset: { encLayer: 'enc-chart' }, checked: true }
      },
      querySelector(sel) {
        const m = sel.match(/data-enc-layer="([^"]+)"/);
        return m ? this.boxes[m[1]] : null;
      },
      querySelectorAll(sel) {
        if (sel === 'input[data-enc-layer]') return Object.values(this.boxes);
        return [];
      }
    }
  };
  const store = new Map(lsMap || []);
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
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'enc-layers.js'), 'utf8'), sandbox, { filename: 'enc-layers.js' });
  return { win, vis };
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const { win, vis } = loadEncLayers();
  win.HelmEncLayers.applyLayer(win.map, 'depare', false, { persist: true });
  ok(vis['depare-fill'] === 'none', 'depare off hides depare-fill');
  ok(win.document.boxes.depare.checked === false, 'depare checkbox syncs');
  ok(win.HelmStore.get('ui.encLayers', {}).depare === false, 'depare persists to HelmStore');
}

{
  const { win, vis } = loadEncLayers();
  win.HelmEncLayers.applyLayer(win.map, 'depcnt', false, { persist: false });
  ok(vis['depcnt-line'] === 'none', 'depcnt off hides depcnt-line');
}

{
  const art = { visible: true, setVisible(v) { this.visible = v; } };
  const { win, vis } = loadEncLayers([], art);
  win.HelmEncLayers.applyLayer(win.map, 'enc-chart', false, { persist: false });
  ok(vis['enc-chart'] === 'none', 'enc-chart off hides MapLibre raster');
  ok(art.visible === false, 'enc-chart off hides WebGPU artifact');
}

{
  const { win, vis } = loadEncLayers([['helm.ui.encLayers', '{"depare":false,"soundg":false}']]);
  win.HelmEncLayers.restore(win.map);
  ok(vis['depare-fill'] === 'none', 'restore applies saved depare off');
  ok(vis['soundg-text'] === 'none', 'restore applies saved soundg off');
  ok(vis['depcnt-line'] === 'visible', 'restore leaves unset layers at default on');
}

{
  const { win } = loadEncLayers();
  ok(win.HelmEncLayers.mapLayerId('depare') === 'depare-fill', 'mapLayerId maps depare');
  ok(win.HelmEncLayers.isOn('soundg') === true, 'isOn reads checkbox');
  win.document.boxes.soundg.checked = false;
  ok(win.HelmEncLayers.isOn('soundg') === false, 'isOn reflects checkbox change');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
