// HelmUiText — one global knob for text legibility, so "every agent picks their own grey" stops.
//
// Two controls, mounted into the Settings drawer, persisted on the boat:
//   • Label shade  — drives --cdim / --cdim2 (the canonical muted-text vars). Brightening these
//                    whitens labels EVERYWHERE that already uses the variable (the AIS cards, lists,
//                    drawers, hints). The card *values* stay near-white (--ctext).
//   • Card text size — drives --ui-scale, applied as `zoom` to the AIS detail card + pinned cards.
//
// Honest scope: --cdim is the shared muted var, so the shade is genuinely global today. The size only
// scales the surfaces wired to --ui-scale (the AIS cards first — the text you read most); more
// surfaces adopt the var over time rather than every hard-coded px migrating at once.
(function () {
  'use strict';

  var SHADES = {
    current:   { label: 'Current',   cdim: '#9bb0c0', cdim2: '#849bad' },
    brighter:  { label: 'Brighter',  cdim: '#b4c5d2', cdim2: '#9aafbf' },
    bright:    { label: 'Bright',    cdim: '#cdd9e2', cdim2: '#b4c3cf' },
    brightest: { label: 'Brightest', cdim: '#e2eaf0', cdim2: '#cdd8e0' }
  };
  var SIZES = { s: { label: 'Small', v: 0.9 }, m: { label: 'Default', v: 1 }, l: { label: 'Large', v: 1.15 }, xl: { label: 'X-large', v: 1.3 } };
  var DEF_SHADE = 'brighter', DEF_SIZE = 'm';                 // a touch whiter than the old default, per request
  var KEY_SHADE = 'helm.ui.textShade', KEY_SIZE = 'helm.ui.textSize';

  function load(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }

  var shade = SHADES[load(KEY_SHADE, DEF_SHADE)] ? load(KEY_SHADE, DEF_SHADE) : DEF_SHADE;
  var size = SIZES[load(KEY_SIZE, DEF_SIZE)] ? load(KEY_SIZE, DEF_SIZE) : DEF_SIZE;

  function injectStyle() {
    if (document.getElementById('helm-uitext-style')) return;
    var s = document.createElement('style'); s.id = 'helm-uitext-style';
    s.textContent = '.helm-ais-card,#helm-ais-pins{zoom:var(--ui-scale,1)}';
    (document.head || document.documentElement).appendChild(s);
  }
  function apply() {
    var root = document.documentElement.style;
    root.setProperty('--cdim', SHADES[shade].cdim);
    root.setProperty('--cdim2', SHADES[shade].cdim2);
    root.setProperty('--ui-scale', String(SIZES[size].v));
  }

  function seg(title, opts, getCur, onPick) {
    var wrap = document.createElement('div'); wrap.style.margin = '8px 0 4px';
    var lab = document.createElement('div');
    lab.style.cssText = 'font-size:11px;color:var(--cdim);margin:0 0 5px;letter-spacing:.02em';
    lab.textContent = title; wrap.appendChild(lab);
    var row = document.createElement('div'); row.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap';
    Object.keys(opts).forEach(function (k) {
      var o = opts[k], b = document.createElement('button'); b.type = 'button';
      b.style.cssText = 'cursor:pointer;font-size:12px;padding:5px 10px;border-radius:8px;border:1px solid rgba(255,255,255,.16);background:transparent;color:var(--ctext);display:inline-flex;align-items:center;gap:6px';
      b.innerHTML = (o.cdim ? '<span style="width:11px;height:11px;border-radius:3px;background:' + o.cdim + ';border:1px solid rgba(255,255,255,.2)"></span>' : '') + o.label;
      function mark(on) { b.style.borderColor = on ? '#5dd0b0' : 'rgba(255,255,255,.16)'; b.style.background = on ? 'rgba(95,208,176,.16)' : 'transparent'; }
      mark(k === getCur());
      b.addEventListener('click', function () {
        for (var i = 0; i < row.children.length; i++) { row.children[i].style.borderColor = 'rgba(255,255,255,.16)'; row.children[i].style.background = 'transparent'; }
        mark(true); onPick(k);
      });
      row.appendChild(b);
    });
    wrap.appendChild(row); return wrap;
  }

  function mount() {
    var drawer = document.getElementById('drawer-settings');
    if (!drawer || document.getElementById('helm-uitext-controls')) return;
    var sec = document.createElement('div'); sec.id = 'helm-uitext-controls'; sec.style.marginTop = '16px';
    var hdr = document.createElement('div'); hdr.className = 'lbl'; hdr.textContent = 'Text — legibility'; sec.appendChild(hdr);
    sec.appendChild(seg('Label shade — how white the muted text reads', SHADES, function () { return shade; }, function (k) { shade = k; save(KEY_SHADE, k); apply(); }));
    sec.appendChild(seg('Card text size', SIZES, function () { return size; }, function (k) { size = k; save(KEY_SIZE, k); apply(); }));
    var hint = document.createElement('div'); hint.className = 'hint'; hint.style.marginTop = '4px';
    hint.textContent = 'Shade brightens the muted labels everywhere; size scales the AIS cards. More surfaces follow as their text moves onto the shared variable.';
    sec.appendChild(hint);
    drawer.appendChild(sec);
  }

  injectStyle(); apply();
  if (document.readyState !== 'loading') mount();
  else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 800);     // belt-and-braces if the drawer mounts late

  window.HelmUiText = { apply: apply, get: function () { return { shade: shade, size: size }; },
    set: function (sh, sz) { if (SHADES[sh]) { shade = sh; save(KEY_SHADE, sh); } if (SIZES[sz]) { size = sz; save(KEY_SIZE, sz); } apply(); } };
})();
