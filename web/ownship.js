// HelmOwnship — the "feels like a chartplotter" layer: a smooth ownship marker plus a
// follow / course-up camera.
//
//  • Eases the DISPLAYED position + heading toward each ~1 Hz fix on every animation frame,
//    so the boat GLIDES instead of teleporting once a second.
//  • Optionally keeps the vessel centred with a look-ahead offset (boat low on screen → you
//    see where you're going), and rotates the chart to COG (course-up) or keeps north up.
//  • NEVER extrapolates past the latest fix. When the feed goes stale/offline the boat simply
//    stops at the last known position — motion is never fabricated ahead of real data.
//  • User panning/rotating disengages follow; the ⌖ button re-engages it.
(function () {
  function easeAngle(cur, tgt, k) {                 // shortest-path angular ease (degrees)
    const d = ((tgt - cur + 540) % 360) - 180;
    return cur + d * k;
  }
  window.HelmOwnship = function (map, opts) {
    opts = opts || {};
    const lookahead = opts.lookahead != null ? opts.lookahead : 0.32;   // top-padding fraction → boat sits low → see ahead
    let target = null, disp = null;                 // latest fix vs eased display state
    let follow = (opts.follow != null) ? !!opts.follow : true;   // follow by default (caller passes false to honor a pinned URL view)
    let courseUp = false, active = true, framedOnce = false;   // active=false → frozen (stale feed); framedOnce → the FIRST real fix frames the boat (we start on a neutral globe, never a hardcoded place)

    const el = document.createElement('div');
    el.className = 'ownship';
    el.style.cssText = 'width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;' +
      'border-bottom:22px solid var(--accent,#5bc0ff);filter:drop-shadow(0 0 6px rgba(91,192,255,.9));';
    const marker = new maplibregl.Marker({ element: el, rotationAlignment: 'map' });
    let added = false;

    // controls as a maplibre control group (bottom-right) — stacks above the native zoom/compass
    // and inherits the glass styling + safe-area offset, so the buttons never overlap them.
    const group = document.createElement('div');
    group.className = 'maplibregl-ctrl maplibregl-ctrl-group';
    const mk = (label, title) => {
      const b = document.createElement('button'); b.type = 'button'; b.title = title; b.textContent = label;
      b.style.cssText = 'font:600 15px system-ui;color:#cfe6ff;touch-action:manipulation;';
      return b;
    };
    const followBtn = mk('⌖', 'Center on boat / follow');
    const modeBtn = mk('N', 'North-up / course-up');
    group.appendChild(followBtn); group.appendChild(modeBtn);
    map.addControl({ onAdd() { return group; }, onRemove() { group.remove(); } }, 'bottom-right');
    const paint = () => {
      followBtn.style.color = follow ? 'var(--accent,#5bc0ff)' : '#cfe6ff';
      modeBtn.textContent = courseUp ? 'C' : 'N';
      modeBtn.style.color = courseUp ? 'var(--accent,#5bc0ff)' : '#cfe6ff';
    };
    const dropFollow = () => { follow = false; map.setPadding({ top: 0, bottom: 0, left: 0, right: 0 }); paint(); };
    followBtn.addEventListener('click', () => { follow = true; paint(); });
    modeBtn.addEventListener('click', () => { courseUp = !courseUp; if (!courseUp) map.easeTo({ bearing: 0, duration: 400 }); paint(); });
    // a user-initiated drag/rotate (has originalEvent) drops follow; our own jumpTo does not
    map.on('dragstart', e => { if (e && e.originalEvent) dropFollow(); });
    map.on('rotatestart', e => { if (e && e.originalEvent) dropFollow(); });
    // CRITICAL: also disengage on the RAW first input. The 60fps follow re-center (jumpTo below)
    // would otherwise slam the camera back every 16ms before maplibre's dragstart/zoom can engage,
    // so pan/scroll-zoom appear frozen. Catching mousedown/wheel/touch breaks that deadlock instantly.
    const inputEl = map.getCanvasContainer();
    ['mousedown', 'wheel', 'touchstart'].forEach(ev =>
      inputEl.addEventListener(ev, () => { if (follow) { follow = false; paint(); } }, { passive: true }));  // just stop re-centering; do NOT setPadding mid-gesture (it cancels the drag)
    paint();

    function frame() {
      requestAnimationFrame(frame);
      if (!target) return;
      if (!disp) disp = { lat: target.lat, lon: target.lon, cog: target.cog };
      const k = active ? 0.14 : 0.30;
      disp.lat += (target.lat - disp.lat) * k;
      disp.lon += (target.lon - disp.lon) * k;
      disp.cog = easeAngle(disp.cog, target.cog, k);
      try {
        if (!added) { marker.setLngLat([disp.lon, disp.lat]).addTo(map); added = true; }
        marker.setLngLat([disp.lon, disp.lat]).setRotation(disp.cog);
        if (follow) {
          // First real fix: if we're still on the neutral zoomed-out start, zoom in to the boat.
          // Otherwise leave zoom alone (preserve a pinned/user zoom). No hardcoded location anywhere.
          const firstZoom = (!framedOnce && map.getZoom() < 8) ? 14 : null;
          framedOnce = true;
          map.jumpTo({
            center: [disp.lon, disp.lat],
            bearing: courseUp ? disp.cog : 0,
            ...(firstZoom != null ? { zoom: firstZoom } : {}),
            // top padding shifts the focal point down → boat sits low → you see ahead.
            // (jumpTo honors `padding`, not `offset` — offset is easeTo/flyTo only.)
            padding: { top: map.getContainer().clientHeight * lookahead, bottom: 0, left: 0, right: 0 }
          });
        }
      } catch (e) { /* map not ready this frame */ }
    }
    requestAnimationFrame(frame);

    return {
      update(s) { if (s && s.pos) target = { lat: s.pos.lat, lon: s.pos.lon, cog: (s.cog != null ? +s.cog : (target ? target.cog : 0)) }; },
      setActive(a) { active = !!a; },             // false when the feed is stale/offline → freeze (no fabricated motion)
      recenter() { follow = true; paint(); },
      isFollowing() { return follow; }
    };
  };
})();
