// HelmCollision — CPA/TCPA collision alarm + COLREGs avoidance guidance.
//
// The engine already computes per-target CPA/TCPA/bearing (OpenCPN's AisDecoder). This module
// turns the dangerous ones into an alarm: it flags the most threatening target, highlights it
// on the chart (intercept line + pulsing ring), and — classifying the encounter geometry against
// the COLREGs — states who is give-way / stand-on and the prescribed action.
//
// SAFETY: this is decision SUPPORT, not an autopilot. The guidance assumes power-driven vessels
// in sight of one another (Rules 11–18); it does not know vessel category, restricted visibility
// (Rule 19), or local rules. The skipper is responsible for collision avoidance and must keep a
// proper lookout (Rule 5) and verify visually. The banner says so, permanently.
(function () {
  const CPA_WARN = 2.0;     // NM   — matches the engine's g_CPAWarn_NM
  const TCPA_MAX = 30.0;    // min  — matches the engine's g_TCPA_Max
  const norm = d => { d %= 360; return d < 0 ? d + 360 : d; };

  // Classify the encounter from own course/speed + the target's bearing/course/speed.
  // Returns { type, role: 'give-way'|'stand-on'|'monitor', rule, action }.
  function classify(own, t) {
    if (!isFinite(own.cog) || t.brg == null || t.cog == null)
      return { type: 'Risk of collision', role: 'monitor', rule: 'Rule 7', action: 'In doubt — assume risk exists. Reduce speed and keep a sharp lookout.' };
    const rel = norm(t.brg - own.cog);           // target relative to own bow: 0 ahead, 90 stbd, 270 port
    const courseDiff = norm(t.cog - own.cog);    // 180 ≈ reciprocal, 0 ≈ same direction

    // Head-on (Rule 14): target near dead ahead AND courses near reciprocal.
    if ((rel < 15 || rel > 345) && courseDiff > 150 && courseDiff < 210)
      return { type: 'Head-on', role: 'give-way', rule: 'Rule 14', action: 'Alter course to STARBOARD — pass port-to-port.' };

    // Overtaking (Rule 13): target abaft own beam → she is overtaking you (you stand on).
    if (rel > 112.5 && rel < 247.5)
      return { type: 'Being overtaken', role: 'stand-on', rule: 'Rule 13', action: 'Hold course & speed. The overtaking vessel must keep clear — watch her.' };

    // …or you are overtaking her: she's forward, near-parallel course, and you're faster.
    if ((courseDiff < 45 || courseDiff > 315) && own.sog > t.sog + 0.3)
      return { type: 'Overtaking', role: 'give-way', rule: 'Rule 13', action: 'Keep well clear — alter early and boldly; do not cut back across her.' };

    // Crossing (Rule 15): target on your STARBOARD bow → you give way.
    if (rel > 0 && rel <= 112.5)
      return { type: 'Crossing', role: 'give-way', rule: 'Rule 15', action: 'She is on your STARBOARD — you give way. Alter to STARBOARD and pass astern. Do not cross ahead.' };

    // …target on your PORT bow → you are the stand-on vessel.
    return { type: 'Crossing', role: 'stand-on', rule: 'Rule 17', action: 'She is on your PORT — you are stand-on. Hold course & speed, but be ready to act if she does not give way.' };
  }

  const dangerous = t => t && t.cpaValid !== false && t.cpa != null &&
    t.cpa < CPA_WARN && t.tcpa != null && t.tcpa > 0 && t.tcpa < TCPA_MAX;
  const fmtNM = nm => (nm < 1 ? Math.round(nm * 100) / 100 : Math.round(nm * 10) / 10) + ' NM';
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  window.HelmCollision = function (map, opts) {
    opts = opts || {};
    let muted = false, ackMmsi = null, lastAlarmMmsi = null, pulse = null, actx = null;
    let lastUpdateAt = Date.now(), everLive = false, lastOwn = null, watchWarned = false;   // AIS-feed health

    // ---- alarm banner ----
    const el = document.createElement('div');
    el.className = 'cpa-alarm glass';
    el.hidden = true;
    document.body.appendChild(el);

    function beep() {
      if (muted) return;
      try {
        actx = actx || new (window.AudioContext || window.webkitAudioContext)();
        if (actx.state === 'suspended') actx.resume();
        const o = actx.createOscillator(), g = actx.createGain();
        o.type = 'sine'; o.frequency.value = 880; o.connect(g); g.connect(actx.destination);
        g.gain.setValueAtTime(0.0001, actx.currentTime);
        g.gain.exponentialRampToValueAtTime(0.16, actx.currentTime + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + 0.45);
        o.start(); o.stop(actx.currentTime + 0.5);
      } catch (e) { /* audio needs a user gesture; banner still shows */ }
    }

    // ---- chart highlight (intercept line own→target + pulsing ring) ----
    function ensureLayers() {
      if (map.getSource('collision')) return;
      map.addSource('collision', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({
        id: 'collision-line', type: 'line', source: 'collision',
        filter: ['==', ['get', 'kind'], 'line'],
        paint: { 'line-color': '#ff5a52', 'line-width': 2, 'line-dasharray': [2, 1.5], 'line-opacity': 0.9 }
      });
      map.addLayer({
        id: 'collision-ring', type: 'circle', source: 'collision',
        filter: ['==', ['get', 'kind'], 'ring'],
        paint: { 'circle-radius': 15, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#ff5a52', 'circle-stroke-width': 2.5 }
      });
    }
    function highlight(own, t) {
      ensureLayers();
      const src = map.getSource('collision'); if (!src) return;
      if (!t) { src.setData({ type: 'FeatureCollection', features: [] }); stopPulse(); return; }
      src.setData({ type: 'FeatureCollection', features: [
        { type: 'Feature', properties: { kind: 'line' }, geometry: { type: 'LineString', coordinates: [[own.lon, own.lat], [t.lon, t.lat]] } },
        { type: 'Feature', properties: { kind: 'ring' }, geometry: { type: 'Point', coordinates: [t.lon, t.lat] } }
      ] });
      startPulse();
    }
    function startPulse() {
      if (pulse) return;
      let on = true;
      pulse = setInterval(() => {
        on = !on;
        if (map.getLayer('collision-ring')) map.setPaintProperty('collision-ring', 'circle-stroke-opacity', on ? 0.95 : 0.35);
      }, 550);
    }
    function stopPulse() { if (pulse) { clearInterval(pulse); pulse = null; } }

    function render(own, t, others) {
      const c = classify(own, t);
      const roleClass = c.role === 'give-way' ? 'give' : c.role === 'stand-on' ? 'stand' : 'mon';
      const roleLabel = c.role === 'give-way' ? 'GIVE-WAY' : c.role === 'stand-on' ? 'STAND-ON' : 'MONITOR';
      // AIS names are fixed-width, right-padded with '@' (6-bit value 0) — strip it (e.g. "LISTRAC@@@@@@" -> "LISTRAC").
      const name = String(t.name == null ? '' : t.name).replace(/@+/g, '').trim() || ('MMSI ' + (t.mmsi ?? '?'));
      el.innerHTML =
        '<div class="cpa-ic">⚠</div>' +
        '<div class="cpa-body">' +
          '<div class="cpa-top"><span class="cpa-ttl">' + esc(c.type) + ' · collision risk</span>' +
            '<span class="cpa-role ' + roleClass + '">' + roleLabel + '</span></div>' +
          '<div class="cpa-tgt">' + esc(name) + ' · CPA ' + fmtNM(t.cpa) + ' in ' + Math.round(t.tcpa) + ' min · ' +
            (t.brg != null ? Math.round(t.brg) + '° / ' + fmtNM(t.range != null ? t.range : 0) : '') + '</div>' +
          '<div class="cpa-act">▸ ' + esc(c.action) + ' <span class="cpa-rule">' + c.rule + '</span></div>' +
          (others > 0 ? '<div class="cpa-more">+' + others + ' other target' + (others > 1 ? 's' : '') + ' at risk</div>' : '') +
          '<div class="cpa-disc">COLREGs guidance, power-driven & in sight — you are responsible. Keep a lookout; verify visually.</div>' +
        '</div>' +
        '<div class="cpa-btns">' +
          '<div class="cpa-btn" data-act="mute" title="Mute sound">' + (muted ? '🔇' : '🔔') + '</div>' +
          '<div class="cpa-btn" data-act="ack" title="Acknowledge">✕</div>' +
        '</div>';
      el.querySelector('[data-act="mute"]').onclick = () => { muted = !muted; render(own, t, others); };
      el.querySelector('[data-act="ack"]').onclick = () => { ackMmsi = t.mmsi; el.hidden = true; highlight(own, null); };
      el.hidden = false;
    }

    // An empty target list must NOT silently read as "all clear" when the AIS feed is actually
    // dead. Show an explicit amber "monitoring offline" notice instead.
    function warnFeed(own) {
      el.innerHTML =
        '<div class="cpa-ic" style="color:#f5c451">⚠</div>' +
        '<div class="cpa-body">' +
          '<div class="cpa-top"><span class="cpa-ttl" style="color:#f5c451">AIS monitoring offline</span></div>' +
          '<div class="cpa-tgt">No live AIS feed — CPA / collision monitoring is paused.</div>' +
          '<div class="cpa-act">▸ Keep a sharp visual lookout; check the AIS source connection.</div>' +
          '<div class="cpa-disc">This is NOT "all clear" — targets may be present but unseen.</div>' +
        '</div>';
      el.hidden = false; highlight(own || {}, null); stopPulse();
    }

    function update(own, list, feedAlive) {
      lastUpdateAt = Date.now(); lastOwn = own; watchWarned = false;
      const arr = Array.isArray(list) ? list : [];
      if (feedAlive === true || arr.length) everLive = true;            // we've seen the feed live at least once
      if (everLive && feedAlive === false) { warnFeed(own); return; }   // source link down -> not "all clear"
      const threats = arr.filter(dangerous)
        .sort((a, b) => (a.tcpa - b.tcpa) || (a.cpa - b.cpa));   // most imminent first
      if (!threats.length) { el.hidden = true; highlight(own, null); ackMmsi = null; lastAlarmMmsi = null; return; }
      const worst = threats[0];
      if (worst.mmsi === ackMmsi) { highlight(own, null); return; }   // acknowledged — stay quiet until it changes
      if (worst.mmsi !== lastAlarmMmsi) { beep(); lastAlarmMmsi = worst.mmsi; }   // new threat → one alert
      highlight(own, worst);
      render(own, worst, threats.length - 1);
    }

    // Watchdog: the engine going fully silent (no nav frames at all) also means no monitoring.
    setInterval(() => {
      if (everLive && !watchWarned && Date.now() - lastUpdateAt > 12000) { watchWarned = true; warnFeed(lastOwn); }
    }, 5000);

    return { update, setMuted: m => { muted = !!m; } };
  };
})();
