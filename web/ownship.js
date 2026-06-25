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
    let follow = (opts.follow != null) ? !!opts.follow : false;   // follow OFF by default — the map is freely pan/zoom; ⌖ engages follow
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
    followBtn.addEventListener('click', () => { if (disp) map.easeTo({ center: [disp.lon, disp.lat], duration: 500 }); });  // one-time "center on boat" — no continuous follow (it froze pan)
    modeBtn.addEventListener('click', () => { courseUp = !courseUp; if (!courseUp) map.easeTo({ bearing: 0, duration: 400 }); paint(); });
    // No drag/zoom interception at all — we no longer continuously re-center, so nothing must touch
    // the camera during a gesture. (The old dragstart→setPadding handler was interrupting the drag.)
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
        if (!framedOnce) {            // ONE-TIME: bring the boat into view on the first fix. After that the camera
          framedOnce = true;          // is FREE — we NEVER continuously re-center (that was freezing pan/zoom).
          map.easeTo({ center: [disp.lon, disp.lat], zoom: Math.max(map.getZoom(), 12), duration: 600 });
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
