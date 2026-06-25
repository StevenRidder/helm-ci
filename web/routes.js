// routes.js — saved-route management UI. Lists the routes the engine persists in OpenCPN's
// navobj.db and lets the helm ACTIVATE or DELETE them over the same nav WebSocket command-plane
// (route.list / route.activate / route.delete). Mirrors connections.js; the engine owns the data.
(function () {
  let client = null, listEl, msgEl, routes = [], msgTimer = null;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])); }
  function send(o) { if (!(client && client.send && client.send(o))) flash('Not connected to the engine.', true); }
  function flash(t, bad) {
    if (!msgEl) return;
    msgEl.textContent = t; msgEl.style.color = bad ? 'var(--danger)' : 'var(--ok)';
    clearTimeout(msgTimer); msgTimer = setTimeout(() => { msgEl.textContent = ''; }, 4500);
  }
  function refresh() { send({ t: 'route.list' }); }

  function render() {
    if (!listEl) return;
    if (!routes.length) { listEl.innerHTML = '<div class="hint" style="margin:6px 0">No saved routes yet — draw one with the route tool, then it appears here.</div>'; return; }
    listEl.innerHTML = '';
    routes.forEach(r => {
      const on = !!r.active;
      const row = document.createElement('div'); row.className = 'conn-row';
      row.innerHTML =
        '<div class="conn-dot" style="color:' + (on ? 'var(--ok)' : 'var(--cdim)') + ';background:' + (on ? 'var(--ok)' : 'var(--cdim)') + '"></div>' +
        '<div class="conn-main">' +
          '<div class="conn-name">' + esc(r.name || 'Route') + (on ? ' <span style="color:var(--ok);font-size:9px;letter-spacing:.04em">ACTIVE</span>' : '') + '</div>' +
          '<div class="conn-meta">' + (r.points || 0) + ' waypoint' + (r.points === 1 ? '' : 's') + '</div>' +
        '</div>' +
        (on ? '' : '<button class="conn-icon" data-act="go" title="Activate (navigate this route)">▸</button>') +
        '<button class="conn-icon" data-act="del" title="Delete route">✕</button>';
      const go = row.querySelector('[data-act="go"]');
      if (go) go.addEventListener('click', () => send({ t: 'route.activate', guid: r.guid }));
      row.querySelector('[data-act="del"]').addEventListener('click', () => {
        if (window.confirm('Delete route "' + (r.name || 'Route') + '"? This removes it from the boat.')) send({ t: 'route.delete', guid: r.guid });
      });
      listEl.appendChild(row);
    });
  }

  function onCommand(msg) {
    if (msg.t === 'route.list' && Array.isArray(msg.routes)) { routes = msg.routes; render(); }
    else if (msg.t === 'route.ack') {
      if (msg.ok === false) flash('Error: ' + (msg.error || 'rejected'), true);
      else { flash(msg.deleted ? 'Route deleted ✓' : (msg.name ? 'Now navigating ' + msg.name + ' ✓' : 'Saved ✓')); refresh(); }
    }
  }
  function init(opts) {
    client = opts && opts.client;
    listEl = document.getElementById('route-list');
    msgEl = document.getElementById('route-msg');
    if (!listEl) return;
    refresh();
  }
  window.HelmRoutes = { init, onCommand, refresh };
})();
