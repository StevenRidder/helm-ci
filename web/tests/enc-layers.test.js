// Unit smoke for web/enc-layers.js (ENC-1 toggles + ENC-2 opacity).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadEncLayers(lsMap, artifact, paint) {
  const vis = {};
  const paints = Object.assign({
    'depare-fill': { 'fill-opacity': ['interpolate', ['linear'], ['get', 'DRVAL1'], 0, 0.5, 40, 0.05] },
    'depcnt-line': { 'line-opacity': 0.85 },
    'soundg-text': { 'text-opacity': 1 },
    'enc-chart': { 'raster-opacity': 1 }
  }, paint || {});
  const win = {
    map: {
      layers: { 'depare-fill': true, 'depcnt-line': true, 'soundg-text': true, 'enc-chart': true },
      getLayer(id) { return this.layers[id] ? { id: id } : null; },
      setLayoutProperty(id, prop, val) {
        if (prop === 'visibility') vis[id] = val;
      },
      getPaintProperty(id, prop) {
        return (paints[id] || {})[prop];
      },
      setPaintProperty(id, prop, val) {
        if (!paints[id]) paints[id] = {};
        paints[id][prop] = val;
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
      sliders: {
        depare: { dataset: { encOpacity: 'depare' }, value: '100' },
        depcnt: { dataset: { encOpacity: 'depcnt' }, value: '100' },
        soundg: { dataset: { encOpacity: 'soundg' }, value: '100' },
        'enc-chart': { dataset: { encOpacity: 'enc-chart' }, value: '100' }
      },
      querySelector(sel) {
        const m = sel.match(/data-enc-layer="([^"]+)"/);
        if (m) return this.boxes[m[1]];
        const o = sel.match(/data-enc-opacity="([^"]+)"/);
        return o ? this.sliders[o[1]] : null;
      },
      querySelectorAll(sel) {
        if (sel === 'input[data-enc-layer]') return Object.values(this.boxes);
        if (sel === 'input[data-enc-opacity]') return Object.values(this.sliders);
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
  return { win, vis, paints };
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
  const art = { visible: true, setVisible(v) { this.visible = v; }, getGpuLayer() { return { canvas: { style: { opacity: '1' } } }; } };
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

{
  const { win, paints } = loadEncLayers();
  win.HelmEncLayers.applyOpacity(win.map, 'depcnt', 50, { persist: true });
  ok(Math.abs(paints['depcnt-line']['line-opacity'] - 0.425) < 0.001, 'depcnt opacity scales scalar line-opacity');
  ok(win.HelmStore.get('ui.encLayerOpacity', {}).depcnt === 50, 'depcnt opacity persists');
}

{
  const { win, paints } = loadEncLayers();
  win.HelmEncLayers.applyOpacity(win.map, 'depare', 80, { persist: false });
  const expr = paints['depare-fill']['fill-opacity'];
  ok(Array.isArray(expr) && expr[0] === '*' && expr[2] === 0.8, 'depare opacity multiplies interpolated fill-opacity');
}

{
  const gpu = { canvas: { style: { opacity: '1' } } };
  const art = { getGpuLayer() { return gpu; } };
  const { win, paints } = loadEncLayers([], art);
  win.HelmEncLayers.applyOpacity(win.map, 'enc-chart', 40, { persist: false });
  ok(paints['enc-chart']['raster-opacity'] === 0.4, 'enc-chart raster-opacity scales');
  ok(gpu.canvas.style.opacity === '0.4', 'enc-chart WebGPU canvas opacity syncs');
}

{
  const { win, paints } = loadEncLayers([['helm.ui.encLayerOpacity', '{"soundg":25}']]);
  win.HelmEncLayers.restoreOpacity(win.map);
  ok(paints['soundg-text']['text-opacity'] === 0.25, 'restoreOpacity applies saved soundg pct');
  ok(win.document.sliders.soundg.value === '25', 'restoreOpacity syncs slider');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
