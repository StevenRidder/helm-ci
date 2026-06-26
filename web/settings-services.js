// settings-services.js — Settings → Connected services.
//
// Keeps API credentials in the Settings rail, alongside live-data connections, while exposing only
// provider-level state to feature modules. Weather is first; the same pattern is ready for AIS,
// satellite imagery, routing, or paid forecast providers.
(function () {
  'use strict';

  var els = {}, booted = false, focusTimer = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m];
    });
  }
  function services() { return window.HelmServices || null; }
  function provider(candidate) {
    var S = services();
    return S ? S.publicWeatherProvider(candidate) : {
      mode: 'free', label: 'Open-Meteo Free', hasApiKey: false, apiKeyMask: '',
      endpoints: { forecast: 'https://api.open-meteo.com/v1/forecast', marine: 'https://marine-api.open-meteo.com/v1/marine' }
    };
  }
  function flash(text, bad) {
    if (!els.msg) return;
    els.msg.textContent = text || '';
    els.msg.style.color = bad ? 'var(--danger)' : 'var(--ok)';
  }
  function hintFor(p) {
    var forecast = p.endpoints && p.endpoints.forecast ? p.endpoints.forecast : '';
    var marine = p.endpoints && p.endpoints.marine ? p.endpoints.marine : '';
    if (p.mode === 'customer') {
      return 'Uses the paid customer endpoint and appends your API key to Open-Meteo requests. Forecast: ' +
        esc(forecast) + ' · Marine: ' + esc(marine);
    }
    return 'Uses Open-Meteo Free — no key, rate-limited, good for non-commercial prototype use. Forecast: ' +
      esc(forecast) + ' · Marine: ' + esc(marine);
  }
  function paint(candidate) {
    var p = provider(candidate);
    if (els.mode) els.mode.value = p.mode === 'customer' ? 'customer' : 'free';
    if (els.keyRow) els.keyRow.hidden = p.mode !== 'customer';
    if (els.key) {
      els.key.value = '';
      els.key.placeholder = p.hasApiKey ? ('Saved key ' + p.apiKeyMask + ' — leave blank to keep') : 'Paste Open-Meteo API key';
    }
    if (els.meta) {
      var bits = [p.label];
      bits.push(p.mode === 'customer' ? (p.hasApiKey ? 'key saved ' + p.apiKeyMask : 'needs key') : 'no key required');
      if (p.testedAt) bits.push(p.lastOk ? 'tested OK' : 'test failed');
      els.meta.textContent = bits.join(' · ');
    }
    if (els.hint) els.hint.innerHTML = hintFor(p);
    if (els.clear) els.clear.disabled = !(p.mode === 'customer' && p.hasApiKey);
  }
  function saveFromForm() {
    var S = services();
    if (!S) return { ok: false, error: 'Service registry is not loaded.' };
    var current = S.weatherProvider();
    var mode = els.mode && els.mode.value === 'customer' ? 'customer' : 'free';
    var typedKey = els.key ? els.key.value.trim() : '';
    var apiKey = mode === 'customer' ? (typedKey || current.apiKey || '') : '';
    var res = S.setWeatherProvider({ mode: mode, apiKey: apiKey });
    if (res.ok) paint();
    return res;
  }
  async function onTest() {
    flash('Testing Open-Meteo connection…', false);
    var saved = saveFromForm();
    if (!saved.ok) { flash(saved.error, true); return; }
    try {
      var res = await services().testWeatherProvider();
      paint();
      flash(res.ok ? 'Open-Meteo test OK ✓' : ('Open-Meteo test failed: ' + res.error), !res.ok);
    } catch (e) {
      flash('Open-Meteo test failed: ' + (e && e.message ? e.message : e), true);
    }
  }
  function onSave(e) {
    if (e) e.preventDefault();
    var res = saveFromForm();
    flash(res.ok ? 'Weather provider saved ✓' : res.error, !res.ok);
  }
  function onClear() {
    var S = services(); if (!S) return;
    S.clearWeatherProvider();
    paint();
    flash('Weather provider reset to Open-Meteo Free.', false);
  }
  function focusWeather() {
    if (!els.root) return;
    try { els.root.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (_) { els.root.scrollIntoView(); }
    els.root.style.boxShadow = '0 0 0 1px var(--accent), 0 0 22px rgba(57,194,201,.22)';
    clearTimeout(focusTimer);
    focusTimer = setTimeout(function () { if (els.root) els.root.style.boxShadow = ''; }, 1700);
    if (els.mode) els.mode.focus();
  }
  function build(drawer) {
    if (!drawer || document.getElementById('svc-settings')) return;
    var root = document.createElement('div');
    root.id = 'svc-settings';
    root.dataset.testid = 'connected-services';
    root.style.cssText = 'margin-top:14px;border-top:.5px solid var(--line);padding-top:2px;border-radius:12px;transition:box-shadow .18s ease';
    root.innerHTML =
      '<div class="lbl">Connected services — API keys</div>' +
      '<div class="conn-row" style="align-items:flex-start">' +
        '<div class="conn-dot" style="margin-top:4px;color:var(--accent);background:var(--accent)"></div>' +
        '<div class="conn-main">' +
          '<div class="conn-name">Weather provider</div>' +
          '<div class="conn-meta" id="svc-weather-meta"></div>' +
        '</div>' +
      '</div>' +
      '<form id="svc-weather-form" class="conn-form" data-testid="weather-provider-form">' +
        '<div class="conn-form-title">Open-Meteo</div>' +
        '<label class="conn-fld">Provider' +
          '<select id="svc-weather-mode" data-testid="weather-provider-mode">' +
            '<option value="free">Open-Meteo Free — no key</option>' +
            '<option value="customer">Open-Meteo Customer API — paid key</option>' +
          '</select>' +
        '</label>' +
        '<label class="conn-fld" id="svc-weather-key-row">API key' +
          '<input id="svc-weather-key" data-testid="weather-api-key" type="password" autocomplete="off" spellcheck="false">' +
        '</label>' +
        '<div id="svc-weather-hint" class="hint" style="margin:0;padding-top:8px"></div>' +
        '<div class="conn-actions">' +
          '<button type="submit" class="conn-btn primary" data-testid="weather-provider-save">Save</button>' +
          '<button type="button" id="svc-weather-test" class="conn-btn" data-testid="weather-provider-test">Test</button>' +
          '<button type="button" id="svc-weather-clear" class="conn-btn" data-testid="weather-provider-clear">Clear</button>' +
        '</div>' +
        '<div id="svc-weather-msg" class="conn-msg"></div>' +
      '</form>' +
      '<div class="hint">Only paste API keys/tokens here — never service account passwords. Prototype storage is device-local; the native app should back this same seam with Keychain or the boat server credential vault.</div>';

    var anchor = document.getElementById('conn-msg');
    if (anchor && anchor.parentNode === drawer) anchor.insertAdjacentElement('afterend', root);
    else {
      var units = Array.prototype.find.call(drawer.querySelectorAll('.lbl'), function (n) { return n.textContent === 'Units'; });
      if (units && units.parentNode) units.insertAdjacentElement('beforebegin', root);
      else drawer.appendChild(root);
    }

    els.root = root;
    els.meta = root.querySelector('#svc-weather-meta');
    els.form = root.querySelector('#svc-weather-form');
    els.mode = root.querySelector('#svc-weather-mode');
    els.keyRow = root.querySelector('#svc-weather-key-row');
    els.key = root.querySelector('#svc-weather-key');
    els.hint = root.querySelector('#svc-weather-hint');
    els.test = root.querySelector('#svc-weather-test');
    els.clear = root.querySelector('#svc-weather-clear');
    els.msg = root.querySelector('#svc-weather-msg');

    els.form.addEventListener('submit', onSave);
    els.mode.addEventListener('change', function () {
      var S = services(), current = S ? S.weatherProvider() : {};
      paint({ mode: els.mode.value, apiKey: els.mode.value === 'customer' ? (current.apiKey || '') : '' });
      flash('', false);
    });
    els.test.addEventListener('click', onTest);
    els.clear.addEventListener('click', onClear);
    window.addEventListener('helm-services-changed', function () { paint(); });
    paint();
  }
  function boot() {
    if (booted) return;
    var drawer = document.getElementById('drawer-settings');
    if (!drawer || !services()) return setTimeout(boot, 250);
    booted = true;
    build(drawer);
  }

  window.HelmServiceSettings = { init: boot, focusWeather: focusWeather, render: paint };
  if (document.readyState === 'complete' || document.readyState === 'interactive') setTimeout(boot, 50);
  else window.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 50); });
})();
