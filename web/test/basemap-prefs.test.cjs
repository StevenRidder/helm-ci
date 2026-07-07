// Unit smoke for web/basemap-prefs.js (SAT-1 basemap memory).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadBasemapPrefs(lsMap) {
  const win = {
    map: {
      layers: { navionics: true, googlesat: true, bingsat: true, arcgis: true },
      getLayer(id) { return this.layers[id] ? { id: id } : null; },
      vis: {},
      setLayoutProperty(id, prop, val) {
        if (prop === 'visibility') this.vis[id] = val;
      }
    },
    HelmStore: null,
    HelmOfflinePacks: { state: { activeId: null } },
    document: {
      radios: [
        { name: 'basemap', dataset: { base: 'navionics' }, checked: true },
        { name: 'basemap', dataset: { base: 'googlesat' }, checked: false }
      ],
      querySelectorAll(sel) {
        if (sel === 'input[name="basemap"]') return this.radios;
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
    },
    remove(k) { store.delete('helm.' + k); }
  };
  const sandbox = { window: win, document: win.document, console };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'basemap-prefs.js'), 'utf8'), sandbox, { filename: 'basemap-prefs.js' });
  return win;
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const win = loadBasemapPrefs();
  win.HelmBasemapPrefs.applyStatic(win.map, 'googlesat', { persist: true });
  ok(win.map.vis.googlesat === 'visible', 'applyStatic shows chosen layer');
  ok(win.map.vis.navionics === 'none', 'applyStatic hides other layers');
  ok(win.HelmStore.get('ui.basemap', '') === 'googlesat', 'applyStatic persists to HelmStore');
  ok(win.document.radios[1].checked === true, 'applyStatic checks matching radio');
}

{
  const win = loadBasemapPrefs([['helm.ui.basemap', '"bingsat"']]);
  win.HelmBasemapPrefs.restoreStatic(win.map);
  ok(win.map.vis.bingsat === 'visible', 'restoreStatic applies saved basemap');
}

{
  const win = loadBasemapPrefs([['helm.ui.basemap', '"googlesat"'], ['helm.offline.activePack', '"fiji-sat"']]);
  const r = win.HelmBasemapPrefs.restoreStatic(win.map);
  ok(r === null, 'restoreStatic skips when offline pack is stored');
  ok(win.map.vis.googlesat !== 'visible', 'offline intent does not apply static restore');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
