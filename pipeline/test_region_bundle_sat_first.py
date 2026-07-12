#!/usr/bin/env python3
"""Tests for OFFLINE-L-1 sat-first region bundle profile."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from region_bundle import build_region_bundle
from region_bundle_sat_first import (
    SatFirstBundleError,
    annotate_sat_first_bundle,
    validate_sat_first_bundle,
)
from test_region_bundle import sample_catalog


class SatFirstBundleTests(unittest.TestCase):
    def _sat_first_bundle(self):
        catalog = sample_catalog()
        bundle = build_region_bundle(
            catalog,
            {
                "packs": ["sat,chart"],
                "bbox": ["178.0,-18.0,179.0,-17.0"],
                "minzoom": ["8"],
                "maxzoom": ["12"],
                "bundle_id": ["fiji-sat-first"],
                "title": ["Fiji sat-first"],
            },
        )
        return annotate_sat_first_bundle(bundle)

    def test_valid_sat_first_bundle_passes(self):
        bundle = self._sat_first_bundle()
        result = validate_sat_first_bundle(bundle, require_profile=True)
        self.assertTrue(result["valid"])
        self.assertEqual(result["basemap_count"], 1)
        self.assertEqual(result["primary_basemap_id"], "pack:sat")
        self.assertEqual(result["chart_count"], 1)

    def test_missing_basemap_fails(self):
        catalog = sample_catalog()
        del catalog["sat"]
        bundle = build_region_bundle(
            catalog,
            {"packs": ["chart"], "bbox": ["178.0,-18.0,179.0,-17.0"]},
        )
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("missing_basemap", str(ctx.exception))

    def test_chart_only_without_sat_fails(self):
        catalog = sample_catalog()
        bundle = build_region_bundle(
            catalog,
            {"packs": ["chart"], "bbox": ["178.0,-18.0,179.0,-17.0"]},
        )
        with self.assertRaises(SatFirstBundleError):
            validate_sat_first_bundle(bundle)

    def test_chart_marked_primary_fails(self):
        bundle = self._sat_first_bundle()
        bundle = copy.deepcopy(bundle)
        for component in bundle["components"]:
            if component.get("role") == "chart":
                component["primary"] = True
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("chart_not_basemap", str(ctx.exception))

    def test_non_satellite_raster_cannot_satisfy_basemap(self):
        bundle = copy.deepcopy(self._sat_first_bundle())
        basemap = next(c for c in bundle["components"] if c.get("role") == "basemap")
        basemap["kind"] = "weather"
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("invalid_basemap", str(ctx.exception))

    def test_private_path_variants_fail_closed_recursively(self):
        variants = (
            "_path",
            "path",
            "file_path",
            "filepath",
            "local_path",
            "private_path",
            "directory",
            "dir",
        )
        for key in variants:
            with self.subTest(key=key):
                bundle = copy.deepcopy(self._sat_first_bundle())
                basemap = next(c for c in bundle["components"] if c.get("role") == "basemap")
                basemap.setdefault("source_info", {})["nested"] = {key: "/private/pack.mbtiles"}
                with self.assertRaises(SatFirstBundleError) as ctx:
                    validate_sat_first_bundle(bundle)
                self.assertIn("private_path_leak", str(ctx.exception))

    def test_summary_basemap_zero_fails(self):
        bundle = copy.deepcopy(self._sat_first_bundle())
        bundle["summary"]["roles"]["basemap"] = 0
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("missing_basemap", str(ctx.exception))

    def test_summary_basemap_count_must_match_components(self):
        bundle = copy.deepcopy(self._sat_first_bundle())
        bundle["summary"]["roles"]["basemap"] = 2
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("basemap_count_mismatch", str(ctx.exception))

    def test_multiple_primary_basemaps_fail(self):
        bundle = copy.deepcopy(self._sat_first_bundle())
        basemap = next(c for c in bundle["components"] if c.get("role") == "basemap")
        basemap["primary"] = True
        second = copy.deepcopy(basemap)
        second["id"] = "pack:sat-2"
        bundle["components"].append(second)
        bundle["summary"]["roles"]["basemap"] = 2
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle)
        self.assertIn("multiple_primary_basemaps", str(ctx.exception))

    def test_implicit_primary_uses_stable_component_order(self):
        bundle = copy.deepcopy(self._sat_first_bundle())
        basemap = next(c for c in bundle["components"] if c.get("role") == "basemap")
        second = copy.deepcopy(basemap)
        second["id"] = "pack:a-sat"
        bundle["components"].append(second)
        bundle["summary"]["roles"]["basemap"] = 2
        result = validate_sat_first_bundle(bundle)
        self.assertEqual(result["primary_basemap_id"], "pack:a-sat")

    def test_wrong_schema_fails(self):
        bundle = self._sat_first_bundle()
        bundle["schema"] = "helm.region_bundle.manifest.v0"
        with self.assertRaises(SatFirstBundleError):
            validate_sat_first_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
