# web/vendor/ — vendored MapLibre + awesome-maplibre plugin bundles

Offline-first: the tracer-bullet app and the Lab drawer load **everything from here**,
no CDN at runtime. This is deliberate — Helm is a chartplotter and must work on a boat
with no internet. The import map in `web/index.html` points each bare specifier at a file
in this directory; the `_maplibre-shim.js` maps `maplibre-gl` to the page's single
`window.maplibregl` so every plugin shares one MapLibre instance.

## Contents

| File | Package(s) | Pinned version |
|---|---|---|
| `maplibre-gl/maplibre-gl.js` + `.css` | `maplibre-gl` (UMD, loaded via `<script>`) | 5.24.0 |
| `pmtiles.js` | `pmtiles` | 4.4.1 |
| `maplibre-cog-protocol.js` | `@geomatico/maplibre-cog-protocol` | 0.9.0 |
| `maplibre-contour.js` | `maplibre-contour` | 0.1.0 |
| `terra-draw.js` | `terra-draw` | 1.31.2 |
| `terra-draw-maplibre-gl-adapter.js` | `terra-draw-maplibre-gl-adapter` | 1.4.1 |
| `maplibre-gl-measures.js` | `maplibre-gl-measures` | 0.0.20 |
| `maplibre-gl-temporal-control.js` | `maplibre-gl-temporal-control` | 1.2.0 |
| `deck.js` | `@deck.gl/mapbox` + `@deck.gl/layers` + `@deck.gl/aggregation-layers` (core + luma bundled in, deduped) | 9.3.4 |

`deck.js` intentionally bundles all three deck sub-packages into **one** file (the import map
maps all three specifiers to it). This is what eliminates the "two instances of `@deck.gl/core`"
duplicate-module hazard that a multi-file CDN setup hits.

## How these were built (to reproduce / bump a version)

Each file is an esbuild bundle: `format=esm`, `platform=browser`, `target=es2020`, minified,
with `maplibre-gl` (and, inside the deck bundle, nothing else) marked **external** so it resolves
through the import map at runtime. Built with `esbuild@0.24.2`.

```sh
mkdir -p /tmp/helm-vendor && cd /tmp/helm-vendor && npm init -y
npm i esbuild@0.24.2 \
  pmtiles@4.4.1 @geomatico/maplibre-cog-protocol@0.9.0 maplibre-contour@0.1.0 \
  terra-draw@1.31.2 terra-draw-maplibre-gl-adapter@1.4.1 \
  maplibre-gl-measures@0.0.20 maplibre-gl-temporal-control@1.2.0 \
  @deck.gl/core@9.3.4 @deck.gl/mapbox@9.3.4 @deck.gl/layers@9.3.4 @deck.gl/aggregation-layers@9.3.4
# then run build.mjs (kept alongside this README as build.mjs) which emits each bundle here.
```

MapLibre core is the published UMD dist, copied verbatim:
`curl -L https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.{js,css}`.
