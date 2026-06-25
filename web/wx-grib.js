// wx-grib.js — Tier-2 value-encoded weather layer + probe.  WX epic · WX-10.
// ----------------------------------------------------------------------------------------------
// Registers a left-rail PANEL + ⌘K command via HelmShell (zero edits to index.html's body) for the
// value-encoded (Mercator) weather tiles baked by pipeline/make_value_tiles.py and rendered/decoded
// by web/integrations/cog.js. Picks a layer, toggles it, scrubs forecast frames, sets opacity, and
// shows a LIVE sample(lat,lon,t) readout under the map centre — proving the heatmap and the probe
// read the SAME decoded values. Also exposes window.__helmWxSample(lat,lon,t) for ROUTING-3's
// spacetime probe and AI-5's layer sample() faces to consume.
(function () {
  'use strict';
  if (!window.HelmShell) { console.warn('[wx-grib] HelmShell missing — value-encoded weather panel not registered'); return; }

  var INDEX_URL = 'data/wxtiles/index.json';
  var cogMod = null;                              // lazily imported web/integrations/cog.js (ES module)
  function cog() { return cogMod ? Promise.resolve(cogMod) : import('./integrations/cog.js').then(function (m) { return (cogMod = m); }); }

  var st = { map: null, layers: null, layer: null, frame: 0, manifest: null, on: false, els: {} };

  function fmtTime(iso) {
    if (!iso) return '';
    var d = new Date(iso.length <= 19 && iso.indexOf('Z') < 0 ? iso + 'Z' : iso);
    return isNaN(d) ? iso : d.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  }
  function notify(msg, level) {
    var s = st.els.status; if (!s) return;
    s.textContent = msg; s.style.color = level === 'warn' ? 'var(--warn,#e8a13a)' : 'var(--cdim,#8aa)';
  }

  // (re)build the layer <select> from data/wxtiles/index.json (honest empty-state if the pack is absent).
  function loadIndex() {
    return fetch(INDEX_URL).then(function (r) { return r.ok ? r.json() : null; }).then(function (idx) {
      st.layers = (idx && idx.layers) || {};
      var sel = st.els.layerSel; sel.innerHTML = '';
      var names = Object.keys(st.layers);
      if (!names.length) { notify('No value-tile pack found — run: pipeline/make_value_tiles.py --demo', 'warn'); st.els.toggle.disabled = true; return; }
      names.forEach(function (n) {
        var o = document.createElement('option'); o.value = n;
        o.textContent = n + ' (' + st.layers[n].unit + ', ' + st.layers[n].frames + 'f, ' + st.layers[n].model + ')';
        sel.appendChild(o);
      });
      st.layer = names[0]; sel.value = st.layer; st.els.toggle.disabled = false;
    }).catch(function () { notify('value-tile index unavailable (offline?)', 'warn'); });
  }

  function manifestUrl(layer) { return 'data/wxtiles/' + layer + '/manifest.json'; }

  function enable() {
    return cog().then(function (m) {
      return m.enableWxTiles(st.map, {
        maplibregl: window.maplibregl, manifestUrl: manifestUrl(st.layer),
        beforeId: st.map.getLayer('route-line') ? 'route-line' : undefined,
        opacity: (+st.els.op.value) / 100, frame: st.frame, notify: notify,
      });
    }).then(function (cfg) {
      if (!cfg) { st.on = false; st.els.toggle.checked = false; return; }
      st.on = true; st.manifest = cfg;
      window.__helmWxActive = { layer: cfg.layer, unit: cfg.unit, model: cfg.model, source: cfg.source };
      buildFrames(cfg); buildLegend(cfg); sampleAtCenter();
    });
  }
  function disable() {
    if (!cogMod) return; st.on = false; window.__helmWxActive = null;
    cogMod.disableWxTiles(st.map); st.els.frameWrap.style.display = 'none';
    st.els.legend.style.display = 'none'; notify('weather layer off');
    st.els.readout.textContent = '';
  }

  function buildFrames(cfg) {
    var n = cfg.times ? cfg.times.length : 1, w = st.els.frameWrap;
    if (n <= 1) { w.style.display = 'none'; return; }
    w.style.display = 'block';
    var sl = st.els.frame; sl.max = n - 1; sl.value = Math.min(st.frame, n - 1);
    st.frame = +sl.value; st.els.frameLbl.textContent = fmtTime(cfg.times[st.frame]);
  }
  function buildLegend(cfg) {
    var leg = st.els.legend; if (!cfg.ramp) { leg.style.display = 'none'; return; }
    var lo = cfg.vmin, hi = cfg.vmax, span = (hi - lo) || 1;
    var grad = cfg.ramp.map(function (s) {
      var pct = Math.max(0, Math.min(100, (s[0] - lo) / span * 100)), c = s[1], a = c.length > 3 ? c[3] : 1;
      return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ') ' + pct + '%';
    }).join(',');
    st.els.legBar.style.background = 'linear-gradient(90deg,' + grad + ')';
    st.els.legMin.textContent = Math.round(lo); st.els.legMax.textContent = Math.round(hi) + ' ' + cfg.unit;
    leg.style.display = 'block';
  }

  // The live probe demo: sample the active value-tile layer under the map centre and show provenance.
  function sampleAtCenter() {
    if (!st.on || !cogMod) { st.els.readout.textContent = ''; return; }
    var c = st.map.getCenter(), t = st.manifest && st.manifest.times ? st.manifest.times[st.frame] : null;
    cogMod.sampleWx(c.lat, c.lng, t).then(function (s) {
      if (!s) { st.els.readout.textContent = ''; return; }
      var v = s.value == null ? '— ' + (s.note || 'no data') : (s.value + ' ' + s.unit);
      st.els.readout.innerHTML = '<b>' + v + '</b> @ centre · <span style="color:var(--cdim,#8aa)">' +
        s.sourceRef.title + (s.validTime ? ' · ' + fmtTime(s.validTime) : '') + ' · ' + s.confidence + '</span>';
    });
  }

  HelmShell.registerPanel({
    id: 'helm-wx-grib', epic: 'WX', title: 'Weather (value-encoded)', icon: 'G',
    render: function (body, ctx) {
      st.map = ctx.map;
      body.innerHTML =
        '<p class="sub" style="margin:.2em 0 1em">Tier-2 value-encoded (Mercator) weather tiles — each pixel\'s RGB ' +
        'is a real measurement, decoded + colourised in your browser (no tiler). The same tiles answer the ' +
        'spacetime probe. <b>Forecast — not for navigation.</b></p>';
      function row(label, el) {
        var r = document.createElement('div'); r.className = 'row'; r.style.cssText = 'display:flex;align-items:center;gap:8px;margin:7px 0';
        var s = document.createElement('span'); s.textContent = label; s.style.cssText = 'font-size:12px;color:var(--cdim,#8aa);min-width:72px';
        r.appendChild(s); r.appendChild(el); body.appendChild(r); return r;
      }
      var sel = document.createElement('select'); sel.style.cssText = 'flex:1;background:rgba(255,255,255,.06);color:#cdd9e3;border:.5px solid var(--line,#345);border-radius:7px;padding:5px';
      var tog = document.createElement('input'); tog.type = 'checkbox';
      var op = document.createElement('input'); op.type = 'range'; op.min = 0; op.max = 100; op.value = 82; op.style.flex = '1';
      var frame = document.createElement('input'); frame.type = 'range'; frame.min = 0; frame.max = 0; frame.value = 0; frame.style.flex = '1';
      st.els = { layerSel: sel, toggle: tog, op: op, frame: frame };

      row('Layer', sel);
      var tr = row('Show', tog);
      st.els.status = document.createElement('div'); st.els.status.style.cssText = 'font-size:11px;color:var(--cdim,#8aa);margin:2px 0 6px;min-height:14px';
      body.appendChild(st.els.status);
      row('Opacity', op);
      var fw = document.createElement('div'); fw.style.display = 'none';
      var fl = document.createElement('div'); fl.style.cssText = 'font-size:11px;color:var(--cdim,#8aa);text-align:center;margin-top:2px';
      fw.appendChild(frame); fw.appendChild(fl); body.appendChild(fw);
      st.els.frameWrap = fw; st.els.frameLbl = fl;
      // legend
      var leg = document.createElement('div'); leg.style.cssText = 'display:none;margin:10px 0 4px';
      var bar = document.createElement('div'); bar.style.cssText = 'height:8px;border-radius:4px;border:.5px solid var(--line,#345)';
      var lr = document.createElement('div'); lr.style.cssText = 'display:flex;justify-content:space-between;font-size:10px;color:var(--cdim,#8aa);margin-top:2px';
      var lmin = document.createElement('span'), lmax = document.createElement('span'); lr.appendChild(lmin); lr.appendChild(lmax);
      leg.appendChild(bar); leg.appendChild(lr); body.appendChild(leg);
      st.els.legend = leg; st.els.legBar = bar; st.els.legMin = lmin; st.els.legMax = lmax;
      // live probe readout
      var ro = document.createElement('div'); ro.style.cssText = 'font-size:12px;margin-top:10px;padding:7px 9px;border:.5px solid var(--line,#345);border-radius:8px;background:rgba(255,255,255,.03);min-height:16px';
      body.appendChild(ro); st.els.readout = ro;
      var hint = document.createElement('div'); hint.className = 'sub'; hint.style.cssText = 'font-size:10px;color:var(--cdim,#8aa);margin-top:5px';
      hint.textContent = 'Sample under map centre — pan to probe. Exposed as window.__helmWxSample(lat,lon,t).';
      body.appendChild(hint);

      // events
      sel.addEventListener('change', function () { st.layer = sel.value; st.frame = 0; if (st.on) enable(); });
      tog.addEventListener('change', function () { tog.checked ? enable() : disable(); });
      op.addEventListener('input', function () { if (cogMod) cogMod.setWxOpacity(st.map, (+op.value) / 100); });
      frame.addEventListener('input', function () {
        st.frame = +frame.value;
        if (st.manifest && st.manifest.times) fl.textContent = fmtTime(st.manifest.times[st.frame]);
        if (cogMod) cogMod.setWxFrame(st.map, st.frame);
        sampleAtCenter();
      });
      st.map.on('moveend', sampleAtCenter);
      loadIndex();
    },
  });

  HelmShell.registerCommand({
    id: 'helm-wx-grib-open', epic: 'WX', title: 'Weather: value-encoded layer + probe',
    subtitle: 'Tier-2 GRIB value tiles', keywords: ['weather', 'grib', 'wind', 'pressure', 'value', 'probe'], group: 'Weather',
    run: function () { var h = HelmShell.panel('helm-wx-grib'); if (h) h.open(); },
  });

  // Probe face for ROUTING-3 (spacetime probe) + AI-5 (layer sample()): sample(lat, lon, t) ->
  // LayerSample. Async (decodes value tiles on demand); returns null if no value layer is active.
  window.__helmWxSample = function (lat, lon, t, opts) {
    return cog().then(function (m) { return m.sampleWx(lat, lon, t, opts); });
  };
})();
