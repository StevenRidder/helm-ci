/*
 * Helm — wx-field-texture-artifact.js (HELMWEBGPU-5)
 * --------------------------------------------------------------------------
 * Shared field-texture artifact seam for helm.env.grid.v1 consumers.
 *
 * The WX scene still samples verified numeric grids and MapLibre still owns
 * composition. This module names the backend-neutral handoff between the data
 * plane and render targets: one assembled environmental field becomes one
 * rg32float texture artifact with traceable source, failure policy, and a
 * deterministic payload checksum. Browser WebGPU and native/VSG harnesses can
 * consume the same artifact contract without making Python or precoloured PNGs
 * part of the runtime path.
 * --------------------------------------------------------------------------
 */
(function (global) {
  'use strict';

  var SCHEMA = 'helm.env.fieldTexture.artifact.v1';
  var FORMAT = 'rg32float';
  var SENTINEL = 1e30;

  function loudError(code, message, details) {
    var err = new Error(message || code);
    err.code = code;
    err.details = details || {};
    return err;
  }

  function assign(a, b) { for (var k in b) if (b && b.hasOwnProperty(k)) a[k] = b[k]; return a; }

  function textureDataFromAssembled(assembled, sentinel) {
    sentinel = sentinel == null ? SENTINEL : +sentinel;
    var m = assembled && assembled.meta;
    if (!m || !m.width || !m.height) throw loudError('bad_field_artifact', 'assembled field has no dimensions');
    if (!m.bands || !m.bands.length) throw loudError('bad_field_artifact', 'assembled field has no bands');
    var n = m.width * m.height;
    var data = new Float32Array(n * 2);
    var b0 = assembled.bands && assembled.bands[m.bands[0]];
    var b1 = m.bands.length > 1 ? assembled.bands[m.bands[1]] : null;
    if (!b0) throw loudError('bad_field_artifact', 'assembled field is missing primary band', { band: m.bands[0] });
    for (var i = 0; i < n; i++) {
      var a = b0[i], b = b1 ? b1[i] : 0;
      data[i * 2] = (a === a) ? a : sentinel;
      data[i * 2 + 1] = (b === b) ? b : (b1 ? sentinel : 0);
    }
    return data;
  }

  function fnv1aFloat32(data) {
    var h = 0x811c9dc5;
    var view = new DataView(new ArrayBuffer(4));
    for (var i = 0; i < data.length; i++) {
      view.setFloat32(0, data[i], true);
      for (var b = 0; b < 4; b++) {
        h ^= view.getUint8(b);
        h = Math.imul(h, 0x01000193) >>> 0;
      }
    }
    return ('00000000' + h.toString(16)).slice(-8);
  }

  function countCells(data, sentinel) {
    var valid = 0, nodata = 0;
    for (var i = 0; i < data.length; i += 2) {
      var bad = Math.max(Math.abs(data[i]), Math.abs(data[i + 1])) > Math.abs(sentinel) / 10;
      if (bad) nodata++;
      else valid++;
    }
    return { validCells: valid, nodataCells: nodata };
  }

  function createArtifact(opts) {
    opts = opts || {};
    var manifest = opts.manifest || {};
    var assembled = opts.assembled;
    var m = assembled && assembled.meta;
    if (!m) throw loudError('bad_field_artifact', 'assembled field has no metadata');
    var sentinel = opts.sentinel == null ? SENTINEL : +opts.sentinel;
    var data = textureDataFromAssembled(assembled, sentinel);
    var counts = countCells(data, sentinel);
    var hash = fnv1aFloat32(data);
    var layer = opts.layer || (m.layer || null);
    var validTime = opts.validTime || null;
    return {
      schema: SCHEMA,
      artifact_id: [
        'field-texture',
        String(manifest.packId || 'unknown').replace(/[^A-Za-z0-9_.-]+/g, '_'),
        layer || 'layer',
        validTime ? String(validTime).replace(/[^A-Za-z0-9_.-]+/g, '') : 'time',
        hash
      ].join(':'),
      source: {
        packId: manifest.packId || null,
        manifestUrl: opts.manifestUrl || null,
        generatedAt: manifest.generatedAt || null,
        provider: manifest.source && manifest.source.provider || null,
        model: manifest.source && manifest.source.model || null,
        advisoryOnly: manifest.source && manifest.source.advisoryOnly !== false,
        notForNavigation: !manifest.source || manifest.source.notForNavigation !== false
      },
      field: {
        layer: layer,
        validTime: validTime,
        tier: m.tier,
        kind: m.kind || 'scalar',
        bands: (m.bands || []).slice(),
        width: m.width,
        height: m.height,
        dx: m.dx,
        dy: m.dy,
        bbox: [m.west, m.south, m.east, m.north],
        global: !!m.global,
        unitFactor: opts.unitFactor == null ? 1 : +opts.unitFactor,
        chunksPlaced: assembled.chunksPlaced == null ? null : assembled.chunksPlaced
      },
      texture: assign(counts, {
        format: FORMAT,
        components: m.kind === 'vector' ? ['u', 'v'] : [m.bands[0], 'reserved'],
        sentinel: sentinel,
        byteLength: data.byteLength,
        payloadChecksum: 'fnv1a32:' + hash,
        data: data
      }),
      renderContract: {
        compositor: 'MapLibre',
        artifactConsumer: 'browser-js-webgpu',
        nativeConsumer: 'vsg-field-texture',
        timeInterpolation: 'value-before-color',
        alpha: 'premultiplied',
        particles: m.kind === 'vector' ? 'same-vector-grid' : 'not-applicable',
        substitution: 'forbidden'
      },
      runtime: {
        requiredBoatRuntime: 'C++',
        pythonRuntimeRequired: false,
        pythonRole: 'tooling/reference/fixture-only'
      }
    };
  }

  function toSerializableArtifact(artifact) {
    var out = JSON.parse(JSON.stringify(artifact, function (key, value) {
      if (key === 'data') return undefined;
      return value;
    }));
    return out;
  }

  function uploadTextureArtifact(device, artifact, usage) {
    if (!device || !device.createTexture || !device.queue || !device.queue.writeTexture) {
      throw loudError('unsupported_renderer_capability', 'WebGPU device cannot upload field texture artifact');
    }
    if (!artifact || artifact.schema !== SCHEMA) {
      throw loudError('bad_field_artifact', 'expected ' + SCHEMA);
    }
    var t = artifact.texture || {};
    var f = artifact.field || {};
    if (!(t.data instanceof Float32Array)) {
      throw loudError('bad_field_artifact', 'field texture artifact has no Float32 payload');
    }
    var gpuUsage = usage || (global.GPUTextureUsage &&
      (global.GPUTextureUsage.TEXTURE_BINDING | global.GPUTextureUsage.COPY_DST));
    if (!gpuUsage) throw loudError('unsupported_renderer_capability', 'GPUTextureUsage is unavailable');
    var tex = device.createTexture({ size: [f.width, f.height], format: t.format, usage: gpuUsage });
    device.queue.writeTexture({ texture: tex }, t.data, { bytesPerRow: f.width * 8 }, [f.width, f.height]);
    return tex;
  }

  var API = {
    SCHEMA: SCHEMA,
    FORMAT: FORMAT,
    SENTINEL: SENTINEL,
    createArtifact: createArtifact,
    textureDataFromAssembled: textureDataFromAssembled,
    toSerializableArtifact: toSerializableArtifact,
    uploadTextureArtifact: uploadTextureArtifact,
    _test: { fnv1aFloat32: fnv1aFloat32, countCells: countCells }
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else global.HelmWxFieldTextureArtifact = API;
})(typeof window !== 'undefined' ? window : this);
