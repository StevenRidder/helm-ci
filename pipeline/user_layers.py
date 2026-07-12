#!/usr/bin/env python3
"""User drop-folder GeoJSON overlays (LAYER-4).

Make ~/.helm/data/layers a functional, self-documenting drop folder for user GeoJSON overlays
that are surfaced by helm.layer.manifest.v1 (LAYER-1) and rendered by web/layer-manifest.js
(LAYER-2):

  * ensure_user_layers_dir(root) — create the folder + a Helm-owned README, and seed a working
    example the first time. Idempotent; never clobbers a user's *.geojson / *.metadata.json.
  * check_user_layers(root)      — report layers/*.geojson that are not valid GeoJSON so a broken
    file surfaces instead of silently vanishing from the manifest (fail-fix-early).

CLI:  python3 pipeline/user_layers.py [--root DIR] [--check]

The user-data root defaults to the same resolver the manifest builder uses
(HELM_USER_DATA_ROOT / $HELM_CONFIG/data / ~/.helm/data).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional, Tuple

try:
    from layer_inventory import _default_user_data_root
except ImportError:  # pragma: no cover - allow running as a bare script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from layer_inventory import _default_user_data_root

README_NAME = "README.md"
SAMPLE_STEM = "example-harbor-notes"

# Bump when the README/sample content changes so ensure() refreshes the Helm-owned README.
README_MARKER = "<!-- helm-user-layers-readme v1 -->"

README_BODY = README_MARKER + """
# Helm user overlay layers — drop folder

Drop GeoJSON files in this folder and they appear as overlays on the Helm chart.

## Quick start
1. Copy a `.geojson` file into this folder (`~/.helm/data/layers/`).
2. In Helm, press **Cmd-K** and run **"Reload user overlay layers"** (or reload the page).
3. Your features draw in the **overlay** band — above the chart, below weather/AIS.

`example-harbor-notes.geojson` here is a working example you can copy or delete.

## What is accepted
- A GeoJSON **FeatureCollection** in a `*.geojson` file. Geometry draws as:
  - Point / MultiPoint → circles
  - LineString / MultiLineString → lines
  - Polygon / MultiPolygon → filled area + outline
- Files starting with `.` and non-`.geojson` files are ignored.
- A file that is not valid JSON / not GeoJSON is **skipped and reported** (see Troubleshooting) —
  it does not silently disappear.

## Optional sidecar metadata
Put a `<name>.metadata.json` next to `<name>.geojson` to control how the layer is labeled and
placed. Every field is optional:

    {
      "id": "harbor-notes",
      "title": "Harbor notes",
      "tier": "overlay",
      "kind": "points",
      "source": { "label": "owned", "license": "private-local" },
      "inspection": { "mode": "feature-properties" }
    }

- `tier` — one of basemap | enc | overlay | weather | nav (default **overlay**; invalid → overlay).
- `source.label` / `source.license` — shown as the layer's provenance (default owned / private-local).
- `inspection.mode` — how taps are handled (default `feature-properties`).

Defaults with no sidecar: `id` = the file name, `title` = a humanized file name, `tier` = overlay,
`source` = owned / private-local.

## Security
Sidecar metadata is treated as **public**. Filesystem paths and secret-looking keys
(`private_path`, `path`, `file_path`, `api_key`, `token`, …) are stripped and never published in
the manifest. Do not use this folder to hide secrets.

## Troubleshooting
If a file does not appear, validate the folder:

    python3 pipeline/user_layers.py --check

It lists any `*.geojson` that is not valid GeoJSON. The pack server also logs these on startup.
"""

SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [178.4419, -18.1416]},
            "properties": {"name": "Example anchorage", "note": "Delete example-harbor-notes.* once you add your own layers."},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [178.4256, -18.1281]},
            "properties": {"name": "Example hazard note", "note": "Sample user overlay feature."},
        },
    ],
}

SAMPLE_SIDECAR = {
    "id": "example-harbor-notes",
    "title": "Example harbor notes",
    "tier": "overlay",
    "kind": "points",
    "source": {"label": "example", "license": "sample-delete-me"},
    "inspection": {"mode": "feature-properties"},
}

GEOJSON_TYPES = {
    "FeatureCollection", "Feature", "Point", "LineString", "Polygon",
    "MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection",
}


def _layers_dir(root: Optional[str]) -> str:
    base = os.path.expanduser(root or _default_user_data_root())
    return os.path.join(base, "layers")


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _has_user_geojson(layers_dir: str) -> bool:
    try:
        names = os.listdir(layers_dir)
    except OSError:
        return False
    return any(n.lower().endswith(".geojson") and not n.startswith(".") for n in names)


def ensure_user_layers_dir(root: Optional[str] = None) -> dict:
    """Create the user-layers drop folder + README, seeding a sample when it is brand new.

    Idempotent. Never overwrites a user's *.geojson / *.metadata.json. Returns a summary dict.
    """
    layers_dir = _layers_dir(root)
    created = not os.path.isdir(layers_dir)
    os.makedirs(layers_dir, exist_ok=True)

    # The README is Helm-owned: (re)write it when missing or stale so the contract stays current.
    readme_path = os.path.join(layers_dir, README_NAME)
    readme_current = False
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, encoding="utf-8") as handle:
                readme_current = README_MARKER in handle.read(len(README_MARKER) + 4)
        except OSError:
            readme_current = False
    if not readme_current:
        with open(readme_path, "w", encoding="utf-8") as handle:
            handle.write(README_BODY)

    # Seed the example only for a brand-new folder that has no user geojson yet.
    seeded = False
    if created and not _has_user_geojson(layers_dir):
        _write_json(os.path.join(layers_dir, SAMPLE_STEM + ".geojson"), SAMPLE_GEOJSON)
        _write_json(os.path.join(layers_dir, SAMPLE_STEM + ".metadata.json"), SAMPLE_SIDECAR)
        seeded = True

    return {
        "layers_dir": layers_dir,
        "created": created,
        "readme_refreshed": not readme_current,
        "sample_seeded": seeded,
    }


def _geojson_problem(doc) -> Optional[str]:
    if not isinstance(doc, dict):
        return "top-level value is not a JSON object"
    gtype = doc.get("type")
    if gtype == "FeatureCollection":
        features = doc.get("features")
        if not isinstance(features, list):
            return "FeatureCollection has no \"features\" array"
        if not features:
            return "FeatureCollection has zero features (nothing to draw)"
        return None
    if gtype in GEOJSON_TYPES:
        return None  # a single Feature/geometry is acceptable
    return "missing or unrecognized GeoJSON \"type\" (expected FeatureCollection)"


def check_user_layers(root: Optional[str] = None) -> List[Tuple[str, str]]:
    """Return [(filename, problem)] for layers/*.geojson that are not valid GeoJSON.

    Surfaces files that would otherwise be silently dropped from the manifest.
    """
    layers_dir = _layers_dir(root)
    problems: List[Tuple[str, str]] = []
    try:
        names = sorted(os.listdir(layers_dir))
    except OSError:
        return problems
    for name in names:
        if name.startswith(".") or not name.lower().endswith(".geojson"):
            continue
        path = os.path.join(layers_dir, name)
        try:
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            problems.append((name, "not valid JSON: " + str(exc)))
            continue
        problem = _geojson_problem(doc)
        if problem:
            problems.append((name, problem))
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Set up and validate the Helm user overlay drop folder (~/.helm/data/layers)."
    )
    ap.add_argument("--root", help="User-data root (default: HELM_USER_DATA_ROOT / $HELM_CONFIG/data / ~/.helm/data).")
    ap.add_argument("--check", action="store_true", help="Only report invalid layers/*.geojson; create nothing.")
    args = ap.parse_args(argv)

    if args.check:
        problems = check_user_layers(args.root)
        if not problems:
            print("user layers: all *.geojson files are valid GeoJSON")
            return 0
        for name, problem in problems:
            print(f"user layers: {name}: {problem}", file=sys.stderr)
        return 1

    summary = ensure_user_layers_dir(args.root)
    print(f"user layers: {summary['layers_dir']}")
    print(
        f"  folder {'created' if summary['created'] else 'exists'}"
        f"; README {'written' if summary['readme_refreshed'] else 'current'}"
        f"; sample {'seeded' if summary['sample_seeded'] else 'skipped'}"
    )
    for name, problem in check_user_layers(args.root):
        print(f"  WARNING {name}: {problem}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
