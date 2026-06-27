/* ============================================================================
 * safety-dock.js — Movable MOB / anchor-watch / guard safety pill (CHART).
 *
 * Keeps the EXISTING MOB/anchor-watch/guard pill exactly as it was. Only:
 *   - DEFAULT lower-left, left-aligned with the nav rail (left:12 / bottom:92)
 *   - FREE-FORM draggable (mouse + touch) — drag anywhere, NO snap
 *   - a real drag never fires a button (small move = tap, larger = drag)
 *   - PERSIST it EDGE-RELATIVE (px from the nearest corner), not absolute px, so it
 *     survives a resize/rotate / desktop->phone instead of stranding off-screen
 *   - CLAMP into the safe area on load + resize so it never goes off-screen / under chrome
 *   - DOUBLE-TAP to reset back to the default lower-left ("go back")
 * No redesign, no scale/attribution changes.
 * ==========================================================================*/
(function () {
  'use strict';
  var KEY = 'helm.mobPill.anchor';
  var DEFAULT = { hx: 'l', vy: 'b', ox: 12, oy: 92 };   // lower-left, aligned with the rail
  var EDGE = 4;                                          // min gap from the screen edge

  function vw() { return window.innerWidth || document.documentElement.clientWidth || 1024; }
  function vh() { return window.innerHeight || document.documentElement.clientHeight || 768; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function loadAnchor() { try { var a = JSON.parse(localStorage.getItem(KEY)); return (a && 'ox' in a) ? a : null; } catch (e) { return null; } }
  function saveAnchor(a) { try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} }

  // turn the current rendered box into an edge-relative anchor (nearest corner + px offsets)
  function anchorFromRect(pill) {
    var r = pill.getBoundingClientRect(), W = vw(), H = vh();
    var hx = (r.left + r.width / 2) < W / 2 ? 'l' : 'r';
    var vy = (r.top + r.height / 2) < H / 2 ? 't' : 'b';
    return {
      hx: hx, vy: vy,
      ox: Math.round(hx === 'l' ? r.left : W - r.right),
      oy: Math.round(vy === 't' ? r.top : H - r.bottom)
    };
  }

  // apply an anchor as CSS, clamped so the pill always stays fully on-screen
  function applyAnchor(pill, a) {
    var w = pill.offsetWidth || 40, h = pill.offsetHeight || 110, W = vw(), H = vh();
    var ox = clamp(a.ox, EDGE, Math.max(EDGE, W - w - EDGE));
    var oy = clamp(a.oy, EDGE, Math.max(EDGE, H - h - EDGE));
    pill.style.left = a.hx === 'l' ? ox + 'px' : 'auto';
    pill.style.right = a.hx === 'r' ? ox + 'px' : 'auto';
    pill.style.top = a.vy === 't' ? oy + 'px' : 'auto';
    pill.style.bottom = a.vy === 'b' ? oy + 'px' : 'auto';
    pill.__anchor = a;
  }

  function findPill() {
    var bl = document.querySelector('.maplibregl-ctrl-bottom-left');
    if (!bl) return null;
    return Array.prototype.find.call(bl.children, function (el) {
      return /MOB/i.test(el.textContent) && !el.classList.contains('maplibregl-ctrl-scale');
    }) || null;
  }

  function enhance(pill) {
    if (pill.__draggable) return; pill.__draggable = true;
    try { document.body.appendChild(pill); } catch (e) {}   // out of the map's stacking context (rail is z6)
    pill.style.position = 'fixed';
    pill.style.zIndex = '7';
    pill.style.margin = '0';
    pill.style.cursor = 'grab';
    pill.style.touchAction = 'none';
    pill.title = 'Drag to move · double-tap to reset';

    applyAnchor(pill, loadAnchor() || DEFAULT);

    var drag = null, moved = false, lastTap = 0;
    pill.addEventListener('pointerdown', function (e) {
      var r = pill.getBoundingClientRect();
      drag = { sx: e.clientX, sy: e.clientY, ox: r.left, oy: r.top };
      moved = false;
      try { pill.setPointerCapture(e.pointerId); } catch (x) {}
    });
    pill.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
      if (!moved && Math.abs(dx) + Math.abs(dy) < 5) return;   // small move = tap, not a drag
      moved = true; pill.style.cursor = 'grabbing';
      var w = pill.offsetWidth, h = pill.offsetHeight, W = vw(), H = vh();
      pill.style.left = clamp(drag.ox + dx, EDGE, W - w - EDGE) + 'px';
      pill.style.top = clamp(drag.oy + dy, EDGE, H - h - EDGE) + 'px';
      pill.style.right = pill.style.bottom = 'auto';
    });
    function end(e) {
      var now = (performance && performance.now) ? performance.now() : Date.now();
      if (drag) {
        try { pill.releasePointerCapture(e.pointerId); } catch (x) {}
        pill.style.cursor = 'grab';
        if (moved) { var a = anchorFromRect(pill); applyAnchor(pill, a); saveAnchor(a); }   // re-anchor edge-relative
      }
      if (!moved && now - lastTap < 320) {                  // double-tap (no drag) = reset
        applyAnchor(pill, DEFAULT); saveAnchor(DEFAULT);
        pill.animate([{ transform: 'scale(1.12)' }, { transform: 'scale(1)' }], { duration: 220 });
      }
      lastTap = now; drag = null;
    }
    pill.addEventListener('pointerup', end);
    pill.addEventListener('pointercancel', function () { drag = null; pill.style.cursor = 'grab'; });
    // a real drag must not also trigger a button action
    pill.addEventListener('click', function (e) { if (moved) { e.stopPropagation(); e.preventDefault(); } }, true);
    // re-apply the anchor (clamped) whenever the viewport changes — the whole point of edge-relative
    window.addEventListener('resize', function () { applyAnchor(pill, pill.__anchor || DEFAULT); });
  }

  function init() {
    var tries = 0, t = setInterval(function () {
      var p = findPill();
      if (p) { enhance(p); clearInterval(t); }
      else if (++tries > 60) clearInterval(t);
    }, 200);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
