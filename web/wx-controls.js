// wx-controls.js — one Weather drawer for Live, offline fields, Tier-2 tiles, ensemble + imports.
// WX epic · weather-ux.
(function () {
  'use strict';
  var cogP = null;
  function cog() { return cogP || (cogP = import('./integrations/cog.js')); }

  var S = {
    map: null, source: 'live', detail: 'standard', model: 'single',
    tileIndex: null, tileManifest: null, els: {}, probeT: null, applyToken: 0
  };

  function activeLayer() { return window.__activeWx || 'wind'; }
  function storeGet(key, dflt) { return window.HelmStore ? HelmStore.get(key, dflt) : dflt; }
  function storeSet(key, value) { if (window.HelmStore) HelmStore.set(key, value); }
  function valid(value, allowed, dflt) { return allowed.indexOf(value) >= 0 ? value : dflt; }

  function notify(msg, level) {
    var n = document.getElementById('wx-notice'); if (!n) return;
    n.textContent = msg; n.style.display = 'block';
    n.style.color = level === 'warn' ? 'var(--warn,#e8a13a)' : (level === 'ok' ? 'var(--ok,#5fd08a)' : 'var(--cdim,#8aa)');
    n.style.borderColor = level === 'warn' ? 'var(--warn,#e8a13a)' : 'var(--line,#345)';
  }
  function clearNotice() {
    var n = document.getElementById('wx-notice'); if (!n) return;
    n.textContent = ''; n.style.display = 'none';
  }

  function showLegacy(visible) {
    var map = S.map; if (!map) return;
    if (map.getLayer('helm-wxfield')) map.setLayoutProperty('helm-wxfield', 'visibility', visible ? 'visible' : 'none');
    if (!visible && window.__helmWindLayer) window.__helmWindLayer.setVisible(false);
    if (visible && window.__helmSetWeather) window.__helmSetWeather(activeLayer());
  }

  var STANDARD_PARTICLES = { wind: true, waves: true, swell: true, current: true };
  function syncParticleControl(available, title) {
    var pc = document.getElementById('particles'); if (!pc) return;
    pc.disabled = !available;
    pc.parentElement.style.opacity = available ? '1' : '.48';
    pc.parentElement.title = available ? '' : (title || 'Animated particles are unavailable in this mode.');
  }

  function bboxIntersectsView(bbox, map) {
    if (!bbox || bbox.length < 4 || !map) return false;
    var b = map.getBounds(), vs = b.getSouth(), vn = b.getNorth();
    if (bbox[3] < vs || bbox[1] > vn) return false;
    var vw = b.getWest(), ve = b.getEast();
    if (ve < vw) ve += 360;
    var bw = bbox[0], be = bbox[2];
    if (be < bw) be += 360;
    for (var shift = -360; shift <= 360; shift += 360) {
      if (be + shift >= vw && bw + shift <= ve) return true;
    }
    return false;
  }

  function setProbe(html) {
    if (S.els.probe) S.els.probe.innerHTML = html ||
      '<span style="color:var(--cdim,#8aa)">move the map to read a value</span>';
  }
  function probeSoon() { clearTimeout(S.probeT); S.probeT = setTimeout(probe, 250); }
  async function probe() {
    var map = S.map, c = map.getCenter(), m = await cog(), layer = activeLayer(), s = null;
    if (layer === 'off') return setProbe('');
    if (S.model === 'ensemble') {
      var e = await m.sampleEnsemble(c.lat, c.lng);
      if (e && e.value != null) return setProbe('<b>' + e.mean + ' ' + e.unit + '</b> · spread ' + e.spread + ' · ' + e.agreement);
    } else if (S.source === 'live' && window.HelmWxLive) {
      s = window.HelmWxLive.sampleAt(c.lat, c.lng);
    } else if (S.detail === 'hires') {
      s = await m.sampleWx(c.lat, c.lng, window.__helmTime || null);
    }
    if (s && s.value != null) {
      return setProbe('<b>' + s.value + ' ' + s.unit + '</b> @ centre · ' +
        (s.sourceRef ? s.sourceRef.title : s.source));
    }
    setProbe('');
  }

  async function tileIndex() {
    if (S.tileIndex) return S.tileIndex;
    var r = await fetch('data/wxtiles/index.json');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    S.tileIndex = await r.json();
    return S.tileIndex;
  }

  async function enableHiRes(map, layer, m) {
    var idx = await tileIndex(), entry = idx && idx.layers && idx.layers[layer];
    if (!entry) {
      notify('No Hi-res tile pack for ' + layer + ' — bake this layer with pipeline/make_value_tiles.py.', 'warn');
      return;
    }
    var manifestUrl = 'data/wxtiles/' + (entry.manifest || (layer + '/manifest.json'));
    var mr = await fetch(manifestUrl);
    if (!mr.ok) throw new Error('manifest HTTP ' + mr.status);
    var manifest = await mr.json();
    if (!bboxIntersectsView(manifest.bbox, map)) {
      notify('Hi-res pack does not cover this view — bake the visible waters for local Tier-2 coverage.', 'warn');
      return;
    }
    showLegacy(false);
    syncParticleControl(false, 'Tier-2 tiles are scalar; use Live wind for animated particles.');
    var cfg = await m.enableWxTiles(map, {
      maplibregl: window.maplibregl, manifestUrl: manifestUrl,
      beforeId: map.getLayer('route-line') ? 'route-line' : undefined,
      opacity: (100 - (+document.getElementById('wxopacity').value)) / 100,
      frame: 0, notify: notify
    });
    S.tileManifest = cfg;
    if (cfg) notify('Hi-res Tier-2 tiles · ' + (cfg.model || cfg.source) + ' · pans and zooms as a tile layer', 'ok');
  }

  async function enableEnsemble(map, layer, m) {
    syncParticleControl(false, 'Particles are hidden while model spread is displayed.');
    showLegacy(false);
    var idx = await fetch('data/wxtiles/ensemble.json').then(function (r) { return r.ok ? r.json() : null; });
    var pair = idx && idx.pairs && (idx.pairs[layer] || idx.pairs.wind);
    if (!pair) { notify('No ensemble pack — run pipeline/make_value_tiles.py --demo-ensemble', 'warn'); return; }
    var mem = Object.keys(pair.members);
    var state = await m.enableEnsemble(map, {
      maplibregl: window.maplibregl,
      manifestA: 'data/wxtiles/' + pair.members[mem[0]].manifest,
      manifestB: 'data/wxtiles/' + pair.members[mem[1]].manifest,
      labelA: mem[0].toUpperCase(), labelB: mem[1].toUpperCase(), layer: layer,
      beforeId: map.getLayer('route-line') ? 'route-line' : undefined,
      opacity: (100 - (+document.getElementById('wxopacity').value)) / 100,
      notify: notify, frame: 6
    });
    if (state && !bboxIntersectsView(state.bbox, map)) {
      m.disableEnsemble(map);
      notify('Ensemble pack does not cover this view — bake both models for the visible waters.', 'warn');
      return;
    }
    if (state) notify('Ensemble spread · ' + state.labelA + ' vs ' + state.labelB, 'ok');
  }

  function updateControlAvailability() {
    var locked = S.model === 'ensemble';
    if (S.els.sourceSeg) {
      Array.prototype.forEach.call(S.els.sourceSeg.children, function (b) { b.disabled = locked; });
      S.els.sourceSeg.style.opacity = locked ? '.48' : '1';
    }
    var detailLocked = locked || S.source === 'live';
    if (S.els.detailSeg) {
      Array.prototype.forEach.call(S.els.detailSeg.children, function (b) { b.disabled = detailLocked; });
      S.els.detailSeg.style.opacity = detailLocked ? '.48' : '1';
      S.els.detailSeg.title = S.source === 'live' && !locked
        ? 'Live fetch-on-pan already follows the viewport. Hi-res selects a baked offline Tier-2 pack.'
        : '';
    }
    if (S.els.help) {
      S.els.help.textContent = locked ? 'Model spread uses two baked Tier-2 packs.'
        : (S.source === 'live' ? 'Default: live sampled coverage for the visible map; cached while you pan/zoom.'
          : (S.detail === 'hires' ? 'Baked value tiles: smooth pan/zoom inside downloaded coverage.'
            : 'Bounded local field: works offline, but only inside its downloaded area.'));
    }
  }

  async function apply() {
    var token = ++S.applyToken, map = S.map, layer = activeLayer();
    if (!map) return;

    if (window.HelmWxLive) window.HelmWxLive.disable(map);
    showLegacy(false);
    updateControlAvailability();

    var m = await cog();
    if (token !== S.applyToken) return;
    m.disableEnsemble(map); m.disableWxTiles(map);
    S.tileManifest = null;

    if (layer === 'off') {
      syncParticleControl(false); clearNotice(); setProbe(''); return;
    }

    try {
      if (S.model === 'ensemble') {
        await enableEnsemble(map, layer, m);
      } else if (S.source === 'live') {
        if (window.HelmWxLive && window.HelmWxLive.supports(layer)) {
          syncParticleControl(layer === 'wind' || layer === 'current');
          window.HelmWxLive.enable(map, {
            layer: layer, particles: !!document.getElementById('particles').checked,
            opacity: (100 - (+document.getElementById('wxopacity').value)) / 100,
            notify: notify
          });
        } else {
          syncParticleControl(!!STANDARD_PARTICLES[layer]);
          showLegacy(true);
          notify(layer + ' has no Live provider — showing its bounded Offline area.', 'warn');
        }
      } else if (S.detail === 'hires') {
        await enableHiRes(map, layer, m);
      } else {
        syncParticleControl(!!STANDARD_PARTICLES[layer]);
        showLegacy(true);
        clearNotice();
      }
    } catch (e) {
      if (token !== S.applyToken) return;
      if (S.source === 'offline' && S.detail === 'standard' && S.model === 'single') showLegacy(true);
      notify('Weather mode unavailable: ' + (e && e.message ? e.message : e), 'warn');
    }
    probeSoon();
  }

  function build(drawer, map) {
    S.map = map;
    S.source = valid(storeGet('wx.source', 'live'), ['live', 'offline'], 'live');
    S.detail = valid(storeGet('wx.detail', 'standard'), ['standard', 'hires'], 'standard');
    S.model = valid(storeGet('wx.model', 'single'), ['single', 'ensemble'], 'single');

    var box = document.createElement('div');
    box.id = 'wx-plus';
    box.style.cssText = 'margin-top:12px;border-top:.5px solid var(--line,#2a3540);padding-top:11px';
    function label(t) {
      var d = document.createElement('div'); d.textContent = t;
      d.style.cssText = 'font-size:11px;color:var(--cdim,#8aa);margin:0 0 5px';
      return d;
    }
    function segctl(opts, testId) {
      var w = document.createElement('div'); w.dataset.testid = testId;
      w.style.cssText = 'display:flex;border:.5px solid var(--line,#345);border-radius:8px;overflow:hidden;margin-bottom:8px';
      opts.forEach(function (o) {
        var b = document.createElement('button'); b.dataset.val = o.val; b.textContent = o.txt;
        b.style.cssText = 'flex:1;font-size:12px;padding:7px 5px;border:0;background:transparent;color:var(--cdim,#8aa);cursor:pointer';
        b.addEventListener('mouseenter', function () { if (b.dataset.sel !== '1' && !b.disabled) b.style.background = 'rgba(255,255,255,.04)'; });
        b.addEventListener('mouseleave', function () { b.style.background = b.dataset.sel === '1' ? 'var(--accent,#39c2c9)' : 'transparent'; });
        w.appendChild(b);
      });
      return w;
    }
    function paintSeg(w, on) {
      Array.prototype.forEach.call(w.children, function (b) {
        var sel = b.dataset.val === on; b.dataset.sel = sel ? '1' : '';
        b.style.background = sel ? 'var(--accent,#39c2c9)' : 'transparent';
        b.style.color = sel ? '#05121d' : 'var(--cdim,#8aa)';
        b.style.fontWeight = sel ? '600' : '400';
      });
    }

    box.appendChild(label('Coverage'));
    var sourceSeg = segctl([
      { val: 'live', txt: 'Live fetch-on-pan' },
      { val: 'offline', txt: 'Offline area' }
    ], 'wx-source');
    box.appendChild(sourceSeg); S.els.sourceSeg = sourceSeg;

    var help = document.createElement('div');
    help.style.cssText = 'font-size:10.5px;color:var(--cdim,#8aa);line-height:1.3;margin:-1px 2px 9px';
    box.appendChild(help); S.els.help = help;

    box.appendChild(label('Offline detail'));
    var detailSeg = segctl([
      { val: 'standard', txt: 'Standard' },
      { val: 'hires', txt: 'Hi-res tiles' }
    ], 'wx-detail');
    box.appendChild(detailSeg); S.els.detailSeg = detailSeg;

    box.appendChild(label('Model'));
    var modSeg = segctl([
      { val: 'single', txt: 'Single' },
      { val: 'ensemble', txt: 'Ensemble spread' }
    ], 'wx-model');
    box.appendChild(modSeg); S.els.modelSeg = modSeg;

    var probeEl = document.createElement('div');
    probeEl.style.cssText = 'font-size:12px;background:rgba(255,255,255,.03);border:.5px solid var(--line,#345);border-radius:8px;padding:8px 10px;margin:2px 0 10px;min-height:16px';
    box.appendChild(probeEl); S.els.probe = probeEl;

    var imp = document.createElement('div');
    imp.style.cssText = 'border:.5px dashed var(--line,#456);border-radius:8px;padding:8px 10px';
    imp.innerHTML = '<div style="font-size:12px;margin-bottom:4px"><span style="vertical-align:1px">⤓</span> Import PredictWind GPX / GRIB</div>' +
      '<div style="font-size:11px;color:var(--cdim,#8aa);margin-bottom:6px">device-local · never synced</div>';
    var file = document.createElement('input'); file.type = 'file';
    file.accept = '.gpx,.grb,.grb2,.grib,.grib2'; file.style.cssText = 'font-size:11px;color:#cdd9e3;width:100%';
    file.addEventListener('change', function () {
      if (file.files && file.files[0] && window.HelmImport) HelmImport.importFile(file.files[0], map, notify);
      file.value = '';
    });
    imp.appendChild(file); box.appendChild(imp);

    var anchor = drawer.querySelector('#wxopacity');
    anchor = anchor ? (anchor.closest('.row') || anchor) : null;
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
    else drawer.appendChild(box);

    paintSeg(sourceSeg, S.source); paintSeg(detailSeg, S.detail); paintSeg(modSeg, S.model);
    sourceSeg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || b.disabled) return;
      S.source = b.dataset.val; storeSet('wx.source', S.source); paintSeg(sourceSeg, S.source); apply();
    });
    detailSeg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || b.disabled) return;
      S.detail = b.dataset.val; storeSet('wx.detail', S.detail); paintSeg(detailSeg, S.detail); apply();
    });
    modSeg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      S.model = b.dataset.val; storeSet('wx.model', S.model); paintSeg(modSeg, S.model); apply();
    });
    setProbe(''); updateControlAvailability();

    var wx = document.getElementById('wx');
    if (wx) wx.addEventListener('click', function (e) { if (e.target.closest('button')) setTimeout(apply, 60); });
    var opacity = document.getElementById('wxopacity');
    if (opacity) opacity.addEventListener('input', function () {
      var o = (100 - (+opacity.value)) / 100;
      if (window.HelmWxLive && HelmWxLive.isEnabled()) HelmWxLive.setOpacity(o);
      cog().then(function (m) {
        if (S.model === 'ensemble') m.setEnsembleOpacity(map, o);
        else if (S.source === 'offline' && S.detail === 'hires') m.setWxOpacity(map, o);
      });
    });
    map.on('moveend', probeSoon);

    // Critical acceptance behaviour: Wind opens full-bleed by default. The bounded offline field is
    // now an explicit user choice, not a misleading startup state that looks like a broken Windy.
    apply();
  }

  function state() {
    return {
      source: S.source, detail: S.detail, model: S.model, layer: activeLayer(),
      live: window.HelmWxLive && window.HelmWxLive.status ? window.HelmWxLive.status() : null,
      tile: S.tileManifest
    };
  }

  function boot() {
    var drawer = document.getElementById('drawer-weather');
    if (!window.map || typeof window.map.on !== 'function' || !drawer) return setTimeout(boot, 300);
    if (document.getElementById('wx-plus')) return;
    build(drawer, window.map);
    window.HelmWxControls = { apply: apply, state: state };
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') setTimeout(boot, 400);
  else window.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 400); });
})();
