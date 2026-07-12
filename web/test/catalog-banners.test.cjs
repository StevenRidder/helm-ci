// Unit test for web/catalog-banners.js (CAT-2 catalog-honesty advisory banners).
// Pure decision core computeBanners({packs, manifestStatus}) + satellite classification + signature.
// No browser, no network, no DOM (the module's self-wire is guarded on setTimeout, absent here).
// Auto-joins web/test/run.mjs.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function load() {
  const win = {};
  // Deliberately NO document and NO setTimeout -> the module stays inert (only exposes the API).
  const sandbox = { window: win, console: { log() {}, warn() {} } };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'catalog-banners.js'), 'utf8'), sandbox, { filename: 'catalog-banners.js' });
  return win.HelmCatalogBanners;
}

const M = load();
let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };
const ids = (banners) => banners.map((b) => b.id);
const byId = (banners, id) => banners.filter((b) => b.id === id)[0] || null;

// ---- fixtures --------------------------------------------------------------------------------
const satFresh   = { id: 'sat-fiji', title: 'Sentinel-2 Fiji', kind: 'satellite', staleness: { status: 'fresh', age_days: 3 } };
const satStale   = { id: 'sat-fiji', title: 'Sentinel-2 Fiji', kind: 'satellite', staleness: { status: 'stale', age_days: 45 } };
const satStale2  = { id: 'sat-old',  title: 'Old Imagery',     kind: 'satellite', staleness: { status: 'stale', age_days: 120 } };
const chartStale = { id: 'navionics', title: 'Navionics FJ', kind: 'chart', staleness: { status: 'stale', age_days: 200 } };

function manifest(enc, extra) {
  const summary = Object.assign({ schema: 'helm.layer.manifest.v1', enc: enc || null,
    loaded: [], degraded: [], skipped: [], rejected: [], errors: [] }, extra || {});
  return { summary, lastError: null, trackedLayers: 0 };
}
const encAllPresent = { expected: ['depare', 'depcnt', 'soundg'], present: ['depare', 'depcnt', 'soundg'], missing: [] };
const encGap        = { expected: ['depare', 'depcnt', 'soundg'], present: ['depare'], missing: ['depcnt', 'soundg'] };

// ---- 1. healthy: nothing shows ----------------------------------------------------------------
{
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: manifest(encAllPresent) });
  ok(b.length === 0, 'healthy state (fresh sat, full ENC, no overlay errors) -> no banners');
}

// ---- 2. stale sat only ------------------------------------------------------------------------
{
  const b = M.computeBanners({ packs: [satStale], manifestStatus: manifest(encAllPresent) });
  ok(ids(b).join() === 'stale-sat', 'stale satellite pack -> exactly the stale-sat banner');
  ok(/45 days old/.test(byId(b, 'stale-sat').message), 'stale-sat message names the age in days (45 days old)');
  ok(/Sentinel-2 Fiji/.test(byId(b, 'stale-sat').message), 'stale-sat message names the pack');
  ok(byId(b, 'stale-sat').level === 'warn', 'stale-sat is a warn-level banner');
}

// ---- 3. only a SATELLITE pack triggers stale-sat; a stale CHART pack does not ------------------
{
  const b = M.computeBanners({ packs: [satFresh, chartStale], manifestStatus: manifest(encAllPresent) });
  ok(b.length === 0, 'a stale CHART pack does NOT raise the satellite-stale banner (kind !== satellite)');
}

// ---- 4. stalest satellite pack is chosen when several are stale --------------------------------
{
  const b = M.computeBanners({ packs: [satStale, satStale2], manifestStatus: manifest(encAllPresent) });
  ok(/120 days old/.test(byId(b, 'stale-sat').message), 'the OLDEST stale satellite pack is surfaced (120 > 45)');
}

// ---- 5. enc gap only --------------------------------------------------------------------------
{
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: manifest(encGap) });
  ok(ids(b).join() === 'enc-gap', 'missing ENC layers -> exactly the enc-gap banner');
  ok(/depcnt, soundg/.test(byId(b, 'enc-gap').message), 'enc-gap names the missing layers');
  ok(/2 of 3 expected/.test(byId(b, 'enc-gap').message), 'enc-gap quantifies missing vs expected');
}

// ---- 6. no ENC summary (absent/404 manifest) is NOT a fabricated gap ---------------------------
{
  const b1 = M.computeBanners({ packs: [satFresh], manifestStatus: manifest(null) });
  ok(b1.length === 0, 'null enc summary -> no enc-gap banner (we do not fabricate a gap)');
  const b2 = M.computeBanners({ packs: [satFresh], manifestStatus: null });
  ok(b2.length === 0, 'null manifestStatus -> no enc-gap / no missing-overlay banner');
  const b3 = M.computeBanners({ packs: [satFresh], manifestStatus: manifest({ expected: ['depare'], present: ['depare'], missing: [] }) });
  ok(b3.length === 0, 'enc summary with empty missing[] -> no gap');
}

// ---- 7. missing overlay: rejected (non-public url) --------------------------------------------
{
  const ms = manifest(encAllPresent, { rejected: [{ id: 'owned-notes', status: 'rejected', reason: 'non-public-url' }] });
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: ms });
  ok(ids(b).join() === 'missing-overlay', 'a rejected overlay -> exactly the missing-overlay banner');
  ok(/owned-notes/.test(byId(b, 'missing-overlay').message), 'missing-overlay names the overlay id');
}

// ---- 8. missing overlay: per-entry error (addSource/addLayer failed) ---------------------------
{
  const ms = manifest(encAllPresent, { errors: [{ id: 'anchorages', status: 'error', reason: 'addSource:boom' }] });
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: ms });
  ok(ids(b).join() === 'missing-overlay', 'a per-entry overlay error -> missing-overlay banner');
  ok(/anchorages/.test(byId(b, 'missing-overlay').message), 'missing-overlay names the failing overlay');
}

// ---- 9. missing overlay: multiple failures are counted + listed -------------------------------
{
  const ms = manifest(encAllPresent, {
    rejected: [{ id: 'notes', reason: 'non-public-url' }],
    errors: [{ id: 'reefs', reason: 'addLayer:boom' }]
  });
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: ms });
  ok(/2 user overlays/.test(byId(b, 'missing-overlay').message), 'two failed overlays -> counted as 2');
  ok(/notes/.test(byId(b, 'missing-overlay').message) && /reefs/.test(byId(b, 'missing-overlay').message), 'both failing overlay ids listed');
}

// ---- 10. whole-manifest load failure (no per-entry ids) surfaces separately --------------------
{
  const ms = { summary: { schema: null, enc: null, loaded: [], degraded: [], skipped: [], rejected: [],
    errors: [{ reason: 'load-failed', message: 'network down' }] }, lastError: { reason: 'load-failed', message: 'network down' } };
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: ms });
  ok(ids(b).join() === 'missing-overlay', 'whole-manifest load failure -> missing-overlay banner');
  ok(/network down/.test(byId(b, 'missing-overlay').message), 'load-failure banner names the underlying cause');
  ok(/unaffected/.test(byId(b, 'missing-overlay').message), 'load-failure banner reassures chart rendering is unaffected');
}

// ---- 11. intentional skips are NOT "missing" --------------------------------------------------
{
  const ms = manifest(encAllPresent, { skipped: [
    { id: 'sat.pmtiles', status: 'skipped', reason: 'deferred-to-offline-packs.js' },
    { id: 'depare', status: 'skipped', reason: 'base-owned' }
  ] });
  const b = M.computeBanners({ packs: [satFresh], manifestStatus: ms });
  ok(b.length === 0, 'deferred/base-owned skipped entries never raise a missing-overlay banner');
}

// ---- 12. all three at once, in stable order ---------------------------------------------------
{
  const ms = manifest(encGap, { rejected: [{ id: 'notes', reason: 'non-public-url' }] });
  const b = M.computeBanners({ packs: [satStale, chartStale], manifestStatus: ms });
  ok(ids(b).join() === 'stale-sat,enc-gap,missing-overlay', 'all three conditions -> three banners in [sat, enc, overlay] order');
}

// ---- 13. staleness via the `freshness` key (some packs) is honoured ----------------------------
{
  const p = { id: 'sat-b', title: 'Bing Sat', kind: 'satellite', freshness: { status: 'stale', age_days: 10 } };
  const b = M.computeBanners({ packs: [p], manifestStatus: manifest(encAllPresent) });
  ok(ids(b).join() === 'stale-sat', 'a pack carrying freshness{} (not staleness{}) is still evaluated');
}

// ---- 14. satellite classification: kind + id/title fallback, no false positives ----------------
{
  ok(M.isSatellitePack({ kind: 'satellite' }) === true, 'kind=satellite -> satellite');
  ok(M.isSatellitePack({ id: 'sentinel-fiji', title: '' }) === true, 'id contains "sentinel" -> satellite (fallback)');
  ok(M.isSatellitePack({ id: 'x', title: 'Aerial Imagery' }) === true, 'title contains "imagery" -> satellite (fallback)');
  ok(M.isSatellitePack({ id: 'navionics', title: 'Navionics', kind: 'chart' }) === false, 'chart pack -> not satellite');
  ok(M.isSatellitePack({ id: 'depare', title: 'Depth soundings', kind: 'raster' }) === false, 'depth/soundings pack -> not satellite');
  ok(M.isSatellitePack(null) === false, 'null pack -> not satellite (no throw)');
}

// ---- 15. age text edge cases ------------------------------------------------------------------
{
  const zero = M.computeBanners({ packs: [{ kind: 'satellite', title: 'S', staleness: { status: 'stale', age_days: 0 } }], manifestStatus: manifest(encAllPresent) });
  ok(/less than a day old/.test(byId(zero, 'stale-sat').message), 'age_days 0 -> "less than a day old"');
  const one = M.computeBanners({ packs: [{ kind: 'satellite', title: 'S', staleness: { status: 'stale', age_days: 1 } }], manifestStatus: manifest(encAllPresent) });
  ok(/\b1 day old\b/.test(byId(one, 'stale-sat').message), 'age_days 1 -> "1 day old" (singular)');
  const none = M.computeBanners({ packs: [{ kind: 'satellite', title: 'S', staleness: { status: 'stale' } }], manifestStatus: manifest(encAllPresent) });
  ok(byId(none, 'stale-sat') && /freshness window/.test(byId(none, 'stale-sat').message), 'missing age_days -> still a banner, worded without a day count');
}

// ---- 16. signature stability + change detection -----------------------------------------------
{
  const a = M.computeBanners({ packs: [satStale], manifestStatus: manifest(encAllPresent) });
  const b = M.computeBanners({ packs: [satStale], manifestStatus: manifest(encAllPresent) });
  ok(M.signature(a) === M.signature(b), 'identical inputs -> identical signature (no needless re-render)');
  const c = M.computeBanners({ packs: [satStale2], manifestStatus: manifest(encAllPresent) });
  ok(M.signature(a) !== M.signature(c), 'a different stale pack -> different signature (re-render / re-show)');
  ok(M.signature([]) === '', 'empty banner set -> empty signature');
}

// ---- 17. robustness: junk / partial inputs never throw ----------------------------------------
{
  ok(M.computeBanners().length === 0, 'no args -> no banners (no throw)');
  ok(M.computeBanners({ packs: 'nope', manifestStatus: 42 }).length === 0, 'garbage inputs -> no banners (no throw)');
  ok(M.computeBanners({ packs: [null, {}], manifestStatus: manifest(null) }).length === 0, 'null/empty packs -> no banners (no throw)');
}

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
