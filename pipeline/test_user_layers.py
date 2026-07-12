#!/usr/bin/env python3
"""Tests for LAYER-4 user drop-folder setup (pipeline/user_layers.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from user_layers import (
    README_NAME,
    SAMPLE_STEM,
    check_user_layers,
    ensure_user_layers_dir,
)
from layer_inventory import VALID_MANIFEST_TIERS, build_layer_manifest


def _feature_collection(props):
    return json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [178.4, -18.1]},
            "properties": props,
        }],
    })


class UserLayersTest(unittest.TestCase):
    def test_ensure_creates_folder_readme_and_valid_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = ensure_user_layers_dir(tmp)
            layers_dir = Path(tmp) / "layers"
            self.assertTrue(summary["created"])
            self.assertTrue(summary["sample_seeded"])
            self.assertTrue((layers_dir / README_NAME).is_file())
            self.assertTrue((layers_dir / (SAMPLE_STEM + ".geojson")).is_file())
            self.assertTrue((layers_dir / (SAMPLE_STEM + ".metadata.json")).is_file())
            doc = json.loads((layers_dir / (SAMPLE_STEM + ".geojson")).read_text())
            self.assertEqual(doc["type"], "FeatureCollection")
            self.assertTrue(doc["features"])
            self.assertEqual(check_user_layers(tmp), [])  # seeded sample is valid

    def test_seeded_sample_appears_in_layer_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_user_layers_dir(tmp)
            manifest = build_layer_manifest(tmp)
            self.assertEqual(manifest["schema"], "helm.layer.manifest.v1")
            layer = next(l for l in manifest["layers"] if l["id"] == "example-harbor-notes")
            self.assertEqual(layer["tier"], "overlay")
            self.assertIn(layer["tier"], VALID_MANIFEST_TIERS)
            self.assertEqual(layer["format"], "geojson")
            self.assertEqual(layer["url"], "/user-data/layers/example-harbor-notes.geojson")
            self.assertEqual(layer["source"]["label"], "example")

    def test_idempotent_and_never_clobbers_user_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_user_layers_dir(tmp)
            layers_dir = Path(tmp) / "layers"
            # User edits the sample and drops their own file.
            (layers_dir / (SAMPLE_STEM + ".geojson")).write_text(_feature_collection({"mine": True}))
            (layers_dir / "mine.geojson").write_text(_feature_collection({"n": 1}))
            summary = ensure_user_layers_dir(tmp)
            self.assertFalse(summary["created"])
            self.assertFalse(summary["sample_seeded"])  # never re-seeds over existing content
            self.assertIn('"mine"', (layers_dir / (SAMPLE_STEM + ".geojson")).read_text())
            self.assertTrue((layers_dir / "mine.geojson").is_file())

    def test_check_reports_invalid_geojson_but_not_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            layers_dir = Path(tmp) / "layers"
            layers_dir.mkdir(parents=True)
            (layers_dir / "broken.geojson").write_text("{ not json")
            (layers_dir / "not-geo.geojson").write_text('{"hello": "world"}')
            (layers_dir / "empty.geojson").write_text('{"type": "FeatureCollection", "features": []}')
            (layers_dir / "ok.geojson").write_text(_feature_collection({"name": "x"}))
            (layers_dir / ".hidden.geojson").write_text("{ not json")  # hidden -> ignored
            problems = dict(check_user_layers(tmp))
            self.assertIn("broken.geojson", problems)
            self.assertIn("not-geo.geojson", problems)
            self.assertIn("empty.geojson", problems)
            self.assertNotIn("ok.geojson", problems)
            self.assertNotIn(".hidden.geojson", problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)
