# Interface: Chart Intake & Library v1

Schema family: `helm.chart_intake.*.v1`<br>
Producer: `helm chart import` CLI + `helm-packd` (auto-discovery) + `helm-server` (ENC load)<br>
Consumers: the MapLibre cockpit (Chart Library panel), `/catalog`, offline tooling<br>
Deliverable: `helm-northstar-fused-map` / milestone `p1-chart-intake`<br>
Tasks: INTAKE-1 (this spec) → INTAKE-2..6<br>
Related: [package-service-v1.md](package-service-v1.md), [region-bundle-sat-first-v1.md](region-bundle-sat-first-v1.md), [layer-manifest-v1.md](layer-manifest-v1.md), [chart-service-v1.md](chart-service-v1.md)

## Purpose

Define **one standard way a customer gets their own charts into Helm** — the "bring your
own charts" intake — across the two customer shapes we serve:

- **ENC-only customers** who navigate on official S-57 vector cells (the OpenCPN audience).
- **Sat-first customers** (the North Star default) who want satellite/raster pixels as the
  base with selective ENC/depth/aids overlays on top.

Today intake works, but through **three unrelated mechanisms** with no shared folder root
and no import UI: raster tile packs are hand-wired via a `HELM_MBTILES_PACKS` env map, ENC
cells via OpenCPN's SENC compile, and GeoJSON overlays via the LAYER-4 drop-folder. This
interface unifies the *intake surface* (one library root + one importer + one panel)
**without** collapsing the underlying storage/render paths, which are legitimately
different per chart type.

## The load-bearing architecture decision

**OpenCPN stays strictly the S-52 ENC→PNG factory. Customer raster tile packs never route
through OpenCPN.**

OpenCPN ships a `ChartMbTiles` class (`gui/include/gui/mbtiles.h`) that *can* import and
render MBTiles natively. In Helm that code path is **deliberately dead**:

- None of the 8 engine patches (`engine/patches/0001..0008`) touch MBTiles or `ChartMbTiles`.
- The ENC-render engine (`helm_server` / `helm_tiles`) has **zero** MBTiles references — it
  only ever opens S-57 `.000` cells (`HELM_ENC` / `HELM_ENC_ROOT`).
- Raster tile packs are served by a **separate binary**, `helm-packd`
  (`engine/vendor/cli/helm_packd.cpp`, port 8091), straight to MapLibre over HTTP. OpenCPN
  never sees them.

This is the "OpenCPN PNG stays the ENC factory; no WebGPU ENC, no CHART-13" bet made
concrete. Teaching OpenCPN's `ChartMbTiles` to handle customer tiles would be the **wrong
layer** — it would render pixels the ENC engine never receives, duplicating what MapLibre
already composites natively, with worse UX. **Extend `helm-packd` and the web import UI, not
OpenCPN's MBTiles code.**

## Canonical chart-library layout

One root, type-routed subdirectories. Default `~/.helm/charts/` (override with
`HELM_CHART_LIBRARY`):

```text
~/.helm/charts/                     # HELM_CHART_LIBRARY root
├─ tiles/                           # raster tile packs   → helm-packd → MapLibre
│    ├─ fiji-navionics.pmtiles
│    ├─ fiji-navionics.metadata.json     # sidecar: source label, license, import date
│    └─ fiji-bingsat.mbtiles
├─ enc/                             # S-57 vector cells   → OpenCPN SENC compile → PNG
│    ├─ US5MIABB.000
│    └─ NZ50xxxx.000
└─ overlays/                        # GeoJSON overlays    → layer manifest → MapLibre
     └─ my-anchorages.geojson
```

Rationale for keeping storage split (not one flat folder): a compiled vector chart database
(ENC/SENC) and a bag of pre-rendered raster tiles (MBTiles/PMTiles) are different data
models with different renderers and different refresh semantics. The **intake** is unified;
the **backends** stay specialized.

## Per-type intake contract

| Type | Customer drops | Subdir | Read by | Rendered by | Refresh / "DB sync" |
|---|---|---|---|---|---|
| Raster tile pack | `*.mbtiles` / `*.pmtiles` | `tiles/` | `helm-packd` (auto-scan) | MapLibre raster layer | **None** — tiles read directly; freshness via catalog (CAT-1/2) |
| ENC vector chart | S-57 `*.000` (or `.zip` cell bundle) | `enc/` | `helm-server` via `HELM_ENC_ROOT` | OpenCPN S-52 → PNG on `/chart` | **SENC compile** — OpenCPN builds `~/.helm/runtime/senc/<hash>_<CELL>.S57`; the `<hash>` fingerprints the source, so a changed cell auto-rebuilds |
| GeoJSON overlay | `*.geojson` | `overlays/` | `helm-server` / manifest | MapLibre vector layer | **None** — served as-is |

All three converge at MapLibre for final compositing into the FUSE-2 layer cake.

**On the "DB refresh/sync" question:** it is real, but only for ENC — and it already exists,
inherited from vanilla OpenCPN as the SENC compile. Raster tiles need no compile. Their
equivalent "is this current / what's loaded" need is the **catalog + freshness** surface,
which is CAT-1 (`/catalog` staleness) and CAT-2 (UI banners), not a database rebuild.

## Importer contract (`helm chart import`)

`helm.chart_intake.import.v1`. INTAKE-2 owns this.

- **Type sniffing by content, not extension** — PMTiles magic header, SQLite/MBTiles
  `metadata` table, S-57 `.000` DSID, GeoJSON `FeatureCollection`. A mislabeled file is
  rejected loudly, not silently misfiled.
- **Route to the matching subdir** under `HELM_CHART_LIBRARY`.
- **Validate before placing** — container/schema valid, bbox derivable. Tile packs run the
  existing sidecar checks; a sat-first bundle would satisfy `region_bundle_sat_first`.
- **No silent overwrite** — a name collision fails with a named error unless `--replace`.
- **Write a sidecar** (`<stem>.metadata.json`) capturing source label, license, and import
  date — never a private absolute path (existing private-path allow-listing applies).
- **Offline & idempotent** — no network; re-importing the same file is a no-op.

## Auto-discovery (helm-packd)

`helm-packd` and the `pipeline/mbtiles_server.py` oracle scan `HELM_CHART_LIBRARY/tiles/`
and expose every `*.mbtiles`/`*.pmtiles` by filename stem, honoring sidecars — retiring the
hand-wired `HELM_MBTILES_PACKS` map for the common case (the explicit map stays as an
advanced override). `/catalog` reflects whatever is in the library, no restart. INTAKE-3.

## Chart Library panel (cockpit)

`helm.chart_intake.library.v1`. INTAKE-5 owns this. Import (drag-drop / file-picker →
importer), list everything loaded (type, coverage bbox, freshness), enable/disable/remove
per pack. Reuses CAT-1/CAT-2 for the stale/gap/missing signals. This is the piece that
turns "hand-edited server + shell scripts" into a customer-usable flow.

## Failure rules

- Unknown/mislabeled file type → rejected with the detected-vs-claimed mismatch named; never
  misfiled.
- Name collision → fail closed unless `--replace`; never silent overwrite.
- Private filesystem paths → never written to sidecars or exposed in `/catalog`.
- A missing/empty library → the app still renders (empty base), and says so; it never fakes
  a green "charts loaded" state.
- ENC cell present but SENC compile fails → surfaced as a loud error + catalog status, not a
  blank chart pretending success.

## Non-goals

- Collapsing ENC and tile storage into one folder shape (they are different data models).
- Routing customer tiles through OpenCPN's `ChartMbTiles` (dead by design — see above).
- Server-fetching or hosting proprietary packs (BYO only — see docs/LEGAL.md).
- Downloading/estimating new packs — that is the existing offline download drawer, a
  different surface from importing files the customer already has.

## Code anchors

- Tile serving / auto-scan: `engine/vendor/cli/helm_packd.cpp` (readdir scan ~L567),
  `pipeline/mbtiles_server.py` (`HELM_MBTILES_DIR`, filename-stem discovery)
- ENC load + SENC: `helm_server`/`helm_tiles` (`HELM_ENC`/`HELM_ENC_ROOT`),
  OpenCPN SENC at `~/.helm/runtime/senc/`
- OpenCPN MBTiles (intentionally unused): `gui/include/gui/mbtiles.h`
- Overlays: `docs/proposals/interfaces/layer-manifest-v1.md`, LAYER-4 drop-folder
- Freshness surface: CAT-1 (`/catalog` staleness), CAT-2 (UI banners)
- Pipeline overview: `docs/CHART-PIPELINE.md`, ports in `docs/PORTS.md`
