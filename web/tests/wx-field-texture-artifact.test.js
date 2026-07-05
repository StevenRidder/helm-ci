// HELMWEBGPU-5 unit test: shared field-texture artifact for helm.env.grid.v1.
// Run: node web/tests/wx-field-texture-artifact.test.js
const assert = require('assert');
const A = require(require('path').join(__dirname, '..', 'wx-field-texture-artifact.js'));

let pass = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + ': ' + e.message); process.exitCode = 1; }
}

const manifest = {
  schema: 'helm.env.grid.pack.v1',
  encoding: 'helm.env.grid.v1',
  packId: 'synthetic/gfs/20260701T000000Z/global-low/global',
  generatedAt: '2026-07-01T00:20:00Z',
  source: { provider: 'synthetic', model: 'fixture', advisoryOnly: true, notForNavigation: true }
};

const vectorField = {
  chunksPlaced: 1,
  meta: {
    tier: 'global-low', kind: 'vector', bands: ['u', 'v'],
    width: 2, height: 2, dx: 0.5, dy: 0.5,
    west: -180, south: -90, east: -179.5, north: -89.5,
    global: true
  },
  bands: {
    u: Float32Array.from([1, NaN, -2, 3.5]),
    v: Float32Array.from([4, 5, NaN, -6])
  }
};

function legacyUploadPayload(assembled, sentinel) {
  const m = assembled.meta;
  const n = m.width * m.height;
  const data = new Float32Array(n * 2);
  const b0 = assembled.bands[m.bands[0]];
  const b1 = assembled.bands[m.bands[1]];
  for (let i = 0; i < n; i++) {
    const a = b0[i], b = b1[i];
    data[i * 2] = (a === a) ? a : sentinel;
    data[i * 2 + 1] = (b === b) ? b : sentinel;
  }
  return data;
}

ok('creates a traceable shared field-texture artifact', () => {
  const art = A.createArtifact({
    manifest,
    manifestUrl: '/wx-packs/current/manifest.json',
    layer: 'wind',
    validTime: '2026-07-01T00:00:00Z',
    assembled: vectorField,
    unitFactor: 1.9438445
  });
  assert.strictEqual(art.schema, A.SCHEMA);
  assert.strictEqual(art.texture.format, 'rg32float');
  assert.deepStrictEqual(art.texture.components, ['u', 'v']);
  assert.strictEqual(art.texture.validCells, 2);
  assert.strictEqual(art.texture.nodataCells, 2);
  assert.strictEqual(art.runtime.pythonRuntimeRequired, false);
  assert.strictEqual(art.renderContract.compositor, 'MapLibre');
  assert.strictEqual(art.renderContract.substitution, 'forbidden');
  assert.ok(art.artifact_id.includes('field-texture'));
});

ok('payload is byte-for-byte the previous WX scene rg32float upload layout', () => {
  const fromArtifact = A.textureDataFromAssembled(vectorField, A.SENTINEL);
  const legacy = legacyUploadPayload(vectorField, A.SENTINEL);
  assert.strictEqual(fromArtifact.byteLength, legacy.byteLength);
  assert.deepStrictEqual(Array.from(fromArtifact), Array.from(legacy));
});

ok('serializable artifact strips the runtime Float32 payload but keeps checksums', () => {
  const art = A.createArtifact({ manifest, layer: 'wind', validTime: '2026-07-01T00:00:00Z', assembled: vectorField });
  const serial = A.toSerializableArtifact(art);
  assert.strictEqual(serial.schema, A.SCHEMA);
  assert.strictEqual(serial.texture.data, undefined);
  assert.ok(/^fnv1a32:[0-9a-f]{8}$/.test(serial.texture.payloadChecksum));
});

ok('uploads through a generic WebGPU device boundary', () => {
  const calls = [];
  const fakeTexture = { id: 'texture' };
  const fakeDevice = {
    createTexture(desc) { calls.push(['createTexture', desc]); return fakeTexture; },
    queue: { writeTexture(dst, data, layout, size) { calls.push(['writeTexture', dst, data, layout, size]); } }
  };
  const art = A.createArtifact({ manifest, layer: 'wind', validTime: '2026-07-01T00:00:00Z', assembled: vectorField });
  assert.strictEqual(A.uploadTextureArtifact(fakeDevice, art, 3), fakeTexture);
  assert.deepStrictEqual(calls[0][1].size, [2, 2]);
  assert.strictEqual(calls[0][1].format, 'rg32float');
  assert.strictEqual(calls[1][3].bytesPerRow, 16);
  assert.deepStrictEqual(calls[1][4], [2, 2]);
});

console.log((process.exitCode ? 'FAIL' : 'ok') + ' - wx-field-texture-artifact: ' + pass + ' groups passed');
