/*
 * Helm — chart-artifact-webgpu.js (WEBGPU-1)
 * --------------------------------------------------------------------------
 * First browser WebGPU nautical layer: load helm.render.artifact.v1 packets
 * produced by the C++ artifact compiler (ARTIFACT-1) and draw primitive
 * geometry over MapLibre. Chart semantics stay server-side; this module only
 * consumes compiled vertices/indices/draw batches.
 *
 * Public API — HelmChartArtifactAuto(map, opts):
 *     load(url?) / setArtifact(json) / setVisible(v) / isVisible()
 *     destroy() / mode()
 *
 * Fallback discipline (matches wx-particles-webgpu.js / WX-25):
 *     window.__helmChartMode = 'gpu' | 'maplibre'
 *     window.__helmChartModeReason = human-readable reason
 *     One console.info line on every path switch. When WebGPU is unavailable
 *     the enc-chart MapLibre raster layer stays visible. Opt out:
 *     HELM_CHART_WEBGPU=false or localStorage helmChartWebgpu=0
 * --------------------------------------------------------------------------
 */
(function (global) {
  'use strict';

  var SCHEMA = 'helm.render.artifact.v1';
  var ENC_LAYER = 'enc-chart';
  var VERTEX_STRIDE = 4; // x, y, material_index, pick_id

  // Fixture/debug palette only — not S-52 presentation decisions.
  var MATERIAL_RGBA = [
    [0.35, 0.35, 0.40, 0.85],
    [0.12, 0.42, 0.72, 0.55],
    [0.05, 0.55, 0.35, 0.95],
    [0.90, 0.55, 0.10, 0.90],
    [0.85, 0.85, 0.20, 0.90],
    [0.70, 0.20, 0.55, 0.90]
  ];

  function mercX(lon) { return lon / 360 + 0.5; }
  function mercY(lat) {
    var s = Math.sin(lat * Math.PI / 180);
    s = Math.max(-0.9999, Math.min(0.9999, s));
    return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI);
  }

  function affineFromProbes(cLng, cLat, dLon, dLat, p0, pE, pN) {
    var mx0 = mercX(cLng), my0 = mercY(cLat);
    var dmx = mercX(cLng + dLon) - mx0;
    var dmy = mercY(cLat + dLat) - my0;
    if (!dmx || !dmy) return null;
    var a = (pE.x - p0.x) / dmx, c = (pE.y - p0.y) / dmx;
    var b = (pN.x - p0.x) / dmy, d = (pN.y - p0.y) / dmy;
    return [a, b, p0.x - a * mx0 - b * my0,
            c, d, p0.y - c * mx0 - d * my0];
  }

  function parseArtifactJson(json) {
    if (!json || json.schema_version !== SCHEMA) {
      throw new Error('expected schema ' + SCHEMA);
    }
    var geo = json.geometry || {};
    var verts = geo.vertices_f32;
    var inds = geo.indices_u32;
    if (!Array.isArray(verts) || !Array.isArray(inds)) {
      throw new Error('artifact geometry missing vertices_f32 or indices_u32');
    }
    if (verts.length % VERTEX_STRIDE !== 0) {
      throw new Error('vertices_f32 length must be a multiple of ' + VERTEX_STRIDE);
    }
    var vp = json.viewport || {};
    var bbox = vp.geographic_bbox || {};
    var px = vp.pixel_size || [1, 1];
    return {
      schema_version: json.schema_version,
      artifact_id: json.artifact_id || '',
      viewport: {
        west: +bbox.west || 0,
        south: +bbox.south || 0,
        east: +bbox.east || 0,
        north: +bbox.north || 0,
        pixel_width: +px[0] || 1,
        pixel_height: +px[1] || 1,
        tile: vp.tile || {}
      },
      checksums: json.checksums || {},
      material_table: json.material_table || [],
      draw_batches: (json.draw_batches || []).slice().sort(function (a, b) {
        return (+a.order_bucket || 0) - (+b.order_bucket || 0);
      }),
      pick_records: json.pick_records || [],
      source_model_id: json.source_model_id || '',
      vertices: new Float32Array(verts),
      indices: new Uint32Array(inds)
    };
  }

  function tilePixelToLonLat(x, y, vp) {
    var pw = vp.pixel_width || 1;
    var ph = vp.pixel_height || 1;
    return {
      lon: vp.west + (x / pw) * (vp.east - vp.west),
      lat: vp.north - (y / ph) * (vp.north - vp.south)
    };
  }

  function buildViewUniform(map, artifact, w, h) {
    var vp = artifact.viewport;
    var c = tilePixelToLonLat(vp.pixel_width * 0.5, vp.pixel_height * 0.5, vp);
    var dLon = (vp.east - vp.west) / Math.max(1, vp.pixel_width);
    var dLat = (vp.north - vp.south) / Math.max(1, vp.pixel_height);
    var p0, pE, pN;
    try {
      p0 = map.project([c.lon, c.lat]);
      pE = map.project([c.lon + dLon, c.lat]);
      pN = map.project([c.lon, c.lat + dLat]);
    } catch (e) {
      return null;
    }
    var aff = affineFromProbes(c.lon, c.lat, dLon, dLat, p0, pE, pN);
    if (!aff) return null;
    return new Float32Array([
      vp.west, vp.north,
      (vp.east - vp.west) / Math.max(1, vp.pixel_width),
      (vp.north - vp.south) / Math.max(1, vp.pixel_height),
      aff[0], aff[1], aff[2], aff[3], aff[4], aff[5],
      1 / Math.max(1, w), 1 / Math.max(1, h)
    ]);
  }

  var WGSL = [
    'struct View {',
    '  west: f32, north: f32, dLonPerPx: f32, dLatPerPx: f32,',
    '  a: f32, b: f32, tx: f32, c: f32, d: f32, ty: f32, invW: f32, invH: f32,',
    '};',
    '@group(0) @binding(0) var<uniform> view: View;',
    'struct VSOut { @builtin(position) pos: vec4<f32>, @location(0) color: vec4<f32> };',
    'fn tileToNdc(px: f32, py: f32) -> vec2<f32> {',
    '  let lon = view.west + px * view.dLonPerPx;',
    '  let lat = view.north - py * view.dLatPerPx;',
    '  let mx = lon / 360.0 + 0.5;',
    '  let s = clamp(sin(lat * 3.14159265 / 180.0), -0.9999, 0.9999);',
    '  let my = 0.5 - log((1.0 + s) / (1.0 - s)) / (4.0 * 3.14159265);',
    '  let sx = view.a * mx + view.b * my + view.tx;',
    '  let sy = view.c * mx + view.d * my + view.ty;',
    '  return vec2<f32>(sx * view.invW * 2.0 - 1.0, 1.0 - sy * view.invH * 2.0);',
    '}',
    'fn matColor(idx: f32) -> vec4<f32> {',
    '  let i = u32(clamp(idx, 0.0, 5.0));',
    '  switch (i) {',
    '    case 0u: { return vec4<f32>(0.35, 0.35, 0.40, 0.85); }',
    '    case 1u: { return vec4<f32>(0.12, 0.42, 0.72, 0.55); }',
    '    case 2u: { return vec4<f32>(0.05, 0.55, 0.35, 0.95); }',
    '    case 3u: { return vec4<f32>(0.90, 0.55, 0.10, 0.90); }',
    '    case 4u: { return vec4<f32>(0.85, 0.85, 0.20, 0.90); }',
    '    default: { return vec4<f32>(0.70, 0.20, 0.55, 0.90); }',
    '  }',
    '}',
    '@vertex fn vs(@location(0) tile_xy: vec2<f32>, @location(1) mat_idx: f32) -> VSOut {',
    '  var o: VSOut;',
    '  let ndc = tileToNdc(tile_xy.x, tile_xy.y);',
    '  o.pos = vec4<f32>(ndc, 0.0, 1.0);',
    '  o.color = matColor(mat_idx);',
    '  return o;',
    '}',
    '@fragment fn fs(in: VSOut) -> @location(0) vec4<f32> { return in.color; }'
  ].join('\n');

  function GpuChartArtifactLayer(map, gpu, artifact) {
    this.map = map;
    this.gpu = gpu;
    this.artifact = artifact;
    this._visible = false;
    this._destroyed = false;
    this._raf = null;
    this._buildCanvas();
    this._buildPipelines();
    if (this.artifact) this._uploadGeometry();
    this._bindMap();
    this._resize();
  }

  GpuChartArtifactLayer.prototype._buildCanvas = function () {
    var mapCanvas = this.map.getCanvas();
    var container = mapCanvas.parentNode;
    var c = document.createElement('canvas');
    c.className = 'helm-chart-artifact-canvas';
    var s = c.style;
    s.position = 'absolute';
    s.top = '0';
    s.left = '0';
    s.width = '100%';
    s.height = '100%';
    s.pointerEvents = 'none';
    s.zIndex = '0';
    s.display = 'none';
    this.canvas = c;
    this.ctx = c.getContext('webgpu');
    if (!this.ctx) throw new Error('canvas.getContext("webgpu") returned null');
    this.ctx.configure({
      device: this.gpu.device,
      format: this.gpu.canvasFormat,
      alphaMode: 'premultiplied'
    });
    (container || mapCanvas.parentNode).appendChild(c);
  };

  GpuChartArtifactLayer.prototype._buildPipelines = function () {
    var dev = this.gpu.device;
    var mod = dev.createShaderModule({ code: WGSL });
    var blend = {
      color: { srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha' },
      alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' }
    };
    var mk = function (topology) {
      return dev.createRenderPipeline({
        layout: 'auto',
        vertex: {
          module: mod,
          entryPoint: 'vs',
          buffers: [{
            arrayStride: VERTEX_STRIDE * 4,
            attributes: [
              { shaderLocation: 0, offset: 0, format: 'float32x2' },
              { shaderLocation: 1, offset: 8, format: 'float32' }
            ]
          }]
        },
        fragment: { module: mod, entryPoint: 'fs', targets: [{ format: this.gpu.canvasFormat, blend: blend }] },
        primitive: { topology: topology }
      });
    }.bind(this);
    this.triPipe = mk('triangle-list');
    this.linePipe = mk('line-list');
    this.pointPipe = mk('point-list');
    this.viewBuf = dev.createBuffer({ size: 64, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  };

  GpuChartArtifactLayer.prototype._uploadGeometry = function () {
    var dev = this.gpu.device;
    var art = this.artifact;
    if (!art) return;
    if (this.vertexBuf) { try { this.vertexBuf.destroy(); } catch (e) {} }
    if (this.indexBuf) { try { this.indexBuf.destroy(); } catch (e) {} }
    this.vertexBuf = dev.createBuffer({
      size: art.vertices.byteLength,
      usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST
    });
    this.indexBuf = dev.createBuffer({
      size: art.indices.byteLength,
      usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST
    });
    dev.queue.writeBuffer(this.vertexBuf, 0, art.vertices);
    dev.queue.writeBuffer(this.indexBuf, 0, art.indices);
    this.viewBindTri = dev.createBindGroup({
      layout: this.triPipe.getBindGroupLayout(0),
      entries: [{ binding: 0, resource: { buffer: this.viewBuf } }]
    });
    this.viewBindLine = dev.createBindGroup({
      layout: this.linePipe.getBindGroupLayout(0),
      entries: [{ binding: 0, resource: { buffer: this.viewBuf } }]
    });
    this.viewBindPoint = dev.createBindGroup({
      layout: this.pointPipe.getBindGroupLayout(0),
      entries: [{ binding: 0, resource: { buffer: this.viewBuf } }]
    });
  };

  GpuChartArtifactLayer.prototype._bindMap = function () {
    var self = this;
    this._onResize = function () { self._resize(); self._draw(); };
    this._onMove = function () { if (self._visible) self._draw(); };
    this.map.on('resize', this._onResize);
    this.map.on('move', this._onMove);
    this.map.on('moveend', this._onMove);
  };

  GpuChartArtifactLayer.prototype._unbindMap = function () {
    this.map.off('resize', this._onResize);
    this.map.off('move', this._onMove);
    this.map.off('moveend', this._onMove);
  };

  GpuChartArtifactLayer.prototype._resize = function () {
    if (this._destroyed) return;
    var mapCanvas = this.map.getCanvas();
    var w = mapCanvas.clientWidth || mapCanvas.width;
    var h = mapCanvas.clientHeight || mapCanvas.height;
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    this._w = w;
    this._h = h;
    this.canvas.width = Math.max(1, Math.round(w * dpr));
    this.canvas.height = Math.max(1, Math.round(h * dpr));
    this.canvas.style.width = w + 'px';
    this.canvas.style.height = h + 'px';
  };

  GpuChartArtifactLayer.prototype._pipeForTopology = function (topology) {
    if (topology === 'line_list') return { pipe: this.linePipe, bind: this.viewBindLine };
    if (topology === 'points') return { pipe: this.pointPipe, bind: this.viewBindPoint };
    return { pipe: this.triPipe, bind: this.viewBindTri };
  };

  GpuChartArtifactLayer.prototype._draw = function () {
    if (this._destroyed || !this._visible || !this.artifact) return;
    var view = buildViewUniform(this.map, this.artifact, this._w, this._h);
    if (!view) return;
    var dev = this.gpu.device;
    dev.queue.writeBuffer(this.viewBuf, 0, view);
    var enc = dev.createCommandEncoder();
    var pass = enc.beginRenderPass({
      colorAttachments: [{
        view: this.ctx.getCurrentTexture().createView(),
        clearValue: { r: 0, g: 0, b: 0, a: 0 },
        loadOp: 'clear',
        storeOp: 'store'
      }]
    });
    var batches = this.artifact.draw_batches || [];
    for (var i = 0; i < batches.length; i++) {
      var b = batches[i];
      if (!b.index_count) continue;
      var sel = this._pipeForTopology(b.topology);
      pass.setPipeline(sel.pipe);
      pass.setBindGroup(0, sel.bind);
      pass.setVertexBuffer(0, this.vertexBuf);
      pass.setIndexBuffer(this.indexBuf, 'uint32');
      pass.drawIndexed(b.index_count, 1, b.first_index, 0, 0);
    }
    pass.end();
    dev.queue.submit([enc.finish()]);
  };

  GpuChartArtifactLayer.prototype.setArtifact = function (artifact) {
    this.artifact = artifact;
    this._uploadGeometry();
    if (this._visible) this._draw();
    return true;
  };

  GpuChartArtifactLayer.prototype.setEncChartVisible = function (visible) {
    try {
      if (this.map.getLayer(ENC_LAYER)) {
        this.map.setLayoutProperty(ENC_LAYER, 'visibility', visible ? 'visible' : 'none');
      }
    } catch (e) {}
  };

  GpuChartArtifactLayer.prototype.setVisible = function (v) {
    this._visible = !!v;
    if (this._visible) {
      this.canvas.style.display = 'block';
      this.setEncChartVisible(false);
      this._resize();
      this._draw();
    } else {
      this.canvas.style.display = 'none';
      this.setEncChartVisible(true);
    }
  };

  GpuChartArtifactLayer.prototype.isVisible = function () { return this._visible; };

  GpuChartArtifactLayer.prototype.destroy = function () {
    if (this._destroyed) return;
    this._destroyed = true;
    this._unbindMap();
    this.setEncChartVisible(true);
    if (this.canvas && this.canvas.parentNode) this.canvas.parentNode.removeChild(this.canvas);
    this.canvas = null;
    var kill = ['vertexBuf', 'indexBuf', 'viewBuf'];
    for (var i = 0; i < kill.length; i++) {
      try { this[kill[i]] && this[kill[i]].destroy(); } catch (e) {}
    }
  };

  function HelmChartArtifactAuto(map, opts) {
    opts = opts || {};
    var inner = null;
    var mode = 'initializing';
    var state = { artifact: null, visible: false, destroyed: false, packetUrl: opts.packetUrl || 'data/render-artifact-chart-1.json' };

    function setMode(m, reason) {
      mode = m;
      global.__helmChartMode = m;
      global.__helmChartModeReason = reason || '';
      console.info('[chart-artifact] ' + (m === 'gpu'
        ? 'WebGPU artifact layer active'
        : 'MapLibre enc-chart fallback — ' + reason));
      try {
        if (map.getLayer(ENC_LAYER)) {
          map.setLayoutProperty(ENC_LAYER, 'visibility', m === 'gpu' && state.visible ? 'none' : 'visible');
        }
      } catch (e) {}
    }

    function replay() {
      if (state.destroyed) { if (inner) inner.destroy(); return; }
      if (state.artifact != null && inner && inner.setArtifact) inner.setArtifact(state.artifact);
      if (state.visible && inner && inner.setVisible) inner.setVisible(true);
    }

    function fallbackMapLibre(reason) {
      inner = { setArtifact: function () { return true; }, setVisible: function () {}, isVisible: function () { return false; }, destroy: function () {} };
      setMode('maplibre', reason);
    }

    var flagOff = (global.HELM_CHART_WEBGPU === false) ||
      (typeof localStorage !== 'undefined' && localStorage.getItem('helmChartWebgpu') === '0');
    var unprojectable = false;
    var upReason = '';
    try {
      if (map.getPitch && map.getPitch() !== 0) { unprojectable = true; upReason = 'map pitch != 0'; }
      var proj = map.getProjection && map.getProjection();
      if (proj && /globe/i.test((proj.type || proj.name || '') + '')) { unprojectable = true; upReason = 'globe projection'; }
    } catch (e) {}

    if (flagOff) { fallbackMapLibre('HELM_CHART_WEBGPU=false'); }
    else if (typeof navigator === 'undefined' || !navigator.gpu) { fallbackMapLibre('WebGPU unavailable (no navigator.gpu)'); }
    else if (unprojectable) { fallbackMapLibre(upReason + ' — mercator-affine draw unsupported'); }
    else {
      navigator.gpu.requestAdapter().then(function (ad) {
        if (!ad) throw new Error('no WebGPU adapter');
        return ad.requestDevice();
      }).then(function (dev) {
        dev.lost.then(function (info) {
          if (mode === 'gpu') {
            try { inner.destroy(); } catch (e) {}
            fallbackMapLibre('WebGPU device lost: ' + ((info && info.reason) || 'unknown'));
          }
        });
        inner = new GpuChartArtifactLayer(map, {
          device: dev,
          canvasFormat: navigator.gpu.getPreferredCanvasFormat()
        }, state.artifact);
        setMode('gpu');
        replay();
      }).catch(function (err) {
        fallbackMapLibre('WebGPU init failed: ' + (err && err.message ? err.message : err));
      });
    }

    function call(fn) {
      if (inner) return fn(inner);
      return undefined;
    }

    return {
      load: function (url) {
        var u = url || state.packetUrl;
        return fetch(u, { cache: 'no-cache' })
          .then(function (r) { if (!r.ok) throw new Error('artifact HTTP ' + r.status); return r.json(); })
          .then(function (json) {
            state.artifact = parseArtifactJson(json);
            var r2 = call(function (e) { return e.setArtifact ? e.setArtifact(state.artifact) : true; });
            return r2 !== false;
          })
          .catch(function (err) {
            console.warn('[chart-artifact] could not load artifact packet:', err && err.message ? err.message : err);
            if (mode === 'gpu') {
              try { inner.destroy(); } catch (e2) {}
              fallbackMapLibre('artifact load failed: ' + (err && err.message ? err.message : err));
            }
            return false;
          });
      },
      setArtifact: function (json) {
        state.artifact = parseArtifactJson(json);
        var r = call(function (e) { return e.setArtifact ? e.setArtifact(state.artifact) : true; });
        return r === undefined ? true : r;
      },
      setVisible: function (v) {
        state.visible = !!v;
        call(function (e) { if (e.setVisible) e.setVisible(v); });
        if (mode === 'maplibre' && v) setMode('maplibre', global.__helmChartModeReason || 'WebGPU unavailable');
      },
      isVisible: function () { return inner && inner.isVisible ? inner.isVisible() : state.visible; },
      getArtifact: function () { return state.artifact; },
      pickAtLngLat: function (lngLat) {
        if (!state.artifact || !global.HelmChartArtifactPick) return { pick_id: 0, pixel: null, trace: null };
        var hit = global.HelmChartArtifactPick.pickAtLngLat(state.artifact, lngLat.lng, lngLat.lat);
        return hit;
      },
      destroy: function () { state.destroyed = true; call(function (e) { e.destroy(); }); },
      mode: function () { return mode; }
    };
  }

  HelmChartArtifactAuto._test = {
    SCHEMA: SCHEMA,
    VERTEX_STRIDE: VERTEX_STRIDE,
    mercX: mercX,
    mercY: mercY,
    affineFromProbes: affineFromProbes,
    parseArtifactJson: parseArtifactJson,
    tilePixelToLonLat: tilePixelToLonLat,
    buildViewUniform: buildViewUniform,
    MATERIAL_RGBA: MATERIAL_RGBA
  };
  HelmChartArtifactAuto.GpuLayer = GpuChartArtifactLayer;

  if (typeof module !== 'undefined' && module.exports) module.exports = HelmChartArtifactAuto;
  else global.HelmChartArtifactAuto = HelmChartArtifactAuto;
})(typeof window !== 'undefined' ? window : this);
