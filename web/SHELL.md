# SHELL — the shared-shell registration seam

`web/index.html` used to be an ~85 KB monolith every UI epic had to hand-edit to add a panel, a
⌘K command, or a map layer — the #1 merge-conflict hazard. The **SHELL** epic de-fangs it: a tiny
global `HelmShell` (in `web/shell.js`) lets your feature module register all three **from its own
file, with zero edits to `index.html`'s body or `style.json`**.

> **The one rule:** edit only your epic's files. Add UI through `HelmShell`. Namespace every id
> you introduce `helm-<epic>-*`. That's the whole collision boundary.

`web/shell-demo.js` is a complete worked example (panel + command + style fragment). Copy its
shape, swap `helm-demo-*` for `helm-<yourepic>-*`, and delete the demo when you no longer need it.

---

## 1. Panels — `HelmShell.registerPanel({...})`

Adds a left-rail icon + a slide-out drawer. Call it at module load (top-level in your `.js`).

```js
HelmShell.registerPanel({
  id:    'helm-ais-targets',     // REQUIRED · unique · namespaced helm-<epic>-*  (also the DOM id)
  epic:  'AIS',                  // your epic tag (emitted as an <!-- EPIC:AIS --> provenance marker)
  title: 'AIS targets',          // drawer heading + rail tooltip
  icon:  'A',                    // a short text label, OR an inline '<svg …></svg>' string
  render(body, { map }) {        // called ONCE, lazily, the first time the panel opens.
    // `body` is the empty drawer <div> (already has class "drawer glass" + your <h2> title).
    // Fill it with your controls. Reuse the shell's CSS classes (.sub .lbl .row .conn-btn .sw …).
  },
  onOpen(body, { map }) {}       // OPTIONAL · called every open (e.g. refresh live data)
});
```

Returns a handle: `{ open(), close(), toggle(), isOpen(), el() }`. Fetch it later with
`HelmShell.panel('helm-ais-targets')`. Opening a registered panel auto-closes every other panel
(registered or built-in), so they stay mutually exclusive like the original drawers.

## 2. ⌘K / toolbar commands — `HelmShell.registerCommand({...})`  (SHELL-3)

Appends one entry to the command palette (opened with **⌘K**/**Ctrl-K**, or by clicking the toolbar
search box). This is the **single stable hook** for the palette — `TOOLS-3`/`AI-6` build their
richer fuzzy-go-to + NL handling on top of the same registry; everyone else just appends a command.

```js
HelmShell.registerCommand({
  id:       'helm-ownship-follow',   // REQUIRED · unique · namespaced
  epic:     'OWNSHIP',
  title:    'Center on boat',        // shown in the palette
  subtitle: 'Follow ownship',        // OPTIONAL dim second line
  keywords: ['center', 'follow'],    // OPTIONAL extra fuzzy-match terms
  group:    'Ownship',               // OPTIONAL right-aligned section tag
  run({ map }) { window.__ownship.recenter(); }   // invoked on pick; palette closes first
});
```

Returns `{ id, remove() }`. Introspection for palette builders:
`HelmShell.commands()` (snapshot), `HelmShell.runCommand(id)`, and
`HelmShell.onCommandsChanged(fn)` (fires now + whenever commands change, so a late registration
re-renders the open palette). `window.HelmCmdK.open()/.close()` opens/closes the baseline palette.

## 3. Map layers — per-domain style fragments  (SHELL-2)

`style.json` is split into per-domain fragments under **`web/style/`**, merged into one style by
`HelmShell.buildStyle()` **before the map is constructed**. The merged result is byte-equivalent to
the legacy monolith (which now survives only as a zero-risk fallback — do not hand-edit it).

A fragment is a partial MapLibre style — `{ "sources": {…}, "layers": [ … ] }`. **Every source id
and layer id MUST be namespaced `helm-<epic>-*`** so two epics never write the same JSON object.

**To add layers for your epic:**

1. Create `web/style/helm-<epic>-<thing>.json`:
   ```json
   {
     "_epic": "AIS",
     "sources": { "helm-ais-tracks": { "type": "geojson", "data": "data/ais-tracks.geojson" } },
     "layers":  [ { "id": "helm-ais-track-line", "type": "line", "source": "helm-ais-tracks",
                    "paint": { "line-color": "#5bc0ff" } } ]
   }
   ```
2. Add its filename to `web/style/manifest.json` **at the right draw position** (the list is
   bottom-layer-first; insert where your layers should paint in the stack).

`buildStyle()` deep-merges base + every manifest fragment, in order. Duplicate source/layer ids are
refused with a console warning (first writer wins) — so a mis-namespaced fragment can never silently
clobber another epic's layer.

**Runtime alternative.** For layers you add dynamically, either:
- call `HelmShell.registerStyleFragment('AIS', objOrUrl)` **before** `buildStyle()` runs (i.e. at
  module load — script tags execute before the inline bootstrap), or
- add them imperatively with `map.addLayer({...})` after `map.on('load')`. Use `beforeId` to control
  stacking (the `route-line` layer is a common anchor).

### Fragment manifest (current draw order)

`helm-base` → `helm-chart-basemaps` → `helm-chart-depth` → `helm-route-line` → `helm-wx-wind` →
`helm-place-whereto` → `helm-place-poi` → `helm-ais-targets` → `helm-place-saved`.

> **Grandfathered legacy ids.** The split preserves the original un-prefixed layer/source ids
> (`enc-chart`, `route-line`, `places-icon`, `ais-vessels`, …) because `index.html` and the feature
> modules reference them by name. Don't rename them. The `helm-<epic>-*` rule applies to **new**
> layers you add.

---

## How the shell consumes it (for reference)

`index.html` runs its body inside an `async main()` that:
1. `const style = await HelmShell.buildStyle({ styleDir: 'style', fallback: 'style.json' })`
2. builds the map with that merged style object,
3. calls `HelmShell.boot({ map, railEl })` — which drains every queued registration (your module
   registered during its own script load) and wires the panels/rail/commands live.

Registration is **order-independent**: register before or after `shell.js` loads, before or after
`boot()` — the shell reconciles it. Your module never needs to know the boot timing.

## File ownership

SHELL owns `web/index.html`, `web/style.json`, `web/serve.py`, `web/shell.js`, `web/shell-demo.js`,
and `web/style/` (the base + manifest + the split layout). You own only the fragment file you add
and your own feature module. If you need a change to the shell itself (a new CSS primitive, a new
lifecycle hook), leave a comment on the relevant task with `project="helm"` and flag it — don't edit
the shell body.
