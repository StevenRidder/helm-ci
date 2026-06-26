// service-credentials.js — device-local API-key registry for customer-owned services.
//
// This is intentionally small and boring: providers live behind one client-side seam so layers
// do not learn where keys are stored. The prototype persists secrets in HelmStore/localStorage,
// which is acceptable for local testing but not a final security boundary. Native clients should
// back this same API with the OS keychain or the boat server's encrypted credential store.
(function () {
  'use strict';

  var STORE_KEY = 'services.weather.openmeteo.v1';
  var FREE = {
    forecast: 'https://api.open-meteo.com/v1/forecast',
    marine: 'https://marine-api.open-meteo.com/v1/marine'
  };
  var CUSTOMER = {
    forecast: 'https://customer-api.open-meteo.com/v1/forecast',
    marine: 'https://customer-api.open-meteo.com/v1/marine'
  };
  var DEFAULT = {
    provider: 'openmeteo',
    mode: 'free',
    apiKey: '',
    updatedAt: null,
    testedAt: null,
    lastOk: false,
    lastError: ''
  };

  function store() { return window.HelmStore || null; }
  function clone(obj) {
    var out = {};
    Object.keys(obj || {}).forEach(function (k) { out[k] = obj[k]; });
    return out;
  }
  function canonicalKind(kind) { return kind === 'marine' ? 'marine' : 'forecast'; }
  function clean(raw) {
    raw = raw || {};
    var mode = raw.mode === 'customer' ? 'customer' : 'free';
    var apiKey = typeof raw.apiKey === 'string' ? raw.apiKey.trim() : '';
    if (mode !== 'customer') apiKey = '';
    return {
      provider: 'openmeteo',
      mode: mode,
      apiKey: apiKey,
      updatedAt: raw.updatedAt || null,
      testedAt: raw.testedAt || null,
      lastOk: raw.lastOk === true,
      lastError: typeof raw.lastError === 'string' ? raw.lastError : ''
    };
  }
  function read() {
    var s = store();
    return clean(s ? s.get(STORE_KEY, DEFAULT) : DEFAULT);
  }
  function write(next) {
    var s = store();
    if (!s) return false;
    return s.set(STORE_KEY, clean(next));
  }
  function dispatch(config) {
    try {
      window.dispatchEvent(new CustomEvent('helm-services-changed', {
        detail: { service: 'weather.openmeteo', config: publicWeatherProvider(config) }
      }));
    } catch (_) {}
  }

  function maskKey(key) {
    key = String(key || '').trim();
    if (!key) return '';
    if (key.length <= 7) return '••••' + key.slice(-2);
    return key.slice(0, 4) + '…' + key.slice(-3);
  }
  function label(config) {
    config = clean(config || read());
    return config.mode === 'customer' ? 'Open-Meteo Customer API' : 'Open-Meteo Free';
  }
  function endpoint(kind, config) {
    config = clean(config || read());
    var table = config.mode === 'customer' ? CUSTOMER : FREE;
    return table[canonicalKind(kind)];
  }
  function providerScope(config) {
    config = clean(config || read());
    return config.mode === 'customer' ? 'openmeteo:customer' : 'openmeteo:free';
  }
  function publicWeatherProvider(config) {
    config = clean(config || read());
    return {
      provider: 'openmeteo',
      mode: config.mode,
      label: label(config),
      hasApiKey: !!config.apiKey,
      apiKeyMask: maskKey(config.apiKey),
      scope: providerScope(config),
      endpoints: {
        forecast: endpoint('forecast', config),
        marine: endpoint('marine', config)
      },
      updatedAt: config.updatedAt || null,
      testedAt: config.testedAt || null,
      lastOk: config.lastOk === true,
      lastError: config.lastError || ''
    };
  }
  function appendAuth(rawUrl, config) {
    config = clean(config || read());
    if (config.mode !== 'customer' || !config.apiKey) return rawUrl;
    return rawUrl + (rawUrl.indexOf('?') === -1 ? '?' : '&') + 'apikey=' + encodeURIComponent(config.apiKey);
  }
  function scrubUrl(rawUrl) {
    return String(rawUrl || '').replace(/([?&]apikey=)[^&]+/i, '$1••••');
  }
  function weatherRequestUrl(kind, query, config) {
    var base = endpoint(kind, config);
    return appendAuth(base + (query ? '?' + query : ''), config);
  }
  function setWeatherProvider(input) {
    var current = read();
    var next = clean(Object.assign({}, current, input || {}, {
      updatedAt: new Date().toISOString(),
      lastError: '',
      lastOk: false
    }));
    if (next.mode === 'customer' && !next.apiKey) {
      return { ok: false, error: 'Enter an Open-Meteo Customer API key.' };
    }
    if (!write(next)) return { ok: false, error: 'Could not save service settings on this device.' };
    dispatch(next);
    return { ok: true, config: publicWeatherProvider(next) };
  }
  function clearWeatherProvider() {
    var s = store(), ok = false;
    if (s) ok = s.remove(STORE_KEY);
    dispatch(DEFAULT);
    return { ok: ok, config: publicWeatherProvider(DEFAULT) };
  }
  function updateTestResult(ok, message) {
    var next = read();
    next.testedAt = new Date().toISOString();
    next.lastOk = !!ok;
    next.lastError = ok ? '' : String(message || 'Connection test failed');
    write(next);
    dispatch(next);
    return publicWeatherProvider(next);
  }
  async function testWeatherProvider() {
    var u = weatherRequestUrl('forecast', 'latitude=0&longitude=0&current=temperature_2m&forecast_days=1');
    try {
      var fn = typeof window.__helmServicesTestFetch === 'function' ? window.__helmServicesTestFetch : window.fetch.bind(window);
      var r = await fn(u, { method: 'GET' });
      if (r && r.ok === false) throw new Error('HTTP ' + r.status);
      if (r && typeof r.json === 'function') await r.json();
      return { ok: true, url: scrubUrl(u), config: updateTestResult(true, '') };
    } catch (e) {
      var msg = e && e.message ? e.message : 'Connection test failed';
      return { ok: false, error: msg, url: scrubUrl(u), config: updateTestResult(false, msg) };
    }
  }

  window.HelmServices = {
    weatherProvider: function () { return clone(read()); },
    publicWeatherProvider: publicWeatherProvider,
    setWeatherProvider: setWeatherProvider,
    clearWeatherProvider: clearWeatherProvider,
    weatherEndpoint: endpoint,
    weatherRequestUrl: weatherRequestUrl,
    withOpenMeteoAuth: appendAuth,
    providerScope: providerScope,
    providerLabel: label,
    scrubUrl: scrubUrl,
    testWeatherProvider: testWeatherProvider,
    _storeKey: STORE_KEY
  };
})();
