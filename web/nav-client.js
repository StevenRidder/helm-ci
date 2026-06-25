// HelmNavClient — the robust live-nav client. ONE code path, local or remote.
//
// Connects to HelmEndpoint.navUrl() (see server-endpoint.js) and feeds the cockpit the
// SAME flat state shape the in-browser sim (nav-source.js / HelmNav) emits — so the UI
// rendering code is identical for real, simulated, local, and remote nav.
//
// What makes it world-class over flaky boat WiFi:
//   • snapshot + delta   — first frame is a full snapshot; later frames carry only what
//     changed (merged here). Legacy full frames (no `t`) are also accepted, so this client
//     works against the current engine unchanged.
//   • AGE WATCHDOG       — staleness is judged by how long since the last frame, NOT by
//     socket state. A half-open WiFi socket reports "open" while no data arrives; we treat
//     LIVE(<3s) / LAGGING(3–10s) / STALE(>10s) purely on frame age. This is the safety rule.
//   • reconnect+resume   — exponential backoff with jitter; on reconnect we send lastSeq so
//     the server can snapshot us immediately.
//   • never fakes position — if a real feed drops we go STALE/OFFLINE and say so; we never
//     silently swap in the simulator presenting a plausible fake fix. The sim is used ONLY
//     when no engine was ever reached (honest prototype mode).
//
// onState(flatState)   — called with the merged, UI-shaped state on every frame.
// onStatus({phase,...})— called whenever the connection phase changes. phase ∈
//     connecting | live | simpos | lagging | stale | offline | sim
(function () {
  function mergeState(base, patch) {
    const out = base ? JSON.parse(JSON.stringify(base)) : {};
    for (const k in patch) {
      const v = patch[k];
      if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object' && !Array.isArray(out[k])) {
        out[k] = Object.assign({}, out[k], v);     // one-level deep (wind, active, sources)
      } else {
        out[k] = v;
      }
    }
    return out;
  }
  const realPos = s => {
    const p = (s && s.sources && s.sources.pos) || (s && s.posSource);
    return !!p && p !== 'simulated' && p !== 'sim';
  };

  window.HelmNavClient = function (onState, onStatus, opts) {
    opts = opts || {};
    const LIVE_MS = 3000, STALE_MS = 10000;        // age thresholds
    const BACKOFF_CAP = 8000, BACKOFF_BASE = 400;  // reconnect schedule
    const status = (phase, extra) => {
      const ep = window.HelmEndpoint ? HelmEndpoint.describe() : '(unresolved)';
      try { onStatus && onStatus(Object.assign({ phase, endpoint: ep }, extra)); }
      catch (e) { console.error('HelmNavClient: onStatus handler threw:', e); }   // surface, don't swallow
    };

    let state = null;          // last merged full state
    let lastSeq = 0;
    let lastFrameAt = 0;       // ms of last frame (Date.now)
    let everEngine = false;    // did we ever receive an engine frame?
    let ws = null, attempt = 0, reconnectTimer = null, watchdog = null, closed = false;
    let sim = null;            // sim interval id, if running
    const startSim = () => { if (opts.sim && !sim && !everEngine) { sim = opts.sim(onState); status('sim'); } };
    const stopSim = () => { if (sim) { clearInterval(sim); sim = null; } };

    function classify() {
      if (!everEngine) return;                     // sim/connecting phases are driven elsewhere
      const age = Date.now() - lastFrameAt;
      if (age < LIVE_MS) status(realPos(state) ? 'live' : 'simpos', { age, seq: lastSeq });
      else if (age < STALE_MS) status('lagging', { age, seq: lastSeq });
      else status('stale', { age, seq: lastSeq });
    }

    function onFrame(msg) {
      if (msg.t === 'ping') { lastFrameAt = Date.now(); return; }   // heartbeat keeps us LIVE
      if (msg.t === 'alarm') { status('alarm', { alarm: msg }); return; }
      if (typeof msg.t === 'string' && (msg.t.indexOf('conn.') === 0 || msg.t.indexOf('route.') === 0 || msg.t.indexOf('track.') === 0)) {
        try { opts.onCommand && opts.onCommand(msg); } catch (e) { console.error('HelmNavClient: onCommand handler threw:', e); }   // command-plane replies
        return;   // not nav state — do not merge or reset the staleness watchdog
      }
      everEngine = true; attempt = 0; stopSim();
      lastFrameAt = Date.now();
      if (typeof msg.seq === 'number') lastSeq = msg.seq;
      // snapshot replaces; delta merges; a legacy full frame (no t) replaces.
      if (msg.t === 'delta') {
        if (!state) {                          // no baseline yet — refuse the partial, surface it, await a snapshot
          console.warn('HelmNavClient: delta seq ' + msg.seq + ' arrived before any snapshot — awaiting baseline (server should send snapshot first)');
          classify(); return;
        }
        state = mergeState(state, msg);
      } else {
        state = mergeState(msg.t === 'snapshot' ? {} : state, msg);
      }
      try { onState(state); } catch (e) { console.error('HelmNavClient: onState handler threw:', e); }   // surface, don't swallow
      classify();
    }

    function connect() {
      if (closed) return;
      if (!window.HelmEndpoint) {
        // Hard wiring error: server-endpoint.js didn't load. Do NOT fabricate a localhost URL
        // and pretend — surface it loudly and stop (reconnecting can't fix a missing module).
        console.error('HelmNavClient: HelmEndpoint missing (server-endpoint.js not loaded). Cannot resolve the engine; not connecting.');
        status('offline', { error: 'no-endpoint' });
        return;
      }
      status('connecting');
      const url = HelmEndpoint.navUrl();
      try { ws = new WebSocket(url); }
      catch (e) { console.error('HelmNavClient: WebSocket(' + url + ') failed to construct:', e && e.message); scheduleReconnect(); return; }

      ws.onopen = () => {
        try { ws.send(JSON.stringify({ t: 'hello', lastSeq, subscribe: opts.subscribe || ['nav', 'route', 'alarms'] })); }
        catch (e) { console.warn('HelmNavClient: hello send failed:', e && e.message); }
      };
      ws.onmessage = e => {
        let m; try { m = JSON.parse(e.data); }
        catch (x) { console.error('HelmNavClient: dropping unparseable frame from engine:', x && x.message); return; }
        onFrame(m);
      };
      ws.onerror = () => { /* close handler drives reconnect / sim */ };
      ws.onclose = () => {
        ws = null;
        if (closed) return;
        if (everEngine) { status('offline', { seq: lastSeq }); scheduleReconnect(); }   // had a feed → keep trying, stay honest
        else if (attempt === 0) { /* very first attempt: give the sim a grace window */ }
        else { scheduleReconnect(); }
      };
    }

    function scheduleReconnect() {
      if (closed || reconnectTimer) return;
      const delay = Math.min(BACKOFF_CAP, BACKOFF_BASE * Math.pow(2, attempt)) * (0.7 + 0.6 * pseudoJitter(attempt));
      attempt++;
      reconnectTimer = setTimeout(() => { reconnectTimer = null; connect(); }, delay);
    }
    // deterministic-ish jitter without Math.random (varies by attempt)
    function pseudoJitter(n) { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); }

    // First-connect grace: if we haven't reached an engine shortly after load, fall back to
    // the honest sim (prototype mode) — but keep trying to connect underneath.
    const graceMs = opts.simGraceMs != null ? opts.simGraceMs : 1500;
    setTimeout(() => { if (!everEngine) startSim(); }, graceMs);

    watchdog = setInterval(classify, 500);
    connect();

    return {
      stop() {
        closed = true;
        if (ws) { try { ws.close(); } catch (e) {} ws = null; }
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
        if (watchdog) { clearInterval(watchdog); watchdog = null; }
        stopSim();
      },
      endpoint() { return HelmEndpoint.describe(); },
      // Send a command to the engine over the SAME nav socket (control-plane: conn.upsert/delete/list,
      // and routes/waypoints next). Returns false if the socket isn't open. Replies arrive via opts.onCommand.
      send(obj) {
        if (ws && ws.readyState === 1) { try { ws.send(JSON.stringify(obj)); return true; } catch (e) { console.warn('HelmNavClient: send failed:', e && e.message); } }
        return false;
      }
    };
  };
})();
