# User overlay layers — drop-folder GeoJSON

Helm can render your own GeoJSON as chart overlays. Drop a `.geojson` file into the user layers
folder, reload, and it appears in the map's **overlay** band (above the chart, below weather/AIS).

This is the LAYER-4 productization of the layer pipeline:

- **LAYER-1** — `helm-packd` / `pipeline/layer_inventory.py` scans the drop folder and publishes it
  as `helm.layer.manifest.v1` at `GET /layer-manifest`
  (see [layer-manifest-v1.md](proposals/interfaces/layer-manifest-v1.md)).
- **LAYER-2** — `web/layer-manifest.js` fetches the manifest and injects each overlay as a MapLibre
  source + layer, placed in its FUSE-2 draw band; a **Cmd-K → "Reload user overlay layers"**
  command reloads without a page refresh.
- **LAYER-4** — `pipeline/user_layers.py` makes the drop folder exist, self-document, ship a working
  example, and surface invalid files instead of silently dropping them.

## The folder

```
~/.helm/data/layers/
```

Overridable with `HELM_USER_DATA_ROOT` (or `$HELM_CONFIG/data`). The local pack server creates the
folder, writes a `README.md`, and seeds `example-harbor-notes.geojson` the first time it starts.
You can also set it up (or re-check it) directly:

```
python3 pipeline/user_layers.py            # create + document + seed the example
python3 pipeline/user_layers.py --check    # report any *.geojson that is not valid GeoJSON
python3 pipeline/user_layers.py --root DIR # use a non-default user-data root
```

Setup never overwrites your files: the README refreshes, but your `*.geojson` / `*.metadata.json`
are left untouched, and the example is only seeded into a brand-new empty folder.

## What is accepted

- A GeoJSON **FeatureCollection** in a `*.geojson` file. Geometry draws as:
  - Point / MultiPoint → circles
  - LineString / MultiLineString → lines
  - Polygon / MultiPolygon → filled area + outline
- Files beginning with `.` and non-`.geojson` files are ignored.
- A file that is not valid JSON / not GeoJSON is **skipped and reported** — on pack-server startup
  and via `--check` — so it never silently disappears from the manifest.

## Optional sidecar metadata

Put a `<name>.metadata.json` next to `<name>.geojson` to control the layer. All fields optional:

| Field | Meaning | Default |
|---|---|---|
| `id` | Stable layer id | slug of the file name |
| `title` | Display name | humanized file name |
| `tier` | Draw band: `basemap` \| `enc` \| `overlay` \| `weather` \| `nav` (invalid → `overlay`) | `overlay` |
| `kind` | Free-form category hint | `geojson` |
| `source.label` / `source.license` | Provenance shown to the user | `owned` / `private-local` |
| `inspection.mode` | How feature taps behave | `feature-properties` |

Example:

```json
{
  "id": "harbor-notes",
  "title": "Harbor notes",
  "tier": "overlay",
  "source": { "label": "owned", "license": "private-local" },
  "inspection": { "mode": "feature-properties" }
}
```

## Security

Sidecar metadata is treated as **public**. Filesystem paths and secret-looking keys
(`private_path`, `path`, `file_path`, `api_key`, `token`, …) are stripped and never published in
the manifest, and `/user-data/` file serving is path-traversal guarded. Do not use this folder to
hide secrets.

## Troubleshooting

- **A layer doesn't appear.** Run `python3 pipeline/user_layers.py --check` — it lists any invalid
  `*.geojson`. The pack server logs the same warnings on startup.
- **Edits don't show.** The manifest is read on demand; run **Cmd-K → "Reload user overlay layers"**
  or reload the page.

## Tests

- `python3 pipeline/test_user_layers.py` — folder setup, idempotency/no-clobber, the seeded sample
  round-tripping through `build_layer_manifest`, and invalid-file detection.
- `python3 pipeline/test_layer_inventory.py`, `pipeline/test_helm_packd_contract.py` — manifest
  build + endpoint contract. `web/test/layer-manifest.test.cjs` — client rendering (LAYER-2).
