// connections.js — the Connections settings UI. Lets the helm enter live-data sources
// (a marine WiFi gateway like the Garmin Vesper Cortex :39150, the PredictWind DataHub,
// or a local NMEA relay) and watch them go live. Talks to the engine over the SAME nav
// WebSocket command-plane (conn.upsert / conn.delete); the ENGINE owns + persists the
// config (~/.helm/connections.json) and streams live per-connection status back in every
// nav frame (s.conns) — so this UI is the reference impl the native clients inherit.
(function () {
  const STATUS = {
    connected:  { label: 'Connected',  color: 'var(--ok)' },
    connecting: { label: 'Connecting', color: 'var(--warn)' },
    nodata:     { label: 'No data',    color: 'var(--warn)' },
    error:      { label: 'Error',      color: 'var(--danger)' },
    disabled:   { label: 'Off',        color: 'var(--cdim)' },
  };
  const TYPES = [
    { v: 'tcp-client', label: 'TCP — connect to device' },
    { v: 'tcp-server', label: 'TCP — listen (relay in)' },
    { v: 'udp',        label: 'UDP — listen' },
  ];
  let client = null, listEl, formEl, msgEl, conns = [], editingId = null, msgTimer = null;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])); }
  function send(obj) { if (!(client && client.send && client.send(obj))) flash('Not connected to the engine.', true); }
  function flash(text, bad) {
    if (!msgEl) return;
    msgEl.textContent = text; msgEl.style.color = bad ? 'var(--danger)' : 'var(--ok)';
    clearTimeout(msgTimer); msgTimer = setTimeout(() => { msgEl.textContent = ''; }, 4500);
  }
  function fmtAge(s) { if (s == null || s < 0) return ''; return s < 90 ? s + 's ago' : Math.round(s / 60) + 'm ago'; }

  function render() {
    if (!listEl) return;
    if (!conns.length) { listEl.innerHTML = '<div class="hint" style="margin:6px 0">No connections yet — add your NMEA/GPS source below.</div>'; return; }
    listEl.innerHTML = '';
    conns.forEach(c => {
      const st = STATUS[c.status] || STATUS.error;
      const live = c.status === 'connected' && c.sentences > 0;
      const row = document.createElement('div'); row.className = 'conn-row';
      row.innerHTML =
        '<div class="conn-dot" style="color:' + st.color + ';background:' + st.color + '"></div>' +
        '<div class="conn-main">' +
          '<div class="conn-name">' + esc(c.name || c.id) + '</div>' +
          '<div class="conn-meta">' + esc(c.type) + ' · ' + esc(c.address || '*') + ':' + c.port +
            ' · <span style="color:' + st.color + '">' + st.label + '</span>' +
            (live ? ' · ' + c.sentences + ' msg · ' + fmtAge(c.ageSec) : '') +
            (c.error && c.status === 'error' ? ' · <span style="color:var(--danger)">' + esc(c.error) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<button class="conn-icon" data-act="edit" title="Edit">✎</button>' +
        '<button class="conn-icon" data-act="del" title="Delete">✕</button>';
      row.querySelector('[data-act="edit"]').addEventListener('click', () => showForm(c));
      row.querySelector('[data-act="del"]').addEventListener('click', () => {
        if (window.confirm('Delete connection "' + (c.name || c.id) + '"?')) send({ t: 'conn.delete', id: c.id });
      });
      listEl.appendChild(row);
    });
  }

  function showForm(c) {
    editingId = c ? c.id : null;
    formEl.hidden = false;
    formEl.querySelector('#conn-form-title').textContent = c ? 'Edit connection' : 'New connection';
    formEl.querySelector('#conn-f-name').value = c ? (c.name || '') : '';
    formEl.querySelector('#conn-f-type').value = c ? c.type : 'tcp-client';
    formEl.querySelector('#conn-f-addr').value = c ? (c.address || '') : '';
    formEl.querySelector('#conn-f-port').value = c ? c.port : '';
    formEl.querySelector('#conn-f-en').checked = c ? c.enabled !== false : true;
    formEl.querySelector('#conn-f-name').focus();
  }
  function hideForm() { formEl.hidden = true; editingId = null; }

  function onSubmit(e) {
    e.preventDefault();
    const conn = {
      name: formEl.querySelector('#conn-f-name').value.trim(),
      type: formEl.querySelector('#conn-f-type').value,
      address: formEl.querySelector('#conn-f-addr').value.trim(),
      port: parseInt(formEl.querySelector('#conn-f-port').value, 10),
      dataProtocol: 'nmea0183',
      enabled: formEl.querySelector('#conn-f-en').checked,
    };
    if (editingId) conn.id = editingId;
    if (!conn.port || conn.port < 1 || conn.port > 65535) { flash('Enter a valid port (1–65535).', true); return; }
    if (conn.type === 'tcp-client' && !conn.address) { flash('Enter the device address (IP or hostname).', true); return; }
    send({ t: 'conn.upsert', conn });
    hideForm();
  }

  function onCommand(msg) {
    if (msg.t === 'conn.ack') flash(msg.ok ? 'Saved ✓' : ('Error: ' + (msg.error || 'rejected')), !msg.ok);
    else if (msg.t === 'conn.list' && Array.isArray(msg.conns)) { conns = msg.conns; render(); }
  }
  function onState(arr) { if (Array.isArray(arr)) { conns = arr; render(); } }

  function init(opts) {
    client = opts && opts.client;
    listEl = document.getElementById('conn-list');
    formEl = document.getElementById('conn-form');
    msgEl  = document.getElementById('conn-msg');
    if (!listEl || !formEl) return;
    formEl.querySelector('#conn-f-type').innerHTML = TYPES.map(t => '<option value="' + t.v + '">' + t.label + '</option>').join('');
    document.getElementById('conn-add-btn').addEventListener('click', () => showForm(null));
    document.getElementById('conn-cancel').addEventListener('click', hideForm);
    formEl.querySelector('#conn-f-type').addEventListener('change', e => {
      const p = formEl.querySelector('#conn-f-port');
      p.placeholder = e.target.value === 'tcp-client' ? '39150' : '10110';
    });
    formEl.addEventListener('submit', onSubmit);
    send({ t: 'conn.list' });   // prime the list (status also rides in every nav frame)
  }

  window.HelmConnections = { init, onState, onCommand };
})();
