// CAT-2 — Catalog-honesty advisory banners: stale satellite, ENC coverage gap, missing overlay.
//
// The North Star fused map is honest about its data (docs/NORTH-STAR.md): "stale data labeled stale,
// missing coverage shown as missing." CAT-1 taught helm-packd to compute real freshness/coverage on
// /catalog (per-pack staleness{status,age_days}) and /layer-manifest (top-level enc{expected,present,
// missing}; per-overlay load status). This module reads those two EXISTING client owners --
// HelmOfflinePacks (/catalog) and HelmLayerManifest (/layer-manifest) -- and surfaces three
// dismissible advisory banners WITHOUT re-fetching or re-deriving anything the backend already said:
//
//   1. stale sat       -- a satellite basemap pack past its own declared freshness window
//   2. enc gap         -- expected ENC depth layers (depare/depcnt/soundg) not all present
//   3. missing overlay -- a user overlay the manifest declared but that could not load
//
// Fail-fix-early: each banner NAMES the real signal (which pack, which layers, why) and never fakes
// green. A banner shows only from real backend data; when everything is healthy, nothing shows. An
// absent/404 manifest or absent catalog is NOT a fabricated gap -- silence, not a red herring.
//
// The pure decision core computeBanners({packs, manifestStatus}) has no DOM/window dependency and is
// unit-tested head-less (web/test/catalog-banners.test.cjs), mirroring web/layer-manifest.js.
(function () {
  'use strict';

  var CONTAINER_ID = 'helm-catalog-banners';
  var REFRESH_MS = 2000;

  function win() { return (typeof window !== 'undefined') ? window : null; }
  function doc() { return (typeof document !== 'undefined') ? document : null; }

  // ---- pure helpers ----------------------------------------------------------------------------

  function lc(s) { return String(s == null ? '' : s).toLowerCase(); }

  // A catalog pack is a satellite basemap when helm-packd classified kind==='satellite'
  // (kind_for: id/title/format matched sat|sentinel|imagery|photo). id/title are a defensive fallback
  // in case a sidecar overrode kind to something non-canonical.
  function isSatellitePack(pack) {
    if (!pack || typeof pack !== 'object') return false;
    if (lc(pack.kind) === 'satellite') return true;
    return /(^|[^a-z])(sat|satellite|sentinel|imagery|photo)([^a-z]|$)/.test(lc(pack.id) + ' ' + lc(pack.title));
  }

  function packFreshness(pack) { return (pack && (pack.staleness || pack.freshness)) || {}; }

  function ageDaysText(fresh) {
    if (!fresh || fresh.age_days == null) return '';
    var d = Number(fresh.age_days);
    if (!isFinite(d) || d < 0) return '';
    if (d < 1) return 'less than a day old';
    d = Math.round(d);
    return d === 1 ? '1 day old' : (d + ' days old');
  }

  // stale sat: the stalest satellite pack whose computed staleness.status === 'stale'.
  function staleSatBanner(packs) {
    if (!Array.isArray(packs)) return null;
    var sats = packs.filter(isSatellitePack).filter(function (p) { return lc(packFreshness(p).status) === 'stale'; });
    if (!sats.length) return null;
    // Prefer the pack we can quantify as oldest; fall back to the first satellite pack.
    sats.sort(function (a, b) { return (Number(packFreshness(b).age_days) || 0) - (Number(packFreshness(a).age_days) || 0); });
    var pack = sats[0];
    var fresh = packFreshness(pack);
    var name = pack.title || pack.id || 'Satellite pack';
    var age = ageDaysText(fresh);
    var msg = name + (age ? ' is ' + age + ' — past its freshness window.' : ' is past its declared freshness window.');
    msg += ' Refresh the satellite imagery pack when you next have a connection.';
    return { id: 'stale-sat', level: 'warn', title: 'Satellite imagery is stale', message: msg };
  }

  // enc gap: expected ENC layers not all present. manifest.enc = {expected, present, missing} (CAT-1).
  // No enc summary (absent/404 manifest) -> we don't know the expected set -> NO gap banner (honest).
  function encGapBanner(manifestStatus) {
    var summary = manifestStatus && manifestStatus.summary;
    var enc = summary && summary.enc;
    if (!enc || !Array.isArray(enc.missing) || !enc.missing.length) return null;
    var missing = enc.missing.map(String);
    var expected = Array.isArray(enc.expected) ? enc.expected.length : missing.length;
    var msg = 'Missing ENC layer' + (missing.length === 1 ? '' : 's') + ': ' + missing.join(', ') +
      ' (' + missing.length + ' of ' + expected + ' expected). Depth/soundings coverage is incomplete here.';
    return { id: 'enc-gap', level: 'warn', title: 'ENC depth data incomplete', message: msg };
  }

  // missing overlay: a declared user overlay that could not load. Genuine not-loaded states from the
  // LAYER-2 loader summary: rejected[] (refused non-public url) + errors[] entries that name an id
  // (addSource/addLayer failed). A whole-manifest load/parse failure (lastError, or an errors[] marker
  // with no id) is surfaced separately. Intentional skipped[] entries (deferred-to-another-module,
  // base-owned, unsupported-format) are NOT "missing" and never banner.
  function missingOverlayBanner(manifestStatus) {
    if (!manifestStatus) return null;
    var summary = manifestStatus.summary || {};
    var rejected = Array.isArray(summary.rejected) ? summary.rejected : [];
    var errors = Array.isArray(summary.errors) ? summary.errors : [];
    var failedEntries = rejected.concat(errors).filter(function (r) { return r && r.id != null && r.id !== ''; });
    var loadError = manifestStatus.lastError ||
      errors.filter(function (r) { return r && (r.id == null || r.id === ''); })[0] || null;

    if (!failedEntries.length && !loadError) return null;

    if (failedEntries.length) {
      var ids = failedEntries.map(function (r) { return String(r.id); });
      var uniq = ids.filter(function (v, i) { return ids.indexOf(v) === i; });
      var msg = uniq.length === 1
        ? 'Overlay "' + uniq[0] + '" is declared in the layer manifest but could not load.'
        : uniq.length + ' user overlays are declared but could not load: ' + uniq.join(', ') + '.';
      return { id: 'missing-overlay', level: 'warn', title: 'Overlay unavailable', message: msg };
    }
    // Only a whole-manifest failure (no per-entry ids). Name it; overlays are non-fatal to charts.
    var detail = (loadError && (loadError.message || loadError.reason)) || 'unknown error';
    return { id: 'missing-overlay', level: 'warn', title: 'User overlays unavailable',
      message: 'Could not load user overlays from /layer-manifest (' + detail + '). Chart rendering is unaffected.' };
  }

  // Pure: given the two client-owner snapshots, the ordered banner list to show. Empty == healthy.
  function computeBanners(input) {
    input = input || {};
    var out = [];
    var sat = staleSatBanner(input.packs); if (sat) out.push(sat);
    var enc = encGapBanner(input.manifestStatus); if (enc) out.push(enc);
    var ov = missingOverlayBanner(input.manifestStatus); if (ov) out.push(ov);
    return out;
  }

  // Stable signature: we touch the DOM only when the visible set/wording changes, and a dismissed
  // banner re-appears when its underlying condition changes (different missing set / different pack).
  function signature(banners) {
    return banners.map(function (b) { return b.id + '::' + b.message; }).join('|');
  }

  // ---- data snapshot (reads existing client owners; never fetches) ------------------------------

  function readPacks() {
    var w = win();
    try {
      var st = w && w.HelmOfflinePacks && w.HelmOfflinePacks.state;
      if (st && Array.isArray(st.packs)) return st.packs;
    } catch (e) {}
    return [];
  }
  function readManifestStatus() {
    var w = win();
    try {
      if (w && w.HelmLayerManifest && typeof w.HelmLayerManifest.status === 'function') return w.HelmLayerManifest.status();
    } catch (e) {}
    return null;
  }
  function snapshot() { return { packs: readPacks(), manifestStatus: readManifestStatus() }; }

  // ---- DOM (guarded; inert head-less) ----------------------------------------------------------

  var dismissed = Object.create(null);   // key = banner.id + '::' + message -> true
  var lastSig = null;

  function bannerKey(b) { return b.id + '::' + b.message; }

  function ensureContainer() {
    var d = doc(); if (!d || !d.body) return null;
    var el = d.getElementById(CONTAINER_ID);
    if (!el) {
      el = d.createElement('div');
      el.id = CONTAINER_ID;
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      d.body.appendChild(el);
    }
    return el;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function render() {
    var el = ensureContainer(); if (!el) return;
    var banners = computeBanners(snapshot()).filter(function (b) { return !dismissed[bannerKey(b)]; });
    var sig = signature(banners);
    if (sig === lastSig) return;   // nothing visibly changed -> no DOM churn
    lastSig = sig;
    if (!banners.length) { el.innerHTML = ''; return; }
    el.innerHTML = banners.map(function (b) {
      return '<div class="helm-catban helm-catban-' + esc(b.level || 'warn') + '" data-catban="' + esc(b.id) + '" role="alert">' +
        '<div class="helm-catban-ic" aria-hidden="true">⚠</div>' +
        '<div class="helm-catban-body"><div class="helm-catban-ttl">' + esc(b.title) + '</div>' +
        '<div class="helm-catban-msg">' + esc(b.message) + '</div></div>' +
        '<div class="helm-catban-x" data-catban-dismiss="' + esc(bannerKey(b)) + '" title="Dismiss" role="button" tabindex="0" aria-label="Dismiss ' + esc(b.title) + '">×</div>' +
        '</div>';
    }).join('');
    var xs = el.querySelectorAll('[data-catban-dismiss]');
    for (var i = 0; i < xs.length; i++) {
      xs[i].addEventListener('click', function (ev) {
        var k = ev.currentTarget.getAttribute('data-catban-dismiss');
        if (k) { dismissed[k] = true; lastSig = null; render(); }
      });
    }
  }

  function refresh() { try { render(); } catch (e) {} }

  var timer = null;
  function start() {
    var w = win(); if (!w || typeof w.setInterval !== 'function') return;
    if (timer) return;
    refresh();
    timer = w.setInterval(refresh, REFRESH_MS);
  }

  function registerCommand() {
    var w = win();
    if (!w || !w.HelmShell || typeof w.HelmShell.registerCommand !== 'function') return;
    try {
      w.HelmShell.registerCommand({
        id: 'helm-catalog-honesty-refresh', epic: 'CAT',
        title: 'Refresh data-honesty banners', subtitle: 'Re-check stale sat / ENC gap / missing overlay',
        keywords: ['stale', 'enc', 'overlay', 'catalog', 'honesty', 'freshness'], group: 'Layers',
        run: function () { lastSig = null; refresh(); }
      });
    } catch (e) {}
  }

  var api = {
    computeBanners: computeBanners,
    isSatellitePack: isSatellitePack,
    signature: signature,
    snapshot: snapshot,
    refresh: refresh,
    CONTAINER_ID: CONTAINER_ID
  };
  if (win()) win().HelmCatalogBanners = api;

  // Self-wire once DOM + client owners exist. Guarded on setTimeout so unit tests (vm sandbox with no
  // timers, no document) stay inert -- mirrors web/layer-manifest.js's deferral.
  if (win() && doc() && typeof setTimeout === 'function') {
    (function boot(attempt) {
      if (doc().body) { registerCommand(); start(); return; }
      if ((attempt || 0) < 150) setTimeout(function () { boot((attempt || 0) + 1); }, 100);
    })(0);
  }
})();
