// ENC-4 — prefer /user-data/ depth GeoJSON from extract_depth.sh over bundled web/data demo.
(function () {
  'use strict';

  var DEPTH_FILES = { depare: 'depare.geojson', depcnt: 'depcnt.geojson', soundg: 'soundg.geojson' };
  var USER_PREFIX = 'user-data/';
  var DEMO_PREFIX = 'data/';
  var lastState = { mode: 'demo', cell: null, layers: {} };

  function resourceExists(fetchFn, url) {
    return fetchFn(url).then(function (r) { return !!(r && r.ok); }).catch(function () { return false; });
  }

  function defaultFetch(url) {
    return fetch(url, { method: 'HEAD', cache: 'no-store' });
  }

  async function preferUserDepthData(style, opts) {
    opts = opts || {};
    var fetchFn = opts.fetch || defaultFetch;
    var layers = {};
    var anyUser = false;
    if (!style || !style.sources) {
      lastState = { mode: 'demo', cell: null, layers: layers };
      return lastState;
    }
    await Promise.all(Object.keys(DEPTH_FILES).map(async function (id) {
      var src = style.sources[id];
      if (!src || src.type !== 'geojson') return;
      var userUrl = USER_PREFIX + DEPTH_FILES[id];
      var demoUrl = DEMO_PREFIX + DEPTH_FILES[id];
      if (await resourceExists(fetchFn, userUrl)) {
        src.data = userUrl;
        layers[id] = 'user';
        anyUser = true;
      } else {
        src.data = demoUrl;
        layers[id] = 'demo';
      }
    }));
    var cell = null;
    if (anyUser && await resourceExists(fetchFn, USER_PREFIX + 'depth-provenance.json')) {
      try {
        var provFetch = opts.get || function (url) { return fetch(url, { cache: 'no-store' }); };
        var resp = await provFetch(USER_PREFIX + 'depth-provenance.json');
        if (resp && resp.ok) {
          var prov = await resp.json();
          cell = prov && prov.cell ? prov.cell : null;
        }
      } catch (e) {}
    }
    lastState = { mode: anyUser ? 'enc' : 'demo', cell: cell, layers: layers };
    return lastState;
  }

  function status() {
    return {
      schema: 'helm.enc_depth_sources.v1',
      mode: lastState.mode,
      cell: lastState.cell,
      layers: Object.assign({}, lastState.layers),
      user_prefix: USER_PREFIX,
      demo_prefix: DEMO_PREFIX
    };
  }

  function summary() {
    var st = status();
    if (st.mode === 'enc') {
      return { mode: 'enc', detail: 'ENC depth' + (st.cell ? ' · ' + st.cell : ''), css: 'ok' };
    }
    return { mode: 'demo', detail: 'Demo depth (synthetic)', css: 'warn' };
  }

  function applyBadge(el) {
    if (!el) return;
    var s = summary();
    el.textContent = s.detail;
    el.className = 'enc-depth-source ' + s.css;
    el.title = s.mode === 'enc'
      ? 'Depth GeoJSON from your ENC cell via extract_depth.sh'
      : 'Bundled synthetic demo depth — run scripts/extract-user-depth.sh for real ENC data';
  }

  window.HelmEncDepthSources = {
    DEPTH_FILES: DEPTH_FILES,
    preferUserDepthData: preferUserDepthData,
    status: status,
    summary: summary,
    applyBadge: applyBadge
  };
})();
