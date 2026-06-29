// OFFLINE-4: local MBTiles/PMTiles pack selector for the MapLibre cockpit.
// Reads the BYO MBTiles helper catalog and activates a selected local pack as
// a dynamic raster layer. User chart files stay outside git and outside this UI.
(function () {
  'use strict';

  var EPIC = 'OFFLINE';
  var PANEL_ID = 'helm-offline-packs';
  var SOURCE_ID = 'helm-offline-active-pack';
  var LAYER_ID = 'helm-offline-active-pack';
  var STORE_KEY = 'offline.activePack';
  var DEFAULT_PORT = '8091';
  var STATIC_BASEMAPS = ['navionics', 'googlesat', 'bingsat', 'arcgis', 'satellite', 'charts'];
  var state = { body: null, map: null, packs: [], activeId: null, loading: false, error: '' };
  var log = (window.HelmLog && HelmLog.scope) ? HelmLog.scope('offline-packs') : console;
  var pmtilesReady = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

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

  function catalogBase() {
    var proto = location.protocol === 'https:' ? 'https:' : 'http:';
    return proto + '//' + endpointHost() + ':' + basemapPort();
  }

  function encodeSegment(s) {
    return encodeURIComponent(String(s == null ? '' : s));
  }

  function tileUrl(pack) {
    return catalogBase() + '/' + encodeSegment(pack.id || pack.name) + '/{z}/{x}/{y}.' + (pack.extension || pack.format || 'png');
  }

  function isPmtilesPack(pack) {
    return !!(pack && (pack.container === 'pmtiles' || pack.pmtiles_url || pack.protocol_url));
  }

  function pmtilesUrl(pack) {
    if (pack.protocol_url) return pack.protocol_url;
    var url = pack.pmtiles_url || pack.url || (catalogBase() + '/' + encodeSegment(pack.id || pack.name) + '.pmtiles');
    return 'pmtiles://' + new URL(url, location.href).href;
  }

  function pmtilesTileUrl(pack) {
    var url = pmtilesUrl(pack);
    if (/\{z\}.*\{x\}.*\{y\}/.test(url)) return url;
    return url.replace(/\/$/, '') + '/{z}/{x}/{y}';
  }

  function pmtilesHandler(protocol) {
    var handler = protocol && (protocol.tile || protocol.tilev4);
    if (typeof handler !== 'function') throw new Error('PMTiles protocol handler unavailable');
    return handler.bind(protocol);
  }

  function ensurePmtilesProtocol() {
    if (window.__helmPmtilesProtocolReady) return window.__helmPmtilesProtocolReady;
    if (pmtilesReady) return pmtilesReady;
    pmtilesReady = import('pmtiles').then(function (mod) {
      var Protocol = mod.Protocol || (mod.default && mod.default.Protocol);
      if (!Protocol) throw new Error('PMTiles Protocol unavailable');
      var protocol = new Protocol();
      if (window.maplibregl && maplibregl.addProtocol) {
        try { maplibregl.addProtocol('pmtiles', pmtilesHandler(protocol)); }
        catch (e) {
          if (!/already|exist|registered/i.test(String((e && e.message) || e))) throw e;
        }
      }
      return protocol;
    });
    window.__helmPmtilesProtocolReady = pmtilesReady;
    return pmtilesReady;
  }

  function fmtBytes(n) {
    n = Number(n || 0);
    if (!n) return '';
    var u = ['B', 'KB', 'MB', 'GB', 'TB'];
    var i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return (i < 2 ? Math.round(n) : n.toFixed(1)) + ' ' + u[i];
  }

  function boundsArray(pack) {
    if (Array.isArray(pack.bounds_array) && pack.bounds_array.length === 4) return pack.bounds_array.map(Number);
    if (typeof pack.bounds === 'string') {
      var b = pack.bounds.split(',').map(function (x) { return Number(x.trim()); });
      if (b.length === 4 && b.every(function (x) { return Number.isFinite(x); })) return b;
    }
    return null;
  }

  function viewStatus(pack) {
    var map = state.map || window.map;
    var b = boundsArray(pack);
    if (!map || !b) return '';
    try {
      var c = map.getCenter();
      var inside = c.lng >= b[0] && c.lng <= b[2] && c.lat >= b[1] && c.lat <= b[3];
      return inside ? 'in view' : 'outside view';
    } catch (e) {
      return '';
    }
  }

  function packLine(pack) {
    var bits = [];
    bits.push((pack.kind || 'raster'));
    if (pack.minzoom != null || pack.maxzoom != null) bits.push('z' + (pack.minzoom || 0) + '-' + (pack.maxzoom || 0));
    if (pack.format) bits.push(String(pack.format).toUpperCase());
    var size = fmtBytes(pack.size_bytes);
    if (size) bits.push(size);
    var vs = viewStatus(pack);
    if (vs) bits.push(vs);
    return bits.join(' | ');
  }

  function hideStaticBasemaps() {
    var map = state.map || window.map;
    if (!map) return;
    STATIC_BASEMAPS.forEach(function (id) {
      try { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none'); } catch (e) {}
    });
    document.querySelectorAll('input[name="basemap"]').forEach(function (rb) { rb.checked = false; });
  }

  function beforeLayerId(map) {
    return map.getLayer('enc-chart') ? 'enc-chart'
      : map.getLayer('depare-fill') ? 'depare-fill'
      : map.getLayer('route-line') ? 'route-line'
      : undefined;
  }

  function removeDynamicLayer() {
    var map = state.map || window.map;
    if (!map) return;
    try { if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID); } catch (e) {}
    try { if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID); } catch (e) {}
  }

  function sourceForPack(pack) {
    var src = {
      type: 'raster',
      tileSize: 256,
      minzoom: Number(pack.minzoom || 0),
      maxzoom: Number(pack.maxzoom || 22),
      attribution: pack.attribution || ''
    };
    if (isPmtilesPack(pack)) src.tiles = [pmtilesTileUrl(pack)];
    else src.tiles = [tileUrl(pack)];
    var b = boundsArray(pack);
    if (b) src.bounds = b;
    return src;
  }

  function installDynamicLayer(pack, attempt) {
    var map = state.map || window.map;
    if (!map || !pack) return;
    if (!(map.getStyle && map.getStyle())) {
      if ((attempt || 0) < 10) setTimeout(function () { installDynamicLayer(pack, (attempt || 0) + 1); }, 100);
      return;
    }
    removeDynamicLayer();
    try {
      map.addSource(SOURCE_ID, sourceForPack(pack));
      map.addLayer({
        id: LAYER_ID,
        type: 'raster',
        source: SOURCE_ID,
        paint: { 'raster-fade-duration': 0, 'raster-opacity': 1 }
      }, beforeLayerId(map));
      applyCurrentThemeTone();
      hideStaticBasemaps();
    } catch (e) {
      state.error = 'Could not load pack: ' + ((e && e.message) || e);
      if (log && log.warn) log.warn(state.error);
    }
  }

  function addDynamicLayer(pack) {
    if (isPmtilesPack(pack)) {
      ensurePmtilesProtocol()
        .then(function () { installDynamicLayer(pack); })
        .catch(function (e) {
          state.error = 'Could not load PMTiles protocol: ' + ((e && e.message) || e);
          if (log && log.warn) log.warn(state.error);
          renderList();
        });
      return;
    }
    installDynamicLayer(pack);
  }

  function applyCurrentThemeTone() {
    var map = state.map || window.map;
    if (!map || !map.getLayer(LAYER_ID)) return;
    var root = document.documentElement;
    var paint = null;
    if (root.classList.contains('theme-night')) {
      paint = { 'raster-brightness-min': 0, 'raster-brightness-max': 0.3, 'raster-saturation': -0.85, 'raster-contrast': -0.05, 'raster-hue-rotate': 0 };
    } else if (root.classList.contains('theme-dusk')) {
      paint = { 'raster-brightness-min': 0, 'raster-brightness-max': 0.6, 'raster-saturation': -0.32, 'raster-contrast': 0.03, 'raster-hue-rotate': 0 };
    }
    if (!paint) return;
    Object.keys(paint).forEach(function (k) {
      try { map.setPaintProperty(LAYER_ID, k, paint[k]); } catch (e) {}
    });
  }

  function activePack() {
    return state.packs.find(function (p) { return String(p.id) === String(state.activeId); }) || null;
  }

  function persistActive(id) {
    state.activeId = id || null;
    try {
      if (window.HelmStore) {
        if (state.activeId) HelmStore.set(STORE_KEY, state.activeId);
        else HelmStore.remove(STORE_KEY);
      }
    } catch (e) {}
  }

  function activate(id, opts) {
    var pack = state.packs.find(function (p) { return String(p.id) === String(id); });
    if (!pack) return;
    persistActive(pack.id);
    addDynamicLayer(pack);
    renderList();
    if (!opts || opts.fit !== false) fitPack(pack);
  }

  function clearActiveFromStaticChoice() {
    persistActive(null);
    removeDynamicLayer();
    renderList();
  }

  function fitPack(pack) {
    var map = state.map || window.map;
    var b = boundsArray(pack || activePack());
    if (!map || !b) return;
    try { map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 72, duration: 450 }); } catch (e) {}
  }

  async function fetchCatalog() {
    state.loading = true;
    state.error = '';
    renderList();
    try {
      var r = await fetch(catalogBase() + '/catalog', { cache: 'no-store' });
      if (!r.ok) throw new Error('catalog ' + r.status);
      var json = await r.json();
      state.packs = Object.keys(json || {}).map(function (id) {
        var p = json[id] || {};
        p.id = p.id || id;
        p.title = p.title || id;
        p.extension = p.extension || (p.format === 'jpeg' ? 'jpg' : (p.format || 'png'));
        return p;
      }).sort(function (a, b) {
        return String(a.title || a.id).localeCompare(String(b.title || b.id));
      });
      if (!state.activeId && window.HelmStore) state.activeId = HelmStore.get(STORE_KEY, null);
      if (state.activeId && state.packs.some(function (p) { return String(p.id) === String(state.activeId); })) {
        addDynamicLayer(activePack());
      }
    } catch (e) {
      state.error = 'No local pack catalog on :' + basemapPort();
      state.packs = [];
      if (log && log.info) log.info('catalog unavailable', e && e.message);
    } finally {
      state.loading = false;
      renderList();
    }
  }

  function rowHtml(pack) {
    var active = String(pack.id) === String(state.activeId);
    var status = viewStatus(pack);
    var warn = status === 'outside view' ? '<span class="helm-pack-warn">outside</span>' : '';
    return [
      '<label class="row helm-pack-row' + (active ? ' is-active' : '') + '">',
      '<input type="radio" name="helm-offline-pack" value="' + esc(pack.id) + '"' + (active ? ' checked' : '') + '>',
      '<span class="helm-pack-main"><b>' + esc(pack.title || pack.id) + '</b><i>' + esc(packLine(pack)) + '</i></span>',
      warn,
      '</label>'
    ].join('');
  }

  function renderList() {
    if (!state.body) return;
    var list = state.body.querySelector('[data-pack-list]');
    var status = state.body.querySelector('[data-pack-status]');
    if (!list || !status) return;
    status.textContent = state.loading ? 'Scanning :' + basemapPort() : (state.error || (state.packs.length + ' local pack' + (state.packs.length === 1 ? '' : 's')));
    if (!state.packs.length) {
      list.innerHTML = '<div class="helm-pack-empty">No local packs are visible.</div>';
      return;
    }
    list.innerHTML = state.packs.map(rowHtml).join('');
  }

  function renderPanel(body, ctx) {
    state.body = body;
    state.map = ctx && ctx.map;
    installStyle();
    body.insertAdjacentHTML('beforeend', [
      '<p class="sub">Local chart and basemap packs</p>',
      '<div class="helm-pack-actions">',
      '<button class="conn-btn" type="button" data-pack-refresh>Refresh</button>',
      '<button class="conn-btn" type="button" data-pack-fit>Fit</button>',
      '<span data-pack-status class="helm-pack-status">Scanning</span>',
      '</div>',
      '<div data-pack-list class="helm-pack-list"></div>'
    ].join(''));
    body.addEventListener('change', function (e) {
      var t = e.target;
      if (t && t.name === 'helm-offline-pack' && t.checked) activate(t.value);
    });
    body.addEventListener('click', function (e) {
      var refresh = e.target && e.target.closest && e.target.closest('[data-pack-refresh]');
      var fit = e.target && e.target.closest && e.target.closest('[data-pack-fit]');
      if (refresh) fetchCatalog();
      if (fit) fitPack();
    });
    var map = state.map;
    if (map && map.on) {
      map.on('moveend', renderList);
      map.on('styledata', function () {
        if (state.activeId && !map.getLayer(LAYER_ID)) addDynamicLayer(activePack());
      });
    }
    fetchCatalog();
  }

  function installStyle() {
    if (document.getElementById('helm-offline-packs-style')) return;
    var style = document.createElement('style');
    style.id = 'helm-offline-packs-style';
    style.textContent = [
      '.helm-pack-actions{display:flex;align-items:center;gap:8px;margin:8px 0 10px}',
      '.helm-pack-status{margin-left:auto;font-size:10px;color:var(--cdim2)}',
      '.helm-pack-list{display:flex;flex-direction:column;gap:6px}',
      '.helm-pack-row{gap:9px;min-height:48px}',
      '.helm-pack-row input{flex:none}',
      '.helm-pack-row.is-active{outline:1px solid rgba(91,192,255,.45);background:rgba(91,192,255,.09)}',
      '.helm-pack-main{display:flex;flex-direction:column;gap:2px;min-width:0}',
      '.helm-pack-main b{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.helm-pack-main i{font-size:10px;color:var(--cdim2);font-style:normal;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.helm-pack-warn{margin-left:auto;font-size:9.5px;color:var(--warn)}',
      '.helm-pack-empty{font-size:11px;color:var(--cdim);padding:10px 0}'
    ].join('\n');
    document.head.appendChild(style);
  }

  function bindStaticBasemapFallback() {
    document.addEventListener('change', function (e) {
      var t = e.target;
      if (t && t.name === 'basemap' && t.checked) clearActiveFromStaticChoice();
    }, true);
  }

  function register() {
    if (!(window.HelmShell && HelmShell.registerPanel)) return;
    HelmShell.registerPanel({
      id: PANEL_ID,
      epic: EPIC,
      title: 'Chart Packs',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"><path d="M4 6h16v12H4z"/><path d="M8 6v12"/><path d="M16 6v12"/><path d="M4 10h16"/><path d="M4 14h16"/></svg>',
      render: renderPanel,
      onOpen: function () { renderList(); }
    });
    if (HelmShell.registerCommand) {
      HelmShell.registerCommand({
        id: 'helm-offline-open-packs',
        epic: EPIC,
        title: 'Open chart packs',
        subtitle: 'Local MBTiles and PMTiles',
        keywords: ['offline', 'mbtiles', 'pmtiles', 'charts', 'basemap'],
        group: 'Layers',
        run: function () { var h = HelmShell.panel(PANEL_ID); if (h) h.open(); }
      });
    }
  }

  bindStaticBasemapFallback();
  register();
  window.HelmOfflinePacks = {
    refresh: fetchCatalog,
    activate: activate,
    fit: fitPack,
    state: state
  };
})();
