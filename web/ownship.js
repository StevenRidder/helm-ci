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
    let courseUp = false, active = true;            // active=false → frozen (stale feed)

    const el = document.createElement('div');
    el.className = 'ownship';
    el.style.cssText = 'width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;' +
      'border-bottom:22px solid var(--accent,#5bc0ff);filter:drop-shadow(0 0 6px rgba(91,192,255,.9));';
    const marker = new maplibregl.Marker({ element: el, rotationAlignment: 'map' });
    let added = false;

    // on-map controls (recenter/follow + north-up/course-up), styled to match the glass UI
    const ctl = document.createElement('div');
    ctl.style.cssText = 'position:absolute;right:10px;bottom:118px;display:flex;flex-direction:column;gap:6px;z-index:5;';
    const mk = (label, title) => {
      const b = document.createElement('button'); b.textContent = label; b.title = title;
      b.style.cssText = 'width:38px;height:38px;min-width:38px;border:0;border-radius:9px;background:rgba(18,24,33,.78);' +
        'color:#cfe6ff;font:600 13px system-ui;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);' +
        'box-shadow:0 1px 6px rgba(0,0,0,.45);cursor:pointer;touch-action:manipulation;';
      return b;
    };
    const followBtn = mk('⌖', 'Center on boat / follow');
    const modeBtn = mk('N', 'North-up / course-up');
    ctl.appendChild(followBtn); ctl.appendChild(modeBtn);
    map.getContainer().appendChild(ctl);
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
          map.jumpTo({
            center: [disp.lon, disp.lat],
            bearing: courseUp ? disp.cog : 0,
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
