/*
 * Helm — chart-artifact-atlas.js (WEBGPU-2)
 * --------------------------------------------------------------------------
 * Atlas resource + material resolver for the browser WebGPU nautical layer.
 * It turns the compiler's style/material keys (helm.render.artifact.v1
 * material_table) plus the artifact cache display_state into concrete render
 * styles: per-palette colors, symbol geometry, line dash/width, pattern tile,
 * and font/glyph references.
 *
 * DISCIPLINE (WEBGPU-2): this module CONSUMES upstream S-52/S-101 decisions —
 * it never re-derives them. Colors, dashes, symbol sizes, and anchors are
 * mirrored from the repo-owned fixture engine/test/fixtures/s52-atlas/
 * s52_atlas.fixture (documented in docs/VULKAN-S52-ATLAS-PIPELINE.md). Where a
 * material has no resolvable atlas ref in the packet (e.g. the synthetic
 * chart-1 area/raster/text families ship refs but no colors/bytes yet), we use
 * a NAMED dev palette fallback and record a visible diagnostic — we never
 * silently invent an authoritative S-52 color.
 *
 * Pure + dependency-free so it unit-tests under node (web/test/*.test.cjs).
 * WEBGPU-3: when a helm.s52.atlas.web.v2 manifest is loaded, resolveMaterial
 * also returns gpu { uv, anchor, atlasImage, uploadable } for bitmap draws.
 * --------------------------------------------------------------------------
 */
(function (global) {
  'use strict';

  // Mirror of engine/test/fixtures/s52-atlas/s52_atlas.fixture. Synthetic,
  // repo-owned, day/dusk/night per asset. NOT invented here — kept byte-parallel
  // with the engine fixture so the browser presents the same values the C++
  // atlas builder would bake.
  var FIXTURE_ENTRIES = [
    { name: 'BOYSPP', kind: 'symbol', width: 12, height: 12, anchor: [6, 6], repeat: [0, 0], dash: [],
      colors: { day: '#f5d76e', dusk: '#b38b2e', night: '#8a5a22' } },
    { name: 'DEPARE01', kind: 'pattern', width: 8, height: 8, anchor: [0, 0], repeat: [8, 8], dash: [],
      colors: { day: '#b9d7e8', dusk: '#5f7a88', night: '#1b3c4b' } },
    { name: 'DEPCNT02', kind: 'line', width: 16, height: 4, anchor: [0, 2], repeat: [0, 0], dash: [3, 2],
      colors: { day: '#4a6f8a', dusk: '#304a5a', night: '#7eb6d6' } }
  ];

  // Artifact material refs are normalized (sym.boyspp) while the fixture uses
  // S-52 asset names (BOYSPP). This alias map is the ref -> fixture-entry bridge.
  var REF_ALIASES = {
    'sym.boyspp': 'BOYSPP',
    'line.depth-contour': 'DEPCNT02',
    'area.depare': 'DEPARE01',
    'pattern.depare': 'DEPARE01',
    'pattern.depare-shallow': 'pattern.depare-shallow',
    'pattern.depare-mid': 'pattern.depare-mid',
    'pattern.depare-deep': 'pattern.depare-deep',
    'pattern.dredged': 'pattern.dredged',
    'pattern.land': 'pattern.land',
    'line.coastline': 'line.coastline',
    'sym.sounding': 'sym.sounding',
    'sym.hazard': 'sym.hazard',
    'font.chart-label': 'font.chart-label'
  };

  // NAMED dev palette fallback, keyed by the compiler's style_key, for materials
  // whose color the packet does not (yet) carry. Values mirror the fixture asset
  // families where one applies (area<-DEPARE01, line<-DEPCNT02, symbol<-BOYSPP);
  // text/raster are neutral chart-label/raster placeholders. Alpha is presentation.
  var STYLE_FALLBACK = {
    fill_area:        { day: '#b9d7e8', dusk: '#5f7a88', night: '#1b3c4b', alpha: 0.55 },
    stroke_line:      { day: '#4a6f8a', dusk: '#304a5a', night: '#7eb6d6', alpha: 1.0 },
    place_symbol:     { day: '#f5d76e', dusk: '#b38b2e', night: '#8a5a22', alpha: 1.0 },
    draw_text:        { day: '#28323c', dusk: '#b4bec8', night: '#c85a5a', alpha: 1.0 },
    draw_sounding:    { day: '#28323c', dusk: '#b4bec8', night: '#c85a5a', alpha: 1.0 },
    draw_raster_sheet:{ day: '#787882', dusk: '#4a4a52', night: '#32323a', alpha: 0.5 }
  };

  var DEFAULT_FALLBACK = { day: '#c0c0c8', dusk: '#707078', night: '#3c3c44', alpha: 0.85 };
  var PALETTES = ['day', 'dusk', 'night'];

  function hexToRgb(hex) {
    var h = String(hex || '').replace('#', '').trim();
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    if (h.length !== 6) return null;
    var n = parseInt(h, 16);
    if (isNaN(n)) return null;
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  // [r,g,b] 0..255 (+ alpha 0..1) -> [r,g,b,a] 0..1 for WebGPU.
  function rgbToUnit(rgb, alpha) {
    if (!rgb) return null;
    var a = alpha == null ? 1 : alpha;
    return [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a];
  }

  function normalizePalette(p) {
    var s = String(p == null ? 'day' : p).toLowerCase();
    return PALETTES.indexOf(s) >= 0 ? s : 'day';
  }

  // Read the initial palette from the artifact cache.display_state (ARTIFACT-2),
  // defaulting to 'day'. Accepts a full artifact, a cache block, or a raw string.
  function paletteFromDisplayState(source) {
    if (!source) return 'day';
    if (typeof source === 'string') return normalizePalette(source);
    var ds = (source.cache && source.cache.display_state) || source.display_state || source;
    return normalizePalette(ds && ds.palette);
  }

  function buildResources(entries) {
    var byName = Object.create(null);
    (entries || []).forEach(function (e) { byName[e.name] = e; });
    return {
      entries: (entries || []).slice(),
      byName: byName,
      refAliases: REF_ALIASES,
      styleFallback: STYLE_FALLBACK
    };
  }

  var DEFAULT_RESOURCES = buildResources(FIXTURE_ENTRIES);

  // WEBGPU-3: helm.s52.atlas.web.v2 manifest (PNG sheets + UV rects).
  function loadGpuManifest(json) {
    if (!json || json.schema_version !== 'helm.s52.atlas.web.v2') return null;
    var byKey = Object.create(null);
    var atlases = Object.create(null);
    (json.atlases || []).forEach(function (a) {
      atlases[a.atlas_id] = a;
    });
    (json.entries || []).forEach(function (e) {
      var key = (e.name || '') + '@' + (e.kind || '') + '@' + (e.palette || 'day');
      byKey[key] = e;
    });
    var aliases = Object.assign({}, REF_ALIASES, json.ref_aliases || {});
    return { schema_version: json.schema_version, atlases: atlases, byKey: byKey, refAliases: aliases, entries: (json.entries || []).slice() };
  }

  function gpuManifestKey(name, kind, palette) {
    return (name || '') + '@' + (kind || '') + '@' + normalizePalette(palette);
  }

  function resolveGpuEntry(ref, kind, palette, gpuManifest) {
    if (!gpuManifest || !ref) return null;
    var aliases = gpuManifest.refAliases || REF_ALIASES;
    var name = aliases[ref] || ref;
    var pal = normalizePalette(palette);
    var entry = gpuManifest.byKey[gpuManifestKey(name, kind, pal)];
    if (!entry && kind === 'font') {
      entry = gpuManifest.byKey[gpuManifestKey('font.chart-label', 'font', pal)];
    }
    if (!entry) return null;
    var atlas = gpuManifest.atlases[entry.atlas_id];
    if (!atlas || !atlas.image) return null;
    return {
      name: name,
      kind: kind,
      palette: pal,
      atlas_id: entry.atlas_id,
      atlasImage: atlas.image,
      format: atlas.format || 'png-rgba',
      uv: (entry.uv || []).slice(),
      pixel_rect: (entry.pixel_rect || []).slice(),
      anchor: (entry.anchor || [0, 0]).slice(),
      repeat: (entry.repeat || [0, 0]).slice(),
      glyph_prefix: entry.glyph_prefix || 'glyph.',
      uploadable: true
    };
  }

  function resolveGlyphGpu(char, palette, gpuManifest) {
    if (!gpuManifest || !char) return null;
    var name = 'glyph.' + char;
    return resolveGpuEntry(name, 'glyph', palette, gpuManifest);
  }

  // Collect distinct atlas images that must be uploaded for a palette.
  function collectGpuUploadSpecs(gpuManifest, palette) {
    if (!gpuManifest) return [];
    var pal = normalizePalette(palette);
    var seen = Object.create(null);
    var out = [];
    (gpuManifest.entries || []).forEach(function (e) {
      if (normalizePalette(e.palette) !== pal) return;
      var atlas = gpuManifest.atlases[e.atlas_id];
      if (!atlas || !atlas.image || seen[atlas.atlas_id]) return;
      seen[atlas.atlas_id] = true;
      out.push({
        atlas_id: atlas.atlas_id,
        kind: atlas.kind,
        palette: pal,
        image: atlas.image,
        format: atlas.format || 'png-rgba',
        width: atlas.width || 0,
        height: atlas.height || 0,
        uploadable: true
      });
    });
    return out;
  }

  function atlasRefsGpuComplete(artifact, palette, gpuManifest) {
    if (!gpuManifest || !artifact) return { complete: false, missing: [] };
    var missing = [];
    (artifact.atlas_refs || []).forEach(function (ref) {
      if (!ref || !ref.atlas_id) return;
      if (String(ref.content_hash || '').indexOf('raster.') >= 0 ||
          ref.kind === 'raster_textures') return;
      var kind = ref.kind === 'symbols' ? 'symbol'
        : ref.kind === 'area_patterns' ? 'pattern'
        : ref.kind === 'line_styles' ? 'line'
        : ref.kind === 'fonts' ? 'font'
        : ref.kind === 'palettes' ? null
        : ref.kind;
      if (!kind) return;
      var gpu = resolveGpuEntry(ref.atlas_id, kind, palette, gpuManifest);
      if (!gpu) missing.push(ref.atlas_id);
    });
    return { complete: missing.length === 0, missing: missing };
  }

  // Load a web-consumable atlas resource JSON (web/data/s52-atlas-fixture.json).
  // Falls back to the built-in mirror when the payload is absent/malformed so the
  // layer still resolves colors — but records why.
  function loadResources(json, gpuManifest) {
    if (!json || !Array.isArray(json.entries) || !json.entries.length) {
      var base = buildResources(FIXTURE_ENTRIES);
      if (gpuManifest) base.gpuManifest = gpuManifest;
      return base;
    }
    var entries = json.entries.map(function (e) {
      return {
        name: e.name, kind: e.kind,
        width: +e.width || 0, height: +e.height || 0,
        anchor: e.anchor || [0, 0], repeat: e.repeat || [0, 0],
        dash: Array.isArray(e.dash) ? e.dash.slice() : [],
        alpha: (e.alpha == null ? null : +e.alpha),
        colors: e.colors || {}
      };
    });
    var res = buildResources(entries);
    if (gpuManifest) res.gpuManifest = gpuManifest;
    return res;
  }

  function resolveEntryForRef(ref, resources) {
    if (!ref) return null;
    var res = resources || DEFAULT_RESOURCES;
    if (res.byName[ref]) return res.byName[ref];
    var alias = res.refAliases[ref] || REF_ALIASES[ref];
    if (alias && res.byName[alias]) return res.byName[alias];
    return null;
  }

  function entryColor(entry, palette) {
    if (!entry || !entry.colors) return null;
    return hexToRgb(entry.colors[palette] || entry.colors.day);
  }

  // Resolve one material_table entry to a concrete render style for a palette.
  // Priority follows the ref that the compiler set on the material; falls back
  // to a NAMED dev palette by style_key with a diagnostic when no ref resolves.
  function resolveMaterial(material, palette, resources) {
    material = material || {};
    palette = normalizePalette(palette);
    var res = resources || DEFAULT_RESOURCES;
    var out = {
      material_id: material.material_id || '',
      style_key: material.style_key || '',
      shader_family: material.shader_family || '',
      palette: palette,
      rgba: null,
      symbol: null,
      line: null,
      pattern: null,
      font: material.font_ref || null,
      source: 'palette-fallback',
      missing: false,
      note: '',
      gpu: null
    };

    var gpuManifest = res.gpuManifest || null;
    var symEntry = resolveEntryForRef(material.symbol_ref, res);
    var lineEntry = resolveEntryForRef(material.line_style_ref, res);
    var patEntry = resolveEntryForRef(material.pattern_ref, res);

    if (symEntry) {
      out.source = 'atlas';
      out.rgba = rgbToUnit(entryColor(symEntry, palette), 1);
      out.symbol = { name: symEntry.name, width: symEntry.width, height: symEntry.height, anchor: symEntry.anchor.slice() };
      out.gpu = resolveGpuEntry(material.symbol_ref, 'symbol', palette, gpuManifest);
    } else if (lineEntry) {
      out.source = 'atlas';
      out.rgba = rgbToUnit(entryColor(lineEntry, palette), 1);
      out.line = { name: lineEntry.name, width: Math.max(1, lineEntry.height || 1), dash: lineEntry.dash.slice() };
      out.gpu = resolveGpuEntry(material.line_style_ref, 'line', palette, gpuManifest);
    } else if (patEntry) {
      out.source = 'atlas';
      // Area fills honor an explicit atlas alpha (S-52 day areas are near-opaque);
      // patterns without one keep the legacy translucent default.
      var patAlpha = (patEntry.alpha == null ? 0.6 : patEntry.alpha);
      out.rgba = rgbToUnit(entryColor(patEntry, palette), patAlpha);
      out.pattern = { name: patEntry.name, width: patEntry.width, height: patEntry.height, repeat: patEntry.repeat.slice() };
      out.gpu = resolveGpuEntry(material.pattern_ref, 'pattern', palette, gpuManifest);
    } else if (material.font_ref) {
      out.gpu = resolveGpuEntry(material.font_ref, 'font', palette, gpuManifest);
      if (out.gpu) {
        out.source = 'atlas';
        var fontFb = STYLE_FALLBACK[out.style_key] || STYLE_FALLBACK.draw_text;
        out.rgba = rgbToUnit(hexToRgb(fontFb[palette] || fontFb.day), fontFb.alpha == null ? 1 : fontFb.alpha);
      }
    }

    if (out.gpu && out.gpu.uploadable) {
      out.missing = false;
      if (out.source === 'palette-fallback') out.source = 'atlas-gpu';
    }

    if (!out.rgba) {
      var fb = STYLE_FALLBACK[out.style_key] || DEFAULT_FALLBACK;
      out.rgba = rgbToUnit(hexToRgb(fb[palette] || fb.day), fb.alpha == null ? 1 : fb.alpha);
      out.source = 'palette-fallback';
      // A material that names an atlas resource we could not resolve is a real
      // gap, not just an un-styled fill — surface it.
      if (material.symbol_ref || material.line_style_ref || material.pattern_ref || material.raster_texture_ref) {
        out.missing = true;
        out.note = 'unresolved atlas ref (' +
          [material.symbol_ref, material.line_style_ref, material.pattern_ref, material.raster_texture_ref, material.font_ref]
            .filter(Boolean).join(',') + ') — using named palette fallback';
      }
    }
    if (material.font_ref && !out.gpu && (out.style_key === 'draw_text' || out.style_key === 'draw_sounding')) {
      out.missing = true;
      out.note = 'unresolved font atlas ref (' + material.font_ref + ')';
    }
    return out;
  }

  // Should a batch draw under the current display_state? Honors show_text /
  // show_soundings from ARTIFACT-2's cache display_state.
  function batchVisibleForDisplayState(material, displayState) {
    var ds = displayState || {};
    var sk = (material && material.style_key) || '';
    if (sk === 'draw_text' && ds.show_text === false) return false;
    if (sk === 'draw_sounding' && ds.show_soundings === false) return false;
    return true;
  }

  // Resolve every material in an artifact for a palette, collecting diagnostics.
  function resolveArtifact(artifact, palette, resources) {
    artifact = artifact || {};
    palette = normalizePalette(palette || paletteFromDisplayState(artifact));
    var mats = artifact.material_table || [];
    var displayState = (artifact.cache && artifact.cache.display_state) || {};
    var resolved = [];
    var diagnostics = [];
    for (var i = 0; i < mats.length; i++) {
      var r = resolveMaterial(mats[i], palette, resources);
      r.visible = batchVisibleForDisplayState(mats[i], displayState);
      resolved.push(r);
      if (r.missing) {
        diagnostics.push({ severity: 'warn', material_index: i, material_id: r.material_id, code: 'atlas.unresolved_ref', message: r.note });
      }
    }
    return { palette: palette, materials: resolved, diagnostics: diagnostics, displayState: displayState };
  }

  // Flat Float32Array of vec4 colors indexed by material_index, for a WGSL
  // uniform array. Pads/truncates to `capacity` materials (16 floats each).
  function packMaterialColors(resolvedMaterials, capacity) {
    var cap = capacity || 32;
    var out = new Float32Array(cap * 4);
    for (var i = 0; i < Math.min(cap, resolvedMaterials.length); i++) {
      var c = resolvedMaterials[i].rgba || [0, 0, 0, 0];
      out[i * 4] = c[0]; out[i * 4 + 1] = c[1]; out[i * 4 + 2] = c[2]; out[i * 4 + 3] = c[3];
    }
    return out;
  }

  // Expand a single segment into dash on/off sub-segments in the SAME coordinate
  // units as the input, using a pixel-space dash array scaled by unitsPerPixel.
  // Returns an array of [x0,y0,x1,y1] "on" sub-segments. Pure + testable.
  function dashSegments(x0, y0, x1, y1, dash, unitsPerPixel) {
    if (!dash || !dash.length) return [[x0, y0, x1, y1]];
    var dx = x1 - x0, dy = y1 - y0;
    var len = Math.sqrt(dx * dx + dy * dy);
    if (len <= 1e-9) return [];
    var upp = unitsPerPixel > 0 ? unitsPerPixel : 1;
    var ux = dx / len, uy = dy / len;
    var out = [];
    var pos = 0, di = 0, on = true;
    var guard = 0;
    while (pos < len && guard++ < 100000) {
      var segPx = dash[di % dash.length];
      var segLen = Math.max(0, segPx * upp);
      var end = Math.min(len, pos + segLen);
      if (on && end > pos) {
        out.push([x0 + ux * pos, y0 + uy * pos, x0 + ux * end, y0 + uy * end]);
      }
      pos = end;
      di++;
      on = !on;
      if (segLen === 0) break;
    }
    return out;
  }

  var API = {
    PALETTES: PALETTES,
    FIXTURE_ENTRIES: FIXTURE_ENTRIES,
    hexToRgb: hexToRgb,
    rgbToUnit: rgbToUnit,
    normalizePalette: normalizePalette,
    paletteFromDisplayState: paletteFromDisplayState,
    loadResources: loadResources,
    loadGpuManifest: loadGpuManifest,
    resolveGpuEntry: resolveGpuEntry,
    resolveGlyphGpu: resolveGlyphGpu,
    collectGpuUploadSpecs: collectGpuUploadSpecs,
    atlasRefsGpuComplete: atlasRefsGpuComplete,
    defaultResources: function () { return DEFAULT_RESOURCES; },
    resolveMaterial: resolveMaterial,
    resolveArtifact: resolveArtifact,
    batchVisibleForDisplayState: batchVisibleForDisplayState,
    packMaterialColors: packMaterialColors,
    dashSegments: dashSegments
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else global.HelmChartArtifactAtlas = API;
})(typeof window !== 'undefined' ? window : this);
