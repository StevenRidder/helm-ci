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
    { v: 'signalk',    label: 'SignalK — WebSocket' },
  ];
  let client = null, listEl, formEl, msgEl, conns = [], editingId = null, msgTimer = null;
  // CONN-7 raw-NMEA monitor: subscribe nmea.monitor{on} → engine streams nmea.raw{lines:[{conn,ts,line}]}.
  let monBtn = null, monEl = null, monBodyEl = null, monLines = [], monitorOn = false;
  const MON_CAP = 250;   // ring-buffer the most recent N sentences

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])); }
  function send(obj) { if (!(client && client.send && client.send(obj))) flash('Not connected to the engine.', true); }
  function flash(text, bad) {
    if (!msgEl) return;
    msgEl.textContent = text; msgEl.style.color = bad ? 'var(--danger)' : 'var(--ok)';
    clearTimeout(msgTimer); msgTimer = setTimeout(() => { msgEl.textContent = ''; }, 4500);
  }
  function fmtAge(s) { if (s == null || s < 0) return ''; return s < 90 ? s + 's ago' : Math.round(s / 60) + 'm ago'; }

  // ---- CONN-7 raw-NMEA monitor ----
  function monTime(ts) { try { return new Date((ts || 0) * 1000).toTimeString().slice(0, 8); } catch (e) { return ''; } }
  function monUi() {
    if (monEl) monEl.hidden = !monitorOn;
    if (monBtn) monBtn.textContent = (monitorOn ? '▾ NMEA monitor (live)' : '▸ NMEA monitor');
  }
  function renderMon() {
    if (!monBodyEl) return;
    if (!monLines.length) { monBodyEl.innerHTML = '<div class="hint" style="margin:2px 0">Waiting for sentences… (none captured yet)</div>'; return; }
    monBodyEl.innerHTML = monLines.map(l =>
      '<div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' +
        '<span style="color:var(--cdim)">' + monTime(l.ts) + '</span> ' +
        '<span style="color:#7fd1ff">' + esc(l.conn) + '</span> ' + esc(l.line) +
      '</div>').join('');
    monBodyEl.scrollTop = monBodyEl.scrollHeight;   // follow the tail
  }
  function appendRaw(lines) {
    for (const l of lines) if (l && typeof l.line === 'string') monLines.push({ conn: l.conn, ts: l.ts, line: l.line });
    if (monLines.length > MON_CAP) monLines.splice(0, monLines.length - MON_CAP);
    if (monitorOn) renderMon();
  }
  function toggleMonitor() { monitorOn = !monitorOn; monUi(); if (monitorOn) renderMon(); send({ t: 'nmea.monitor', on: monitorOn }); }

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
            ' · prio ' + (c.priority || 0) +
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
    const prioEl = formEl.querySelector('#conn-f-prio'); if (prioEl) prioEl.value = c ? (c.priority || 0) : '';
    formEl.querySelector('#conn-f-en').checked = c ? c.enabled !== false : true;
    formEl.querySelector('#conn-f-name').focus();
  }
  function hideForm() { formEl.hidden = true; editingId = null; }

  function onSubmit(e) {
    e.preventDefault();
    const type = formEl.querySelector('#conn-f-type').value;
    const conn = {
      name: formEl.querySelector('#conn-f-name').value.trim(),
      type,
      address: formEl.querySelector('#conn-f-addr').value.trim(),
      port: parseInt(formEl.querySelector('#conn-f-port').value, 10),
      dataProtocol: type === 'signalk' ? 'signalk' : 'nmea0183',
      priority: parseInt((formEl.querySelector('#conn-f-prio') || {}).value, 10) || 0,   // CONN-6: higher wins; lower fills in on failover
      enabled: formEl.querySelector('#conn-f-en').checked,
    };
    if (editingId) conn.id = editingId;
    if (!conn.port || conn.port < 1 || conn.port > 65535) { flash('Enter a valid port (1–65535).', true); return; }
    // tcp-client and signalk both need a target address (engine rejects either without one)
    if ((type === 'tcp-client' || type === 'signalk') && !conn.address) {
      flash(type === 'signalk' ? 'Enter the SignalK host (or ws:// URL).' : 'Enter the device address (IP or hostname).', true); return;
    }
    send({ t: 'conn.upsert', conn });
    hideForm();
  }

  function onCommand(msg) {
    if (msg.t === 'conn.ack') flash(msg.ok ? 'Saved ✓' : ('Error: ' + (msg.error || 'rejected')), !msg.ok);
    else if (msg.t === 'conn.list' && Array.isArray(msg.conns)) { conns = msg.conns; render(); }
    else if (msg.t === 'nmea.monitor.ack') { monitorOn = !!msg.on; monUi(); }              // CONN-7: subscribe confirmation
    else if (msg.t === 'nmea.raw' && Array.isArray(msg.lines)) appendRaw(msg.lines);        // CONN-7: raw sentence batch
  }
  function onState(arr) { if (Array.isArray(arr)) { conns = arr; render(); } }

  function init(opts) {
    client = opts && opts.client;
    listEl = document.getElementById('conn-list');
    formEl = document.getElementById('conn-form');
    msgEl  = document.getElementById('conn-msg');
    if (!listEl || !formEl) return;
    formEl.querySelector('#conn-f-type').innerHTML = TYPES.map(t => '<option value="' + t.v + '">' + t.label + '</option>').join('');
    // CONN-6: inject a Priority field into the form (kept in connections.js — CONN's lane, no shell edit).
    // Engine merge (helm_server.cpp): a fresh higher-priority source wins; a lower-priority one fills a
    // field only when the current holder goes stale (failover), and the primary reclaims when it returns.
    (function () {
      const portEl = formEl.querySelector('#conn-f-port');
      const portFld = portEl && portEl.closest('.conn-fld');
      if (portFld && !formEl.querySelector('#conn-f-prio')) {
        const lab = document.createElement('label');
        lab.className = 'conn-fld';
        lab.innerHTML = 'Priority <span style="color:var(--cdim);font-size:11px">(higher wins; lower fills in on failover)</span>' +
                        '<input id="conn-f-prio" type="number" min="0" max="100" step="1" placeholder="0">';
        portFld.insertAdjacentElement('afterend', lab);
      }
    })();
    document.getElementById('conn-add-btn').addEventListener('click', () => showForm(null));
    document.getElementById('conn-cancel').addEventListener('click', hideForm);
    formEl.querySelector('#conn-f-type').addEventListener('change', e => {
      const p = formEl.querySelector('#conn-f-port');
      p.placeholder = e.target.value === 'tcp-client' ? '39150' : e.target.value === 'signalk' ? '3000' : '10110';
    });
    formEl.addEventListener('submit', onSubmit);
    // CONN-7: inject a raw-NMEA monitor below the connection list (kept in connections.js — CONN's
    // lane, no shell edit). Toggling it sends nmea.monitor{on}; engine streams nmea.raw while on.
    if (msgEl && !document.getElementById('conn-mon-btn')) {
      const wrap = document.createElement('div'); wrap.style.marginTop = '10px';
      monBtn = document.createElement('button');
      monBtn.id = 'conn-mon-btn'; monBtn.type = 'button'; monBtn.className = 'conn-btn'; monBtn.textContent = '▸ NMEA monitor';
      monEl = document.createElement('div'); monEl.id = 'conn-mon'; monEl.hidden = true; monEl.style.marginTop = '8px';
      const head = document.createElement('div');
      head.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px';
      head.innerHTML = '<span class="hint" style="margin:0">Raw sentences from every source (debug)</span>';
      const clr = document.createElement('button');
      clr.type = 'button'; clr.className = 'conn-icon'; clr.textContent = 'Clear';
      clr.style.cssText = 'width:auto;padding:0 8px';
      clr.addEventListener('click', () => { monLines = []; renderMon(); });
      head.appendChild(clr);
      monBodyEl = document.createElement('div'); monBodyEl.id = 'conn-mon-body';
      monBodyEl.style.cssText = 'font-family:ui-monospace,Menlo,monospace;font-size:10.5px;line-height:1.5;max-height:160px;overflow:auto;background:rgba(0,0,0,.25);border:.5px solid var(--line);border-radius:8px;padding:6px';
      monEl.appendChild(head); monEl.appendChild(monBodyEl);
      monBtn.addEventListener('click', toggleMonitor);
      wrap.appendChild(monBtn); wrap.appendChild(monEl);
      msgEl.insertAdjacentElement('afterend', wrap);
    }
    send({ t: 'conn.list' });   // prime the list (status also rides in every nav frame)
  }

  window.HelmConnections = { init, onState, onCommand };
})();
