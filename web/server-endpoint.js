// HelmEndpoint — resolves the boat-server address ONCE, for every client surface.
//
// The whole "behaves the same whether the engine is on this MacBook or on a Mac mini
// across the cabin" property lives here. There is no "local mode" and no "remote mode" —
// just an address the client resolves. `localhost` is simply one possible value of it.
//
// Resolution order (first hit wins):
//   1. explicit override   ?server=host[:port]   or   localStorage 'helm.server'
//        (dev convenience: when the UI is served separately from the engine)
//   2. the page's own host  (location.hostname)
//        the elegant case — if you OPEN the UI from the engine, you talk to that engine.
//        Load http://localhost  → talk to localhost.   Load http://helm.local → talk to
//        helm.local.   Load http://192.168.1.50 → talk to that.   One code path; the
//        address is an input, never a branch.
//   3. fallback             127.0.0.1
//        file:// or an unknown context — bare dev default.
//
// Transport MIRRORS the page's scheme — never hardcoded: an https page yields wss+https
// (so it satisfies iOS App Transport Security and avoids mixed-content blocking); an http
// page yields ws+http. Serve the UI over https from the boat server and the whole client
// is wss/https with zero extra code. That mirroring is exactly why local and remote are
// the same path: you change how you LOADED the page, not the client.
(function () {
  const DEFAULT_PORT = 8090;          // one origin — WS (/nav) and HTTP tiles (/chart) share it

  function override() {
    try {
      const q = new URLSearchParams(location.search).get('server');
      const ls = (window.localStorage && localStorage.getItem('helm.server')) || null;
      return q || ls || null;
    } catch (e) { return null; }
  }

  function resolve() {
    const ov = override();
    let host, port;
    if (ov) {
      const i = ov.lastIndexOf(':');
      if (i > 0 && /^\d+$/.test(ov.slice(i + 1))) { host = ov.slice(0, i); port = +ov.slice(i + 1); }
      else { host = ov; port = DEFAULT_PORT; }
    } else if (location.protocol.startsWith('http') && location.hostname) {
      host = location.hostname;
      port = location.port ? +location.port : DEFAULT_PORT;
    } else {
      host = '127.0.0.1'; port = DEFAULT_PORT;        // file:// etc.
    }
    const secure = location.protocol === 'https:';     // mirror the page scheme
    return {
      host, port, secure,
      ws: secure ? 'wss' : 'ws',
      http: secure ? 'https' : 'http',
      origin: function () { return this.http + '://' + host + ':' + port; },
      navUrl: function () { return this.ws + '://' + host + ':' + port + '/nav'; },
      tileTemplate: function () { return this.http + '://' + host + ':' + port + '/chart/{z}/{x}/{y}.png'; },
      healthUrl: function () { return this.http + '://' + host + ':' + port + '/health'; },
      describe: function () { return host + ':' + port + (secure ? ' (tls)' : ''); }
    };
  }

  // Resolved once at load. Call HelmEndpoint.refresh() if the override changes at runtime.
  let cur = resolve();
  window.HelmEndpoint = {
    host: () => cur.host,
    port: () => cur.port,
    secure: () => cur.secure,
    navUrl: () => cur.navUrl(),
    tileTemplate: () => cur.tileTemplate(),
    healthUrl: () => cur.healthUrl(),
    origin: () => cur.origin(),
    describe: () => cur.describe(),
    refresh: () => { cur = resolve(); return cur.describe(); }
  };
})();
