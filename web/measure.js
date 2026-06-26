// HelmMeasure — keepable, editable range/bearing planning lines for the chart.
//
// Draw a line (tap to add points, ⏎ or double-tap to finish); it STAYS on the chart with its per-leg
// range·bearing labels and persists across reloads (HelmStore). Keep as many as you like — for a quick
// measure, or for laying out tack lines. With the tool open you can tap a finished line to re-select +
// extend it, drag any vertex to adjust, Backspace to drop the last point, or ✕ to delete it. Closing the
// tool leaves every line drawn on the chart; reopening lets you edit again.
//
// Units: nautical miles + degrees true (great-circle), matching ScaleControl + the nav core.
(function () {
  const R = 3440.065;                         // earth radius, nautical miles
  const toR = d => d * Math.PI / 180, toD = r => r * 180 / Math.PI;

  function dist(a, b) {                        // great-circle NM between [lng,lat] points
    const dLat = toR(b[1] - a[1]), dLon = toR(b[0] - a[0]);
    const s = Math.sin(dLat / 2) ** 2 +
      Math.cos(toR(a[1])) * Math.cos(toR(b[1])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
  }
  function brg(a, b) {                         // initial bearing °, [lng,lat] points
    const y = Math.sin(toR(b[0] - a[0])) * Math.cos(toR(b[1]));
    const x = Math.cos(toR(a[1])) * Math.sin(toR(b[1])) -
      Math.sin(toR(a[1])) * Math.cos(toR(b[1])) * Math.cos(toR(b[0] - a[0]));
    return (toD(Math.atan2(y, x)) + 360) % 360;
  }
  const mid = (a, b) => [a[0] + (b[0] - a[0]) / 2, a[1] + (b[1] - a[1]) / 2];   // fine for short legs
  const fmtNM = nm => (nm < 1 ? Math.round(nm * 100) / 100 : Math.round(nm * 10) / 10) + ' NM';
  const fmtBrg = d => String(Math.round(d) % 360).padStart(3, '0') + '°';

  window.HelmMeasure = function (map, opts) {
    opts = opts || {};
    const onChange = opts.onChange || function () {};
    const COL = opts.color || '#5bc0ff';        // line colour
    const HI = '#9fe0ff';                        // selected / editing line + its vertices
    const STORE = 'measure.lines';

    let active = false;       // tool (edit) mode on
    let lines = [];           // saved lines: [{ id, pts:[[lng,lat], …] }]
    let cur = null;           // id of the line being drawn / edited, or null
    let drawing = false;      // rubber-band active (taps extend `cur`)
    let cursor = null;        // live cursor for the rubber-band
    let drag = null;          // { id, idx } vertex being dragged
    let justDragged = false;  // swallow the click that ends a drag
    let _seq = 0; const uid = () => 'm' + (++_seq);
    const lineById = id => lines.find(l => l.id === id);

    // ---- persistence (HelmStore) — a tack plan survives a reload ----
    function persist() { try { if (window.HelmStore) HelmStore.set(STORE, lines.map(l => l.pts)); } catch (e) {} }
    function load() {
      try { const raw = window.HelmStore ? (HelmStore.get(STORE, []) || []) : [];
        return raw.filter(a => Array.isArray(a) && a.length >= 2).map(pts => ({ id: uid(), pts: pts.slice() }));
      } catch (e) { return []; }
    }

    // ---- HUD (glass card, one big number) ----
    const hud = document.createElement('div');
    hud.className = 'measure-hud glass';
    hud.hidden = true;
    hud.innerHTML =
      '<div><div class="mt" id="measure-total">0 NM</div>' +
      '<div class="ms" id="measure-sub">Tap the chart to start</div></div>' +
      '<div class="mx" id="measure-clear" title="Delete this line">✕</div>';
    document.body.appendChild(hud);
    const elTotal = hud.querySelector('#measure-total');
    const elSub = hud.querySelector('#measure-sub');
    hud.querySelector('#measure-clear').addEventListener('click', deleteCur);

    // ---- map source + layers (added once the style is ready) ----
    function ensureLayers() {
      if (!map.getStyle || !map.getStyle() || map.getSource('measure')) return;
      map.addSource('measure', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({
        id: 'measure-line', type: 'line', source: 'measure', filter: ['==', ['get', 'kind'], 'line'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ['case', ['get', 'sel'], HI, COL], 'line-width': ['case', ['get', 'sel'], 3, 2.5] }
      });
      map.addLayer({
        id: 'measure-preview', type: 'line', source: 'measure', filter: ['==', ['get', 'kind'], 'preview'],
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': COL, 'line-width': 2, 'line-opacity': 0.8, 'line-dasharray': [1.5, 1.5] }
      });
      map.addLayer({
        id: 'measure-points', type: 'circle', source: 'measure', filter: ['==', ['get', 'kind'], 'vertex'],
        paint: {
          'circle-radius': ['case', ['get', 'sel'], 6, 4.5], 'circle-color': ['case', ['get', 'sel'], HI, COL],
          'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5
        }
      });
      map.addLayer({
        id: 'measure-labels', type: 'symbol', source: 'measure', filter: ['==', ['get', 'kind'], 'label'],
        layout: { 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Regular'], 'text-size': 11, 'text-offset': [0, -0.9], 'text-allow-overlap': true },
        paint: { 'text-color': '#eef4f9', 'text-halo-color': 'rgba(5,8,12,0.9)', 'text-halo-width': 1.4 }
      });
      // grab-cursor over vertices + start a vertex drag (mouse + touch)
      map.on('mouseenter', 'measure-points', () => { if (active) map.getCanvas().style.cursor = 'grab'; });
      map.on('mouseleave', 'measure-points', () => { if (active) map.getCanvas().style.cursor = 'crosshair'; });
      ['mousedown', 'touchstart'].forEach(ev => map.on(ev, 'measure-points', startDrag));
    }

    // ---- render every saved line + the one being drawn ----
    function build() {
      ensureLayers();
      const feats = [];
      lines.forEach(L => {
        const sel = (L.id === cur);
        if (L.pts.length >= 2) feats.push({ type: 'Feature', properties: { kind: 'line', sel, lid: L.id }, geometry: { type: 'LineString', coordinates: L.pts } });
        for (let i = 0; i < L.pts.length - 1; i++) feats.push({
          type: 'Feature', properties: { kind: 'label', label: fmtNM(dist(L.pts[i], L.pts[i + 1])) + ' · ' + fmtBrg(brg(L.pts[i], L.pts[i + 1])) },
          geometry: { type: 'Point', coordinates: mid(L.pts[i], L.pts[i + 1]) }
        });
        L.pts.forEach((p, idx) => feats.push({ type: 'Feature', properties: { kind: 'vertex', sel, lid: L.id, idx }, geometry: { type: 'Point', coordinates: p } }));
      });
      if (active && drawing && cur != null && cursor) {
        const L = lineById(cur);
        if (L && L.pts.length >= 1) feats.push({ type: 'Feature', properties: { kind: 'preview' }, geometry: { type: 'LineString', coordinates: [L.pts[L.pts.length - 1], cursor] } });
      }
      const src = map.getSource('measure'); if (src) src.setData({ type: 'FeatureCollection', features: feats });
      updateHud();
    }

    function updateHud() {
      if (!active) { hud.hidden = true; return; }   // tool closed: lines stay drawn, HUD hidden
      hud.hidden = false;
      const L = cur != null ? lineById(cur) : null;
      if (L) {
        let leg = null, legBrg = null, extra = 0;
        if (drawing && cursor && L.pts.length >= 1) { leg = dist(L.pts[L.pts.length - 1], cursor); legBrg = brg(L.pts[L.pts.length - 1], cursor); extra = leg; }
        else if (L.pts.length >= 2) { leg = dist(L.pts[L.pts.length - 2], L.pts[L.pts.length - 1]); legBrg = brg(L.pts[L.pts.length - 2], L.pts[L.pts.length - 1]); }
        let t = 0; for (let i = 0; i < L.pts.length - 1; i++) t += dist(L.pts[i], L.pts[i + 1]); t += extra;
        elTotal.textContent = fmtNM(t);
        elSub.textContent = leg != null ? 'leg ' + fmtNM(leg) + ' · ' + fmtBrg(legBrg) + 'T' : 'Tap to add · ⏎ or double-tap to finish';
      } else {
        elTotal.textContent = lines.length ? (lines.length + (lines.length === 1 ? ' line' : ' lines')) : '0 NM';
        elSub.textContent = lines.length ? 'Tap a line to edit · tap the chart for a new one' : 'Tap the chart to start';
      }
    }

    // pick a saved line under a click (small pixel tolerance), or null
    function pickLine(pt) {
      try { const b = 6;
        const fs = map.queryRenderedFeatures([[pt.x - b, pt.y - b], [pt.x + b, pt.y + b]], { layers: ['measure-line'] });
        return (fs && fs.length) ? fs[0].properties.lid : null;
      } catch (e) { return null; }
    }

    // ---- interaction ----
    function onClick(e) {
      if (!active) return;
      if (justDragged) { justDragged = false; return; }   // the click that ended a vertex drag
      const p = [e.lngLat.lng, e.lngLat.lat];
      if (!drawing) {                                       // idle: tapping an existing line re-opens it for editing
        const hit = e.point ? pickLine(e.point) : null;
        if (hit != null) { cur = hit; drawing = true; build(); return; }
      }
      if (cur == null || !drawing) { const L = { id: uid(), pts: [p] }; lines.push(L); cur = L.id; drawing = true; }
      else lineById(cur).pts.push(p);
      persist(); build();
    }
    function onMove(e) { if (!active || !drawing || cur == null) return; cursor = [e.lngLat.lng, e.lngLat.lat]; build(); }

    function finish() {                                     // commit the current line (⏎)
      if (cur != null) { const L = lineById(cur); if (L && L.pts.length < 2) lines = lines.filter(x => x.id !== cur); }
      drawing = false; cur = null; cursor = null; persist(); build();
    }
    function onDbl(e) {
      if (!active) return; if (e && e.preventDefault) e.preventDefault();   // don't zoom
      if (cur != null && drawing) { const L = lineById(cur); if (L) L.pts.pop(); }   // drop the dup the dblclick added
      finish();
    }
    function deleteCur() {
      if (cur == null) return;
      lines = lines.filter(x => x.id !== cur); cur = null; drawing = false; cursor = null; persist(); build();
    }
    function onKey(e) {
      if (!active) return;
      if (e.key === 'Escape') { if (drawing) finish(); else setActive(false); }
      else if (e.key === 'Enter') { if (drawing) finish(); }
      else if (e.key === 'Backspace' || e.key === 'Delete') {
        if (drawing && cur != null) { const L = lineById(cur);
          if (L && L.pts.length) { L.pts.pop(); if (!L.pts.length) { lines = lines.filter(x => x.id !== cur); cur = null; drawing = false; } persist(); build(); } }
      }
    }

    // ---- drag a vertex (mouse + touch) ----
    function startDrag(e) {
      if (!active) return;
      const f = e.features && e.features[0]; if (!f) return;
      e.preventDefault();
      cur = f.properties.lid; drawing = false; cursor = null;
      drag = { id: f.properties.lid, idx: f.properties.idx };
      const touch = e.type === 'touchstart';
      const mv = touch ? 'touchmove' : 'mousemove', up = touch ? 'touchend' : 'mouseup';
      map.dragPan.disable();
      const move = (ev) => { if (!drag) return; const L = lineById(drag.id); if (L) { L.pts[drag.idx] = [ev.lngLat.lng, ev.lngLat.lat]; build(); } };
      const end = () => { map.off(mv, move); drag = null; justDragged = true; map.dragPan.enable(); persist(); };
      map.on(mv, move); map.once(up, end);
      build();
    }

    function setActive(on) {
      if (on === active) return;
      active = on;
      map.getCanvas().style.cursor = on ? 'crosshair' : '';
      if (on) map.doubleClickZoom.disable();
      else {                                               // CLOSE: keep every finished line, drop only the in-progress draft state
        map.doubleClickZoom.enable(); drawing = false; cur = null; cursor = null;
        lines = lines.filter(l => l.pts.length >= 2); persist();
      }
      build();
      onChange(active);
    }

    lines = load();
    map.on('click', onClick);
    map.on('mousemove', onMove);
    map.on('dblclick', onDbl);
    document.addEventListener('keydown', onKey);
    if (map.isStyleLoaded && map.isStyleLoaded()) build(); else map.once('load', build);   // draw saved lines at startup

    const api = {
      toggle: () => setActive(!active),
      setActive,
      active: () => active,
      clear: deleteCur,                                    // delete the current/selected line
      clearAll: () => { lines = []; cur = null; drawing = false; cursor = null; persist(); build(); },
      count: () => lines.length
    };
    window.__helmMeasure = api;   // lets the click-popup handlers suppress while measuring
    return api;
  };
})();
