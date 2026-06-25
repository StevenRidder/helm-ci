// HelmAlarms — safety alarms + banner, computed client-side off the live nav stream.
//
// The OpenCPN backend doesn't emit alarm frames yet, so depth / anchor-watch / MOB /
// off-course / arrival are evaluated here from the nav feed; the same banner also displays
// engine `t:"alarm"` frames (via fromEngine) once the engine sends them.
//
// FAIL-FAST honesty: alarms are only (re)evaluated on FRESH nav data. When the feed goes
// stale/offline (setActive(false)) we HOLD — we neither raise new alarms nor clear active
// ones from data we can't trust. Nothing is fabricated; per-field source tags are respected
// (e.g. depth is NOT alarmed while it reads simulated).
//
//   • Anchor — drop at the current fix, set a swing radius (−/+), live drift readout, and a
//              DEBOUNCED critical alarm so a single GPS jitter fix can't false-trip it.
//   • Depth  — warns when REAL depth < threshold (default 3.0 m), with hysteresis.
//   • Off-course — XTE beyond a limit while a route is actively being navigated.
//   • Arrival — within the arrival radius of the next waypoint.
//   • MOB    — drops a man-overboard mark; critical alarm with live range/bearing.
//   • CPA/TCPA — from the engine's LIVE AIS via collision.js (not duplicated here).
window.HelmAlarms = function (map, opts) {
  opts = opts || {};
  const depthLimit = opts.depthLimit != null ? opts.depthLimit : 3.0;   // metres
  const depthClear = depthLimit + 0.3;                                   // hysteresis
  let anchorRadius = opts.anchorRadius != null ? opts.anchorRadius : 40; // metres (settable)
  const xteLimit = opts.xteLimit != null ? opts.xteLimit : 100;          // metres off track
  const arrivalNM = opts.arrivalNM != null ? opts.arrivalNM : 0.10;      // NM to next wp
  const ONROUTE_NM = 60;        // only judge XTE/arrival when plausibly ON the route (guards a stale demo route)
  const DRAG_DEBOUNCE_MS = 8000; // must stay outside the circle this long before the drag alarm trips

  // ---- alarm state ----
  const active = {};            // kind -> { kind, sev, msg, acked }
  let fresh = true;             // false when feed stale/offline → hold (don't evaluate)
  const num = v => { const m = String(v == null ? '' : v).match(/-?\d+(\.\d+)?/); return m ? parseFloat(m[0]) : NaN; };

  // ---- distance / bearing (metres, degrees) ----
  const R = 6371000, toR = d => d * Math.PI / 180, toD = r => r * 180 / Math.PI;
  function distM(a, b) {
    const dLat = toR(b.lat - a.lat), dLon = toR(b.lon - a.lon);
    const s = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a.lat)) * Math.cos(toR(b.lat)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
  }
  function bearing(a, b) {
    const y = Math.sin(toR(b.lon - a.lon)) * Math.cos(toR(b.lat));
    const x = Math.cos(toR(a.lat)) * Math.sin(toR(b.lat)) - Math.sin(toR(a.lat)) * Math.cos(toR(b.lat)) * Math.cos(toR(b.lon - a.lon));
    return (toD(Math.atan2(y, x)) + 360) % 360;
  }

  // ---- audible alert (WebAudio); browsers need a user gesture to start audio ----
  let ac = null;
  document.addEventListener('pointerdown', () => { try { ac = ac || new (window.AudioContext || window.webkitAudioContext)(); if (ac.state === 'suspended') ac.resume(); } catch (e) {} }, { once: false });
  function beep() {
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      if (ac.state === 'suspended') ac.resume();
      const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
      o.type = 'square'; o.frequency.value = 920;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.22, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
      o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + 0.24);
    } catch (e) { /* audio blocked until a gesture — banner still shows */ }
  }
  setInterval(() => { if (fresh && Object.values(active).some(a => !a.acked && a.sev === 'critical')) beep(); }, 1600);

  // ---- banner ----
  const banner = document.createElement('div');
  banner.id = 'alarm-banner';
  banner.style.cssText = 'position:fixed;top:calc(64px + env(safe-area-inset-top));left:50%;transform:translateX(-50%);' +
    'z-index:9;display:none;min-width:240px;max-width:min(560px,92vw);box-sizing:border-box;padding:10px 12px;border-radius:12px;' +
    'font:600 13px -apple-system,system-ui;color:#fff;align-items:center;gap:10px;box-shadow:0 10px 40px -10px rgba(0,0,0,.7);' +
    '-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);';
  banner.innerHTML = '<span id="alarm-ico" style="font-size:16px">⚠︎</span>' +
    '<span id="alarm-txt" style="flex:1;line-height:1.25"></span>' +
    '<button id="alarm-ack" style="flex:none;border:0;border-radius:7px;padding:6px 11px;font:600 12px system-ui;' +
    'background:rgba(255,255,255,.92);color:#111;cursor:pointer;touch-action:manipulation">ACK</button>';
  document.body.appendChild(banner);
  banner.querySelector('#alarm-ack').addEventListener('click', () => {
    Object.values(active).forEach(a => a.acked = true);   // silence; banner stays while the condition holds
    try { ac = ac || new (window.AudioContext || window.webkitAudioContext)(); ac.resume(); } catch (e) {}
    render();
  });
  // keep out from under collision.js's CPA banner (both are top-centre) — stack below it when shown
  function positionBanner() {
    if (banner.style.display === 'none') return;
    const cpa = document.querySelector('.cpa-alarm');
    const vis = cpa && !cpa.hasAttribute('hidden') && cpa.offsetParent !== null;
    banner.style.top = vis ? (Math.round(cpa.getBoundingClientRect().bottom) + 8) + 'px' : 'calc(64px + env(safe-area-inset-top))';
  }
  function render() {
    const list = Object.values(active);
    if (!list.length) { banner.style.display = 'none'; return; }
    list.sort((a, b) => (a.sev === 'critical' ? -1 : 1) - (b.sev === 'critical' ? -1 : 1));
    const top = list[0], crit = top.sev === 'critical', unacked = list.some(a => !a.acked);
    banner.style.display = 'flex';
    positionBanner();
    banner.style.background = crit ? 'rgba(200,30,40,.94)' : 'rgba(190,120,20,.94)';
    banner.style.animation = (crit && unacked) ? 'srcpulse 1s infinite' : 'none';
    banner.querySelector('#alarm-ico').textContent = top.kind === 'mob' ? '🛟' : (top.kind === 'anchor' ? '⚓' : (top.kind === 'arrival' ? '🏁' : '⚠︎'));
    banner.querySelector('#alarm-txt').textContent = top.msg + (list.length > 1 ? '   (+' + (list.length - 1) + ' more)' : '');
    const ack = banner.querySelector('#alarm-ack'); ack.style.display = unacked ? '' : 'none';
  }
  function fire(kind, sev, msg) {
    const prev = active[kind];
    active[kind] = { kind, sev, msg, acked: prev ? prev.acked : false };   // keep ack across message updates
    render();
  }
  function clear(kind) { if (active[kind]) { delete active[kind]; render(); } }

  // ---- anchor watch (map circle + set-point + live drift readout + radius control) ----
  let anchor = null, dragSince = null;
  function ensureAnchorLayers() {
    if (map.getSource('helm-anchor')) return;
    map.addSource('helm-anchor', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({ id: 'helm-anchor-fill', type: 'fill', source: 'helm-anchor', filter: ['==', '$type', 'Polygon'], paint: { 'fill-color': '#ff6b6b', 'fill-opacity': 0.10 } });
    map.addLayer({ id: 'helm-anchor-line', type: 'line', source: 'helm-anchor', filter: ['==', '$type', 'Polygon'], paint: { 'line-color': '#ff6b6b', 'line-width': 1.5, 'line-dasharray': [2, 2] } });
    map.addLayer({ id: 'helm-anchor-pt', type: 'circle', source: 'helm-anchor', filter: ['==', '$type', 'Point'], paint: { 'circle-radius': 5, 'circle-color': '#ff6b6b', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } });
  }
  function anchorCircle(c, rM) {
    const pts = [], dLat = rM / 111320, dLon = rM / (111320 * Math.cos(toR(c.lat)));
    for (let i = 0; i <= 48; i++) { const a = toR(i * 7.5); pts.push([c.lon + dLon * Math.sin(a), c.lat + dLat * Math.cos(a)]); }
    return { type: 'FeatureCollection', features: [
      { type: 'Feature', geometry: { type: 'Polygon', coordinates: [pts] } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [c.lon, c.lat] } }
    ] };
  }
  function redrawAnchor() { try { ensureAnchorLayers(); map.getSource('helm-anchor').setData(anchorCircle(anchor, anchorRadius)); } catch (e) {} }
  function dropAnchor(pos) {
    if (!pos) return;
    anchor = { lat: pos.lat, lon: pos.lon }; dragSince = null;
    redrawAnchor(); pill.style.display = 'flex'; updatePill(0); paintCtl();
  }
  function weighAnchor() {
    anchor = null; dragSince = null; clear('anchor'); pill.style.display = 'none';
    try { if (map.getSource('helm-anchor')) map.getSource('helm-anchor').setData({ type: 'FeatureCollection', features: [] }); } catch (e) {}
    paintCtl();
  }
  function setRadius(delta) {
    anchorRadius = Math.max(10, Math.min(300, anchorRadius + delta));
    if (anchor) { redrawAnchor(); updatePill(lastPos ? distM(lastPos, anchor) : 0); }
  }

  // anchor status pill (live drift / radius + radius control), bottom-centre, only while anchored
  const pill = document.createElement('div');
  pill.id = 'anchor-pill';
  pill.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:96px;z-index:8;display:none;align-items:center;gap:8px;' +
    'padding:5px 8px;border-radius:11px;font:600 12px -apple-system,system-ui;color:#eef4f9;background:rgba(13,19,27,.82);' +
    '-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border:.5px solid rgba(255,255,255,.14);box-shadow:0 12px 40px -16px rgba(0,0,0,.8)';
  const mkPillBtn = t => { const b = document.createElement('button'); b.type = 'button'; b.textContent = t;
    b.style.cssText = 'width:22px;height:22px;border:0;border-radius:7px;background:rgba(255,255,255,.12);color:#eef4f9;font:700 14px system-ui;cursor:pointer;touch-action:manipulation'; return b; };
  const pillMinus = mkPillBtn('−'), pillTxt = document.createElement('span'), pillPlus = mkPillBtn('+');
  pillTxt.style.cssText = 'min-width:118px;text-align:center;font-variant-numeric:tabular-nums';
  pill.appendChild(document.createTextNode('⚓')); pill.appendChild(pillMinus); pill.appendChild(pillTxt); pill.appendChild(pillPlus);
  document.body.appendChild(pill);
  pillMinus.addEventListener('click', () => setRadius(-5));
  pillPlus.addEventListener('click', () => setRadius(+5));
  function updatePill(d) {
    const ratio = d / anchorRadius;
    const col = !anchor ? '#eef4f9' : (ratio > 1 ? '#ff6b6b' : ratio > 0.85 ? '#ffc06a' : '#46e0a0');
    pillTxt.innerHTML = '<b style="color:' + col + '">' + Math.round(d) + '</b> / ' + anchorRadius + ' m';
  }

  // ---- MOB ----
  let mob = null, mobMarker = null;
  function markMOB(pos) {
    if (!pos) return;
    mob = { lat: pos.lat, lon: pos.lon };
    try {
      const el = document.createElement('div');
      el.style.cssText = 'width:16px;height:16px;border-radius:50%;background:#ff3b30;border:2px solid #fff;box-shadow:0 0 8px rgba(255,59,48,.9)';
      mobMarker = new maplibregl.Marker({ element: el }).setLngLat([mob.lon, mob.lat]).addTo(map);
    } catch (e) {}
    fire('mob', 'critical', 'MAN OVERBOARD');
    paintCtl();
  }
  function cancelMOB() { mob = null; if (mobMarker) { try { mobMarker.remove(); } catch (e) {} mobMarker = null; } clear('mob'); paintCtl(); }

  // ---- controls (maplibre group, bottom-left, away from zoom/ownship) ----
  const group = document.createElement('div');
  group.className = 'maplibregl-ctrl maplibregl-ctrl-group';
  const mkBtn = (label, title, color) => { const b = document.createElement('button'); b.type = 'button'; b.title = title; b.textContent = label; b.style.cssText = 'font:700 12px system-ui;color:' + (color || '#cfe6ff') + ';touch-action:manipulation'; return b; };
  const anchorBtn = mkBtn('⚓', 'Drop / weigh anchor watch');
  const mobBtn = mkBtn('MOB', 'Man overboard', '#ff6b6b');
  group.appendChild(anchorBtn); group.appendChild(mobBtn);
  map.addControl({ onAdd() { return group; }, onRemove() { group.remove(); } }, 'bottom-left');
  let lastPos = null;
  anchorBtn.addEventListener('click', () => { anchor ? weighAnchor() : dropAnchor(lastPos); });
  mobBtn.addEventListener('click', () => { mob ? cancelMOB() : markMOB(lastPos); });
  function paintCtl() {
    anchorBtn.style.color = anchor ? '#ff6b6b' : '#cfe6ff';
    mobBtn.textContent = mob ? '✕MOB' : 'MOB';
  }

  // ---- evaluate alarms from each fresh nav frame ----
  function onNav(s) {
    if (!s || !s.pos) return;
    lastPos = s.pos;
    if (!fresh) return;                  // hold on stale feed — never (re)evaluate from data we can't trust
    positionBanner();                    // track collision.js's CPA banner so the two never overlap
    const src = s.sources || {};

    // depth (only on a REAL depth feed — never alarm on the simulated fill; hysteresis avoids flapping)
    if (typeof s.depth === 'number' && src.depth && src.depth !== 'simulated' && src.depth !== 'sim') {
      if (s.depth < depthLimit) fire('depth', 'warning', 'Shallow water — ' + s.depth.toFixed(1) + ' m (limit ' + depthLimit.toFixed(1) + ' m)');
      else if (s.depth >= depthClear) clear('depth');
    } else { clear('depth'); }

    // anchor watch — live drift readout + DEBOUNCED drag alarm (a single jitter fix can't trip it)
    if (anchor) {
      const d = distM(s.pos, anchor);
      updatePill(d);
      if (d > anchorRadius) {
        if (!dragSince) dragSince = Date.now();
        if (Date.now() - dragSince >= DRAG_DEBOUNCE_MS) {
          const b = Math.round(bearing(anchor, s.pos));
          fire('anchor', 'critical', 'Anchor dragging — ' + Math.round(d) + ' m from set point (limit ' + anchorRadius + ' m), bearing ' + b + '°');
        }
      } else { dragSince = null; clear('anchor'); }
    }

    // off-course (XTE) + arrival — only while plausibly navigating a real route (guards a stale demo route)
    if (s.active && s.active.nextWp) {
      const dtgNM = num(s.active.dtg), xteM = num(s.active.xte);
      if (isFinite(dtgNM) && dtgNM < ONROUTE_NM) {
        if (isFinite(dtgNM) && dtgNM <= arrivalNM) fire('arrival', 'warning', 'Arriving — ' + s.active.nextWp);
        else clear('arrival');
        if (isFinite(xteM) && xteM > xteLimit) fire('xte', 'warning', 'Off course — ' + Math.round(xteM) + ' m cross-track (limit ' + xteLimit + ' m)');
        else clear('xte');
      } else { clear('arrival'); clear('xte'); }
    }

    // MOB range/bearing (alarm stays critical until cancelled)
    if (mob) {
      const d = distM(s.pos, mob), b = Math.round(bearing(s.pos, mob));
      fire('mob', 'critical', 'MAN OVERBOARD — ' + (d < 1852 ? Math.round(d) + ' m' : (d / 1852).toFixed(2) + ' NM') + ', bearing ' + b + '°');
    }
    // CPA/TCPA is owned by collision.js (richer COLREGs guidance + audio); not duplicated here.
  }

  return {
    onNav,
    setActive(f) { fresh = !!f; },                       // false → hold (stale/offline)
    fromEngine(a) { if (a && a.kind) fire(a.kind, a.sev || 'warning', a.msg || a.kind); },  // engine t:"alarm" frames
    dropAnchor: p => dropAnchor(p || lastPos), markMOB: () => markMOB(lastPos), setRadius,
    _state: () => ({ active: Object.keys(active), anchor: !!anchor, radius: anchorRadius, mob: !!mob })   // for tests
  };
};
