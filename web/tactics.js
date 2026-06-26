// tactics.js — opposite-tack assist. Given the live TRUE wind (WX-13) it shows the maneuver to switch
// to the other tack: TACK (head up through the wind) or GYBE (bear away through downwind), the turn
// (how much + which way), the heading you'll settle on, and a line on the chart from the boat along
// that heading (green = starboard tack, red = port). The opposite tack is the MIRROR of your heading
// across the wind, NOT a fixed rotation — at a broad reach you GYBE, and a naive turn toward the wind
// would put you head-to-wind / in irons.
//
// INSTRUMENT-ONLY (per the boat's setup): nothing is shown without REAL wind — no forecast or manual
// fallback. It lights up the moment a masthead instrument is on the network (WX-13 already ingests
// NMEA MWV / SignalK / N2K apparent wind and derives true).
(function (root) {
  'use strict';
  var R = 3440.065, D2R = Math.PI / 180, R2D = 180 / Math.PI;
  function norm360(d) { d %= 360; return d < 0 ? d + 360 : d; }
  function num(x) { return typeof x === 'number' && isFinite(x); }

  // PURE (unit-tested): from TRUE wind {twd, twa(signed −180..180), twaSide:'S'|'P'} → the other-tack
  // maneuver. twa = twd − heading (WX-13's convention), so the opposite-tack heading = twd + twa
  // (= reflect the heading across the wind). null if no wind; {irons:true} if ~head to wind.
  function oppositeTack(tw) {
    if (!tw || !num(tw.twd) || !num(tw.twa)) return null;
    var off = Math.abs(tw.twa);                                  // angle off the wind, 0..180
    if (off < 8) return { irons: true };                         // basically head to wind — no clean other tack
    var gybe = off > 90.5;                                        // past a beam reach ⇒ gybe; else tack
    var windSide = tw.twaSide === 'S' ? 'starboard' : 'port';     // side the wind is on = the tack you're on
    return {
      irons: false,
      maneuver: gybe ? 'gybe' : 'tack',
      oppHeading: Math.round(norm360(tw.twd + tw.twa)),           // the heading you settle on
      turn: Math.round(gybe ? 2 * (180 - off) : 2 * off),         // tack = 2×off; gybe = 2×(180−off)
      turnSide: gybe ? (windSide === 'starboard' ? 'port' : 'starboard') : windSide,   // tack→toward wind, gybe→away
      newTack: windSide === 'starboard' ? 'port' : 'starboard',
      off: Math.round(off)
    };
  }
  // a point `nm` NM from [lng,lat] along compass bearing `brg` (great-circle)
  function dest(lng, lat, brg, nm) {
    var d = nm / R, b = brg * D2R, la = lat * D2R, lo = lng * D2R;
    var la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(b));
    var lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
    return [lo2 * R2D, la2 * R2D];
  }

  var api = { oppositeTack: oppositeTack };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;   // node / tests
  root.HelmTactics = api;
  if (typeof document === 'undefined') return;                                 // node: stop here

  // ---- browser module ----
  var enabled = false, chip = null, lastNav = null;
  var GREEN = '#46e0a0', RED = '#ff6b6b', EMPTY = { type: 'FeatureCollection', features: [] };
  var lastResult = { enabled: false, hasWind: false, maneuver: null, lineDrawn: false };
  api._last = function () { return lastResult; };

  function store(k, d) { try { return window.HelmStore ? HelmStore.get(k, d) : d; } catch (e) { return d; } }
  function save(k, v) { try { if (window.HelmStore) HelmStore.set(k, v); } catch (e) {} }
  // The live MapLibre map — fetched lazily (window.map is assigned after our init runs, so never cache it).
  function theMap() { var m = window.map; return (m && typeof m.getSource === 'function') ? m : null; }

  function ensureLayer() {
    var m = theMap(); if (!m || !m.getStyle || !m.getStyle()) return null;
    if (!m.getSource('tack')) {
      m.addSource('tack', { type: 'geojson', data: EMPTY });
      m.addLayer({
        id: 'tack-line', type: 'line', source: 'tack', filter: ['==', ['get', 'kind'], 'line'],
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': ['get', 'col'], 'line-width': 2.5, 'line-dasharray': [2, 1.5], 'line-opacity': 0.9 }
      });
      m.addLayer({
        id: 'tack-end', type: 'symbol', source: 'tack', filter: ['==', ['get', 'kind'], 'end'],
        layout: { 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Regular'], 'text-size': 11, 'text-offset': [0, -0.8], 'text-allow-overlap': true },
        paint: { 'text-color': ['get', 'col'], 'text-halo-color': 'rgba(5,8,12,0.9)', 'text-halo-width': 1.4 }
      });
    }
    return m;
  }
  function clearLine() { var m = ensureLayer(); var s = m && m.getSource('tack'); if (s) s.setData(EMPTY); }
  function drawLine(pos, man) {
    var m = ensureLayer(); var s = m && m.getSource('tack'); if (!s) return false;
    var col = man.newTack === 'starboard' ? GREEN : RED;
    var end = dest(pos.lon, pos.lat, man.oppHeading, 3);          // 3 NM stub from the boat
    s.setData({ type: 'FeatureCollection', features: [
      { type: 'Feature', properties: { kind: 'line', col: col }, geometry: { type: 'LineString', coordinates: [[pos.lon, pos.lat], end] } },
      { type: 'Feature', properties: { kind: 'end', col: col, label: man.oppHeading + '°' }, geometry: { type: 'Point', coordinates: end } }
    ] });
    return true;
  }

  function setTxt(t) { var el = chip && chip.querySelector('.tk-txt'); if (el) el.textContent = t; }

  function render(s) {
    lastNav = s;
    if (!chip) return;
    if (!enabled) { setTxt('Tack assist'); clearLine(); lastResult = { enabled: false, hasWind: false, maneuver: null, lineDrawn: false }; return; }
    var noWind = !s || !s.sources || s.sources.wind === 'missing';
    var tw = noWind ? null : (window.HelmTrueWind && HelmTrueWind.fromNav(s));
    var man = tw ? oppositeTack(tw) : null;
    if (!man || man.irons || noWind) {
      setTxt(noWind ? 'Tack — no wind' : (man && man.irons ? 'Tack — head to wind' : 'Tack — …'));
      clearLine(); lastResult = { enabled: true, hasWind: !noWind, maneuver: null, lineDrawn: false }; return;
    }
    var arrow = man.turnSide === 'starboard' ? '↻' : '↺';
    setTxt(man.maneuver.toUpperCase() + ' ' + man.oppHeading + '°  ·  ' +
      (man.maneuver === 'gybe' ? 'bear away ' : 'head up ') + man.turn + '° ' + arrow + '  ·  ' + man.newTack + ' tack');
    var drawn = (s.pos && num(s.pos.lat) && num(s.pos.lon)) ? drawLine(s.pos, man) : (clearLine(), false);
    lastResult = { enabled: true, hasWind: true, maneuver: man.maneuver, oppHeading: man.oppHeading, turn: man.turn, turnSide: man.turnSide, newTack: man.newTack, lineDrawn: drawn };
  }

  function setEnabled(on) {
    enabled = on; save('ui.tackAssist', on);
    if (chip) chip.classList.toggle('on', on);
    if (!on) clearLine();
    render(lastNav);
  }

  function buildUI() {
    var st = document.createElement('style');
    st.textContent =
      '#tack-chip{position:absolute;left:50%;transform:translateX(-50%);bottom:96px;z-index:7;display:flex;' +
      'align-items:center;gap:8px;padding:6px 13px;border-radius:18px;font-size:12.5px;color:var(--cdim);' +
      'cursor:pointer;user-select:none;transition:color .15s} #tack-chip:hover,#tack-chip.on{color:var(--ctext)}' +
      ' #tack-chip .tk-ico{font-size:13px;color:var(--accent)}';
    document.head.appendChild(st);
    chip = document.createElement('div');
    chip.id = 'tack-chip'; chip.className = 'tack-chip glass';
    chip.title = 'Opposite-tack assist — needs a wind instrument';
    chip.innerHTML = '<span class="tk-ico">⊲</span><span class="tk-txt">Tack assist</span>';
    chip.addEventListener('click', function () { setEnabled(!enabled); });
    document.body.appendChild(chip);
    enabled = !!store('ui.tackAssist', false);
    chip.classList.toggle('on', enabled);
  }

  function init() {
    if (!window.map) { setTimeout(init, 250); return; }
    buildUI();
    var m = window.map;
    if (m.isStyleLoaded && m.isStyleLoaded()) ensureLayer(); else if (m.once) m.once('load', ensureLayer);
    if (window.HelmShell && HelmShell.onNav) HelmShell.onNav(render);
    render(null);
  }
  if (document.readyState !== 'loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(typeof self !== 'undefined' ? self : (typeof globalThis !== 'undefined' ? globalThis : this));
