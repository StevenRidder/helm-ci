// web/tides.js — TIDES presentation layer (SHELL drop-in).
// A "Tides" rail panel + tide-station map markers + a tap card, all on index.html's --accent/--glass
// tokens. Data from the engine: /tides/summary (now), /tides/curve (24h in one call), /tides/stations.
// No edits to index.html beyond the <script> tag; everything registers through window.HelmShell.
(function () {
  'use strict';
  if (!window.HelmShell) { (window.console || {}).error && console.error('tides.js: HelmShell missing'); return; }
  var Shell = window.HelmShell;

  // ---------- helpers ----------
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmtM(v) { return (v == null || isNaN(v)) ? '—' : (Math.round(v * 100) / 100).toFixed(2); }
  function hhmm(iso) { try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return iso; } }
  var KIND = { high_water: 'High water', low_water: 'Low water', high: 'High water', low: 'Low water' };
  function kindLabel(k) { return KIND[k] || String(k || '').replace(/_/g, ' '); }
  function getJSON(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) { if (j && j.ok === false) throw new Error(j.error || 'tide error'); return j; });
  }

  // where to query: live boat fix → else map centre → else Honolulu (the free default station)
  var navPos = null;
  if (Shell.onNav) Shell.onNav(function (s) { if (s && typeof s.lat === 'number' && typeof s.lon === 'number') navPos = { lat: s.lat, lon: s.lon }; });
  function queryPoint(map) {
    if (navPos) return navPos;
    if (map && map.getCenter) { var c = map.getCenter(); return { lat: c.lat, lon: c.lng }; }
    return { lat: 21.3069, lon: -157.8583 };
  }

  // ---------- the tide-curve instrument (inline SVG) ----------
  // A real instrument: smooth-ish line + area, datum/zero reference, time-of-day grid, a NOW marker,
  // and high/low pins from curve.events — so the headline number and the plot agree.
  function curveSVG(curve) {
    var s = (curve && curve.samples) || [];
    if (s.length < 2) return '<div class="t-empty">curve unavailable</div>';
    var W = 244, H = 132, L = 6, R = 6, T = 12, B = 20;
    var xs = s.map(function (p) { return Date.parse(p.t_utc); });
    var ys = s.map(function (p) { return p.value_m; });
    var t0 = xs[0], t1 = xs[xs.length - 1];
    var ymin = Math.min.apply(null, ys), ymax = Math.max.apply(null, ys);
    if (curve.datum_m != null) { ymin = Math.min(ymin, curve.datum_m); ymax = Math.max(ymax, curve.datum_m); }
    var pad = Math.max(0.05, (ymax - ymin) * 0.16); ymin -= pad; ymax += pad;
    var X = function (t) { return L + (t - t0) / (t1 - t0) * (W - L - R); };
    var Y = function (v) { return T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B); };
    var line = '', i;
    for (i = 0; i < s.length; i++) line += (i ? 'L' : 'M') + X(xs[i]).toFixed(1) + ' ' + Y(ys[i]).toFixed(1) + ' ';
    var area = line + 'L' + X(t1).toFixed(1) + ' ' + Y(ymin).toFixed(1) + ' L' + X(t0).toFixed(1) + ' ' + Y(ymin).toFixed(1) + ' Z';

    // time-of-day gridlines every 6h (local), labelled
    var grid = '', d = new Date(t0); d.setMinutes(0, 0, 0); d.setHours(Math.ceil(d.getHours() / 6) * 6);
    for (var g = d.getTime(); g <= t1; g += 6 * 3600e3) {
      var gx = X(g).toFixed(1);
      grid += '<line x1="' + gx + '" y1="' + T + '" x2="' + gx + '" y2="' + (H - B) + '" stroke="var(--line2)"/>';
      grid += '<text x="' + gx + '" y="' + (H - 6) + '" fill="var(--cdim2)" font-size="8.5" text-anchor="middle">' +
        new Date(g).toLocaleTimeString([], { hour: '2-digit' }).replace(/\s/g, '') + '</text>';
    }
    // datum / zero reference
    var datum = '';
    if (curve.datum_m != null && curve.datum_m >= ymin && curve.datum_m <= ymax) {
      var dy = Y(curve.datum_m).toFixed(1);
      datum = '<line x1="' + L + '" y1="' + dy + '" x2="' + (W - R) + '" y2="' + dy + '" stroke="var(--cdim2)" stroke-dasharray="3 3"/>' +
        '<text x="' + (W - R) + '" y="' + (Number(dy) - 3) + '" fill="var(--cdim2)" font-size="8" text-anchor="end">datum ' + fmtM(curve.datum_m) + 'm</text>';
    }
    // NOW marker
    var now = Date.now(), nowEl = '';
    if (now >= t0 && now <= t1) {
      var nx = X(now).toFixed(1);
      // interpolate the current value for the dot
      var k = 0; while (k < xs.length - 1 && xs[k + 1] < now) k++;
      var f = (now - xs[k]) / (xs[k + 1] - xs[k] || 1), nv = ys[k] + (ys[k + 1] - ys[k]) * f;
      nowEl = '<line x1="' + nx + '" y1="' + T + '" x2="' + nx + '" y2="' + (H - B) + '" stroke="var(--accent)" stroke-width="1.25"/>' +
        '<circle cx="' + nx + '" cy="' + Y(nv).toFixed(1) + '" r="3.4" fill="var(--accent)" stroke="var(--bg,#05080c)" stroke-width="1.5"/>';
    }
    // high/low pins
    var pins = '';
    (curve.events || []).forEach(function (e) {
      var t = Date.parse(e.event_utc); if (t < t0 || t > t1) return;
      var px = X(t), py = Y(e.value_m), hi = /high/.test(e.kind);
      pins += '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="2.6" fill="var(--ctext)"/>' +
        '<text x="' + px.toFixed(1) + '" y="' + (hi ? py - 5 : py + 11).toFixed(1) + '" fill="var(--cdim)" font-size="8" text-anchor="middle">' +
        (hi ? '▲' : '▼') + ' ' + hhmm(e.event_utc) + '</text>';
    });
    return '<svg class="t-curve" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">' +
      grid + datum +
      '<path d="' + area + '" fill="var(--accent)" fill-opacity="0.13"/>' +
      '<path d="' + line + '" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
      pins + nowEl + '</svg>';
  }

  // ---------- the tide card body (shared by the panel + the map tap popup) ----------
  function cardHTML(sum, curve) {
    var st = (sum && sum.station) || {};
    var ev = (sum && sum.next_event) || {};
    var cleared = st.source_redistribution_cleared;
    var chips =
      '<span class="t-chip ' + (cleared ? 'ok' : 'warn') + '">' + (cleared ? 'Free · public-domain' : 'Commercial-review') + '</span>' +
      (st.source_enabled_by_default ? '<span class="t-chip ok">default source</span>' : '<span class="t-chip warn">explicit opt-in</span>');
    var next = (ev && ev.ok !== false && ev.kind)
      ? '<div class="t-next"><span class="t-nl">Next ' + esc(kindLabel(ev.kind)).toLowerCase() + '</span>' +
        '<span class="t-nt">' + hhmm(ev.event_utc) + '</span><span class="t-nv">' + fmtM(ev.value_m) + ' m</span></div>'
      : '<div class="t-next"><span class="t-nl">Next event</span><span class="t-nt t-dim">unavailable</span></div>';
    return '' +
      '<div class="t-hero"><div class="t-big">' + fmtM(sum && sum.value_m) + '<span class="t-unit">m</span></div>' +
        '<div class="t-stn">' + esc(st.name || '—') + '</div>' +
        '<div class="t-meta">' + (st.distance_nm >= 0 ? (Math.round(st.distance_nm * 10) / 10) + ' nm to station · ' : '') +
        (st.has_datum ? 'datum ' + fmtM(st.datum_m) + ' m' : 'no datum') + '</div>' +
        '<div class="t-chips">' + chips + '</div></div>' +
      next +
      (curve ? '<div class="t-curvewrap">' + curveSVG(curve) + '</div>' : '');
  }

  function styles() {
    return '<style id="helm-tides-style">' +
      '.t-hero .t-big{font:600 40px/1 var(--font,inherit);letter-spacing:-1px;color:var(--ctext);font-variant-numeric:tabular-nums}' +
      '.t-hero .t-unit{font-size:16px;color:var(--cdim);margin-left:3px}' +
      '.t-stn{font-size:12px;color:var(--ctext);margin-top:6px}' +
      '.t-meta{font-size:10.5px;color:var(--cdim);margin-top:2px;font-variant-numeric:tabular-nums}' +
      '.t-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}' +
      '.t-chip{font-size:9.5px;padding:2px 7px;border-radius:999px;border:.5px solid var(--line);background:var(--glass2);color:var(--cdim)}' +
      '.t-chip.ok{color:var(--ok);border-color:rgba(70,224,160,.35)}' +
      '.t-chip.warn{color:var(--warn);border-color:rgba(255,192,106,.35)}' +
      '.t-next{display:flex;align-items:baseline;gap:8px;margin:12px 0;padding-top:10px;border-top:.5px solid var(--line2)}' +
      '.t-nl{font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--cdim2)}' +
      '.t-nt{font-size:15px;color:var(--ctext);font-variant-numeric:tabular-nums}' +
      '.t-nv{font-size:12px;color:var(--cdim)}.t-dim{color:var(--cdim2)}' +
      '.t-curvewrap{margin-top:6px}.t-curve{width:100%;height:auto;display:block}' +
      '.t-empty{font-size:10.5px;color:var(--cdim2);padding:14px 0}' +
      '.t-src{margin-top:12px;padding-top:10px;border-top:.5px solid var(--line2)}' +
      '.t-srcrow{display:flex;justify-content:space-between;gap:8px;font-size:10px;padding:3px 0;color:var(--cdim)}' +
      '.t-srcrow b{color:var(--ctext);font-weight:500}' +
      '.maplibregl-popup.helm-tides-pop .maplibregl-popup-content{min-width:212px}' +
      '</style>';
  }

  // ---------- the Tides panel ----------
  var lastQP = null;
  function loadInto(el, map) {
    var qp = queryPoint(map); lastQP = qp;
    el.querySelector('.t-body').innerHTML = '<div class="t-empty">loading tides…</div>';
    var q = '?lat=' + qp.lat.toFixed(4) + '&lon=' + qp.lon.toFixed(4);
    Promise.all([getJSON('/tides/summary' + q), getJSON('/tides/curve' + q + '&hours=24&step=30').catch(function () { return null; })])
      .then(function (r) {
        var sum = r[0], curve = r[1];
        el.querySelector('.t-body').innerHTML = cardHTML(sum, curve) + sourceLedger(sum);
      })
      .catch(function (e) { el.querySelector('.t-body').innerHTML = '<div class="t-empty" style="color:var(--danger)">tides: ' + esc(e.message) + '</div>'; });
  }
  function sourceLedger(sum) {
    var src = (sum && sum.loaded_sources) || [];
    if (!src.length) return '';
    var rows = src.map(function (s) {
      return '<div class="t-srcrow"><b>' + esc(s.basename || s.path) + '</b><span>' + esc(s.license || 'unknown') + '</span></div>';
    }).join('');
    return '<div class="t-src"><div class="lbl">Sources · ' + esc(sum.source_policy || '') + '</div>' + rows + '</div>';
  }

  var TIDE_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M2 15c2.5 0 2.5-3 5-3s2.5 3 5 3 2.5-3 5-3 2.5 3 5 3"/><path d="M2 10c2.5 0 2.5-3 5-3s2.5 3 5 3 2.5-3 5-3 2.5 3 5 3"/></svg>';

  Shell.registerPanel({
    id: 'helm-tides-panel', epic: 'TIDES', title: 'Tides', icon: TIDE_ICON,
    render: function (body, ctx) {
      if (!document.getElementById('helm-tides-style')) body.insertAdjacentHTML('beforeend', styles());
      body.insertAdjacentHTML('beforeend', '<div class="sub">Offline harmonics, source-tagged · OpenCPN TCMgr</div><div class="t-body"></div>');
      ensureStations(ctx && ctx.map);
      loadInto(body, ctx && ctx.map);
    },
    onOpen: function (body, ctx) { loadInto(body, ctx && ctx.map); }
  });
  if (Shell.registerCommand) Shell.registerCommand({
    id: 'helm-tides-open', epic: 'TIDES', title: 'Tides', subtitle: 'water level, next high/low, station',
    keywords: 'tide tides water level high low slack', group: 'Layers',
    run: function () { var p = Shell.panel && Shell.panel('helm-tides-panel'); if (p) p.open(); }
  });

  // ---------- tide-station markers + tap card ----------
  var stationsWired = false, stTimer = null;
  function ensureStations(map) {
    if (!map || stationsWired) return;
    function wire() {
      if (map.getSource('helm-tides-src')) return;
      map.addSource('helm-tides-src', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'helm-tides-station', type: 'circle', source: 'helm-tides-src', minzoom: 6,
        paint: { 'circle-radius': 5, 'circle-color': '#0b1620', 'circle-stroke-color': '#5bc0ff', 'circle-stroke-width': 2, 'circle-opacity': 0.95 } });
      map.addLayer({ id: 'helm-tides-station-label', type: 'symbol', source: 'helm-tides-src', minzoom: 10,
        layout: { 'text-field': ['get', 'name'], 'text-size': 10, 'text-offset': [0, 1.1], 'text-anchor': 'top', 'text-optional': true },
        paint: { 'text-color': '#bcd3e2', 'text-halo-color': '#05080c', 'text-halo-width': 1.2 } });
      map.on('moveend', function () { refreshStations(map); });
      map.on('mouseenter', 'helm-tides-station', function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'helm-tides-station', function () { map.getCanvas().style.cursor = ''; });
      map.on('click', 'helm-tides-station', function (e) {
        if (window.measuring && window.measuring()) return;
        var f = e.features && e.features[0]; if (!f) return;
        openStationCard(map, f.geometry.coordinates, f.properties);
      });
      refreshStations(map);
      stationsWired = true;
    }
    if (map.isStyleLoaded && map.isStyleLoaded()) wire(); else map.once('load', wire);
  }
  function refreshStations(map) {   // trailing debounce: always fetch once after the view settles (robust vs hash-set views)
    clearTimeout(stTimer);
    stTimer = setTimeout(function () {
      if (map.getZoom() < 6) { var s = map.getSource('helm-tides-src'); if (s) s.setData({ type: 'FeatureCollection', features: [] }); return; }
      var b = map.getBounds();
      var bbox = b.getWest().toFixed(4) + ',' + b.getSouth().toFixed(4) + ',' + b.getEast().toFixed(4) + ',' + b.getNorth().toFixed(4);
      getJSON('/tides/stations?bbox=' + bbox + '&limit=300').then(function (fc) {
        var src = map.getSource('helm-tides-src'); if (src && fc && fc.features) src.setData(fc);
      }).catch(function () {});
    }, 250);
  }
  function openStationCard(map, lngLat, props) {
    if (!window.maplibregl) return;
    var q = '?lat=' + lngLat[1].toFixed(4) + '&lon=' + lngLat[0].toFixed(4);
    var pop = new window.maplibregl.Popup({ className: 'helm-tides-pop', maxWidth: '248px', closeButton: true })
      .setLngLat(lngLat).setHTML('<div class="t-body"><div class="t-empty">loading…</div></div>').addTo(map);
    if (!document.getElementById('helm-tides-style')) document.head.insertAdjacentHTML('beforeend', styles());
    Promise.all([getJSON('/tides/summary' + q), getJSON('/tides/curve' + q + '&hours=24&step=30').catch(function () { return null; })])
      .then(function (r) { try { pop.setHTML('<div class="t-body">' + cardHTML(r[0], r[1]) + '</div>'); } catch (e) {} })
      .catch(function (e) { pop.setHTML('<div class="t-body"><div class="t-empty" style="color:var(--danger)">' + esc(e.message) + '</div></div>'); });
  }

  // Wire the tide-station markers as soon as the map exists — independent of the Tides panel,
  // so stations show on the chart whenever you're zoomed in (not only when the drawer is open).
  (function waitForMap(tries) {
    if (window.map && window.map.isStyleLoaded) { ensureStations(window.map); return; }
    if (tries < 120) setTimeout(function () { waitForMap(tries + 1); }, 200);
  })(0);
})();
