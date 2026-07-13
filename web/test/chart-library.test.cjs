// Unit test for web/chart-library.js (INTAKE-5 Chart Library panel).
// Pure decision core only: catalog id join, freshness mapping, group tabs,
// empty-state selection, validation badges. No browser, no network, no DOM —
// the module registers nothing without window.HelmShell. Auto-joins run.mjs.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

function load() {
  const win = {};
  const sandbox = { window: win, console: { log() {}, warn() {} } };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'chart-library.js'), 'utf8'), sandbox, { filename: 'chart-library.js' });
  return win.HelmChartLibrary;
}

const M = load();
let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  PASS  ' : '  FAIL  ') + m); c ? pass++ : fail++; };

// ---- fixtures ---------------------------------------------------------------------------------
const lagoon = { id: 'chart-1', root_id: 'root-a', relative_path: 'FIJI/lagoon.mbtiles', filename: 'lagoon.mbtiles',
  group: 'FIJI', chart_type: 'tile_pack', extension: '.mbtiles', size_bytes: 5 * 1048576,
  bbox: [178, -18, 179, -17], validation: { status: 'valid', code: 'ok', message: 'ok' } };
const reef = { id: 'chart-2', root_id: 'root-a', relative_path: 'TONGA/reef.pmtiles', filename: 'reef.pmtiles',
  group: 'TONGA', chart_type: 'tile_pack', extension: '.pmtiles', size_bytes: 1024,
  validation: { status: 'valid', code: 'ok', message: 'ok' } };
const cell = { id: 'chart-3', root_id: 'root-a', relative_path: 'cell.000', filename: 'cell.000', group: '.',
  chart_type: 'enc', extension: '.000', size_bytes: 10, update_count: 2, latest_update: 2,
  validation: { status: 'error', code: 'contents_extension_mismatch', message: 'junk' } };
const passage = { id: 'chart-4', root_id: 'root-a', relative_path: 'FIJI/passage.geojson', filename: 'passage.geojson',
  group: 'FIJI', chart_type: 'overlay', extension: '.geojson', size_bytes: 200,
  validation: { status: 'valid', code: 'ok', message: 'ok' } };

// ---- collision pack id mirrors the server -----------------------------------------------------
ok(M.collisionPackId('FIJI/SAT/lagoon.mbtiles') === 'FIJI--SAT--lagoon', 'collisionPackId: subdirs join with --');
ok(M.collisionPackId('a b/c!.mbtiles') === 'a-b--c', 'collisionPackId: punctuation collapses to single dash, ends trimmed');
ok(M.collisionPackId('!!!.mbtiles') === 'pack', 'collisionPackId: degenerate input falls back to "pack"');

// ---- catalog join -----------------------------------------------------------------------------
{
  const catalog = { lagoon: { id: 'lagoon', staleness: { status: 'stale', age_days: 40 } } };
  ok(M.catalogIdCandidates(lagoon).join() === 'lagoon,FIJI--lagoon', 'candidates: filename stem first, collision id second');
  ok(M.catalogRecordFor(lagoon, catalog).id === 'lagoon', 'join finds the stem-keyed catalog record');
  const collided = { 'FIJI--lagoon': { id: 'FIJI--lagoon' } };
  ok(M.catalogRecordFor(lagoon, collided).id === 'FIJI--lagoon', 'join falls back to the collision id');
  const suffixed = { 'lagoon--r2': { id: 'lagoon--r2' } };
  ok(M.catalogRecordFor(lagoon, suffixed).id === 'lagoon--r2', 'join tolerates the cross-root --rN suffix');
  ok(M.catalogRecordFor(lagoon, {}) === null, 'join returns null when the pack is not served');
  ok(M.catalogRecordFor(passage, catalog) === null, 'overlays never join /catalog');
}

// ---- freshness mapping (CAT-1 staleness, honest fallbacks) -------------------------------------
{
  const stale = M.freshnessFor(lagoon, { staleness: { status: 'stale', age_days: 40 } }, '');
  ok(stale.status === 'stale' && /40d/.test(stale.label), 'tile pack + stale staleness -> stale with age');
  const fresh = M.freshnessFor(lagoon, { staleness: { status: 'fresh', age_days: 3 } }, '');
  ok(fresh.status === 'fresh', 'tile pack + fresh staleness -> fresh');
  const unknown = M.freshnessFor(lagoon, { staleness: { status: 'unknown' } }, '');
  ok(unknown.status === 'unknown' && /render_date/.test(unknown.label), 'unknown staleness names the missing sidecar, never fakes fresh');
  const unlisted = M.freshnessFor(lagoon, null, '');
  ok(unlisted.status === 'unlisted' && /catalog/.test(unlisted.label), 'pack missing from /catalog says so');
  const down = M.freshnessFor(lagoon, null, 'connection refused');
  ok(down.status === 'unknown' && /unreachable/.test(down.label), 'catalog fetch failure -> unknown with the named reason');
  const enc = M.freshnessFor(cell, null, '');
  ok(enc.status === 'enc' && /2 update cells/.test(enc.label), 'ENC row reports its update cells');
}

// ---- validation badge --------------------------------------------------------------------------
ok(M.validationBadge(lagoon) === null, 'valid chart -> no badge');
{
  const badge = M.validationBadge(cell);
  ok(badge.level === 'error' && badge.code === 'contents_extension_mismatch', 'invalid chart -> error badge with the named code');
}

// ---- groups ------------------------------------------------------------------------------------
{
  const groups = M.groupsOf([lagoon, reef, cell, passage]);
  ok(groups.join() === 'FIJI,TONGA,.', 'groups: named regions alphabetical, top-level last');
  ok(M.groupLabel('.') === 'Top level' && M.groupLabel('FIJI') === 'FIJI', 'group labels');
  ok(M.chartsInGroup([lagoon, reef, cell], 'FIJI').length === 1, 'group filter');
  ok(M.chartsInGroup([lagoon, reef, cell], 'all').length === 3, '"all" passes everything through');
}

// ---- empty states -------------------------------------------------------------------------------
{
  ok(M.emptyStateFor(null, 'boom').kind === 'error', 'index fetch failure -> error state');
  ok(M.emptyStateFor(null, '').kind === 'loading', 'no index yet -> loading state');
  const firstRun = M.emptyStateFor({ chart_count: 0, roots: [{ id: 'r', default: true, status: 'available' }] }, '');
  ok(firstRun.kind === 'first-run', 'empty library with a reachable root -> first-run prompt');
  const missing = M.emptyStateFor({ chart_count: 0, roots: [{ id: 'r', status: 'unavailable' }] }, '');
  ok(missing.kind === 'roots-missing', 'all roots unavailable -> roots-missing state');
  ok(M.emptyStateFor({ chart_count: 3, roots: [] }, '') === null, 'charts present -> no empty state');
}

// ---- formatting ---------------------------------------------------------------------------------
ok(M.fmtSize(5 * 1048576) === '5.0 MB' && M.fmtSize(1024) === '1 KB', 'size formatting');
ok(M.typeLabel(lagoon) === 'MBTiles' && M.typeLabel(reef) === 'PMTiles' && M.typeLabel(cell) === 'ENC S-57' && M.typeLabel(passage) === 'GeoJSON overlay', 'type labels');

console.log(`\nchart-library: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
