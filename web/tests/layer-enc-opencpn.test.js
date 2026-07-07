// Unit smoke for web/layer-enc-opencpn.js (LAYER-5 OpenCPN aids on satellite).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');

function loadModule(opts) {
  opts = opts || {};
  const win = {
    map: opts.map || null,
    HelmEndpoint: opts.endpoint || { tileTemplate: () => 'http://boat.local:8090/chart/{z}/{x}/{y}.png' }
  };
  const sandbox = { window: win, global: win, console };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'layer-enc-opencpn.js'), 'utf8'), sandbox);
  return { win, mod: win.HelmLayerEncOpenCPN };
}

function mockMap(vis) {
  vis = vis || {};
  return {
    getStyle() {
      return { layers: [{ id: 'googlesat' }, { id: 'enc-chart' }] };
    },
    getLayer(id) { return vis[id] === undefined ? { id: id } : (vis[id] === 'missing' ? null : { id: id }); },
    getLayoutProperty(id) { return vis[id] || 'visible'; }
  };
}

const { mod } = loadModule();
assert.strictEqual(mod.SYMBOL_AUTHORITY, 'opencpn-engine-png');
assert.strictEqual(mod.ENC_LAYER, 'enc-chart');

const fused = loadModule({
  map: mockMap({ googlesat: 'visible', 'enc-chart': 'visible' }),
  endpoint: { tileTemplate: () => 'http://127.0.0.1:8090/chart/{z}/{x}/{y}.png' }
});
const st = fused.mod.status(fused.win.map);
assert.strictEqual(st.fused_on_satellite, true);
assert.strictEqual(st.satellite_basemap, 'googlesat');
assert.strictEqual(st.icon_forge_deferred, true);
assert.ok(st.tile_template.includes('/chart/'));

const hidden = loadModule({ map: mockMap({ googlesat: 'visible', 'enc-chart': 'none' }) });
assert.strictEqual(hidden.mod.status(hidden.win.map).fused_on_satellite, false);
assert.strictEqual(hidden.mod.summary(hidden.win.map).mode, 'hidden');

console.log('layer-enc-opencpn.test.js: ok');
