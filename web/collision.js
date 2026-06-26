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
  // HARD dependency: HelmAisRisk (ais-risk.js) is the single source of truth for collision-risk
  // tiers. It is loaded by a <script> before this file. If it is missing we DO NOT silently fall
  // back to a duplicate predicate (that would mask the load failure and could drift from the alarm)
  // — we surface it loudly and let the direct calls below throw, so the failure can't hide.
  if (!window.HelmAisRisk) console.error('[AIS] collision.js requires ais-risk.js (HelmAisRisk) — it must load FIRST. Collision-risk classification is unavailable; this is a real failure, not a soft default.');
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

  // The alarm trigger IS the HelmAisRisk danger tier — one source of truth, no duplicate fallback.
  const dangerous = t => HelmAisRisk.isDanger(t);
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
      if (!map.getStyle()) return;   // startup-race guard: addSource/addLayer throw "Style is not done loading" before the style SPEC loads; re-runs next nav frame. (Guard on getStyle()/_loaded, NOT isStyleLoaded() — the latter also waits on every source, which can stay false indefinitely and would suppress the overlay.)
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
      // AIS names are fixed-width, right-padded with '@' (6-bit 0); "Unknown" is OpenCPN's pre-Msg5
      // placeholder. Strip the padding and fall back to MMSI for either (e.g. "LISTRAC@@@@@@" -> "LISTRAC").
      const raw = String(t.name == null ? '' : t.name).replace(/@+/g, '').trim();
      const name = (raw && !/^unknown$/i.test(raw)) ? raw : ('MMSI ' + (t.mmsi ?? '?'));
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
      aisList.feed(own, arr, feedAlive);                 // AIS-3: share live targets with the target-list panel
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

    // ============================================================================================
    //  AIS-2 — full symbology set on the map (Class A/B, AtoN, base, SART/MOB, lost cross-out)
    // ============================================================================================
    // The legacy `ais-vessels` layer (style.json / helm-ais-targets.json) draws one ▲ for EVERY
    // target, coloured by CPA. OpenCPN draws a different symbol per AIS class and crosses out lost
    // targets. We add richer `helm-ais-*` symbol layers that read the SAME `ais` source and pick the
    // glyph/rotation/colour per target with MapLibre data-driven expressions — then hide the legacy
    // generic triangle so each target is drawn exactly once. No `kind` property is written onto the
    // features (index.html owns updateAisFromEngine); selection is purely expression-driven on the
    // raw class/navStatus/mmsi/ageSec props, so it stays in lane.
    const symbology = (function () {
      const SRC = 'ais';
      // Canonical palette + risk colour come from HelmAisRisk — the single source of truth. No
      // fallback palette: a missing dependency must surface (see the loud guard at top), not silently
      // paint with a duplicate that could drift from the alarm.
      const C = HelmAisRisk.COL;
      const lost = C.lost, sart = C.sart;
      // string prefix helpers as MapLibre expressions (slice on the stringified mmsi)
      const mmsiStr = ['to-string', ['coalesce', ['get', 'mmsi'], '']];
      const pfx2 = ['slice', mmsiStr, 0, 2];
      const pfx3 = ['slice', mmsiStr, 0, 3];
      // kind expression — mirrors HelmAisMeta.symbolKind() priority, in MapLibre expression form.
      const isSart = ['any', ['==', ['coalesce', ['get', 'class'], -1], 6], ['==', ['coalesce', ['get', 'navStatus'], -1], 14],
        ['==', pfx3, '970'], ['==', pfx3, '972'], ['==', pfx3, '974']];
      const isAton = ['any', ['==', ['coalesce', ['get', 'class'], -1], 2], ['==', pfx2, '99']];
      const isBase = ['any', ['==', ['coalesce', ['get', 'class'], -1], 3], ['==', pfx2, '00']];
      const isLost = ['>', ['coalesce', ['get', 'ageSec'], 0], (window.HelmAisMeta && HelmAisMeta.LOST_SEC) || 360];
      // Class A vs B share the ▲ glyph (OpenCPN distinguishes them by fill, not shape); the list
      // table + tap card carry the A/B label. point-style kinds (AtoN/base/SART) don't rotate;
      // vessels (A/B/lost) point along COG.
      const rotates = ['all', ['!', isSart], ['!', isAton], ['!', isBase]];
      // glyph per kind
      const glyph = ['case', isSart, '✚', isAton, '◆', isBase, '◉', '▲'];
      // colour: SART distress pink → lost grey → risk-tier colour (HelmAisRisk, == the alarm).
      const cpaCol = HelmAisRisk.riskColorExpr();
      const color = ['case', isSart, sart, isLost, lost, cpaCol];

      // AIS-6 — moored/slow suppression (OpenCPN g_ShowMoored_Kts). State lives here; the panel
      // drives it via setMooredSuppress(). A target is "moored/slow" when SOG ≤ threshold AND it's
      // moored/at-anchor/unknown-status. SAFETY: never suppress a SART or anything dangerous — the
      // visible filter ORs those guards in. Default off (show everything) until the skipper opts in.
      let suppressOn = false, suppressKts = 0.5;
      function mooredExpr() {
        return ['all',
          ['<=', ['coalesce', ['get', 'sog'], 99], suppressKts],
          ['any', ['!', ['has', 'navStatus']], ['==', ['get', 'navStatus'], 1], ['==', ['get', 'navStatus'], 5]]];
      }
      // never suppress a target the CPA alarm fires on — same danger band as the alarm (HelmAisRisk).
      const isDanger = HelmAisRisk.dangerExpr();
      // The layer filter that decides VISIBILITY: show unless suppressing AND moored/slow AND
      // not (SART or dangerous). When suppression is off, this collapses to "show all".
      function visibleFilter() {
        if (!suppressOn) return null;
        return ['any', ['!', mooredExpr()], isSart, isDanger];
      }
      function applyFilters() {
        const v = visibleFilter();
        try { if (map.getLayer('helm-ais-symbol')) map.setFilter('helm-ais-symbol', v); } catch (e) { console.error('[AIS] suppression filter (symbol) failed:', e && e.message); }
        // lost layer already filters on isLost — AND it with visibility so suppressed lost targets vanish too.
        try { if (map.getLayer('helm-ais-lost')) map.setFilter('helm-ais-lost', v ? ['all', isLost, v] : isLost); } catch (e) { console.error('[AIS] suppression filter (lost) failed:', e && e.message); }
      }

      function add() {
        if (!map.getSource(SRC) || map.getLayer('helm-ais-symbol')) return;
        // hide the legacy generic triangle — our richer layer replaces it (label layer stays).
        if (map.getLayer('ais-vessels')) { try { map.setLayoutProperty('ais-vessels', 'visibility', 'none'); } catch (e) {} }
        const anchor = map.getLayer('ais-label') ? 'ais-label' : undefined;   // draw symbols under the existing labels
        map.addLayer({
          id: 'helm-ais-symbol', type: 'symbol', source: SRC,
          filter: visibleFilter() || ['literal', true],
          layout: {
            'text-field': glyph, 'text-font': ['Noto Sans Regular'],
            'text-size': ['case', isSart, 19, isAton, 13, isBase, 13, 15],
            'text-rotate': ['case', rotates, ['coalesce', ['get', 'cog'], 0], 0],
            'text-rotation-alignment': 'map', 'text-allow-overlap': true, 'text-ignore-placement': true
          },
          paint: {
            'text-color': color, 'text-halo-color': 'rgba(13,19,27,0.9)', 'text-halo-width': 1.4,
            'text-opacity': ['case', isLost, 0.55, 1]
          }
        }, anchor);
        // Lost cross-out: a red ✕ drawn over targets unheard past the timeout (OpenCPN convention).
        map.addLayer({
          id: 'helm-ais-lost', type: 'symbol', source: SRC,
          filter: isLost,
          layout: { 'text-field': '✕', 'text-font': ['Noto Sans Regular'], 'text-size': 17,
            'text-allow-overlap': true, 'text-ignore-placement': true },
          paint: { 'text-color': '#ff6b6b', 'text-halo-color': 'rgba(13,19,27,0.9)', 'text-halo-width': 1.2 }
        }, anchor);
        applyFilters();
      }
      // The map may already be loaded when HelmCollision() is constructed, or not yet — handle both,
      // and re-add after any style reload (basemap switch fires 'styledata').
      // Surface a real failure to build the symbology layers (e.g. a missing dependency or a bad
      // expression) instead of silently leaving the chart with no AIS symbols.
      function ensure() { try { add(); } catch (e) { console.error('[AIS] symbology layer build failed — targets may be unsymbolised:', e && e.message); } }
      if (map.isStyleLoaded && map.isStyleLoaded()) ensure(); else map.on('load', ensure);
      map.on('styledata', ensure);
      return {
        ensure,
        setMooredSuppress(on, kts) { suppressOn = !!on; if (kts != null) suppressKts = +kts; applyFilters(); },
        getSuppress() { return { on: suppressOn, kts: suppressKts }; }
      };
    })();

    // ============================================================================================
    //  AIS-3 — sortable AIS target list (HelmShell panel `helm-ais-list`)
    // ============================================================================================
    // A drawer with a sortable table of every AIS target (by CPA / range / name / type). Each row
    // focuses the target on the map and opens its rich tap card. Data comes from the live feed
    // (collision.update → feed()) when an engine is connected, and falls back to reading the `ais`
    // map source directly so the sim sample still populates the list with no engine.
    const aisList = (function () {
      const meta = () => window.HelmAisMeta || {};
      let cachedOwn = null, cachedList = null, sortKey = 'cpa', sortDir = 1, bodyEl = null, statEl = null;
      let suppressOn = false, suppressKts = 0.5;            // AIS-6: moored/slow suppression (off by default)

      // A target is hidden by suppression when it's moored/slow AND not a SART and not dangerous —
      // the same safety override the map filter uses. Kept in JS so the list count matches the map.
      function suppressed(t) {
        if (!suppressOn) return false;
        if (!(meta().isMooredSlow && meta().isMooredSlow(t, suppressKts))) return false;
        const m = meta();
        if (m.symbolKind && m.symbolKind(t) === 'sart') return false;          // never hide distress
        return !HelmAisRisk.isDanger(t);                                        // never hide an imminent threat (== the alarm)
      }
      // Push the current suppression state to the map symbology so the chart matches the list.
      function syncMap() { try { symbology.setMooredSuppress(suppressOn, suppressKts); } catch (e) {} }

      // The suppression control row: a checkbox + a ± stepper for the speed threshold (0–5 kn).
      // Mirrors OpenCPN's "Show moored targets ≤ N kn" but inverted to "hide" for decluttering.
      let suppEl = null, ktsEl = null;
      function buildSuppressUI() {
        const wrap = document.createElement('div');
        wrap.className = 'ais-supp' + (suppressOn ? '' : ' off');
        wrap.innerHTML =
          '<input type="checkbox" id="helm-ais-supp-cb"' + (suppressOn ? ' checked' : '') + '>' +
          '<label class="lbl2" for="helm-ais-supp-cb" title="Declutter: hide anchored/moored targets below the speed threshold">Hide moored / slow</label>' +
          '<span class="kts"><span class="stp" data-d="-1">–</span><span id="helm-ais-supp-kts">' +
            suppressKts.toFixed(1) + '</span><span style="opacity:.6">kn</span><span class="stp" data-d="1">+</span></span>';
        suppEl = wrap; ktsEl = wrap.querySelector('#helm-ais-supp-kts');
        wrap.querySelector('#helm-ais-supp-cb').onchange = e => {
          suppressOn = !!e.target.checked; wrap.classList.toggle('off', !suppressOn); syncMap(); render();
        };
        wrap.querySelectorAll('.stp').forEach(s => s.onclick = () => {
          const d = +s.dataset.d * 0.5;
          suppressKts = Math.max(0, Math.min(5, Math.round((suppressKts + d) * 2) / 2));
          if (ktsEl) ktsEl.textContent = suppressKts.toFixed(1);
          if (suppressOn) { syncMap(); render(); }
        });
        return wrap;
      }

      // strip AIS '@'/space padding; "Unknown" placeholder -> empty
      const clean = s => { const n = String(s == null ? '' : s).replace(/@+/g, '').trim(); return /^unknown$/i.test(n) ? '' : n; };
      const nameOf = t => clean(t.name) || ('MMSI ' + (t.mmsi != null ? t.mmsi : '?'));
      const fmtNM = v => (v == null || !isFinite(+v)) ? '—' : (+v < 1 ? (Math.round(+v * 100) / 100).toFixed(2) : (Math.round(+v * 10) / 10).toFixed(1));

      // Read targets from the live cache when an engine is feeding us, else from the `ais` map
      // source — the sim sample AND engine writes (updateAisFromEngine → setData) both land there.
      // source.serialize().data is the resolved FeatureCollection in every MapLibre version (the
      // private _data can be an unresolved URL); _data + querySourceFeatures are extra fallbacks.
      const fromFeatures = fc => (fc && Array.isArray(fc.features) ? fc.features : [])
        .filter(f => f && f.geometry && Array.isArray(f.geometry.coordinates))
        .map(f => Object.assign({}, f.properties,
          { lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }));
      function targets() {
        if (cachedList && cachedList.length) return cachedList;
        try {
          const s = map.getSource('ais'); if (s) {
            const ser = s.serialize && s.serialize();
            let out = fromFeatures(ser && ser.data);
            if (!out.length && s._data && typeof s._data === 'object') out = fromFeatures(s._data);
            if (out.length) return out;
          }
        } catch (e) {}
        try {
          const out = fromFeatures({ features: map.querySourceFeatures('ais') || [] });
          if (out.length) return out;
        } catch (e) {}
        return [];
      }

      const COMPARE = {
        cpa:   (a, b) => num(a.cpa) - num(b.cpa),
        range: (a, b) => num(a.range) - num(b.range),
        name:  (a, b) => nameOf(a).localeCompare(nameOf(b)),
        type:  (a, b) => (meta().symbolKind ? meta().symbolKind(a) : '').localeCompare(meta().symbolKind ? meta().symbolKind(b) : '')
      };
      const num = v => (v == null || !isFinite(+v)) ? Infinity : +v;   // missing sorts last

      function render() {
        if (!bodyEl) return;
        const all = targets().slice();
        // compute range/bearing if the engine didn't (sim sample has neither) so sort + display work.
        if (cachedOwn) all.forEach(t => { if (t.range == null && isFinite(t.lon) && isFinite(t.lat)) t.range = haversineNM(cachedOwn, t); });
        const hidden = all.filter(suppressed).length;                   // AIS-6: moored/slow held back
        const list = all.filter(t => !suppressed(t));
        list.sort((a, b) => (COMPARE[sortKey] || COMPARE.cpa)(a, b) * sortDir);

        if (statEl) statEl.textContent = list.length
          ? (list.length + ' target' + (list.length > 1 ? 's' : '') + (hidden ? '  ·  ' + hidden + ' moored hidden' : ''))
          : (hidden ? hidden + ' moored hidden' : 'No AIS targets');
        if (!list.length) {
          bodyEl.innerHTML = '<div class="sub" style="padding:14px 4px">' + (hidden
            ? ('All ' + hidden + ' target' + (hidden > 1 ? 's' : '') + ' are moored/slow and hidden. ' +
               'Turn off suppression above to show them.')
            : ('No AIS targets in range.<br>Targets appear here when an AIS source is connected (or the sim sample loads).'))
            + '</div>';
          return;
        }
        const head = '<thead><tr>' +
          th('name', 'Name') + th('type', 'Type') + th('range', 'Rng') + th('cpa', 'CPA') +
          '</tr></thead>';
        const rows = list.map(t => {
          const kind = meta().symbolKind ? meta().symbolKind(t) : 'classB';
          const sym = meta().symbol ? meta().symbol(kind) : { glyph: '▲', label: '' };
          const fl = meta().flag ? meta().flag(t.mmsi) : '';
          // risk colour from HelmAisRisk (== the alarm/chart/popup); SART + lost override the tier.
          const C2 = HelmAisRisk.COL, rt = HelmAisRisk.tier(t);
          const col = kind === 'sart' ? C2.sart : kind === 'lost' ? C2.lost
            : rt === 'danger' ? C2.danger : rt === 'caution' ? C2.caution : C2.normal;
          const lost = kind === 'lost';
          return '<tr class="ais-row' + (lost ? ' lost' : '') + '" data-lon="' + t.lon + '" data-lat="' + t.lat +
            '" data-mmsi="' + esc(t.mmsi) + '">' +
            '<td class="nm"><span class="gl" style="color:' + col + '">' + sym.glyph + '</span>' +
              (fl ? '<span class="fl">' + fl + '</span>' : '') + '<span class="tx">' + esc(nameOf(t)) + '</span></td>' +
            '<td class="ty">' + esc(sym.label) + '</td>' +
            '<td class="rg">' + fmtNM(t.range) + '</td>' +
            '<td class="cp" style="color:' + col + '">' + fmtNM(t.cpa) + '</td>' +
            '</tr>';
        }).join('');
        bodyEl.innerHTML = '<table class="ais-tbl">' + head + '<tbody>' + rows + '</tbody></table>';
        bodyEl.querySelectorAll('th[data-k]').forEach(h => h.onclick = () => {
          const k = h.dataset.k;
          if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }   // new column → ascending
          render();
        });
        bodyEl.querySelectorAll('tr.ais-row').forEach(r => r.onclick = () => focus(r));
      }
      function th(k, label) {
        const arrow = sortKey === k ? (sortDir > 0 ? ' ▴' : ' ▾') : '';
        return '<th data-k="' + k + '"' + (sortKey === k ? ' class="on"' : '') + '>' + label + arrow + '</th>';
      }

      // Focus a target: fly to it + briefly highlight, then open its rich tap card. We reuse the
      // existing `ais-vessels` click popup by querying rendered features at the target after the
      // map settles; if that misses (off-screen/zoomed), we open our own compact card.
      function focus(row) {
        const lon = +row.dataset.lon, lat = +row.dataset.lat, mmsi = row.dataset.mmsi;
        if (!isFinite(lon) || !isFinite(lat)) return;
        map.flyTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), 13), duration: 700 });
        map.once('moveend', () => openCard(lon, lat, mmsi));
      }
      function openCard(lon, lat, mmsi) {
        const t = targets().find(x => String(x.mmsi) === String(mmsi)) || { lon, lat, mmsi };
        try {
          new maplibregl.Popup({ closeButton: true, maxWidth: '260px' })
            .setLngLat([lon, lat]).setHTML(cardHTML(t)).addTo(map);
        } catch (e) {}
      }
      // A compact tap card built from the same ais-meta helpers the index.html card uses, so the
      // list is self-contained (index.html's aisPopupHTML isn't exported). Mirrors its key fields.
      function cardHTML(t) {
        const m = meta();
        const kind = m.symbolKind ? m.symbolKind(t) : 'classB';
        const sym = m.symbol ? m.symbol(kind) : { label: '' };
        const fl = m.flag ? m.flag(t.mmsi) : '';
        const type = m.shipType ? m.shipType(t.shipType != null ? t.shipType : t.type) : null;
        const ns = m.navStatus ? m.navStatus(t.navStatus) : null;
        const valid = t.cpaValid !== false && t.cpa != null;
        const row = (l, v) => '<div style="display:flex;justify-content:space-between;gap:12px;font-size:11.5px;padding:1px 0">' +
          '<span style="color:var(--cdim,#9bb0c0)">' + l + '</span><span style="font-variant-numeric:tabular-nums">' + v + '</span></div>';
        let badge = '';
        if (ns && m.navStyle) { const st = m.navStyle(ns.tone);
          badge = '<div style="display:inline-block;font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:9px;margin:2px 0 4px;background:' +
            st.bg + ';color:' + st.fg + '">' + st.icon + ' ' + esc(ns.label.toUpperCase()) + '</div>'; }
        return '<div style="min-width:180px' + (kind === 'lost' ? ';opacity:.6' : '') + '">' +
          '<div style="display:flex;align-items:baseline;gap:6px">' +
            '<span style="font-weight:700;font-size:13px;flex:1">' + esc(nameOf(t)) + '</span>' +
            (fl ? '<span style="font-size:14px">' + fl + '</span>' : '') +
            '<span style="font-size:9.5px;color:var(--cdim,#9bb0c0)">' + esc(sym.label) + '</span></div>' +
          (type || t.mmsi ? '<div style="font-size:10px;color:var(--cdim,#9bb0c0);margin-bottom:3px">' +
            [type, t.mmsi ? 'MMSI ' + t.mmsi : ''].filter(Boolean).join(' · ') + '</div>' : '') +
          badge +
          row('SOG', (t.sog != null ? (+t.sog).toFixed(1) : '—') + ' kn') +
          row('COG', (t.cog != null ? Math.round(+t.cog) : '—') + '°') +
          (t.range != null ? row('Range', fmtNM(t.range) + ' NM') : '') +
          row('CPA', valid ? fmtNM(t.cpa) + ' NM' : '—') +
          row('TCPA', (valid && t.tcpa != null) ? (+t.tcpa).toFixed(0) + ' min' : '—') +
          '</div>';
      }

      // ---- panel + command registration (no edit to index.html) ----
      if (window.HelmShell) {
        const ICON = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" ' +
          'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M3 6h18M3 12h18M3 18h12"/><path d="M19 16l2 2-2 2"/></svg>';
        // scoped CSS for the wider table panel — injected once, scoped to #helm-ais-list (in lane).
        const css = document.createElement('style');
        css.textContent =
          '#helm-ais-list{width:300px}' +
          '#helm-ais-list .ais-stat{font-size:10px;color:var(--cdim,#9bb0c0);letter-spacing:.04em;margin:0 0 6px}' +
          '#helm-ais-list .ais-tbl{width:100%;border-collapse:collapse;font-size:11.5px}' +
          '#helm-ais-list .ais-tbl th{position:sticky;top:0;text-align:left;font-weight:600;font-size:9.5px;' +
            'letter-spacing:.05em;text-transform:uppercase;color:var(--cdim2,#6f8597);padding:4px 5px;cursor:pointer;' +
            'background:var(--card,rgba(20,28,38,.7));border-bottom:.5px solid var(--line,rgba(255,255,255,.13));white-space:nowrap}' +
          '#helm-ais-list .ais-tbl th.on{color:var(--accent,#5bc0ff)}' +
          '#helm-ais-list .ais-tbl th:last-child,#helm-ais-list .ais-tbl td:last-child{text-align:right}' +
          '#helm-ais-list .ais-tbl th:nth-child(3),#helm-ais-list .ais-tbl td.rg{text-align:right}' +
          '#helm-ais-list .ais-tbl td{padding:5px 5px;border-bottom:.5px solid var(--line2,rgba(255,255,255,.07));' +
            'font-variant-numeric:tabular-nums;color:#cdd9e3}' +
          '#helm-ais-list tr.ais-row{cursor:pointer}' +
          '#helm-ais-list tr.ais-row:hover td{background:rgba(255,255,255,.05)}' +
          '#helm-ais-list tr.lost td{opacity:.55;text-decoration:line-through}' +
          '#helm-ais-list td.nm{display:flex;align-items:center;gap:5px;max-width:150px}' +
          '#helm-ais-list td.nm .gl{font-size:12px;flex:0 0 auto}' +
          '#helm-ais-list td.nm .fl{font-size:12px;flex:0 0 auto}' +
          '#helm-ais-list td.nm .tx{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
          '#helm-ais-list td.ty{color:var(--cdim,#9bb0c0);white-space:nowrap}' +
          '#helm-ais-list .ais-scroll{max-height:56vh;overflow:auto;margin:0 -4px}' +
          // AIS-6 moored-suppression control row
          '#helm-ais-list .ais-supp{display:flex;align-items:center;gap:7px;font-size:11px;color:#cdd9e3;' +
            'padding:6px 0 8px;margin:0 0 4px;border-bottom:.5px solid var(--line2,rgba(255,255,255,.07))}' +
          '#helm-ais-list .ais-supp input[type=checkbox]{accent-color:var(--accent,#5bc0ff);width:14px;height:14px;flex:0 0 auto}' +
          '#helm-ais-list .ais-supp .lbl2{flex:1;cursor:pointer}' +
          '#helm-ais-list .ais-supp .kts{display:flex;align-items:center;gap:3px;font-variant-numeric:tabular-nums;color:var(--cdim,#9bb0c0)}' +
          '#helm-ais-list .ais-supp .stp{width:20px;height:20px;line-height:18px;text-align:center;border:.5px solid var(--line,rgba(255,255,255,.13));' +
            'border-radius:6px;background:rgba(255,255,255,.05);color:#cdd9e3;cursor:pointer;font-size:13px;user-select:none}' +
          '#helm-ais-list .ais-supp.off .kts{opacity:.35;pointer-events:none}';
        document.head.appendChild(css);

        // AIS-10: render into the consolidated AIS hub (one boat icon) when present; else fall back
        // to a standalone rail panel so a missing hub never leaves a dead button.
        (window.HelmAisHub && HelmAisHub.registerTab ? HelmAisHub.registerTab : HelmShell.registerPanel)({
          id: 'helm-ais-list', epic: 'AIS', title: 'AIS targets', icon: ICON,
          render(body) {
            body.appendChild(buildSuppressUI());           // AIS-6: hide moored/slow toggle + threshold
            const stat = document.createElement('div'); stat.className = 'ais-stat'; stat.textContent = 'Loading…';
            const wrap = document.createElement('div'); wrap.className = 'ais-scroll';
            body.appendChild(stat); body.appendChild(wrap);
            statEl = stat; bodyEl = wrap; render();
          },
          onOpen() { render(); }                                  // refresh live data each time it opens
        });
        HelmShell.registerCommand({
          id: 'helm-ais-open-list', epic: 'AIS', title: 'AIS target list',
          subtitle: 'Sortable table of all AIS targets', keywords: ['ais', 'targets', 'traffic', 'vessels', 'list'],
          group: 'AIS', run() { if (window.HelmAisHub) return HelmAisHub.open('helm-ais-list'); const h = HelmShell.panel('helm-ais-list'); if (h) h.open(); }
        });
        HelmShell.registerCommand({
          id: 'helm-ais-toggle-moored', epic: 'AIS', title: 'Toggle moored / slow AIS targets',
          subtitle: 'Declutter: hide or show anchored vessels', keywords: ['ais', 'moored', 'anchored', 'slow', 'declutter', 'suppress'],
          group: 'AIS', run() {
            suppressOn = !suppressOn;
            if (suppEl) { suppEl.classList.toggle('off', !suppressOn); const cb = suppEl.querySelector('#helm-ais-supp-cb'); if (cb) cb.checked = suppressOn; }
            syncMap(); render();
          }
        });
      }

      function feed(own, list, alive) {
        cachedOwn = own || cachedOwn;
        cachedList = (Array.isArray(list) ? list : []).map(t => Object.assign({}, t));
        // live-refresh the table only while the panel is open (cheap; skips DOM churn otherwise)
        const h = window.HelmShell && HelmShell.panel('helm-ais-list');
        if (h && h.isOpen && h.isOpen()) render();
      }
      return { feed, setMooredSuppress(on, kts) { suppressOn = !!on; if (kts != null) suppressKts = +kts; syncMap(); render(); } };
    })();

    return { update, setMuted: m => { muted = !!m; }, _symbology: symbology, _list: aisList };
  };

  // --- small geo helper for sim-mode range (engine supplies range when present) ---
  function haversineNM(a, b) {
    const R = 3440.065, toR = Math.PI / 180;
    const dLat = (b.lat - a.lat) * toR, dLon = (b.lon - a.lon) * toR;
    const la1 = a.lat * toR, la2 = b.lat * toR;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }
})();
