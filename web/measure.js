// HelmMeasure — a range/bearing ruler for the chart.
//
// Design: Mapbox-idiomatic mechanics (one GeoJSON source backing a line + vertex layers,
// click-to-add, live rubber-band to the cursor) + Apple-idiomatic presentation (a calm glass
// HUD showing one big primary number, live-updating). Because this is a chartplotter, each
// committed leg is labelled with BOTH range and bearing (°T) — the OpenCPN / MFD convention —
// and the HUD shows cumulative distance plus the live leg.
//
// Units: nautical miles + degrees true (great-circle), matching the app's ScaleControl and
// the nav core. Math mirrors web/nav-source.js so the ruler agrees with the engine's BRG/DTW.
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
    const COL = opts.color || '#5bc0ff';

    let active = false;     // measure mode on/off
    let drawing = false;    // currently extending a line
    let pts = [];           // committed vertices [[lng,lat], …]
    let cursor = null;      // live cursor for the rubber-band

    // ---- HUD (Apple-style glass card, one big number) ----
    const hud = document.createElement('div');
    hud.className = 'measure-hud glass';
    hud.hidden = true;
    hud.innerHTML =
      '<div><div class="mt" id="measure-total">0 NM</div>' +
      '<div class="ms" id="measure-sub">Tap the chart to start</div></div>' +
      '<div class="mx" id="measure-clear" title="Clear">✕</div>';
    document.body.appendChild(hud);
    const elTotal = hud.querySelector('#measure-total');
    const elSub = hud.querySelector('#measure-sub');
    hud.querySelector('#measure-clear').addEventListener('click', clear);

    // ---- map source + layers (added on top, once the style is ready) ----
    function ensureLayers() {
      if (map.getSource('measure')) return;
      map.addSource('measure', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({
        id: 'measure-line', type: 'line', source: 'measure',
        filter: ['==', ['get', 'kind'], 'line'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': COL, 'line-width': 2.5 }
      });
      map.addLayer({
        id: 'measure-preview', type: 'line', source: 'measure',
        filter: ['==', ['get', 'kind'], 'preview'],
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': COL, 'line-width': 2, 'line-opacity': 0.8, 'line-dasharray': [1.5, 1.5] }
      });
      map.addLayer({
        id: 'measure-points', type: 'circle', source: 'measure',
        filter: ['==', ['get', 'kind'], 'vertex'],
        paint: {
          'circle-radius': 4.5, 'circle-color': COL,
          'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5
        }
      });
      map.addLayer({
        id: 'measure-labels', type: 'symbol', source: 'measure',
        filter: ['==', ['get', 'kind'], 'label'],
        layout: {
          'text-field': ['get', 'label'], 'text-font': ['Noto Sans Regular'],
          'text-size': 11, 'text-offset': [0, -0.9], 'text-allow-overlap': true
        },
        paint: { 'text-color': '#eef4f9', 'text-halo-color': 'rgba(5,8,12,0.9)', 'text-halo-width': 1.4 }
      });
    }

    function totalNM(extra) {
      let t = 0;
      for (let i = 0; i < pts.length - 1; i++) t += dist(pts[i], pts[i + 1]);
      return t + (extra || 0);
    }

    function build() {
      ensureLayers();
      const feats = [];
      if (pts.length >= 2)
        feats.push({ type: 'Feature', properties: { kind: 'line' }, geometry: { type: 'LineString', coordinates: pts } });
      for (let i = 0; i < pts.length - 1; i++) {
        feats.push({
          type: 'Feature',
          properties: { kind: 'label', label: fmtNM(dist(pts[i], pts[i + 1])) + ' · ' + fmtBrg(brg(pts[i], pts[i + 1])) },
          geometry: { type: 'Point', coordinates: mid(pts[i], pts[i + 1]) }
        });
      }
      pts.forEach(p => feats.push({ type: 'Feature', properties: { kind: 'vertex' }, geometry: { type: 'Point', coordinates: p } }));
      if (active && drawing && cursor && pts.length >= 1)
        feats.push({ type: 'Feature', properties: { kind: 'preview' }, geometry: { type: 'LineString', coordinates: [pts[pts.length - 1], cursor] } });
      const src = map.getSource('measure');
      if (src) src.setData({ type: 'FeatureCollection', features: feats });
      updateHud();
    }

    function updateHud() {
      if (!active && pts.length === 0) { hud.hidden = true; return; }
      hud.hidden = false;
      let leg = null, legBrg = null, extra = 0;
      if (active && drawing && cursor && pts.length >= 1) {           // live leg to cursor
        leg = dist(pts[pts.length - 1], cursor); legBrg = brg(pts[pts.length - 1], cursor); extra = leg;
      } else if (pts.length >= 2) {                                   // last committed leg
        leg = dist(pts[pts.length - 2], pts[pts.length - 1]); legBrg = brg(pts[pts.length - 2], pts[pts.length - 1]);
      }
      elTotal.textContent = fmtNM(totalNM(extra));
      elSub.textContent = leg != null
        ? 'leg ' + fmtNM(leg) + ' · ' + fmtBrg(legBrg) + 'T'
        : (active ? 'Tap the chart to start' : '');
    }

    // ---- interaction ----
    function onClick(e) {
      if (!active) return;
      const p = [e.lngLat.lng, e.lngLat.lat];
      if (!drawing) { pts = [p]; drawing = true; }   // first click starts a fresh measurement
      else pts.push(p);
      build();
    }
    function onMove(e) {
      if (!active || !drawing) return;
      cursor = [e.lngLat.lng, e.lngLat.lat];
      build();
    }
    function onDbl(e) {
      if (!active) return;
      if (e && e.preventDefault) e.preventDefault();   // don't zoom
      if (drawing) {
        pts.pop();                                     // drop the duplicate point the dblclick added
        if (pts.length < 2) pts = [];
        drawing = false; cursor = null; build();
      }
    }
    function onKey(e) {
      if (!active) return;
      if (e.key === 'Escape') { if (drawing) { onDbl(); } else { setActive(false); } }
      else if (e.key === 'Backspace' || e.key === 'Delete') {
        if (drawing && pts.length) { pts.pop(); if (!pts.length) drawing = false; build(); }
      }
    }

    function setActive(on) {
      if (on === active) return;
      active = on;
      map.getCanvas().style.cursor = on ? 'crosshair' : '';
      if (on) { map.doubleClickZoom.disable(); }
      else { map.doubleClickZoom.enable(); drawing = false; cursor = null; pts = []; }  // exit clears (Apple-like)
      build();
      onChange(active);
    }
    function clear() { pts = []; drawing = false; cursor = null; build(); }

    map.on('click', onClick);
    map.on('mousemove', onMove);
    map.on('dblclick', onDbl);
    document.addEventListener('keydown', onKey);

    const api = {
      toggle: () => setActive(!active),
      setActive,
      active: () => active,
      clear
    };
    window.__helmMeasure = api;   // lets the click-popup handlers suppress while measuring
    return api;
  };
})();
