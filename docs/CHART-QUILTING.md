# Chart engine: multi-cell tiler → quilting, vs OpenCPN

**Status:** 2026-06-24 · `engine/vendor/cli/helm_tiles.cpp`
**TL;DR:** the tiler went from **one hard-coded cell** to **multi-cell, zoom-aware selection**
— it loads a whole folder of ENC cells and, for every `{z}/{x}/{y}` tile, renders the
cell whose native scale best matches that zoom (overview when out, harbour when in). That is
the tile-layer analogue of OpenCPN's quilt *reference-chart selection*, minus the GUI coupling.
This doc explains what we built, the remaining gap to **full** quilting, and — concretely —
**where OpenCPN's quilting falls short in its own code**, and what we do instead.

> Honesty note: OpenCPN class/method names below come from our file-by-file read
> ([docs/research/opencpn-deep-read.json](research/opencpn-deep-read.json)); the quilt lives in
> `gui/src/Quilt.cpp` + `ChartCanvas` (`gui/src/chcanv.cpp`). Treat exact symbol names as
> "as-read," re-verify against source before quoting in anything binding. The architectural
> claims (GUI/viewport coupling, dual GL/DC paths, no tile cache) are well-established.

---

## 1. What "quilting" means, and the three rungs

A sea area is covered by *many* ENC cells at different **usage bands** (1 overview … 6 berthing),
which overlap. Showing charts well means:

1. **Single-cell** *(where we were)* — load one cell, render its area, blank elsewhere.
2. **Multi-cell selection** *(where we are now)* — load all cells; per tile, pick the
   zoom-appropriate covering cell. Seamless coverage as you pan; right detail as you zoom.
3. **Full quilting** *(next)* — within one view, **stitch overlapping cells of different
   scales into one picture**: finer-on-top, coverage-clipped, no seams, no holes.

Rung 2 gets ~80% of the daily benefit. Rung 3 is the remaining polish — and, crucially, our
architecture lets us reach it *per tile* without inheriting OpenCPN's quilt problems.

---

## 2. What we built (rung 2)

`helm_tiles.cpp` now:

- **Loads a folder of cells** (`init_charts(root)` → `wxDir::GetAllFiles("*.000")`), each into a
  `Cell { s57chart*, Extent, scale, path }`. Bad cells are **skipped, not fatal** (a real region
  folder has dud cells; keep serving the good ones). Fail-closed per cell on invalid native
  scale (SCAMIN/safety-contour selection can't be trusted then).
- **Picks the cell per tile** (`pick_cell`): of the cells covering the tile, choose the one whose
  native scale is closest **in log space** to the tile's display scale
  (`zoom_scale = 559082264.029·cos φ / 2^z`, the OGC Web-Mercator scale denominator), preferring
  a cell that contains the tile centre. Verified: at lat 24.5°, z8–10 → overview (1:700k),
  z11–12 → coastal (1:150k), z13–14 → approach (1:40k), z15–16 → harbour (1:12k).
- Renders that cell on the main thread (CoreGraphics) via the existing job queue; transparent
  tile where no cell covers.

**Known limit of rung 2:** a tile straddling two same-band cells renders the centre's cell, so
the other sliver shows that cell's no-data background. Seam artifacts are confined to boundary
tiles. Rung 3 (below) removes them.

---

## 3. The path to full quilting (rung 3)

Two pieces, both of which our tile model makes *easier* than OpenCPN's canvas model:

1. **NODTA → transparent.** Make the S-52 no-data colour render transparent (already on the
   roadmap for depth-on-satellite). Then a cell only paints where it has coverage.
2. **Per-tile compositing.** `pick_cell` becomes `rank_cells` (all covering cells, coarsest→
   finest); render each into the tile back-to-front and alpha-composite. Finer cells land on top
   exactly within their M_COVR; coarser fills the rest. One tile, fully quilted, **cacheable**.

This is quilting *as a pure function of the tile* — deterministic, parallelizable, headless,
and CDN/offline-cacheable. OpenCPN cannot do any of those (see §4).

---

## 4. Where OpenCPN's quilting falls short — in its own code

These are properties of OpenCPN's `Quilt`/`ChartCanvas` design, not user error:

| # | OpenCPN, per its code | Consequence | What we do instead |
|---|---|---|---|
| 1 | **Quilt is welded to the GUI ViewPort and the canvas paint thread.** `Quilt::Compose` runs on the wx paint path against the live `ViewPort`. | Pan/zoom **recomputes the candidate array and re-renders the whole viewport every frame**; no persistent cache → repeated work, stutter on big chart sets / slow hardware. | **Per-tile render, cached.** A pan is cache hits, not recompute. Tiles are immutable for a cell version. |
| 2 | **Reference-chart selection is a scale-threshold heuristic** (`m_reference_scale`, `m_refchart_dbIndex`, `BuildExtendedChartArray`). | Well-known **"quilt flashing"** (charts popping in/out while zooming), wrong reference chart at band boundaries, and **quilt holes** where mismatched-scale overlaps leave gaps. | **Deterministic per-tile log-scale nearest pick.** No frame-to-frame popping (a tile's choice is fixed); holes impossible once compositing fills coarser-under-finer. |
| 3 | **Two divergent render paths** — `RenderQuiltViewGL` vs `…DC`. | They drift; overzoom/blending bugs differ between GL and DC; double the maintenance. | **One DC path, headless.** GL isn't needed — MapLibre composites the raster tiles at 60 fps. |
| 4 | **Coverage clipping via per-chart `M_COVR` regions on the canvas.** | Geometry edge-cases → **visible seams/overlaps at cell edges** (notably CM93 composite). | Compositing clips by the same coverage but **per tile**, so errors are bounded to one 256-px tile and fixed by finer-on-top fill. |
| 5 | **No tiling, no tile cache, no headless mode, single-client.** It *is* a desktop canvas. | Can't pre-bake tiles, can't serve a CDN, can't feed multiple displays, can't run server/edge-side. | **Slippy-tile HTTP server today**; trivially cache to disk / mbtiles (offline) / CDN; multi-client; already headless. |
| 6 | **Renders to the chart canvas only.** | **Cannot composite ENC over satellite** — depth-on-satellite (Helm's headline differentiator) is impossible in OpenCPN's model. | ENC tiles composite over MapLibre's satellite/raster — the fused screen. |
| 7 | **Loads full SENC for every quilt candidate** held in memory. | Large areas = heavy RAM; no demand paging. | Same today (we load all cells), but the tile model allows **lazy load + LRU evict per tile demand** — a clean future win OpenCPN's design resists. |

---

## 5. Where OpenCPN is still ahead (what we must earn)

Not overclaiming — these are real and we haven't matched them yet:

- **True multi-scale-in-one-view** (a single screen stitching harbour + approach + coastal). We
  pick one band per tile today; rung-3 compositing closes most of this, but OpenCPN's view-level
  quilt is more general.
- **Decades of M_COVR/seam hardening** across thousands of messy real-world cells, plus **CM93**,
  **S-63/oeSENC encrypted** formats, and the long tail of **S-52 conditional symbology**.
- **Mature SCAMIN/overzoom behaviour** tuned over many releases.

The plan reaches **parity on correctness** (rung 3 + format coverage) while **beating OpenCPN on
architecture** (cacheable, headless, multi-client, fused-over-satellite, parallel pre-bake) —
because those wins fall out of the tile-server design, not from out-coding a mature renderer.

---

## 6. Try it

```bash
# folder of ENC cells (recursively scanned), or a single .000:
HELM_ENC_ROOT=/path/to/ENC_ROOT  "$HELM_OCPN_DIR/build/cli/helm-tiles"
#   → loads N cells, logs "native scales 1:x .. 1:y", serves zoom-quilted tiles on :8082
```

The MapLibre `enc` raster source (`web/style.json`, "S-52 charts (engine)" toggle) consumes it
unchanged — now with real coverage as you pan and the right band as you zoom.

*Cross-references: [OPENCPN-REUSE.md](OPENCPN-REUSE.md) (quilting = "rebuild, high"),
[CHART-PIPELINE.md](CHART-PIPELINE.md) (on-demand download + depth-on-satellite),
[FEATURE-AUDIT.md](FEATURE-AUDIT.md) §4.1 (chart capability matrix).*
