// web/offline.js — OFFLINE-3 + OFFLINE-L-3: the Download drawer (lasso → size estimate → handoff)
// ------------------------------------------------------------------------------------------------
// Fills #drawer-download with a working "cache only what you need" panel. Two modes share one lasso:
//   • Sat-first region pack (OFFLINE-L-3, default): lasso an area, then ask the local pack server
//     (helm-packd /bundle?profile=sat_first) for a LIVE size estimate built from real pack sizes.
//     A satellite basemap is required; chart/depth ride along as optional overlays
//     (docs/proposals/interfaces/region-bundle-sat-first-v1.md). No satellite coverage ⇒ the drawer
//     says so (missing_basemap); the pack server is down ⇒ it says that too. It never invents a
//     number. The bake itself stays server-side (OFFLINE-L-2); this panel only scopes + estimates.
//   • Single tile source (OFFLINE-3, legacy): pick an XYZ template, get a client-side estimate and a
//     copyable pipeline/fetch_tiles.py command. deg2num mirrors fetch_tiles.py so the two agree.
//
// Stays in-lane: fills the EXISTING download drawer (rail button + opener already wired in
// index.html); registers no second rail icon. All CSS scoped under #drawer-download. Owns no shell.
(function () {
  'use strict';
  var EL = document.getElementById('drawer-download');
  if (!EL) { console.warn('[offline] #drawer-download missing — download drawer not mounted'); return; }

  // ---- local pack server origin — mirrors offline-packs.js catalogBase() so the live estimate
  //      hits the same helm-packd the pack selector uses (kept standalone; no cross-file export) ----
  var DEFAULT_PORT = '8091';
  function basemapPort() {
    try {
      var q = new URLSearchParams(location.search);
      return q.get('basemapPort') || window.HELM_BASEMAP_PORT || DEFAULT_PORT;
    } catch (e) { return window.HELM_BASEMAP_PORT || DEFAULT_PORT; }
  }
  function endpointHost() {
    try { if (window.HelmEndpoint && HelmEndpoint.host) return HelmEndpoint.host(); } catch (e) {}
    return location.hostname || '127.0.0.1';
  }
  function packdBase() {
    var proto = location.protocol === 'https:' ? 'https:' : 'http:';
    return proto + '//' + endpointHost() + ':' + basemapPort();
  }

  // ---- sources. The sat-first region pack is the default (live, multi-layer, accurate); the XYZ
  //      single-source rows keep the OFFLINE-3 client-side estimate + fetch_tiles.py handoff. ----
  var BUNDLE_SOURCE = { id: 'satfirst', label: 'Sat-first region pack (offline)', bundle: true, note: 'live estimate from the local pack server' };
  var SOURCES = [
    BUNDLE_SOURCE,
    { id: 'noaa',      label: 'NOAA ENC charts',     url: 'https://tileservice.charts.noaa.gov/tiles/50000_1/{z}/{x}/{y}.png', fmt: 'png', kb: 12, note: 'public · free' },
    { id: 'eox',       label: 'Sentinel-2 (EOX)',    url: 'http://localhost:8095/basemap/eox/{z}/{x}/{y}.jpg',                 fmt: 'jpg', kb: 26, note: 'needs :8095 online-fill' },
    { id: 'navionics', label: 'Navionics (proxy)',   url: 'http://localhost:8091/navionics/{z}/{x}/{y}.png',                  fmt: 'png', kb: 22, note: 'needs :8091 basemap' },
    { id: 'googlesat', label: 'Google satellite',    url: 'http://localhost:8091/googlesat/{z}/{x}/{y}.jpg',                  fmt: 'jpg', kb: 30, note: 'personal use' },
    { id: 'custom',    label: 'Custom {z}/{x}/{y}…',  url: '',                                                                fmt: 'png', kb: 20, note: 'paste an XYZ template below' }
  ];

  // Zoom caps — charts rarely render past ~16; the hard cap stops a deep span from queuing millions
  // of tiles. SOFT_TILES warns; HARD_TILES blocks the legacy command (fail-loud, never a runaway).
  var ZMIN_FLOOR = 1, ZMAX_CEIL = 16, SOFT_TILES = 40000, HARD_TILES = 250000;

  // ---- tile math — mirrors pipeline/fetch_tiles.deg2num (legacy single-source estimate) ----
  function deg2num(lon, lat, z) {
    var n = Math.pow(2, z);
    var x = Math.floor((lon + 180) / 360 * n);
    var y = Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    var clamp = function (v) { return Math.max(0, Math.min(n - 1, v)); };
    return [clamp(x), clamp(y)];
  }
  function tileCount(bb, zmin, zmax) {
    if (!bb || zmax < zmin) return 0;
    var w = bb[0], s = bb[1], e = bb[2], nn = bb[3], total = 0;
    for (var z = zmin; z <= zmax; z++) {
      var nw = deg2num(w, nn, z), se = deg2num(e, s, z);
      total += (Math.abs(se[0] - nw[0]) + 1) * (Math.abs(se[1] - nw[1]) + 1);
    }
    return total;
  }
  function human(n) { return n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(n); }
  function humanMB(kb) { return kb >= 1024 ? (kb / 1024).toFixed(1) + ' GB' : Math.max(1, Math.round(kb)) + ' MB'; }
  // Human bytes for the live /bundle estimate (real byte totals, not the legacy per-tile guess).
  function humanBytes(bytes) {
    if (bytes == null || isNaN(bytes)) return null;
    var mb = bytes / (1024 * 1024);
    if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB';
    if (mb >= 1) return (mb < 10 ? mb.toFixed(1) : Math.round(mb)) + ' MB';
    return Math.max(1, Math.round(bytes / 1024)) + ' KB';
  }

  // ---- scoped styles (one injection; every selector under #drawer-download) ----
  (function () {
    var css = document.createElement('style');
    css.textContent =
      '#drawer-download{width:316px}' +
      '#drawer-download .dl-fld{margin:10px 0 4px;font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--cdim,#9bb0c0)}' +
      '#drawer-download select,#drawer-download input[type=text]{width:100%;box-sizing:border-box;font:12px/1.3 inherit;color:#e6eef5;' +
        'background:rgba(255,255,255,.05);border:.5px solid var(--line,rgba(255,255,255,.14));border-radius:8px;padding:7px 9px}' +
      '#drawer-download .dl-src-note{font-size:10px;color:var(--cdim,#9bb0c0);margin-top:4px}' +
      '#drawer-download .dl-row{display:flex;gap:8px;align-items:center;margin-top:6px}' +
      '#drawer-download .dl-row button{flex:1;font:500 11.5px/1 inherit;padding:8px 6px;border-radius:8px;cursor:pointer;' +
        'border:.5px solid var(--line,rgba(255,255,255,.14));background:transparent;color:#cdd9e3}' +
      '#drawer-download .dl-row button.pri{background:rgba(67,209,125,.16);border-color:rgba(67,209,125,.55);color:#a4f4c1}' +
      '#drawer-download .dl-bbox{font:11px/1.4 ui-monospace,Menlo,monospace;color:#cdd9e3;background:rgba(255,255,255,.04);' +
        'border:.5px solid var(--line,rgba(255,255,255,.1));border-radius:7px;padding:6px 8px;margin-top:6px;word-break:break-all}' +
      '#drawer-download .dl-bbox.none{color:var(--cdim,#9bb0c0)}' +
      '#drawer-download .dl-zooms{display:flex;gap:10px;margin-top:4px}' +
      '#drawer-download .dl-zooms label{flex:1;font-size:10.5px;color:var(--cdim,#9bb0c0)}' +
      '#drawer-download .dl-zooms input{width:100%;box-sizing:border-box;font:12px inherit;color:#e6eef5;text-align:center;' +
        'background:rgba(255,255,255,.05);border:.5px solid var(--line,rgba(255,255,255,.14));border-radius:8px;padding:6px}' +
      '#drawer-download .dl-est{margin-top:10px;font-size:12.5px;color:#e6eef5;display:flex;justify-content:space-between;align-items:baseline;gap:8px}' +
      '#drawer-download .dl-est b{font-variant-numeric:tabular-nums;text-align:right}' +
      '#drawer-download .dl-est .warn{color:var(--warn,#ffc06a)}' +
      '#drawer-download .dl-est .danger{color:var(--danger,#ff6a6a)}' +
      '#drawer-download .dl-breakdown{margin-top:8px;display:flex;flex-direction:column;gap:3px}' +
      '#drawer-download .dl-breakdown:empty{display:none}' +
      '#drawer-download .dl-layer{display:flex;justify-content:space-between;gap:8px;font:11px/1.35 inherit;color:#cdd9e3}' +
      '#drawer-download .dl-layer-k{color:var(--cdim,#9bb0c0);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '#drawer-download .dl-layer.pri .dl-layer-k{color:#a4f4c1}' +
      '#drawer-download .dl-layer-v{font-variant-numeric:tabular-nums;white-space:nowrap}' +
      '#drawer-download .dl-error{margin-top:9px;font:11.5px/1.45 inherit;color:#ffb4b4;' +
        'background:rgba(255,80,80,.09);border:.5px solid rgba(255,106,106,.5);border-radius:8px;padding:8px 9px}' +
      '#drawer-download .dl-cmd{margin-top:9px;font:10.5px/1.4 ui-monospace,Menlo,monospace;color:#bfe9cf;white-space:pre-wrap;word-break:break-all;' +
        'background:rgba(8,14,20,.7);border:.5px solid var(--line,rgba(255,255,255,.1));border-radius:8px;padding:8px 9px;max-height:120px;overflow:auto}' +
      '#drawer-download .dl-copy{margin-top:7px;width:100%;font:500 11.5px/1 inherit;padding:8px;border-radius:8px;cursor:pointer;' +
        'border:.5px solid var(--line,rgba(255,255,255,.14));background:transparent;color:#cdd9e3}' +
      '#drawer-download .dl-copy:disabled{opacity:.4;cursor:not-allowed}';
    document.head.appendChild(css);
  })();

  // ---- state ----
  var bbox = (Array.isArray(window.__helmBbox) ? window.__helmBbox : null);
  var sourceId = 'satfirst';
  var customUrl = '';
  var lastBundle = null;   // last successful sat-first bundle manifest (test/debug surface)
  var bundleSeq = 0;       // guards against out-of-order /bundle responses
  var bundleTimer = null;  // debounce for the live estimate while dragging inputs

  // ---- build the panel body (keeps the existing <h2> the drawer already has) ----
  EL.querySelectorAll(':scope > *:not(h2)').forEach(function (n) { n.remove(); });  // strip mock remnants

  EL.appendChild(el('p', 'sub', 'Cache only what you need · lasso an area, then estimate an offline pack.'));

  EL.appendChild(el('div', 'dl-fld', 'Source'));
  var sel = document.createElement('select'); sel.setAttribute('data-testid', 'dl-source');
  SOURCES.forEach(function (s) { var o = document.createElement('option'); o.value = s.id; o.textContent = s.label; sel.appendChild(o); });
  sel.value = sourceId;
  EL.appendChild(sel);
  var srcNote = el('div', 'dl-src-note', '');
  EL.appendChild(srcNote);
  var customWrap = document.createElement('input'); customWrap.type = 'text';
  customWrap.placeholder = 'https://…/{z}/{x}/{y}.png'; customWrap.style.marginTop = '6px'; customWrap.hidden = true;
  EL.appendChild(customWrap);

  EL.appendChild(el('div', 'dl-fld', 'Area'));
  var rowArea = el('div', 'dl-row');
  var btnLasso = btn('▢ Select area', 'pri'); var btnView = btn('Use current view');
  rowArea.appendChild(btnLasso); rowArea.appendChild(btnView); EL.appendChild(rowArea);
  var bboxEl = el('div', 'dl-bbox none', 'No area selected — lasso a box or use the current view.');
  bboxEl.setAttribute('data-testid', 'dl-bbox');
  EL.appendChild(bboxEl);

  EL.appendChild(el('div', 'dl-fld', 'Zoom range (detail)'));
  var zooms = el('div', 'dl-zooms');
  var zmin = numIn('min', 9), zmax = numIn('max', 15);
  zmin.setAttribute('data-testid', 'dl-zmin'); zmax.setAttribute('data-testid', 'dl-zmax');
  zooms.appendChild(zlabel('min zoom', zmin)); zooms.appendChild(zlabel('max zoom', zmax));
  EL.appendChild(zooms);

  var est = el('div', 'dl-est'); est.setAttribute('data-testid', 'dl-estimate');
  est.innerHTML = '<span>Estimate</span><b>—</b>'; EL.appendChild(est);
  var breakdown = el('div', 'dl-breakdown'); breakdown.setAttribute('data-testid', 'dl-breakdown'); EL.appendChild(breakdown);
  var errorEl = el('div', 'dl-error'); errorEl.setAttribute('data-testid', 'dl-error'); errorEl.hidden = true; EL.appendChild(errorEl);
  var cmd = el('div', 'dl-cmd', '# select an area to estimate an offline pack'); EL.appendChild(cmd);
  var copy = document.createElement('button'); copy.className = 'dl-copy'; copy.textContent = 'Copy command'; copy.disabled = true; EL.appendChild(copy);
  var hint = el('div', 'hint', ''); EL.appendChild(hint);

  // ---- helpers to build elements ----
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function btn(txt, cls) { var b = document.createElement('button'); b.type = 'button'; b.textContent = txt; if (cls) b.classList.add(cls); return b; }
  function numIn(name, val) { var i = document.createElement('input'); i.type = 'number'; i.value = val; i.min = ZMIN_FLOOR; i.max = ZMAX_CEIL; i.step = 1; return i; }
  function zlabel(txt, input) { var l = document.createElement('label'); l.textContent = txt; l.appendChild(input); return l; }

  function source() { var s = SOURCES.filter(function (x) { return x.id === sourceId; })[0] || SOURCES[0]; return s; }
  function slug() { return source().id + '-' + (bbox ? bbox.join('_').replace(/[.\-]/g, function (c) { return c === '-' ? 'm' : 'p'; }) : 'area'); }

  function clampZoom() {
    var lo = Math.max(ZMIN_FLOOR, Math.min(ZMAX_CEIL, parseInt(zmin.value, 10) || 9));
    var hi = Math.max(ZMIN_FLOOR, Math.min(ZMAX_CEIL, parseInt(zmax.value, 10) || 15));
    if (hi < lo) hi = lo;
    if (String(lo) !== zmin.value) zmin.value = lo;
    if (String(hi) !== zmax.value) zmax.value = hi;
    return [lo, hi];
  }

  // ---- refresh dispatch: sat-first live estimate vs legacy single-source command ----
  function refresh() {
    var s = source();
    customWrap.hidden = (s.id !== 'custom');
    if (s.bundle) refreshBundle();
    else refreshLegacy(s);
  }

  // OFFLINE-3 legacy path: client-side estimate + copyable fetch_tiles.py command.
  function refreshLegacy(s) {
    breakdown.textContent = ''; errorEl.hidden = true;
    hint.textContent = 'Safe handoff — runs pipeline/fetch_tiles.py (no fetch logic in the browser).';
    srcNote.textContent = s.note + (s.id === 'custom' ? '' : '  ·  ' + s.url);
    var z = clampZoom();
    if (!bbox) {
      bboxEl.className = 'dl-bbox none'; bboxEl.textContent = 'No area selected — lasso a box or use the current view.';
      est.innerHTML = '<span>Estimate</span><b>—</b>'; cmd.textContent = '# select an area to generate the fetch command';
      copy.disabled = true; return;
    }
    bboxEl.className = 'dl-bbox'; bboxEl.textContent = 'bbox  ' + bbox.join(', ');
    var tiles = tileCount(bbox, z[0], z[1]);
    var mb = tiles * s.kb / 1024;
    var cls = tiles > HARD_TILES ? 'danger' : tiles > SOFT_TILES ? 'warn' : '';
    var note = tiles > HARD_TILES ? ' · too large — tighten zoom/area' : tiles > SOFT_TILES ? ' · large' : '';
    est.innerHTML = '<span>Estimate</span><b class="' + cls + '">~' + human(tiles) + ' tiles · ~' + humanMB(mb) + note + '</b>';
    if (tiles > HARD_TILES) {
      cmd.textContent = '# ' + human(tiles) + ' tiles exceeds the safety cap (' + human(HARD_TILES) + ').\n# Tighten the area or lower max zoom before downloading.';
      copy.disabled = true;
    } else {
      cmd.textContent = fetchCommand(s, bbox, z[0], z[1]); copy.disabled = false;
    }
  }

  function fetchCommand(s, b, lo, hi) {
    return 'python3 pipeline/fetch_tiles.py \\\n' +
      '  --source "' + (s.id === 'custom' ? (customUrl || '{z}/{x}/{y}.png') : s.url) + '" \\\n' +
      '  --bbox "' + b.join(',') + '" \\\n' +
      '  --minzoom ' + lo + ' --maxzoom ' + hi + ' --fmt ' + s.fmt + ' \\\n' +
      '  --out web/data/' + slug() + '.mbtiles \\\n' +
      '  --name "' + s.label + ' ' + b.join(',') + '"';
  }

  // OFFLINE-L-3 path: ask helm-packd for a live sat-first bundle estimate over the lassoed area.
  function refreshBundle() {
    srcNote.textContent = BUNDLE_SOURCE.note;
    hint.textContent = 'Live estimate from helm-packd on :' + basemapPort() + ' · a satellite basemap is required (OFFLINE-L-2 bakes it).';
    var z = clampZoom();
    if (!bbox) {
      bboxEl.className = 'dl-bbox none'; bboxEl.textContent = 'No area selected — lasso a box or use the current view.';
      est.innerHTML = '<span>Estimate</span><b>—</b>'; breakdown.textContent = ''; errorEl.hidden = true;
      cmd.textContent = '# lasso an area to estimate a sat-first offline pack'; copy.disabled = true; lastBundle = null; return;
    }
    bboxEl.className = 'dl-bbox'; bboxEl.textContent = 'bbox  ' + bbox.join(', ');
    var url = packdBase() + '/bundle?profile=sat_first&include_tiles=0' +
      '&bbox=' + encodeURIComponent(bbox.join(',')) + '&minzoom=' + z[0] + '&maxzoom=' + z[1];
    est.innerHTML = '<span>Estimate</span><b>… querying pack server</b>';
    breakdown.textContent = ''; errorEl.hidden = true; copy.disabled = true;
    cmd.textContent = 'GET ' + url;
    var seq = ++bundleSeq;
    if (bundleTimer) clearTimeout(bundleTimer);
    bundleTimer = setTimeout(function () {
      fetch(url, { cache: 'no-store' })
        .then(function (r) { return r.text().then(function (t) { var b = null; try { b = JSON.parse(t); } catch (e) {} return { status: r.status, body: b }; }); })
        .then(function (res) {
          if (seq !== bundleSeq) return;  // a newer request superseded this one
          if (res.status === 200 && res.body) renderBundle(res.body, z);
          else showBundleError(res.body || {}, res.status);
        })
        .catch(function () { if (seq === bundleSeq) showBundleError({ error: 'packd_unreachable' }, 0); });
    }, 220);
  }

  function renderBundle(bundle, z) {
    lastBundle = bundle;
    errorEl.hidden = true;
    var summary = bundle.summary || {};
    var tiles = summary.prefetch_tiles || 0;
    var sizeText = humanBytes(summary.estimated_bytes);
    var cls = tiles > HARD_TILES ? 'danger' : tiles > SOFT_TILES ? 'warn' : '';
    var note = tiles > HARD_TILES ? ' · large — tighten area/zoom' : tiles > SOFT_TILES ? ' · large' : '';
    est.innerHTML = '<span>Estimate</span><b class="' + cls + '">' + (sizeText ? '~' + sizeText : 'size n/a') + ' · ~' + human(tiles) + ' tiles' + note + '</b>';

    breakdown.textContent = '';
    var comps = (bundle.components || []).filter(function (c) { return c.prefetch && (c.prefetch.tile_count || 0) > 0; });
    comps.sort(function (a, b) { return roleRank(a.role) - roleRank(b.role); });
    comps.forEach(function (c) {
      var pf = c.prefetch || {};
      var row = el('div', 'dl-layer' + (c.primary ? ' pri' : ''));
      row.appendChild(el('span', 'dl-layer-k', (c.primary ? '★ ' : '') + roleLabel(c.role) + ' · ' + (c.title || c.pack_id || c.id)));
      row.appendChild(el('span', 'dl-layer-v', '~' + human(pf.tile_count || 0) + ' · ' + (humanBytes(pf.estimated_bytes) || '—')));
      breakdown.appendChild(row);
    });
    if (!comps.length) breakdown.appendChild(el('div', 'dl-layer', summary.estimated_bytes == null ? 'basemap matched, sizes unknown' : 'no tiles in this area'));

    cmd.textContent = bundleCommand(bbox, z);  // real, runnable manifest build; OFFLINE-L-2 bakes tiles
    copy.disabled = false;
  }

  // Fail loud (never a green fake): surface the real reason there is no estimate.
  function showBundleError(body, status) {
    lastBundle = null;
    var code = (body && body.error) || (status === 0 ? 'packd_unreachable' : 'bundle_error');
    est.innerHTML = '<span>Estimate</span><b class="danger">unavailable</b>';
    breakdown.textContent = '';
    errorEl.hidden = false;
    errorEl.setAttribute('data-error-code', code);
    errorEl.textContent = bundleErrorText(code, body);
    copy.disabled = true;
  }

  function bundleErrorText(code, body) {
    if (code === 'missing_basemap') return 'No offline satellite basemap covers this area. Bake a sat pack for this region first (OFFLINE-L-2), then estimate again.';
    if (code === 'chart_not_basemap') return 'Only chart packs cover this area — a satellite basemap is required for a sat-first pack.';
    if (code === 'packd_unreachable') return 'Can’t reach the local pack server on :' + basemapPort() + '. Start helm-packd to estimate an offline pack.';
    return (body && body.message) || ('Bundle estimate failed (' + code + ').');
  }

  function bundleCommand(b, z) {
    return 'python3 pipeline/region_bundle.py \\\n' +
      '  --catalog "' + packdBase() + '/catalog" --profile sat_first \\\n' +
      '  --bbox "' + b.join(',') + '" --minzoom ' + z[0] + ' --maxzoom ' + z[1] + ' \\\n' +
      '  --output web/data/' + slug() + '.bundle.json';
  }

  function roleRank(role) { var r = { basemap: 0, chart: 1, depth: 2, places: 3 }; return r[role] != null ? r[role] : 4; }
  function roleLabel(role) { return ({ basemap: 'satellite', chart: 'chart', depth: 'depth', places: 'places' })[role] || role || 'layer'; }

  // ---- area selection ----
  function setBbox(b) { if (Array.isArray(b) && b.length === 4) { bbox = b.map(function (n) { return +(+n).toFixed(4); }); refresh(); } }
  btnLasso.addEventListener('click', function () {
    var map = window.map;
    import('./integrations/draw.js')
      .then(function (m) { m.lasso(map, { notify: toast }); toast('Drag a rectangle over the area to cache', 'info'); })
      .catch(function (e) { console.error('[offline] draw load failed', e); toast('Could not start area select', 'warn'); });
  });
  btnView.addEventListener('click', function () {
    var map = window.map; if (!map || !map.getBounds) { toast('Map not ready', 'warn'); return; }
    var b = map.getBounds();
    setBbox([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
  });
  window.addEventListener('helm:bbox', function (e) { setBbox(e.detail); });

  // copy
  copy.addEventListener('click', function () {
    var text = cmd.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { toast('Command copied', 'ok'); }, function () { toast('Copy failed', 'warn'); });
    } else { toast('Clipboard unavailable', 'warn'); }
  });

  // input wiring
  sel.addEventListener('change', function () { sourceId = sel.value; refresh(); });
  customWrap.addEventListener('input', function () { customUrl = customWrap.value.trim(); refresh(); });
  zmin.addEventListener('input', refresh); zmax.addEventListener('input', refresh);
  zmin.addEventListener('change', refresh); zmax.addEventListener('change', refresh);

  // a tiny toast (independent of lab.js so this panel stands alone)
  function toast(msg, kind) {
    var host = document.getElementById('helm-toast');
    if (!host) { host = document.createElement('div'); host.id = 'helm-toast';
      host.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);z-index:20;display:flex;flex-direction:column;gap:6px;align-items:center;pointer-events:none';
      document.body.appendChild(host); }
    var colors = { ok: '#46e0a0', warn: '#ffc06a', info: '#5bc0ff' };
    var e = document.createElement('div'); e.textContent = msg;
    e.style.cssText = 'font:12px/1.3 -apple-system,sans-serif;color:#eef4f9;background:rgba(13,19,27,.86);border:.5px solid ' + (colors[kind] || colors.info) + ';border-radius:10px;padding:7px 13px;opacity:0;transition:opacity .25s';
    host.appendChild(e); requestAnimationFrame(function () { e.style.opacity = '1'; });
    setTimeout(function () { e.style.opacity = '0'; setTimeout(function () { e.remove(); }, 300); }, 3600);
  }

  // Test/debug surface — lets e2e drive the drawer without Terra Draw and read the live estimate.
  window.HelmDownloadDrawer = {
    setBbox: setBbox,
    setSource: function (id) { sourceId = id; sel.value = id; refresh(); },
    refresh: refresh,
    packdBase: packdBase,
    els: { estimate: est, breakdown: breakdown, error: errorEl, cmd: cmd, source: sel },
    get state() { return { sourceId: sourceId, bbox: bbox, bundle: lastBundle }; }
  };

  refresh();
  console.info('[offline] download drawer ready (sat-first live estimate + legacy fetch_tiles handoff)');
})();
