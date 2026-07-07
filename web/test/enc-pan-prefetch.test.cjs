// Unit smoke for web/enc-pan-prefetch.js (SAT-2 never-blank pan).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadModule(opts) {
  opts = opts || {};
  const warmed = [];
  const win = {
    map: opts.map || null,
    HelmEncLayers: { isOn: () => true },
    HelmBasemapPrefs: {
      offlinePackId: () => opts.offlinePack || null,
      restoreStatic: (m) => {
        win._restored = true;
        if (m && m.vis) {
          m.vis.navionics = 'visible';
        }
      }
    },
    HelmStore: opts.store || { keys: () => [], get: (_, d) => d },
    HelmEndpoint: { tileTemplate: () => 'http://127.0.0.1:8090/chart/{z}/{x}/{y}.png' },
    Image: function () {
      this.decoding = '';
      Object.defineProperty(this, 'src', {
        set(v) { warmed.push(v); },
        get() { return ''; }
      });
    },
    document: { querySelector: () => null }
  };
  const sandbox = { window: win, document: win.document, console, Image: win.Image };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'enc-pan-prefetch.js'), 'utf8'), sandbox, { filename: 'enc-pan-prefetch.js' });
  win._warmed = warmed;
  return win;
}

function mockMap(overrides) {
  const vis = Object.assign({ googlesat: 'visible', 'helm-chart-online-fill': 'none' }, (overrides && overrides.vis) || {});
  const style = overrides && overrides.style || {
    sources: {
      googlesat: { bounds: [175.0, -22.5, 180.5, -11.0] }
    }
  };
  return {
    vis: vis,
    zoom: overrides && overrides.zoom != null ? overrides.zoom : 12,
    center: overrides && overrides.center || { lng: 177.5, lat: -17.5 },
    getLayer(id) { return vis[id] != null ? { id: id } : null; },
    setLayoutProperty(id, prop, val) { if (prop === 'visibility') vis[id] = val; },
    getLayoutProperty(id, prop) { return prop === 'visibility' ? vis[id] : null; },
    getZoom() { return this.zoom; },
    getCenter() { return this.center; },
    getBounds() {
      return {
        getWest: () => this.center.lng - 0.2,
        getEast: () => this.center.lng + 0.2,
        getNorth: () => this.center.lat + 0.2,
        getSouth: () => this.center.lat - 0.2
      };
    },
    getStyle() { return style; },
    on() {},
    isStyleLoaded: () => true
  };
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const win = loadModule();
  ok(win.HelmEncPanPrefetch.pointInBounds({ lng: 177, lat: -17 }, [175, -22, 180, -11]), 'point inside Fiji bounds');
  ok(!win.HelmEncPanPrefetch.pointInBounds({ lng: 10, lat: 50 }, [175, -22, 180, -11]), 'point outside Fiji bounds');
}

{
  const map = mockMap({ vis: { googlesat: 'none', navionics: 'none' } });
  const win = loadModule({ map: map });
  win.HelmEncPanPrefetch._test.resetPrefetchSeen();
  ok(win.HelmEncPanPrefetch.ensureBasemapUnderEnc(map), 'restores basemap when all static layers hidden');
  ok(win._restored === true, 'restoreStatic called');
}

{
  const map = mockMap();
  const win = loadModule({ map: map });
  win.HelmEncPanPrefetch._test.resetPrefetchSeen();
  const n = win.HelmEncPanPrefetch.prefetchEnc(map);
  ok(n > 0, 'prefetch warms ENC tiles for viewport');
  ok(win._warmed.some(u => /\/chart\/\d+\/\d+\/\d+\.png/.test(u)), 'prefetch uses engine tile template');
}

{
  const map = mockMap({
    center: { lng: 10, lat: 50 },
    vis: { googlesat: 'visible', 'helm-chart-online-fill': 'none' }
  });
  const win = loadModule({ map: map });
  win.HelmEncPanPrefetch._test.resetOpportunistic();
  const on = win.HelmEncPanPrefetch.syncOpportunisticFill(map);
  ok(on === true, 'opportunistic online-fill outside owned pack bounds');
  ok(map.vis['helm-chart-online-fill'] === 'visible', 'online-fill layer shown opportunistically');
}

{
  const map = mockMap();
  const win = loadModule({
    map: map,
    store: { keys: () => ['ui.onlineFill'], get: (k, d) => (k === 'ui.onlineFill' ? false : d) }
  });
  win.HelmEncPanPrefetch._test.resetOpportunistic();
  map.center = { lng: 10, lat: 50 };
  win.HelmEncPanPrefetch.syncOpportunisticFill(map);
  ok(map.vis['helm-chart-online-fill'] !== 'visible', 'respects explicit ui.onlineFill user preference');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
