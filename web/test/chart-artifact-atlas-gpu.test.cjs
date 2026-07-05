// WEBGPU-3: GPU atlas manifest + upload plan unit tests.
const fs = require('fs'), path = require('path');
const assert = require('assert');

const A = require(path.join(__dirname, '..', 'chart-artifact-atlas.js'));
const AG = require(path.join(__dirname, '..', 'chart-artifact-atlas-gpu.js'));
const fixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'data', 'render-artifact-chart-1.json'), 'utf8'));
const gpuManifest = A.loadGpuManifest(JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'data', 's52-atlas-web', 'manifest.json'), 'utf8')));

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

ok('loadGpuManifest parses helm.s52.atlas.web.v2', () => {
  assert.strictEqual(gpuManifest.schema_version, 'helm.s52.atlas.web.v2');
  assert.ok(Object.keys(gpuManifest.atlases).length >= 4);
});

ok('resolveGpuEntry returns uploadable UV for sym.boyspp day', () => {
  const g = A.resolveGpuEntry('sym.boyspp', 'symbol', 'day', gpuManifest);
  assert.ok(g && g.uploadable);
  assert.strictEqual(g.atlasImage, 'data/s52-atlas-web/s52_symbols_day.png');
  assert.strictEqual(g.uv.length, 4);
});

ok('resolveGlyphGpu resolves digit glyphs', () => {
  const g = A.resolveGlyphGpu('7', 'day', gpuManifest);
  assert.ok(g && g.uploadable);
  assert.ok(g.uv[2] > g.uv[0]);
});

ok('collectGpuUploadSpecs lists PNG sheets for day palette', () => {
  const specs = A.collectGpuUploadSpecs(gpuManifest, 'day');
  assert.ok(specs.length >= 4);
  assert.ok(specs.every(s => s.uploadable && /\.png$/.test(s.image)));
});

ok('resolveMaterial attaches gpu bitmap for buoy symbol', () => {
  const res = A.loadResources(JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 's52-atlas-fixture.json'), 'utf8')), gpuManifest);
  const mat = fixture.material_table.find(m => m.style_key === 'place_symbol');
  const r = A.resolveMaterial(mat, 'day', res);
  assert.ok(r.gpu && r.gpu.uploadable);
  assert.strictEqual(r.missing, false);
});

ok('resolveMaterial attaches gpu font for draw_sounding', () => {
  const res = A.loadResources(JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 's52-atlas-fixture.json'), 'utf8')), gpuManifest);
  const mat = fixture.material_table.find(m => m.style_key === 'draw_sounding');
  const r = A.resolveMaterial(mat, 'day', res);
  assert.ok(r.gpu && r.gpu.uploadable);
  assert.strictEqual(r.missing, false);
});

ok('atlasRefsGpuComplete passes for chart-1 atlas_refs (excluding raster)', () => {
  const res = A.loadResources(JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 's52-atlas-fixture.json'), 'utf8')), gpuManifest);
  const check = A.atlasRefsGpuComplete(fixture, 'day', gpuManifest);
  assert.strictEqual(check.complete, true, 'missing: ' + check.missing.join(','));
});

ok('buildTexQuadsForBatch emits symbol quads for buoy batch', () => {
  const res = A.resolveArtifact(fixture, 'day', A.loadResources(JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 's52-atlas-fixture.json'), 'utf8')), gpuManifest));
  const batch = fixture.draw_batches.find(b => b.shader_family === 'SymbolInstanced');
  const rm = res.materials[batch.material_index];
  const verts = AG.buildTexQuadsForBatch(fixture, batch, rm, gpuManifest, 'day', A);
  assert.ok(verts && verts.length >= 36);
});

ok('buildTexQuadsForBatch emits glyph quads for sounding label 7.4', () => {
  assert.ok(Array.isArray(fixture.text_instances) && fixture.text_instances.length >= 1);
  const res = A.resolveArtifact(fixture, 'day', A.loadResources(JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'data', 's52-atlas-fixture.json'), 'utf8')), gpuManifest));
  const batch = fixture.draw_batches.find(b => b.batch_id === 'batch.cmd.sounding.soundg-1');
  const rm = res.materials[batch.material_index];
  const verts = AG.buildTexQuadsForBatch(fixture, batch, rm, gpuManifest, 'day', A);
  assert.ok(verts && verts.length >= 36 * 3);
});

console.log('\n' + pass + ' passed');
