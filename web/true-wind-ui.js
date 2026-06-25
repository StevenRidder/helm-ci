// true-wind-ui.js — WX-13 UI: live True Wind readout (TWS/TWD/TWA), wired through the SHELL
// registration seam. The pure derivation lives in true-wind.js (HelmTrueWind, fully unit-tested);
// this file is just the on-screen surface + the per-frame update. Lane: WX-owned new file.
//
// Registers a HelmShell panel + a ⌘K command from THIS file (no index.html body edits beyond the
// two <script> tags + one applyNav() wiring line — the existing convention for a new nav consumer;
// see the note on a future HelmShell.onNav() hook below).
(function () {
  'use strict';
  if (typeof window === 'undefined') return;

  var els = null, last = null;
  var fmtDir = function (d) { return d == null ? '—' : (Math.round(d) % 360) + '°'; };
  var fmtSpd = function (s) { return s == null ? '—' : s.toFixed(1); };
  var fmtTwa = function (tw) { return tw == null ? '—' : (Math.abs(Math.round(tw.twa)) + '°' + (tw.twaSide === 'P' ? ' P' : ' S')); };

  function paint() {
    if (!els) return;
    if (!last) { els.empty.style.display = ''; els.grid.style.display = 'none'; return; }
    els.empty.style.display = 'none'; els.grid.style.display = '';
    els.tws.textContent = fmtSpd(last.tws);
    els.twd.textContent = fmtDir(last.twd);
    els.twa.textContent = fmtTwa(last);
  }

  function render(body) {
    body.innerHTML =
      '<div class="sub">Derived from apparent wind + boat motion (SOG/COG). Ground-referenced.</div>' +
      '<div id="helm-wx-tw-empty" class="sub" style="opacity:.7">Waiting for wind + motion data…</div>' +
      '<div id="helm-wx-tw-grid" style="display:none">' +
      '  <div class="row"><span class="lbl">True wind speed</span><span><b id="helm-wx-tw-tws">—</b> kn</span></div>' +
      '  <div class="row"><span class="lbl">True wind dir (TWD)</span><b id="helm-wx-tw-twd">—</b></div>' +
      '  <div class="row"><span class="lbl">True wind angle (TWA)</span><b id="helm-wx-tw-twa">—</b></div>' +
      '</div>';
    els = {
      empty: body.querySelector('#helm-wx-tw-empty'), grid: body.querySelector('#helm-wx-tw-grid'),
      tws: body.querySelector('#helm-wx-tw-tws'), twd: body.querySelector('#helm-wx-tw-twd'), twa: body.querySelector('#helm-wx-tw-twa')
    };
    paint();
  }

  // Called every nav frame from index.html applyNav(). Computes true wind and updates the panel
  // + a global (window.__truewind) that laylines (ROUTING-6) and any instrument can read.
  function onNav(s) {
    if (!window.HelmTrueWind || !s) return;
    var tw = window.HelmTrueWind.fromNav(s);   // treats nav `wind` as apparent
    if (tw) { last = tw; window.__truewind = tw; paint(); }
  }

  // Register the panel + ⌘K command from this module (queued until HelmShell.boot()).
  if (window.HelmShell && typeof window.HelmShell.registerPanel === 'function') {
    window.HelmShell.registerPanel({
      id: 'helm-wx-truewind', epic: 'WX', title: 'True wind', icon: 'TW', render: render
    });
    window.HelmShell.registerCommand({
      id: 'helm-wx-truewind-show', epic: 'WX', title: 'Show true wind', subtitle: 'TWS / TWD / TWA',
      keywords: 'wind true twa twd tws apparent', group: 'Weather',
      run: function () { var p = window.HelmShell.panel && window.HelmShell.panel('helm-wx-truewind'); if (p) p.open(); }
    });
  }

  window.HelmTrueWindUI = { onNav: onNav, current: function () { return last; } };
})();
