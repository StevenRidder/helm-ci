/*
 * Helm — chart-artifact-atlas-gpu.js (WEBGPU-3)
 * Browser-side GPU texture cache for S-52 atlas PNG sheets.
 * Pure planning helpers are testable under node; upload requires WebGPU.
 */
(function (global) {
  'use strict';

  function atlasKindSlot(kind) {
    if (kind === 'symbol') return 0;
    if (kind === 'pattern') return 1;
    if (kind === 'line') return 2;
    if (kind === 'glyph') return 3;
    return -1;
  }

  function buildTextQuadVerts(x, y, char, glyphGpu, mat, pick, cellW, cellH) {
    if (!glyphGpu || !glyphGpu.uv || glyphGpu.uv.length < 4) return [];
    var u0 = glyphGpu.uv[0], v0 = glyphGpu.uv[1], u1 = glyphGpu.uv[2], v1 = glyphGpu.uv[3];
    var w = cellW || 8, h = cellH || 12;
    return [
      x, y, u0, v0, mat, pick,
      x + w, y, u1, v0, mat, pick,
      x + w, y + h, u1, v1, mat, pick,
      x, y, u0, v0, mat, pick,
      x + w, y + h, u1, v1, mat, pick,
      x, y + h, u0, v1, mat, pick
    ];
  }

  function buildSymbolQuadVertsFromPoint(x, y, gpu, mat, pick, scale) {
    if (!gpu || !gpu.uv || gpu.uv.length < 4) return [];
    var u0 = gpu.uv[0], v0 = gpu.uv[1], u1 = gpu.uv[2], v1 = gpu.uv[3];
    var aw = (gpu.pixel_rect && gpu.pixel_rect[2]) || 12;
    var ah = (gpu.pixel_rect && gpu.pixel_rect[3]) || 12;
    var ax = (gpu.anchor && gpu.anchor[0]) || aw * 0.5;
    var ay = (gpu.anchor && gpu.anchor[1]) || ah * 0.5;
    var s = scale == null ? 1 : scale;
    var w = aw * s, h = ah * s;
    var x0 = x - ax * s, y0 = y - ay * s;
    return [
      x0, y0, u0, v0, mat, pick,
      x0 + w, y0, u1, v0, mat, pick,
      x0 + w, y0 + h, u1, v1, mat, pick,
      x0, y0, u0, v0, mat, pick,
      x0 + w, y0 + h, u1, v1, mat, pick,
      x0, y0 + h, u0, v1, mat, pick
    ];
  }

  function buildTexQuadsForBatch(artifact, batch, resolvedMaterial, gpuManifest, palette, atlasApi) {
    var out = [];
    if (!batch || !resolvedMaterial || !resolvedMaterial.gpu) return null;
    var geo = artifact.geometry || {};
    var verts = artifact.vertices || geo.vertices_f32;
    var inds = artifact.indices || geo.indices_u32;
    if (!verts || !inds) return null;
    var gpu = resolvedMaterial.gpu;
    var A = atlasApi;
    if (batch.shader_family === 'SymbolInstanced' || (batch.topology === 'points' && resolvedMaterial.symbol)) {
      if (batch.topology === 'points') {
        var vi = inds[batch.first_index];
        var x = verts[vi * 4], y = verts[vi * 4 + 1];
        var mat = verts[vi * 4 + 2], pick = verts[vi * 4 + 3];
        out = out.concat(buildSymbolQuadVertsFromPoint(x, y, gpu, mat, pick, 1));
      } else {
        for (var k2 = 0; k2 + 2 < batch.index_count; k2 += 3) {
          var xs = [], ys = [], mat2 = 0, pick2 = 0;
          for (var t = 0; t < 3; t++) {
            var vi2 = inds[batch.first_index + k2 + t];
            xs.push(verts[vi2 * 4]); ys.push(verts[vi2 * 4 + 1]);
            mat2 = verts[vi2 * 4 + 2]; pick2 = verts[vi2 * 4 + 3];
          }
          var minX = Math.min(xs[0], xs[1], xs[2]), maxX = Math.max(xs[0], xs[1], xs[2]);
          var minY = Math.min(ys[0], ys[1], ys[2]), maxY = Math.max(ys[0], ys[1], ys[2]);
          var u0 = gpu.uv[0], v0 = gpu.uv[1], u1 = gpu.uv[2], v1 = gpu.uv[3];
          out = out.concat([
            minX, minY, u0, v0, mat2, pick2,
            maxX, minY, u1, v0, mat2, pick2,
            maxX, maxY, u1, v1, mat2, pick2,
            minX, minY, u0, v0, mat2, pick2,
            maxX, maxY, u1, v1, mat2, pick2,
            minX, maxY, u0, v1, mat2, pick2
          ]);
        }
      }
    } else if (batch.shader_family === 'TextGlyph' && batch.topology === 'points') {
      var labels = artifact.text_instances || [];
      for (var li = 0; li < labels.length; li++) {
        var lab = labels[li];
        if (lab.material_index !== batch.material_index) continue;
        var text = String(lab.text || '');
        var cx = +lab.x || 0, cy = +lab.y || 0;
        var mat3 = lab.material_index, pick3 = lab.pick_id || 0;
        var cellW = 8, cellH = 12;
        for (var ci = 0; ci < text.length; ci++) {
          var g = A && A.resolveGlyphGpu ? A.resolveGlyphGpu(text.charAt(ci), palette, gpuManifest) : null;
          if (!g) continue;
          out = out.concat(buildTextQuadVerts(cx + ci * cellW, cy, text.charAt(ci), g, mat3, pick3, cellW, cellH));
        }
      }
    }
    return out.length ? new Float32Array(out) : null;
  }

  async function uploadAtlasTextures(device, specs, fetchFn) {
    var fetchImpl = fetchFn || (typeof fetch !== 'undefined' ? fetch.bind(global) : null);
    if (!device || !fetchImpl) return { textures: {}, sampler: null, errors: ['no device or fetch'] };
    var sampler = device.createSampler({ magFilter: 'linear', minFilter: 'linear' });
    var textures = Object.create(null);
    var errors = [];
    for (var i = 0; i < specs.length; i++) {
      var spec = specs[i];
      try {
        var resp = await fetchImpl(spec.image, { cache: 'force-cache' });
        if (!resp.ok) throw new Error('fetch ' + spec.image + ' -> ' + resp.status);
        var blob = await resp.blob();
        var bmp = await createImageBitmap(blob);
        var tex = device.createTexture({
          size: { width: bmp.width, height: bmp.height },
          format: 'rgba8unorm',
          usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT
        });
        device.queue.copyExternalImageToTexture({ source: bmp }, { texture: tex }, { width: bmp.width, height: bmp.height });
        textures[spec.atlas_id] = { texture: tex, kind: spec.kind, palette: spec.palette, view: tex.createView() };
      } catch (e) {
        errors.push(String(e.message || e));
      }
    }
    return { textures: textures, sampler: sampler, errors: errors };
  }

  function createTextureBindGroup(device, pipeline, cache, kind) {
    if (!cache || !cache.textures || !cache.sampler) return null;
    var slot = atlasKindSlot(kind);
    var texEntry = null;
    Object.keys(cache.textures).forEach(function (id) {
      if (cache.textures[id].kind === kind) texEntry = cache.textures[id];
    });
    if (!texEntry) return null;
    return device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: { buffer: cache.viewBufPlaceholder || cache._viewBuf } },
        { binding: 1, resource: { buffer: cache.materialsBufPlaceholder || cache._materialsBuf } },
        { binding: 2, resource: { buffer: cache.blendBufPlaceholder || cache._blendBuf } },
        { binding: 3, resource: texEntry.view },
        { binding: 4, resource: cache.sampler }
      ]
    });
  }

  var API = {
    atlasKindSlot: atlasKindSlot,
    buildTextQuadVerts: buildTextQuadVerts,
    buildSymbolQuadVertsFromPoint: buildSymbolQuadVertsFromPoint,
    buildTexQuadsForBatch: buildTexQuadsForBatch,
    uploadAtlasTextures: uploadAtlasTextures,
    createTextureBindGroup: createTextureBindGroup
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else global.HelmChartArtifactAtlasGpu = API;
})(typeof window !== 'undefined' ? window : this);
