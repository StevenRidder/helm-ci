// wx-controls.js — the unified Weather panel.  WX epic · weather-ux.
// ----------------------------------------------------------------------------------------------
// Folds the three former rail icons (value-encoded tiles / ensemble spread / PredictWind import)
// INTO the existing Weather drawer as inline controls, so weather lives in one place and the left
// rail stops overflowing. Injected into #drawer-weather at runtime from this WX-owned file — no edit
// to the shell body. Orchestrates four engines:
//   • legacy field overlay (Standard)        — index.html setWeather()
//   • fetch-on-pan live full-bleed (Live)     — web/wx-live.js
//   • GFS-vs-ECMWF spread (Ensemble)          — web/integrations/cog.js
//   • PredictWind GPX/GRIB import             — web/wx-import.js (window.HelmImport)
(function () {
  'use strict';
  var cogP = null;
  function cog() { return cogP || (cogP = import('./integrations/cog.js')); }
  var S = { map: null, resolution: 'live', model: 'single', els: {}, probeT: null };  // Live (fill-the-view) is the default — Windy-style

  function activeLayer() { return window.__activeWx || 'wind'; }
  function notify(msg, level) {
    var n = document.getElementById('wx-notice'); if (!n) return;
    n.textContent = msg; n.style.display = 'block';
    n.style.color = level === 'warn' ? 'var(--warn,#e8a13a)' : (level === 'ok' ? 'var(--ok,#5fd08a)' : 'var(--cdim,#8aa)');
    n.style.borderColor = level === 'warn' ? 'var(--warn,#e8a13a)' : 'var(--line,#345)';
  }
  function seg(el, on) { Array.prototype.forEach.call(el.children, function (b) { b.dataset.sel = (b.dataset.val === on) ? '1' : ''; }); }

  function showLegacy(visible) {
    var map = S.map; if (!map) return;
    if (map.getLayer('helm-wxfield')) map.setLayoutProperty('helm-wxfield', 'visibility', visible ? 'visible' : 'none');
    var pc = document.getElementById('particles');
    // particle canvas is driven by the legacy code; just hide its layer if present
    if (map.getLayer('wind-particles')) map.setLayoutProperty('wind-particles', 'visibility', visible ? 'visible' : 'none');
  }

  async function apply() {
    var map = S.map, layer = activeLayer(), m = await cog();
    if (window.HelmWxLive) window.HelmWxLive.disable(map);
    m.disableEnsemble(map); m.disableWxTiles(map);
    if (layer === 'off') { showLegacy(false); setProbe(''); return; }

    if (S.model === 'ensemble') {
      showLegacy(false);
      // GFS-vs-ECMWF spread. Live two-model needs a connection; offline we show the committed demo
      // pack (Key West), clearly labelled — bake your area for a local ensemble.
      try {
        var idx = await fetch('data/wxtiles/ensemble.json').then(function (r) { return r.ok ? r.json() : null; });
        var pair = idx && idx.pairs && (idx.pairs[layer] || idx.pairs.wind);
        if (pair) {
          var mem = Object.keys(pair.members);
          await m.enableEnsemble(map, { maplibregl: window.maplibregl,
            manifestA: 'data/wxtiles/' + pair.members[mem[0]].manifest, manifestB: 'data/wxtiles/' + pair.members[mem[1]].manifest,
            labelA: mem[0].toUpperCase(), labelB: mem[1].toUpperCase(), layer: layer, beforeId: 'route-line', opacity: 0.85, notify: notify, frame: 6 });
          notify('Ensemble spread · GFS vs ECMWF (demo pack — bake your area for local)', 'ok');
        } else notify('No ensemble pack — run pipeline/make_value_tiles.py --demo-ensemble', 'warn');
      } catch (e) { notify('ensemble unavailable: ' + (e.message || e), 'warn'); }
    } else if (S.resolution === 'live') {
      if (window.HelmWxLive && window.HelmWxLive.supports(layer)) {
        showLegacy(false);
        // onState: online → Live (particles + field) fills the view; offline → fall back to the
        // static local field so there's always something (never a blank screen).
        window.HelmWxLive.enable(map, { layer: layer, notify: notify, onState: function (s) { showLegacy(s === 'offline'); } });
      } else {
        showLegacy(true);                                  // marine layers (waves/swell/sst/current) — static for now
        notify(layer + ' is a marine layer — Live not wired yet; showing Standard.', 'warn');
      }
    } else {
      showLegacy(true);                                   // Standard + Single → the legacy field handles it
      notify('');
      var nn = document.getElementById('wx-notice'); if (nn) nn.style.display = 'none';
    }
    probeSoon();
  }

  function setProbe(html) { if (S.els.probe) S.els.probe.innerHTML = html || '<span style="color:var(--cdim,#8aa)">move the map to read a value</span>'; }
  function probeSoon() { clearTimeout(S.probeT); S.probeT = setTimeout(probe, 250); }
  async function probe() {
    var map = S.map, c = map.getCenter(), m = await cog(), layer = activeLayer();
    if (layer === 'off') return setProbe('');
    var s = null;
    if (S.model === 'ensemble') { var e = await m.sampleEnsemble(c.lat, c.lng); if (e && e.value != null) return setProbe('<b>' + e.mean + ' ' + e.unit + '</b> · spread ' + e.spread + ' · ' + e.agreement); }
    else if (S.resolution === 'live' && window.HelmWxLive) { s = window.HelmWxLive.sampleAt(c.lat, c.lng); }
    if (s && s.value != null) return setProbe('<b>' + s.value + ' ' + s.unit + '</b> @ centre · ' + (s.sourceRef ? s.sourceRef.title : s.source));
    setProbe('');
  }

  function build(drawer, map) {
    S.map = map;
    var box = document.createElement('div');
    box.id = 'wx-plus';
    box.style.cssText = 'margin-top:12px;border-top:.5px solid var(--line,#2a3540);padding-top:11px';
    function label(t) { var d = document.createElement('div'); d.textContent = t; d.style.cssText = 'font-size:11px;color:var(--cdim,#8aa);margin:0 0 5px'; return d; }
    function segctl(opts) {
      var w = document.createElement('div'); w.style.cssText = 'display:flex;border:.5px solid var(--line,#345);border-radius:8px;overflow:hidden;margin-bottom:10px';
      opts.forEach(function (o) {
        var b = document.createElement('button'); b.dataset.val = o.val; b.textContent = o.txt;
        b.style.cssText = 'flex:1;font-size:12px;padding:7px;border:0;background:transparent;color:var(--cdim,#8aa);cursor:pointer';
        b.addEventListener('mouseenter', function () { if (b.dataset.sel !== '1') b.style.background = 'rgba(255,255,255,.04)'; });
        b.addEventListener('mouseleave', function () { b.style.background = b.dataset.sel === '1' ? 'var(--accent,#39c2c9)' : 'transparent'; });
        w.appendChild(b);
      });
      return w;
    }
    function paintSeg(w, on) { Array.prototype.forEach.call(w.children, function (b) { var sel = b.dataset.val === on; b.dataset.sel = sel ? '1' : ''; b.style.background = sel ? 'var(--accent,#39c2c9)' : 'transparent'; b.style.color = sel ? '#05121d' : 'var(--cdim,#8aa)'; b.style.fontWeight = sel ? '600' : '400'; }); }

    box.appendChild(label('Resolution'));
    var resSeg = segctl([{ val: 'standard', txt: 'Standard' }, { val: 'live', txt: 'Live · fills view' }]);
    box.appendChild(resSeg);
    box.appendChild(label('Model'));
    var modSeg = segctl([{ val: 'single', txt: 'Single' }, { val: 'ensemble', txt: 'Ensemble spread' }]);
    box.appendChild(modSeg);

    var probe = document.createElement('div');
    probe.style.cssText = 'font-size:12px;background:rgba(255,255,255,.03);border:.5px solid var(--line,#345);border-radius:8px;padding:8px 10px;margin-bottom:10px;min-height:16px';
    box.appendChild(probe); S.els.probe = probe;

    var imp = document.createElement('div');
    imp.style.cssText = 'border:.5px dashed var(--line,#456);border-radius:8px;padding:8px 10px';
    imp.innerHTML = '<div style="font-size:12px;margin-bottom:4px"><span style="vertical-align:1px">⤓</span> Import PredictWind GPX / GRIB</div>' +
      '<div style="font-size:11px;color:var(--cdim,#8aa);margin-bottom:6px">device-local · never synced</div>';
    var file = document.createElement('input'); file.type = 'file'; file.accept = '.gpx,.grb,.grb2,.grib,.grib2'; file.style.cssText = 'font-size:11px;color:#cdd9e3;width:100%';
    file.addEventListener('change', function () { if (file.files && file.files[0] && window.HelmImport) { window.HelmImport.importFile(file.files[0], map, notify); } file.value = ''; });
    imp.appendChild(file); box.appendChild(imp);

    // insert after the transparency row (#wxopacity), before the legend
    var anchor = drawer.querySelector('#wxopacity');
    anchor = anchor ? (anchor.closest('.row') || anchor) : null;
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
    else drawer.appendChild(box);

    paintSeg(resSeg, S.resolution); paintSeg(modSeg, S.model);
    resSeg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; S.resolution = b.dataset.val; paintSeg(resSeg, S.resolution); apply(); });
    modSeg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; S.model = b.dataset.val; paintSeg(modSeg, S.model); apply(); });
    setProbe('');

    // re-apply my mode whenever the user picks a different weather layer
    var wx = document.getElementById('wx');
    if (wx) wx.addEventListener('click', function (e) { if (e.target.closest('button')) setTimeout(apply, 60); });
    map.on('moveend', probeSoon);
  }

  function boot() {
    var map = window.map || (window.HelmShell && HelmShell.panel ? null : null);
    var drawer = document.getElementById('drawer-weather');
    if (!window.map || !drawer) return setTimeout(boot, 300);
    if (document.getElementById('wx-plus')) return;        // already built
    build(drawer, window.map);
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') setTimeout(boot, 400);
  else window.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 400); });
})();
