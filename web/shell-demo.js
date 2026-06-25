// shell-demo.js — a WORKED EXAMPLE for epic agents (SHELL). NOT a product feature.
// ----------------------------------------------------------------------------------------------
// This is the proof-of-seam: a complete feature module that adds a left-rail PANEL, a ⌘K COMMAND,
// and a map STYLE FRAGMENT *without editing index.html's body or style.json*. Copy this shape into
// your own epic module (web/<yourthing>.js) and swap the `helm-demo-*` ids for `helm-<epic>-*`.
//
// It is wired in index.html by ONE example <script> tag tagged `SHELL demo`. To remove the demo
// entirely, delete that tag and this file — nothing else references it.
(function () {
  'use strict';
  if (!window.HelmShell) { console.warn('[shell-demo] HelmShell missing'); return; }

  // 1) A PANEL — a left-rail icon + drawer. render() runs once, lazily, on first open.
  HelmShell.registerPanel({
    id: 'helm-demo-panel',                 // namespaced helm-<epic>-*
    epic: 'DEMO',
    title: 'Shell demo',
    icon: 'D',                             // a short label, or pass an inline '<svg…>' string
    render: function (body, ctx) {
      var p = document.createElement('p');
      p.className = 'sub';
      p.textContent = 'Registered from web/shell-demo.js with zero edits to index.html. ' +
        'This drawer, its rail button, the ⌘K entry, and a map layer were all added via HelmShell.';
      body.appendChild(p);
      var btn = document.createElement('button');
      btn.className = 'conn-btn primary';
      btn.textContent = 'Fly to ownship area';
      btn.addEventListener('click', function () { ctx.map.flyTo({ center: [177.4, -17.7], zoom: 12 }); });
      body.appendChild(btn);
    }
  });

  // 2) A ⌘K COMMAND — appears in the palette; epics append one line from their own file.
  HelmShell.registerCommand({
    id: 'helm-demo-open-panel',
    epic: 'DEMO',
    title: 'Open the shell demo panel',
    subtitle: 'Proves registerCommand()',
    keywords: ['demo', 'shell', 'example'],
    group: 'Demo',
    run: function () { var h = HelmShell.panel('helm-demo-panel'); if (h) h.open(); }
  });

  // 3) A STYLE FRAGMENT — per-domain map layers, merged before the map is built. Every source/layer
  //    id is namespaced helm-<epic>-* so two epics never touch the same JSON object. (Hidden by
  //    default here so the demo never alters the visible map.)
  HelmShell.registerStyleFragment('DEMO', {
    sources: {
      'helm-demo-src': { type: 'geojson', data: { type: 'FeatureCollection', features: [] } }
    },
    layers: [
      { id: 'helm-demo-layer', type: 'circle', source: 'helm-demo-src',
        layout: { visibility: 'none' }, paint: { 'circle-radius': 4, 'circle-color': '#5bc0ff' } }
    ]
  });
})();
