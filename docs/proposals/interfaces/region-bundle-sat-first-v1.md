# Interface: Sat-first Region Bundle Profile v1

Schema family: `helm.region_bundle.*.v1`<br>
Profile: `helm.region_bundle.profile.sat_first.v1`<br>
Base manifest: `helm.region_bundle.manifest.v1` (OFFLINE-8)<br>
Producer: `helm-packd`, `pipeline/region_bundle.py`<br>
Consumers: offline download drawer (OFFLINE-L-3), MapLibre client (`offline-packs.js`), bake tooling (OFFLINE-L-2)<br>
Deliverable: `helm-northstar-fused-map` / milestone `p1-offline-packs`<br>
Task: OFFLINE-L-1

## Purpose

Define the **sat-first** offline region bundle profile for the Helm North Star fused map. A sat-first bundle treats **satellite raster pixels as the only required offline base layer**. ENC/chart snapshots, depth GeoJSON, places, and weather remain **optional overlays** that must never substitute for missing satellite coverage.

This profile does not replace `helm.region_bundle.manifest.v1`. It constrains how producers populate that manifest and how clients interpret component roles for the FUSE-2 layer cake.

## Owns

- Required vs optional component roles for sat-first offline packs.
- Draw-order hints aligned with `web/SHELL.md` North Star bands (basemap → enc → overlays → weather → nav).
- Pack-selection rules when building a bundle from `/catalog`.
- Validation rules clients and bake scripts can fail closed on.
- Example Fiji fixture shape used by OFFLINE-20 / QA-L-1 proofs.

## Does Not Own

- Tile download, retention, or eviction policy (OFFLINE-L-3 drawer).
- ENC bake execution (OFFLINE-L-2).
- Online basemap providers (Navionics, Google, Bing, ArcGIS).
- Chart portrayal semantics (OpenCPN PNG factory remains authoritative for live ENC).
- Proprietary pack licensing beyond public catalog metadata.

## Relationship to generic region bundles

| Layer | Generic OFFLINE-8 | Sat-first profile (this doc) |
|---|---|---|
| Manifest schema | `helm.region_bundle.manifest.v1` | same |
| Required components | any selected packs | **≥1 `basemap` satellite raster** |
| Chart raster | optional | optional overlay (`chart` role) |
| Depth GeoJSON | optional dataset | optional overlay (`depth` role) |
| Primary offline UX | chart-first or mixed | **satellite pixels fill the viewport**; chart is selective overlay |

## Component roles

Roles come from catalog `pack_role` / `kind` normalization in `pipeline/region_bundle.py` and `helm_packd.cpp`.

| Role | Required | Typical source | Map band (FUSE-2) | Notes |
|---|---|---|---|---|
| `basemap` | **yes (exactly one primary)** | Satellite MBTiles/PMTiles (`kind=satellite`) | basemap | Inserts `helm-offline-active-pack` before `enc-chart` at runtime. |
| `chart` | no | S-52 snapshot PMTiles from OpenCPN PNG bake | enc | Must not be the only raster in a sat-first bundle. |
| `depth` | no | `extract_depth.sh` GeoJSON | enc (vector) | Depth-on-sat paints above basemap raster. |
| `places` | no | User drop-folder GeoJSON | nav | Optional POI overlay. |
| `vector` / other | no | MVT, aids, etc. | overlays | Future; must not claim basemap authority. |

## Manifest extensions

Sat-first bundles use the base manifest unchanged and add an optional top-level profile block:

```json
{
  "schema": "helm.region_bundle.manifest.v1",
  "profile": "sat_first",
  "id": "fiji-sat-first",
  "title": "Fiji — satellite-first offline region",
  "generated_at": "2026-07-08T06:00:00Z",
  "request": {
    "packs": ["fiji-sat", "fiji-s52-day"],
    "bbox": "178.0,-18.5,179.0,-17.5",
    "minzoom": 8,
    "maxzoom": 14,
    "radius_nm": 2.0,
    "include_tiles": "0"
  },
  "corridor": {},
  "prefetch": {},
  "components": [],
  "summary": {
    "roles": {"basemap": 1, "chart": 1},
    "stale": 0,
    "out_of_coverage": 0,
    "warnings": 0
  }
}
```

Rules:

- `profile` when present must be the literal string `sat_first`.
- `summary.roles.basemap` must be `>= 1`.
- Exactly one basemap component should be marked `primary: true` when multiple satellite packs exist (regional mosaics). If omitted, the first `basemap` component in stable sort order is primary.
- Optional `draw_order` array lists component ids bottom → top within the enc/overlay bands; clients may ignore unknown ids.

### Basemap component (required)

```json
{
  "id": "pack:fiji-sat",
  "pack_id": "fiji-sat",
  "role": "basemap",
  "primary": true,
  "kind": "satellite",
  "type": "raster",
  "format": "jpg",
  "container": "pmtiles",
  "bounds_array": [177.8, -18.2, 179.2, -16.8],
  "minzoom": 8,
  "maxzoom": 14,
  "pmtiles_url": "http://127.0.0.1:9120/fiji-sat.pmtiles",
  "source_info": {"label": "Sentinel-2 cloudless (EOX)", "license": "CC-BY-4.0"},
  "inspection": {"mode": "raster_metadata", "semantic_objects": "unavailable"},
  "status": {"freshness": "fresh", "coverage": "complete", "states": ["current"]},
  "fingerprint": "…"
}
```

### Chart overlay component (optional, OFFLINE-L-2)

```json
{
  "id": "pack:fiji-s52-day",
  "pack_id": "fiji-s52-day",
  "role": "chart",
  "kind": "chart",
  "renderer": "s52",
  "palette": "day",
  "container": "pmtiles",
  "format": "png",
  "display_category": "std",
  "pmtiles_url": "http://127.0.0.1:9120/fiji-s52-day.pmtiles",
  "staleness": {"status": "fresh", "render_date": "2026-06-29T00:00:00Z"},
  "coverage": {"status": "partial", "gap_count": 10},
  "status": {"freshness": "fresh", "coverage": "partial", "states": ["current"]},
  "fingerprint": "…"
}
```

Chart components are **verification-only overlays**: they do not satisfy Done/merge authority and must not be selected as the offline basemap in `offline-packs.js`.

### Depth dataset component (optional)

```json
{
  "id": "depth:fiji-depare",
  "dataset_id": "fiji-depare",
  "role": "depth",
  "kind": "geojson",
  "format": "geojson",
  "url": "/user-data/depth/fiji-depare.geojson",
  "feature_count": 1204,
  "source_info": {"label": "NOAA ENC extract", "license": "public-domain"},
  "status": {"freshness": "unknown", "coverage": "unknown", "states": ["current"]},
  "fingerprint": "…"
}
```

## Pack selection (producer rules)

When `GET /bundle` or `region_bundle.py` builds a sat-first bundle:

1. Require `profile=sat_first` query flag **or** `bundle_profile=sat_first` in the POST body (future).
2. Select **all** catalog packs matching the route/bbox query, then validate:
   - at least one pack maps to role `basemap`;
   - if zero basemap packs match, return `error` with code `missing_basemap` — do not silently promote a chart pack to basemap.
3. Prefer the highest-resolution satellite pack as `primary` when multiple basemap candidates overlap (larger `maxzoom`, then larger `size_bytes`).
4. Include chart packs only when explicitly listed in `packs=` or when `include_chart=1` is set (default **off** for sat-first profile).
5. Attach depth/places datasets from `/layers` inventory when present; never fabricate placeholder datasets.

## Client behavior (`offline-packs.js`)

- Activating a sat-first bundle must bind **basemap** raster to `helm-offline-active-pack`.
- Chart raster from the same bundle toggles `enc-chart` visibility; it does not replace the basemap source.
- Raster inspect UI must report `semantic_objects: unavailable` for basemap taps (pixels only).
- Out-of-coverage taps show the existing honest message; chart gaps must not hide basemap holes.

## Failure rules

| Condition | HTTP / status | Code |
|---|---|---|
| No satellite pack in catalog for bbox/route | 422 | `missing_basemap` |
| Profile sat_first but only chart packs selected | 422 | `chart_not_basemap` |
| Private filesystem path in component | strip / reject | `private_path_leak` |
| Basemap stale | 200 with warning | `pack_stale` in component warnings |
| Basemap out of coverage | 200 with state | `out_of_coverage` |

Services must not return `ok` with an empty basemap slot for sat-first requests.

## Validation

Reference validator: `pipeline/region_bundle_sat_first.py` → `validate_sat_first_bundle(manifest)`.

Tests: `python3 pipeline/test_region_bundle_sat_first.py`.

A bundle passes when:

- `schema == helm.region_bundle.manifest.v1`
- `profile` absent or `sat_first`
- `summary.roles.basemap >= 1`
- every `basemap` component has raster type and pmtiles/mbtiles container
- no component with role `chart` is marked `primary: true`

## Non-goals (this profile)

- Multi-region world basemap mosaics beyond one primary satellite pack.
- WebGPU ENC or CHART-13 vector portrayal.
- Automatic download scheduling (OFFLINE-L-3).
- Replacing SAT-1 online basemap memory with offline defaults.

## Code anchors

- Generic bundle builder: `pipeline/region_bundle.py`, `engine/vendor/cli/helm_packd.cpp`
- Offline pack UI: `web/offline-packs.js`
- Layer stack: `web/SHELL.md`, `web/tests/fuse-2-layer-order.test.js`
- Fiji proof: `web/test/e2e/offline20-sat-first-fiji.spec.js`, `scripts/verify-offline20-sat-first-fiji.sh`
- ENC depth extract: `pipeline/extract_depth.sh` (ENC-4)
- ENC bake execution (OFFLINE-L-2): `pipeline/bake_s52_region_pack.py`, end-to-end proof in
  `pipeline/test_offline_l2_enc_snapshot_bake.py`
