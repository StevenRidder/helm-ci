// RENDERMODEL-5: multi-zoom artifact pyramid index + geometry density gate.
// Run: node web/test/rendermodel5-pyramid-parity.test.cjs
const fs = require('fs'), path = require('path');
const { spawnSync } = require('child_process');
const assert = require('assert');

const WEB = path.join(__dirname, '..');
const ROOT = path.join(WEB, '..');
const indexPath = path.join(WEB, 'data', 'render-artifact-index-us5ga2bc.json');

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

if (!fs.existsSync(indexPath)) {
  console.log('  skip - render-artifact-index-us5ga2bc.json not built yet (run scripts/render-artifact-pyramid)');
  process.exit(0);
}

const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));

ok('index schema is helm.render.artifact_index.v1', () => {
  assert.strictEqual(index.schema_version, 'helm.render.artifact_index.v1');
  assert.strictEqual(index.cell_id, 'US5GA2BC');
});

ok('index lists >= 30 tile packets across z11-z15', () => {
  assert.ok(index.tile_count >= 30, `tile_count ${index.tile_count}`);
  assert.ok(index.entries.length >= 30);
  const zmax = Math.max(...index.entries.map(e => e.tile.z));
  assert.ok(zmax >= 15, `expected z15 tiles, max z=${zmax}`);
});

ok('z16 documented as NODTA when omitted from pyramid', () => {
  const zmax = index.z_range ? index.z_range[1] : null;
  if (zmax === 16) return;
  assert.ok(Array.isArray(index.nodata_z_levels) && index.nodata_z_levels.includes(16),
    'nodata_z_levels must include 16 when z16 not built');
});

ok('each entry resolves a committed artifact on disk', () => {
  for (const e of index.entries) {
    const p = path.join(WEB, e.artifact_url);
    assert.ok(fs.existsSync(p), `missing ${e.artifact_url}`);
    const art = JSON.parse(fs.readFileSync(p, 'utf8'));
    assert.strictEqual(art.schema_version, 'helm.render.artifact.v1');
  }
});

ok('render-artifact-compile --check reproduces sample pyramid packets', () => {
  const samples = index.entries.filter(e => e.tile.z === 13).slice(0, 1)
    .concat(index.entries.filter(e => e.tile.z === 15).slice(0, 1));
  for (const e of samples) {
    const rel = e.fixture_relpath || '';
    const fixtureDir = rel
      ? path.join(ROOT, 'engine/captures/us5ga2bc', path.dirname(rel).replace(/^pyramid\//, 'pyramid/'))
      : null;
    if (!fixtureDir || !fs.existsSync(path.join(fixtureDir, 'scene.commands.json'))) continue;
    const res = spawnSync(path.join(ROOT, 'scripts/render-artifact-compile'),
      [fixtureDir, '--check'], { encoding: 'utf8' });
    assert.strictEqual(res.status, 0, `compile --check failed for z${e.tile.z}/${e.tile.x}/${e.tile.y}: ${res.stderr}`);
  }
});

function sumVertsForTileFootprint(entries, zParent, xParent, yParent, zChild) {
  const scale = 1 << (zChild - zParent);
  const x0 = xParent * scale;
  const y0 = yParent * scale;
  const x1 = x0 + scale - 1;
  const y1 = y0 + scale - 1;
  return entries
    .filter(e => e.tile.z === zChild &&
      e.tile.x >= x0 && e.tile.x <= x1 &&
      e.tile.y >= y0 && e.tile.y <= y1)
    .reduce((s, e) => s + (e.vertex_count || 0), 0);
}

ok('higher zoom same footprint has more geometry than z13 (not identical stretch)', () => {
  const byZ = {};
  for (const e of index.entries) byZ[e.tile.z] = (byZ[e.tile.z] || []).concat(e);
  const z13Center = (byZ[13] || []).find(e => e.tile.x === 2241 && e.tile.y === 3357)
    || (byZ[13] || []).sort((a, b) => b.vertex_count - a.vertex_count)[0];
  assert.ok(z13Center, 'need z13 harbor center tile 2241/3357 or fallback');
  const z15Sum = sumVertsForTileFootprint(index.entries, z13Center.tile.z, z13Center.tile.x,
    z13Center.tile.y, 15);
  assert.ok(z15Sum > 0, 'need z15 child tiles covering z13 center footprint');
  assert.ok(z15Sum > z13Center.vertex_count * 1.15,
    `z15 footprint verts ${z15Sum} must exceed z13 center ${z13Center.vertex_count} by >15%`);
});

console.log(`\n${pass} checks passed`);
