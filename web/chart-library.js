// INTAKE-5: Chart Library panel — the cockpit's OpenCPN-baselined chart manager.
// Backed by the INTAKE-2/3 chart-intake seam on helm-packd (board decision #13):
//   GET  /chart-index          helm.chart_intake.index.v1 (roots + per-chart inventory)
//   GET  /chart-roots          registered roots (labels only, never paths)
//   POST /chart-roots          register a folder the customer already has
//   POST /chart-roots/remove   unregister a root (files always stay put)
//   POST /rescan               "I just dropped files in" (OpenCPN Rebuild Chart DB)
// Freshness joins CAT-1 /catalog staleness client-side; overlays that the layer
// manifest does not serve yet are labeled as such — no fabricated green states.
(function () {
  'use strict';

  var EPIC = 'INTAKE';
  var PANEL_ID = 'helm-chart-library';
  var GROUP_KEY = 'chartlib.group';
  var DEFAULT_PORT = '8091';
  var state = {
    body: null, map: null,
    index: null, roots: null, rootsSource: '', catalog: null,
    indexError: '', rootsError: '', catalogError: '',
    loading: false, busy: false, notice: '', group: 'all'
  };
  var log = (window.HelmLog && HelmLog.scope) ? HelmLog.scope('chart-library') : console;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ---- endpoint resolution (same convention as offline-packs.js) ------------------------------
  function basemapPort() {
    try {
      var q = new URLSearchParams(location.search);
      return q.get('basemapPort') || window.HELM_BASEMAP_PORT || DEFAULT_PORT;
    } catch (e) {
      return window.HELM_BASEMAP_PORT || DEFAULT_PORT;
    }
  }

  function endpointHost() {
    try {
      if (window.HelmEndpoint && HelmEndpoint.host) return HelmEndpoint.host();
    } catch (e) {}
    return location.hostname || '127.0.0.1';
  }

  function apiBase() {
    var proto = location.protocol === 'https:' ? 'https:' : 'http:';
    return proto + '//' + endpointHost() + ':' + basemapPort();
  }

  // ---- pure decision core (unit-tested headless in chart-library.test.cjs) --------------------

  // Mirror of the server's collision pack id (mbtiles_server._collision_id /
  // helm_packd collision_pack_id): relative path minus extension, '/' -> '--',
  // other punctuation collapsed to single '-'.
  function collisionPackId(relativePath) {
    var stem = String(relativePath == null ? '' : relativePath).replace(/\.[^/.]*$/, '');
    var id = '';
    for (var i = 0; i < stem.length; i++) {
      var c = stem[i];
      if (c === '/') id += '--';
      else if (/[A-Za-z0-9._-]/.test(c)) id += c;
      else if (!id || id[id.length - 1] !== '-') id += '-';
    }
    id = id.replace(/^-+/, '').replace(/-+$/, '');
    return id || 'pack';
  }

  function chartStem(chart) {
    return String(chart.filename || '').replace(/\.[^.]*$/, '');
  }

  function catalogIdCandidates(chart) {
    var out = [chartStem(chart), collisionPackId(chart.relative_path || chart.filename || '')];
    return out.filter(function (v, i) { return v && out.indexOf(v) === i; });
  }

  // Find the CAT-1 /catalog record for a tile pack. Exact candidate id first,
  // then the server's cross-root disambiguation suffix ("<id>--rN").
  function catalogRecordFor(chart, catalog) {
    if (!catalog || chart.chart_type !== 'tile_pack') return null;
    var candidates = catalogIdCandidates(chart);
    for (var i = 0; i < candidates.length; i++) {
      if (catalog[candidates[i]]) return catalog[candidates[i]];
    }
    var keys = Object.keys(catalog);
    for (var j = 0; j < candidates.length; j++) {
      for (var k = 0; k < keys.length; k++) {
        if (keys[k].indexOf(candidates[j] + '--r') === 0) return catalog[keys[k]];
      }
    }
    return null;
  }

  // Honest freshness for a chart row. Tile packs read CAT-1 staleness off the
  // joined catalog record; everything else states why there is no window.
  function freshnessFor(chart, catalogRec, catalogError) {
    if (chart.chart_type === 'tile_pack') {
      if (catalogError) return { status: 'unknown', label: 'freshness unknown (/catalog unreachable)' };
      if (!catalogRec) return { status: 'unlisted', label: 'not served by /catalog' };
      var staleness = catalogRec.staleness || {};
      var status = staleness.status || 'unknown';
      var age = (typeof staleness.age_days === 'number') ? staleness.age_days : null;
      if (status === 'stale') return { status: 'stale', age_days: age, label: 'stale' + (age != null ? ' · ' + age + 'd old' : '') };
      if (status === 'fresh') return { status: 'fresh', age_days: age, label: 'fresh' + (age != null ? ' · ' + age + 'd' : '') };
      return { status: 'unknown', age_days: age, label: 'freshness unknown (no render_date sidecar)' };
    }
    if (chart.chart_type === 'enc') {
      var updates = chart.update_count || 0;
      return { status: 'enc', label: updates > 0 ? updates + ' update cell' + (updates === 1 ? '' : 's') : 'no update cells' };
    }
    return { status: 'overlay', label: '' };
  }

  function validationBadge(chart) {
    var v = chart.validation || {};
    if (v.status === 'valid') return null;
    return { level: v.status === 'error' ? 'error' : 'warn', code: v.code || v.status || 'unknown', message: v.message || '' };
  }

  // Group tabs: named region folders alphabetically, root-level ('.') last.
  function groupsOf(charts) {
    var seen = {};
    (charts || []).forEach(function (c) { if (c.group) seen[c.group] = true; });
    var named = Object.keys(seen).filter(function (g) { return g !== '.'; }).sort();
    if (seen['.']) named.push('.');
    return named;
  }

  function groupLabel(group) {
    return group === '.' ? 'Top level' : group;
  }

  function chartsInGroup(charts, group) {
    if (!group || group === 'all') return charts || [];
    return (charts || []).filter(function (c) { return c.group === group; });
  }

  // First-run / empty-state decision: which prompt the panel body shows when
  // there is nothing to list. Never invents charts; names the actual state.
  function emptyStateFor(index, indexError) {
    if (indexError) return { kind: 'error', message: indexError };
    if (!index) return { kind: 'loading', message: 'Reading chart library…' };
    if ((index.chart_count || 0) > 0) return null;
    var roots = index.roots || [];
    var missing = roots.filter(function (r) { return r.status !== 'available'; });
    if (roots.length && missing.length === roots.length) {
      return { kind: 'roots-missing', message: 'No registered chart folder is reachable.' };
    }
    return { kind: 'first-run', message: 'No charts in the library yet.' };
  }

  function fmtSize(bytes) {
    if (typeof bytes !== 'number' || !(bytes >= 0)) return '';
    if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  function typeLabel(chart) {
    if (chart.chart_type === 'tile_pack') return chart.extension === '.pmtiles' ? 'PMTiles' : 'MBTiles';
    if (chart.chart_type === 'enc') return 'ENC S-57';
    return 'GeoJSON overlay';
  }

  // ---- overlay <-> layer-manifest join (map-side, not pure) -----------------------------------
  function overlayLayerIds(chart) {
    var map = state.map;
    var lm = window.HelmLayerManifest;
    if (!map || !map.getStyle || !lm || !lm.slug || !lm.ID_PREFIX) return [];
    var prefix = lm.ID_PREFIX + lm.slug(chartStem(chart));
    var style;
    try { style = map.getStyle(); } catch (e) { return []; }
    return ((style && style.layers) || []).map(function (l) { return l.id; }).filter(function (id) {
      return id === prefix || id.indexOf(prefix + '-') === 0;
    });
  }

  function overlayVisible(layerIds) {
    var map = state.map;
    if (!map || !layerIds.length) return false;
    return layerIds.some(function (id) {
      try { return map.getLayoutProperty(id, 'visibility') !== 'none'; } catch (e) { return false; }
    });
  }

  // ---- fetch -----------------------------------------------------------------------------------
  function fetchJson(url, options) {
    return fetch(url, options).then(function (resp) {
      return resp.json().catch(function () { return {}; }).then(function (body) {
        return { ok: resp.ok, status: resp.status, body: body };
      });
    });
  }

  function refresh() {
    if (state.loading) return Promise.resolve();
    state.loading = true;
    render();
    var base = apiBase();
    var index = fetchJson(base + '/chart-index').then(function (r) {
      if (!r.ok) throw new Error((r.body && r.body.message) || ('HTTP ' + r.status));
      state.index = r.body; state.indexError = '';
    }).catch(function (e) {
      state.index = null;
      state.indexError = 'chart-index unreachable at ' + base + ' — ' + ((e && e.message) || e);
    });
    var roots = fetchJson(base + '/chart-roots').then(function (r) {
      if (!r.ok) throw new Error((r.body && r.body.message) || ('HTTP ' + r.status));
      state.roots = r.body.roots || []; state.rootsSource = r.body.source || ''; state.rootsError = '';
    }).catch(function (e) {
      state.roots = null; state.rootsSource = '';
      state.rootsError = ((e && e.message) || String(e));
    });
    var catalog = fetchJson(base + '/catalog').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      state.catalog = r.body; state.catalogError = '';
    }).catch(function (e) {
      state.catalog = null;
      state.catalogError = ((e && e.message) || String(e));
    });
    return Promise.all([index, roots, catalog]).then(function () {
      state.loading = false;
      render();
    });
  }

  function postJson(path, payload) {
    return fetchJson(apiBase() + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {})
    });
  }

  function runAction(promise, describe) {
    state.busy = true;
    state.notice = '';
    render();
    return promise.then(function (r) {
      state.busy = false;
      if (!r.ok) {
        state.notice = 'error: ' + ((r.body && r.body.message) || ('HTTP ' + r.status));
        render();
        return null;
      }
      state.notice = describe(r.body);
      return refresh().then(function () { return r.body; });
    }).catch(function (e) {
      state.busy = false;
      state.notice = 'error: ' + ((e && e.message) || e);
      render();
      return null;
    });
  }

  function addRoot(path, label) {
    var payload = { path: path };
    if (label) payload.label = label;
    return runAction(postJson('/chart-roots', payload), function (body) {
      var root = body.root || {};
      return body.changed === false
        ? 'folder already registered as “' + (root.label || '?') + '”'
        : 'registered “' + (root.label || '?') + '”';
    });
  }

  function removeRoot(id) {
    return runAction(postJson('/chart-roots/remove', { id: id }), function (body) {
      return 'unregistered “' + ((body.removed && body.removed.label) || id) + '” (files stay put)';
    });
  }

  function rescan() {
    return runAction(postJson('/rescan', {}), function (body) {
      return 'rescan: ' + body.packs + ' pack' + (body.packs === 1 ? '' : 's') + (body.changed ? ', tree changed' : ', no change');
    });
  }

  // ---- actions on charts -----------------------------------------------------------------------
  function showTilePack(chart) {
    var rec = catalogRecordFor(chart, state.catalog);
    if (!rec) { state.notice = 'error: ' + chart.filename + ' is not in /catalog'; render(); return; }
    var packs = window.HelmOfflinePacks;
    if (!packs || !packs.activate) {
      state.notice = 'error: offline-packs module unavailable'; render(); return;
    }
    var packId = String(rec.id || rec.name);
    // The pack owner activates from its OWN catalog list; make sure it has one
    // before delegating, and verify the activation actually took (no fake green).
    var listed = ((packs.state && packs.state.packs) || []).some(function (p) { return String(p.id) === packId; });
    var ready = listed ? Promise.resolve() : Promise.resolve(packs.refresh && packs.refresh());
    state.busy = true;
    render();
    ready.then(function () {
      packs.activate(packId);
      state.busy = false;
      if (packs.state && String(packs.state.activeId) === packId) {
        state.notice = 'showing “' + (rec.title || packId) + '” as the active pack';
      } else {
        state.notice = 'error: offline-packs did not activate “' + packId + '” — ' +
          ((packs.state && packs.state.error) || 'pack missing from its catalog');
      }
      render();
    }).catch(function (e) {
      state.busy = false;
      state.notice = 'error: ' + ((e && e.message) || e);
      render();
    });
  }

  function locateChart(chart) {
    var map = state.map;
    var bbox = chart.bbox;
    if (!map || !bbox || bbox.length !== 4) return;
    try {
      map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 48, duration: 500, maxZoom: 14 });
    } catch (e) { log.warn && log.warn('fitBounds failed: ' + e); }
  }

  function toggleOverlay(chart) {
    var ids = overlayLayerIds(chart);
    var map = state.map;
    if (!map || !ids.length) return;
    var next = overlayVisible(ids) ? 'none' : 'visible';
    ids.forEach(function (id) {
      try { map.setLayoutProperty(id, 'visibility', next); } catch (e) {}
    });
    render();
  }

  // ---- rendering --------------------------------------------------------------------------------
  function rootRowHtml(root) {
    var status = root.status === 'available'
      ? '<span class="helm-chartlib-ok">available</span>'
      : '<span class="helm-chartlib-err">unavailable</span>';
    var meta = [];
    if (root.default) meta.push('default');
    var indexRoot = ((state.index && state.index.roots) || []).filter(function (r) { return r.id === root.id; })[0];
    if (indexRoot && typeof indexRoot.chart_count === 'number') {
      meta.push(indexRoot.chart_count + ' chart' + (indexRoot.chart_count === 1 ? '' : 's'));
      if (indexRoot.group_count > 0) meta.push(indexRoot.group_count + ' group' + (indexRoot.group_count === 1 ? '' : 's'));
    }
    var removable = !root.default && state.rootsSource === 'file' && !state.busy;
    return [
      '<div class="helm-chartlib-root" data-root-id="', esc(root.id), '">',
      '<div class="helm-chartlib-root-main"><b>', esc(root.label || 'Charts'), '</b>',
      '<i>', esc(meta.join(' · ')), '</i></div>',
      status,
      removable ? '<button class="conn-btn" type="button" data-chartlib-remove="' + esc(root.id) + '">Unregister</button>' : '',
      '</div>'
    ].join('');
  }

  function chartRowHtml(chart) {
    var badge = validationBadge(chart);
    var rec = catalogRecordFor(chart, state.catalog);
    var freshness = freshnessFor(chart, rec, state.catalogError);
    var bits = [typeLabel(chart), fmtSize(chart.size_bytes)];
    if (chart.group && chart.group !== '.') bits.push(chart.group);
    var freshnessHtml = '';
    if (freshness.status === 'stale') freshnessHtml = '<span class="helm-chartlib-warn">' + esc(freshness.label) + '</span>';
    else if (freshness.status === 'fresh') freshnessHtml = '<span class="helm-chartlib-ok">' + esc(freshness.label) + '</span>';
    else if (freshness.label) freshnessHtml = '<span class="helm-chartlib-dim">' + esc(freshness.label) + '</span>';
    var actions = [];
    if (chart.chart_type === 'tile_pack' && rec && !state.busy) {
      actions.push('<button class="conn-btn" type="button" data-chartlib-show="' + esc(chart.id) + '">Show</button>');
    }
    if (chart.bbox && chart.bbox.length === 4) {
      actions.push('<button class="conn-btn" type="button" data-chartlib-locate="' + esc(chart.id) + '">Locate</button>');
    }
    var note = '';
    if (chart.chart_type === 'overlay') {
      var layerIds = overlayLayerIds(chart);
      if (layerIds.length) {
        actions.push('<button class="conn-btn" type="button" data-chartlib-overlay="' + esc(chart.id) + '">'
          + (overlayVisible(layerIds) ? 'Hide' : 'Show') + '</button>');
      } else {
        note = 'indexed, not yet served — the layer manifest publishes overlays from user-data/layers';
      }
    }
    if (chart.chart_type === 'enc') {
      note = 'rendered by the ENC engine — toggle depth layers in the Layers drawer';
    }
    return [
      '<div class="helm-chartlib-row', badge && badge.level === 'error' ? ' is-invalid' : '', '">',
      '<div class="helm-chartlib-main">',
      '<b>', esc(chart.filename), '</b>',
      '<i>', esc(bits.filter(Boolean).join(' · ')), '</i>',
      badge ? '<i class="helm-chartlib-' + (badge.level === 'error' ? 'err' : 'warn') + '" title="' + esc(badge.message) + '">'
        + esc(badge.level === 'error' ? 'invalid: ' : 'warning: ') + esc(badge.code) + '</i>' : '',
      note ? '<i class="helm-chartlib-dim">' + esc(note) + '</i>' : '',
      '</div>',
      '<div class="helm-chartlib-side">', freshnessHtml, actions.join(''), '</div>',
      '</div>'
    ].join('');
  }

  function render() {
    var body = state.body;
    if (!body) return;
    var el = body.querySelector('[data-chartlib]');
    if (!el) return;

    var index = state.index;
    var charts = (index && index.charts) || [];
    var groups = groupsOf(charts);
    if (state.group !== 'all' && groups.indexOf(state.group) === -1) state.group = 'all';
    var visible = chartsInGroup(charts, state.group);
    var empty = emptyStateFor(index, state.indexError);
    var envManaged = state.rootsSource === 'env';

    var html = [];
    html.push('<div class="helm-chartlib-statusline">',
      state.loading ? 'Reading library…' : (index ? index.chart_count + ' chart' + (index.chart_count === 1 ? '' : 's')
        + (index.invalid_count ? ' · <span class="helm-chartlib-err">' + index.invalid_count + ' invalid</span>' : '')
        + (index.warning_count ? ' · <span class="helm-chartlib-warn">' + index.warning_count + ' warning' + (index.warning_count === 1 ? '' : 's') + '</span>' : '') : ''),
      '</div>');
    if (state.notice) {
      html.push('<div class="helm-chartlib-notice', state.notice.indexOf('error:') === 0 ? ' is-error' : '', '">', esc(state.notice), '</div>');
    }

    html.push('<div class="helm-chartlib-section">Chart folders</div>');
    if (state.rootsError) {
      html.push('<div class="helm-chartlib-notice is-error">chart-roots unreachable — ', esc(state.rootsError), '</div>');
    } else {
      (state.roots || []).forEach(function (root) { html.push(rootRowHtml(root)); });
    }
    if (envManaged) {
      html.push('<div class="helm-chartlib-dimnote">Folders are managed by HELM_CHART_ROOTS; register/unregister is disabled.</div>');
    } else {
      html.push('<form class="helm-chartlib-add" data-chartlib-add>',
        '<input type="text" name="path" placeholder="/path/to/your/chart/folder" autocomplete="off" spellcheck="false"', state.busy ? ' disabled' : '', '>',
        '<input type="text" name="label" placeholder="Label (optional)" autocomplete="off"', state.busy ? ' disabled' : '', '>',
        '<div class="helm-chartlib-addrow">',
        '<button class="conn-btn" type="submit"', state.busy ? ' disabled' : '', '>Add folder</button>',
        '<button class="conn-btn" type="button" data-chartlib-rescan', state.busy ? ' disabled' : '', '>Rescan</button>',
        '</div></form>');
    }

    if (empty) {
      var emptyBody = { 'error': esc(empty.message) + ' <button class="conn-btn" type="button" data-chartlib-retry>Retry</button>',
        'loading': esc(empty.message),
        'roots-missing': esc(empty.message) + ' Reconnect the drive or unregister the folder.',
        'first-run': esc(empty.message) + (envManaged ? '' : ' Point Helm at a folder you already keep charts in — it is scanned recursively in place; nothing is moved or renamed.') }[empty.kind];
      html.push('<div class="helm-chartlib-empty" data-empty-kind="', esc(empty.kind), '">', emptyBody, '</div>');
    } else {
      html.push('<div class="helm-chartlib-section">Charts</div>');
      if (groups.length > 1) {
        html.push('<div class="helm-chartlib-tabs">');
        ['all'].concat(groups).forEach(function (g) {
          html.push('<button type="button" class="helm-chartlib-tab', g === state.group ? ' on' : '',
            '" data-chartlib-group="', esc(g), '">', esc(g === 'all' ? 'All' : groupLabel(g)), '</button>');
        });
        html.push('</div>');
      }
      html.push('<div class="helm-chartlib-list">');
      visible.forEach(function (chart) { html.push(chartRowHtml(chart)); });
      html.push('</div>');
    }
    el.innerHTML = html.join('');
  }

  function chartById(id) {
    var charts = (state.index && state.index.charts) || [];
    return charts.filter(function (c) { return c.id === id; })[0] || null;
  }

  function renderPanel(body, ctx) {
    state.body = body;
    state.map = ctx && ctx.map;
    installStyle();
    try { state.group = (window.HelmStore && HelmStore.get(GROUP_KEY, 'all')) || 'all'; } catch (e) {}
    body.insertAdjacentHTML('beforeend', [
      '<p class="sub">Your chart folders, indexed in place</p>',
      '<div data-chartlib></div>'
    ].join(''));

    body.addEventListener('click', function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var group = t.closest('[data-chartlib-group]');
      if (group) {
        state.group = group.getAttribute('data-chartlib-group') || 'all';
        try { window.HelmStore && HelmStore.set(GROUP_KEY, state.group); } catch (err) {}
        render();
        return;
      }
      var remove = t.closest('[data-chartlib-remove]');
      if (remove) { removeRoot(remove.getAttribute('data-chartlib-remove')); return; }
      var rescanBtn = t.closest('[data-chartlib-rescan]');
      if (rescanBtn) { rescan(); return; }
      var retry = t.closest('[data-chartlib-retry]');
      if (retry) { refresh(); return; }
      var show = t.closest('[data-chartlib-show]');
      if (show) { var c1 = chartById(show.getAttribute('data-chartlib-show')); if (c1) showTilePack(c1); return; }
      var locate = t.closest('[data-chartlib-locate]');
      if (locate) { var c2 = chartById(locate.getAttribute('data-chartlib-locate')); if (c2) locateChart(c2); return; }
      var overlay = t.closest('[data-chartlib-overlay]');
      if (overlay) { var c3 = chartById(overlay.getAttribute('data-chartlib-overlay')); if (c3) toggleOverlay(c3); }
    });
    body.addEventListener('submit', function (e) {
      var form = e.target && e.target.closest && e.target.closest('[data-chartlib-add]');
      if (!form) return;
      e.preventDefault();
      var path = (form.querySelector('input[name="path"]').value || '').trim();
      var label = (form.querySelector('input[name="label"]').value || '').trim();
      if (!path) { state.notice = 'error: enter the folder path to register'; render(); return; }
      addRoot(path, label || null);
    });

    refresh();
  }

  function installStyle() {
    if (document.getElementById('helm-chart-library-style')) return;
    var style = document.createElement('style');
    style.id = 'helm-chart-library-style';
    style.textContent = [
      '.helm-chartlib-statusline{font-size:10.5px;color:var(--cdim2);margin:6px 0 8px}',
      '.helm-chartlib-section{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--cdim2);margin:12px 0 6px}',
      '.helm-chartlib-root{display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid var(--line);border-radius:7px;margin-bottom:5px}',
      '.helm-chartlib-root-main{display:flex;flex-direction:column;gap:1px;min-width:0;flex:1}',
      '.helm-chartlib-root-main b{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.helm-chartlib-root-main i{font-size:10px;color:var(--cdim2);font-style:normal}',
      '.helm-chartlib-add{display:flex;flex-direction:column;gap:6px;margin:8px 0 4px}',
      '.helm-chartlib-add input{background:rgba(255,255,255,.05);border:1px solid var(--line);border-radius:6px;color:var(--ctext);font-size:11.5px;padding:7px 9px;outline:none;min-height:34px}',
      '.helm-chartlib-add input:focus{border-color:var(--accent)}',
      '.helm-chartlib-addrow{display:flex;gap:8px}',
      '.helm-chartlib-tabs{display:flex;flex-wrap:wrap;gap:5px;margin:2px 0 8px}',
      '.helm-chartlib-tab{border:1px solid var(--line);background:transparent;color:var(--cdim);font-size:10.5px;padding:5px 10px;border-radius:999px;cursor:pointer;min-height:28px}',
      '.helm-chartlib-tab.on{color:var(--accent);border-color:rgba(91,192,255,.55);background:rgba(91,192,255,.10)}',
      '.helm-chartlib-list{display:flex;flex-direction:column;gap:6px}',
      '.helm-chartlib-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px 9px;padding:7px 9px;border:1px solid var(--line);border-radius:7px;min-height:48px}',
      '.helm-chartlib-row.is-invalid{border-color:rgba(255,110,110,.4)}',
      // flex-basis keeps the filename column alive in the 230px drawer; the
      // freshness/action side wraps beneath it instead of starving it to 0.
      '.helm-chartlib-main{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1 1 140px}',
      '.helm-chartlib-main b{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.helm-chartlib-main i{font-size:10px;color:var(--cdim2);font-style:normal;overflow:hidden;text-overflow:ellipsis}',
      '.helm-chartlib-side{display:flex;align-items:center;gap:6px;flex:none;margin-left:auto}',
      '.helm-chartlib-side .conn-btn{min-height:30px}',
      '.helm-chartlib-ok{font-size:10px;color:var(--ok,#5fd08a)}',
      '.helm-chartlib-warn{font-size:10px;color:var(--warn,#e0a23a)}',
      '.helm-chartlib-err{font-size:10px;color:#ff7d7d}',
      '.helm-chartlib-dim{font-size:10px;color:var(--cdim2)}',
      '.helm-chartlib-dimnote{font-size:10.5px;color:var(--cdim);margin:6px 0}',
      '.helm-chartlib-notice{font-size:10.5px;color:var(--cdim);border:1px solid var(--line);border-radius:6px;padding:6px 8px;margin:6px 0}',
      '.helm-chartlib-notice.is-error{color:#ff9d9d;border-color:rgba(255,110,110,.4)}',
      '.helm-chartlib-empty{font-size:11.5px;color:var(--cdim);line-height:1.5;padding:10px 2px}'
    ].join('\n');
    document.head.appendChild(style);
  }

  function register() {
    if (!(window.HelmShell && HelmShell.registerPanel)) return;
    HelmShell.registerPanel({
      id: PANEL_ID,
      epic: EPIC,
      // The left rail is already full (see web/coordinates.js: an 11th icon
      // overflows it and pushes the Settings button under the instrument bar,
      // failing verified-local-ui). Enter via the ⌘K command below, matching the
      // established overflow-panel pattern; the icon is kept for when a rail slot
      // frees up or the rail gains a scroll affordance.
      rail: false,
      title: 'Chart Library',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"><path d="M3 5.5 9 3l6 2.5L21 3v15.5L15 21l-6-2.5L3 21z"/><path d="M9 3v15.5"/><path d="M15 5.5V21"/></svg>',
      render: renderPanel,
      onOpen: function () { refresh(); }
    });
    if (HelmShell.registerCommand) {
      HelmShell.registerCommand({
        id: 'helm-intake-open-chart-library',
        epic: EPIC,
        title: 'Open chart library',
        subtitle: 'Register chart folders, rescan, region groups',
        keywords: ['charts', 'library', 'folders', 'intake', 'rescan', 'enc', 'mbtiles'],
        group: 'Layers',
        run: function () { var h = HelmShell.panel(PANEL_ID); if (h) h.open(); }
      });
    }
  }

  // Pure core exposed for headless unit tests + other modules; DOM/registration
  // stays inert when the shell is absent (vm sandbox in chart-library.test.cjs).
  window.HelmChartLibrary = {
    state: state,
    refresh: refresh,
    collisionPackId: collisionPackId,
    catalogIdCandidates: catalogIdCandidates,
    catalogRecordFor: catalogRecordFor,
    freshnessFor: freshnessFor,
    validationBadge: validationBadge,
    groupsOf: groupsOf,
    groupLabel: groupLabel,
    chartsInGroup: chartsInGroup,
    emptyStateFor: emptyStateFor,
    fmtSize: fmtSize,
    typeLabel: typeLabel
  };

  register();
})();
