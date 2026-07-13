# Interface: Chart Intake & Library v1

Schema family: `helm.chart_intake.*.v1`<br>
Producer: `helm-server` (ENC scan) + `helm-packd` (tile scan) + a chart-index/rescan step<br>
Consumers: the MapLibre cockpit (Chart Library panel), `/catalog`, offline tooling<br>
Deliverable: `helm-northstar-fused-map` / milestone `p1-chart-intake`<br>
Tasks: INTAKE-1 (this spec) → INTAKE-2..8<br>
Related: [package-service-v1.md](package-service-v1.md), [region-bundle-sat-first-v1.md](region-bundle-sat-first-v1.md), [layer-manifest-v1.md](layer-manifest-v1.md), [chart-service-v1.md](chart-service-v1.md)

## Purpose

Define **one standard way a customer gets their own charts into Helm** — the "bring your
own charts" intake — across the two customer shapes we serve:

- **ENC-only customers** who navigate on official S-57 vector cells (the OpenCPN audience).
- **Sat-first customers** (the North Star default) who want satellite/raster pixels as the
  base with selective ENC/depth/aids overlays on top.

The model is **OpenCPN's, deliberately**: the customer keeps their charts in their own
folders, organized however they already organize them (e.g. `FIJI/`, `TONGA/`,
`COOK-ISLANDS/`, `PACIFIC/`), and **points Helm at the root(s)**. Helm scans **recursively**,
classifies each file **by type**, and indexes it **in place** — it never relocates the
customer's files. This is exactly how OpenCPN's *Options → Charts → Add Directory* works
today (`options.cpp:7027`), and it means a customer's existing ChartLocker/OpenCPN layout
works with **zero reorganization**.

Today Helm's intake works but through three unrelated, un-unified mechanisms: raster tile
packs are hand-wired via a `HELM_MBTILES_PACKS` env map, ENC via OpenCPN's SENC compile, and
GeoJSON overlays via the LAYER-4 drop-folder. This interface unifies the *intake surface*
(one "add a chart folder" action + one recursive scan + one Chart Library panel) **without**
collapsing the underlying per-type render/refresh paths, which are legitimately different.

## The load-bearing architecture decision

**OpenCPN stays strictly the S-52 ENC→PNG factory. Customer raster tile packs never route
through OpenCPN.**

OpenCPN ships a `ChartMbTiles` class (`gui/include/gui/mbtiles.h`) that *can* import and
render MBTiles natively — it's why dropping MBTiles into an OpenCPN chart folder "just works"
there. In Helm that code path is **deliberately dead**:

- None of the 8 engine patches (`engine/patches/0001..0008`) touch MBTiles or `ChartMbTiles`.
- The ENC-render engine (`helm_server` / `helm_tiles`) has **zero** MBTiles references — it
  only ever opens S-57 `.000` cells (`HELM_ENC` / `HELM_ENC_ROOT`).
- Raster tile packs are served by a **separate binary**, `helm-packd`
  (`engine/vendor/cli/helm_packd.cpp`, port 8091), straight to MapLibre over HTTP. OpenCPN
  never sees them.

Teaching OpenCPN's `ChartMbTiles` to handle customer tiles would be the **wrong layer** — it
would render pixels the ENC engine never receives, duplicating what MapLibre already
composites natively, with worse UX. **Extend `helm-packd` + the web UI, not OpenCPN's MBTiles
code.** This is "OpenCPN PNG stays the ENC factory; no WebGPU ENC, no CHART-13" made concrete.

## Chart roots & recursive scan (the OpenCPN model)

There is **no Helm-imposed folder shape**. The customer registers one or more **chart
roots** (default `~/.helm/charts/`, plus any external paths — e.g. an existing ChartLocker
directory), and organizes charts inside them by region, voyage, or whatever they like:

```text
<any chart root the customer registers>        # e.g. ~/.helm/charts/ or ~/Charts/
├─ FIJI/
│    ├─ Fiji_TCL2407_Navionics.mbtiles          # tile pack   -> helm-packd -> MapLibre
│    ├─ Fiji_TCL2407_BingSat.pmtiles            # tile pack   -> helm-packd -> MapLibre
│    ├─ NZ50xxxx.000                            # ENC cell    -> OpenCPN S-52 -> PNG
│    └─ my-fiji-anchorages.geojson              # overlay     -> layer manifest -> MapLibre
├─ TONGA/
│    └─ ...
└─ PACIFIC/
     └─ oceanic-overview.pmtiles
```

Rules, mirroring OpenCPN:

- **Recursive.** Registering a root indexes every recognized chart in its whole subtree
  (OpenCPN: `wxDIR_DEFAULT`, *"recurse into subdirs"*, `chartdbs.cpp:2315`). One root entry
  covers all your region subfolders.
- **Classify by type, index in place.** Each file is matched to a chart class and handed to
  the consumer that owns it. Files are **never moved or renamed**.
- **Region is the customer's organization, preserved.** Subfolder names (`FIJI/`, `TONGA/`)
  are surfaced as **groups** (see Chart Library panel), the direct analog of OpenCPN's Chart
  Groups (`chartdbs.h:469`, `options.cpp:3842`) — they never dictate storage.
- **Each consumer claims its own extensions from the same tree.** The ENC engine grabs
  `*.000` cells (already recursive via `HELM_ENC_ROOT`, `helm_tiles.cpp:366`); helm-packd
  grabs `*.mbtiles`/`*.pmtiles`; the overlay loader grabs `*.geojson`. They coexist in one
  folder with no conflict.

### Chart-type classification (extension registry)

Classification is **extension-based**, mirroring OpenCPN's `ChartClassDescriptor` registry
(`chartdbs.cpp:1349`), not deep content-sniffing — simpler and proven:

| Extension | Chart type | Read by | Rendered by | Refresh / "DB sync" |
|---|---|---|---|---|
| `*.mbtiles`, `*.pmtiles` | raster tile pack | `helm-packd` (recursive scan) | MapLibre raster layer | **None** — read directly; freshness via CAT-1 catalog staleness |
| `*.000` (+ `.001/.002...` updates) | S-57 ENC cell | `helm-server` via `HELM_ENC_ROOT` | OpenCPN S-52 -> PNG on `/chart` | **SENC compile** — `~/.helm/runtime/senc/<sha1(dir)>_<CELL>.S57`; rebuilt on version bump / newer edition / new update cell / newer mtime (OpenCPN `s57chart.cpp:2693`) |
| `*.geojson` | vector overlay | overlay loader / manifest | MapLibre vector layer | **None** — served as-is |

A light validation runs when a file is first indexed (container/schema opens, bbox
derivable); a file whose contents don't match its extension is flagged loudly in the
catalog, not silently trusted. All three types converge at MapLibre for final compositing
into the FUSE-2 layer cake.

## Chart index & rescan

Helm keeps a **chart index** (surfaced as `/catalog`) of everything found across the
registered roots — per chart: type, coverage bbox, edition/freshness, region/group. This is
the analog of OpenCPN's binary chart database + `ChartTableEntry` (`chartdbs.h`, DB v18).

- **Rescan trigger** mirrors OpenCPN's change detection: hash the registered tree
  (names/sizes/mtimes) and rebuild the index when it changes, plus an explicit **Rescan**
  action for "I just dropped files in" (OpenCPN's *Rebuild Chart Database* /
  `DetectDirChange`, `chartdbs.cpp:2045`). No process restart.
- **Freshness** is already computed for tile/overlay packs by **CAT-1** (`/catalog` +
  `/layer-manifest` staleness) and surfaced as banners by **CAT-2**. ENC freshness is the
  SENC rebuild above. So the "DB refresh/sync" a customer remembers from OpenCPN maps to two
  concrete things here: the SENC compile (ENC) and the catalog index + rescan (everything).

## Registering & indexing (INTAKE-2)

`helm.chart_intake.register.v1`. INTAKE-2 owns this — modeled on OpenCPN *Add Directory*,
**not** a file-relocating importer:

- **Register a chart root** (a folder the customer already has), or drop files into the
  default root. Recursive scan indexes them in place.
- **No file movement or renaming** — Helm indexes; the customer's layout is the source of
  truth (contrast the earlier v1 draft, which sorted files into type folders — removed).
- **Rescan** re-reads the tree and updates the index; a Rescan is idempotent.
- **Sidecars stay optional** — a `<stem>.metadata.json` next to a pack still supplies
  source/license/attribution and is honored, never a private absolute path.
- The one place Helm *writes* into a root is the download drawer (INTAKE-8) and the ENC
  depth extract (INTAKE-7); both deposit alongside the customer's files with sidecars.

## Recursive tile discovery (INTAKE-3)

`helm-packd` (and the `pipeline/mbtiles_server.py` oracle) scan the registered roots
**recursively** and expose every `*.mbtiles`/`*.pmtiles` found, honoring sidecars — retiring
the hand-wired `HELM_MBTILES_PACKS` map for the common case (the explicit map stays as an
advanced override). Today's scan is a **flat** single-directory `readdir`
(`helm_packd.cpp:~567`); INTAKE-3 makes it recursive to match the ENC engine, and wires the
rescan trigger above so `/catalog` reflects the library with no restart.

## Depth extraction on ENC index (INTAKE-7)

Indexing an ENC gives you the S-52 *chart* immediately (OpenCPN renders it), but the
**depth-on-satellite** overlay (depare/depcnt/soundg shading) is a *distinct* product
derived from the same cell by the ENC-4 depth pipeline. To make "add an ENC -> depth just
appears" true, indexing a new/updated `*.000` runs that extraction (honoring the pyogrio /
no-system-GDAL constraint) and registers the resulting GeoJSON via the layer manifest with a
depth-provenance sidecar. Idempotent; a cell that can't be extracted fails loud (named error
+ catalog status), never a silent skip. INTAKE-7 wires the existing ENC-4 extraction into
the index flow.

## Download convergence (INTAKE-8)

The "lasso an area -> download PMTiles" offline drawer and file import are **one library, two
front doors**. The drawer deposits its output into a registered chart root with a sidecar
(source, license, bbox, download date), so a downloaded pack and a customer's own file land
in the same tree and the recursive discovery above picks it up with no extra step — the
lasso result immediately becomes a toggleable library layer. INTAKE-8. (Supersedes the
original v1 stance that kept download and import as separate surfaces. Fetching the *bytes*
is still the drawer's job; INTAKE-8 only converges *where they land*.)

## Chart Library panel (cockpit) — INTAKE-5

`helm.chart_intake.library.v1`. INTAKE-5 owns the cockpit UX, baselined on OpenCPN's chart
management (`options.cpp`, `chartgroupsui.cpp`, `piano.cpp`) but adapted for touch:

- **Add / manage chart folders** — a directory picker that registers a root, the list of
  registered roots, and a **Rescan** button (OpenCPN's *Add Directory* + *Rebuild Chart
  Database*, `options.cpp:7027, 2573`). Recursion is automatic; no toggle.
- **Region groups** — surface subfolder/region groups as selectable tabs/filters, the direct
  analog of OpenCPN Chart Groups ("FIJI", "TONGA"), so a customer opens the region they're in.
- **Per-chart info & state** — for each indexed chart: type, coverage bbox, edition/freshness
  (from CAT-1), enable/disable/remove, and honest stale/gap/missing banners (CAT-2). Mirrors
  OpenCPN's on-demand chart-info popup (`chartdbs.cpp:1579`).
- **First-run empty state** — when no roots are registered, prompt to add a chart folder
  (OpenCPN's empty *Chart Files* tab).

This turns "hand-edited server + shell scripts" into a customer-usable flow, and gives the
sat-first cockpit the chart-management surface OpenCPN users already expect.

## Failure rules

- File contents don't match extension → flagged in the catalog with the mismatch named;
  never silently trusted.
- Private filesystem paths → never written to sidecars or exposed in `/catalog`.
- A missing/empty library → the app still renders (empty base) and says so; it never fakes a
  green "charts loaded" state.
- ENC cell present but SENC compile fails → surfaced as a loud error + catalog status, not a
  blank chart pretending success.
- A registered root that disappears → indexed charts marked unavailable with a named reason,
  not silently dropped.

## Non-goals

- **Reorganizing the customer's files.** Helm indexes in place; it never moves, renames, or
  imposes a type-folder layout on the customer's charts.
- Routing customer tiles through OpenCPN's `ChartMbTiles` (dead by design — see above).
- Server-fetching or hosting proprietary packs (BYO only — see docs/LEGAL.md).
- **Weather.** Environmental/met-ocean data is a separate pipeline (the WX system: Open-Meteo
  bakes -> `helm-envd` packs) with its own storage and refresh. Chart intake is charts, depth,
  and overlays only; it never ingests or implies weather.
- Fetching *new* pack bytes from a provider (still the download drawer's job; INTAKE-8 only
  converges where its output lands).

## Code anchors

**Helm:**
- Tile serving / scan (make recursive): `engine/vendor/cli/helm_packd.cpp` (readdir ~L567),
  `pipeline/mbtiles_server.py` (`HELM_MBTILES_DIR`, filename-stem discovery)
- ENC load + recursive cell scan: `helm_server`/`helm_tiles.cpp:366` (`HELM_ENC`/`HELM_ENC_ROOT`),
  OpenCPN SENC at `~/.helm/runtime/senc/`
- Overlays: `docs/proposals/interfaces/layer-manifest-v1.md`, LAYER-4 drop-folder
- Depth-on-index (INTAKE-7): `pipeline/chart_intake.py` depth pass -> `user-data/enc-depth/<CELL>/`;
  manifest scan in `engine/vendor/cli/helm_packd_manifest.hpp` + `pipeline/layer_inventory.py`
- Freshness: CAT-1 (`/catalog` + `/layer-manifest` staleness), CAT-2 (UI banners)
- Pipeline overview: `docs/CHART-PIPELINE.md`; ports in `docs/PORTS.md`

**OpenCPN baseline (vendored source, for mirroring — GPL, not linked):**
- Recursive scan: `gui/src/chartdbs.cpp:2315` (`SearchDirAndAddCharts`, `wxDIR_DEFAULT`)
- Extension registry: `gui/src/chartdbs.cpp:1349` (`UpdateChartClassDescriptorArray`)
- Chart DB + change detection: `gui/src/chartdbs.cpp:1804, 2045` (`Update`, `DetectDirChange`)
- SENC naming/staleness: `gui/src/s57chart.cpp:2608, 2693`
- MBTiles (intentionally unused): `gui/include/gui/mbtiles.h`
- Add-Directory UI: `gui/src/options.cpp:7027, 2573`
- Chart Groups: `gui/include/gui/chartdbs.h:469`, `gui/src/options.cpp:3842`
- Piano selector / quilt: `gui/src/piano.cpp`, `gui/src/chcanv.cpp:13990`
- Chart info popup: `gui/src/chartdbs.cpp:1579`
