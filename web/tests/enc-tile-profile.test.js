// Unit smoke for web/enc-tile-profile.js (ENC-3 engine ?profile= wiring).
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function load(encState, endpoint) {
  const tiles = [];
  const win = {
    HelmEncLayers: {
      readState() { return Object.assign({ depare: true, depcnt: true, soundg: true, 'enc-chart': true }, encState || {}); }
    },
    HelmEndpoint: endpoint || {
      tileTemplate(opts) {
        const base = 'http://127.0.0.1:8090/chart/{z}/{x}/{y}.png';
        if (opts && opts.profile && opts.profile !== 'standard') {
          return base + '?profile=' + encodeURIComponent(opts.profile);
        }
        return base;
      }
    },
    map: {
      getSource(id) {
        return id === 'enc' ? { setTiles(u) { tiles.length = 0; tiles.push.apply(tiles, u); } } : null;
      },
      isStyleLoaded() { return true; },
      on() {}
    },
    document: {
      querySelectorAll() { return []; }
    }
  };
  const sandbox = { window: win, document: win.document, console };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'enc-tile-profile.js'), 'utf8'), sandbox, { filename: 'enc-tile-profile.js' });
  return { win, tiles };
}

let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

{
  const { win } = load({ depare: true, depcnt: false, soundg: false, 'enc-chart': true });
  ok(win.HelmEncTileProfile.resolve() === 'aids', 'depth layers on + enc-chart -> aids profile');
  ok(win.HelmEncTileProfile.tileUrl().includes('profile=aids'), 'tileUrl adds ?profile=aids');
}

{
  const { win } = load({ depare: false, depcnt: false, soundg: false, 'enc-chart': true });
  ok(win.HelmEncTileProfile.resolve() === 'standard', 'no depth layers -> standard');
  ok(!win.HelmEncTileProfile.tileUrl().includes('profile='), 'standard omits profile query');
}

{
  const { win } = load({ depare: true, 'enc-chart': false });
  ok(win.HelmEncTileProfile.resolve() === null, 'enc-chart off -> no profile');
}

{
  const { win, tiles } = load({ depare: true, soundg: true, 'enc-chart': true });
  ok(win.HelmEncTileProfile.sync(win.map) === true, 'sync updates enc source');
  ok(tiles[0] && tiles[0].includes('profile=aids'), 'sync sets aids tile template');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
