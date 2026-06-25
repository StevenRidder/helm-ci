// track.js — ownship breadcrumb trail. The ENGINE records the trail (helm_server.cpp owns it,
// single source of truth, so a reconnect or a second client gets the whole line); this module
// just DISPLAYS it — the full trail from snapshot frames (s.track), appended points from deltas
// (s.trackAdd) — and offers Record / Clear over the command-plane (track.arm / track.clear).
// This is the honest, working replacement for the old dead "Share my track" checkbox.
(function () {
  const SRC = 'helm-track';
  let map = null, client = null, coords = [], armed = true, recBtn = null, recLbl = null;

  function lineGeo() {
    return { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: coords.length >= 2 ? coords : [] } };
  }
  function ensureLayer() {
    if (!map || map.getSource(SRC)) return;
    map.addSource(SRC, { type: 'geojson', data: lineGeo() });
    map.addLayer({
      id: 'helm-track-line', type: 'line', source: SRC,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#5bc0ff', 'line-width': 2, 'line-opacity': 0.85 },
    });
  }
  function redraw() { try { ensureLayer(); const s = map && map.getSource(SRC); if (s) s.setData(lineGeo()); } catch (e) {} }

  function setArmedUI(on) {
    armed = !!on;
    if (recBtn) recBtn.classList.toggle('rec', armed);
    if (recLbl) recLbl.textContent = armed ? '● REC' : '○ REC';   // ● / ○
  }

  function onState(s) {
    if (!s) return;
    if (Array.isArray(s.track)) { coords = s.track.map(p => [p[1], p[0]]); redraw(); }             // snapshot: full trail ([lat,lon]->[lon,lat])
    else if (Array.isArray(s.trackAdd) && s.trackAdd.length) { for (const p of s.trackAdd) coords.push([p[1], p[0]]); redraw(); }  // delta: append
    if (typeof s.trackArmed === 'boolean') setArmedUI(s.trackArmed);
  }

  function buildControl() {
    const wrap = document.createElement('div'); wrap.className = 'helm-track-ctl glass';
    recBtn = document.createElement('button'); recBtn.type = 'button'; recBtn.className = 'helm-track-rec';
    recBtn.title = 'Record ownship track (breadcrumb trail)';
    recLbl = document.createElement('span'); recLbl.textContent = '● REC'; recBtn.appendChild(recLbl);
    recBtn.addEventListener('click', () => { const next = !armed; if (client) client.send({ t: 'track.arm', on: next }); setArmedUI(next); });
    const clr = document.createElement('button'); clr.type = 'button'; clr.className = 'helm-track-clear'; clr.textContent = 'Clear';
    clr.title = 'Clear the recorded track';
    clr.addEventListener('click', () => { if (window.confirm('Clear the recorded track?')) { if (client) client.send({ t: 'track.clear' }); coords = []; redraw(); } });
    wrap.appendChild(recBtn); wrap.appendChild(clr);
    (document.getElementById('map') || document.body).appendChild(wrap);
  }

  function init(opts) {
    map = opts.map; client = opts.client;
    if (!map) return;
    buildControl();
    if (map.isStyleLoaded && map.isStyleLoaded()) ensureLayer(); else map.on('load', ensureLayer);
  }
  window.HelmTrack = { init, onState };
})();
