#!/usr/bin/env python3
"""Tests for OFFLINE-8 region bundle manifests and delta plans."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pipeline" / "region_bundle.py"
sys.path.insert(0, str(ROOT / "pipeline"))

from region_bundle import BundleError, build_region_bundle, diff_region_bundles
from region_bundle_sat_first import (
    SAT_FIRST_PROFILE,
    SatFirstBundleError,
    validate_sat_first_bundle,
)


def sample_catalog():
    return {
        "chart": {
            "id": "chart",
            "title": "Fiji S-52 Day",
            "container": "pmtiles",
            "kind": "chart",
            "type": "raster",
            "format": "png",
            "renderer": "s52",
            "palette": "day",
            "display_category": "std",
            "bounds_array": [178.0, -18.0, 179.0, -17.0],
            "minzoom": 7,
            "maxzoom": 12,
            "size_bytes": 100000,
            "addressed_tiles": 100,
            "modified": "2026-06-29T00:00:00Z",
            "modified_epoch": 1782691200,
            "license": "local-user-owned",
            "source_info": {
                "label": "ChartLocker Fiji fixture",
                "id": "FJ-FIXTURE",
                "format": "raster",
                "updated": "2026-06-01T00:00:00Z",
                "confidence": "fixture",
            },
            "coverage": {
                "status": "partial",
                "tile_count": 90,
                "tile_count_expected": 100,
                "gap_count": 10,
            },
            "staleness": {
                "status": "fresh",
                "render_date": "2026-06-29T00:00:00Z",
            },
            "inspection": {
                "mode": "raster_metadata",
                "semantic_objects": "unavailable",
                "tap_action": "show_pack_source_metadata",
                "private_path": "/private/tmp/should-not-leak",
            },
            "warnings": [
                {
                    "code": "pack_out_of_coverage",
                    "severity": "warning",
                    "message": "Fixture coverage gap.",
                }
            ],
            "pmtiles_url": "http://127.0.0.1:9120/chart.pmtiles",
            "protocol_url": "pmtiles://http://127.0.0.1:9120/chart.pmtiles",
            "url": "http://127.0.0.1:9120/chart.pmtiles",
        },
        "sat": {
            "id": "sat",
            "title": "Fiji Satellite",
            "container": "mbtiles",
            "kind": "satellite",
            "type": "raster",
            "format": "jpg",
            "bounds_array": [177.8, -18.2, 179.2, -16.8],
            "minzoom": 7,
            "maxzoom": 11,
            "size_bytes": 200000,
            "tile_count": 200,
            "modified_epoch": 946684800,
            "source_info": {
                "label": "Sentinel-2 fixture",
                "updated": "2000-01-01T00:00:00Z",
            },
            "coverage": {"status": "complete"},
            "staleness": {
                "status": "stale",
                "render_date": "2000-01-01T00:00:00Z",
            },
            "warnings": [
                {
                    "code": "pack_stale",
                    "severity": "warning",
                    "message": "Pack render date is older than the freshness window.",
                }
            ],
            "tile_url": "http://127.0.0.1:9120/sat/{z}/{x}/{y}.jpg",
            "url": "http://127.0.0.1:9120/sat/{z}/{x}/{y}.jpg",
        },
    }


class RegionBundleTest(unittest.TestCase):
    def test_builds_bundle_with_prefetch_metadata_and_no_private_paths(self):
        bundle = build_region_bundle(
            sample_catalog(),
            {
                "bundle_id": ["fiji"],
                "title": ["Fiji Local Bundle"],
                "bbox": ["178.0,-18.0,178.5,-17.5"],
                "minzoom": ["7"],
                "maxzoom": ["8"],
                "include_tiles": ["0"],
            },
            generated_at="2026-06-29T00:00:00Z",
            places={
                "id": "places",
                "title": "Fiji Places",
                "feature_count": 12,
                "source_info": {"label": "OpenStreetMap fixture"},
            },
            depth={
                "id": "depth",
                "title": "Fiji Depth",
                "coverage": {"status": "unknown"},
                "source_info": {"confidence": "fixture"},
            },
        )

        self.assertEqual(bundle["schema"], "helm.region_bundle.manifest.v1")
        self.assertEqual(bundle["id"], "fiji")
        self.assertEqual(bundle["prefetch"]["schema"], "helm.prefetch.manifest.v1")
        self.assertEqual(bundle["corridor"]["bbox"], [178.0, -18.0, 178.5, -17.5])
        self.assertEqual(bundle["summary"]["roles"]["chart"], 1)
        self.assertEqual(bundle["summary"]["roles"]["basemap"], 1)
        self.assertEqual(bundle["summary"]["roles"]["places"], 1)
        self.assertEqual(bundle["summary"]["roles"]["depth"], 1)

        chart = next(c for c in bundle["components"] if c["id"] == "pack:chart")
        self.assertEqual(chart["role"], "chart")
        self.assertEqual(chart["source_info"]["id"], "FJ-FIXTURE")
        self.assertEqual(chart["prefetch"]["tile_count"], 3)
        self.assertIn("out_of_coverage", chart["status"]["states"])
        self.assertEqual(len(chart["fingerprint"]), 64)

        sat = next(c for c in bundle["components"] if c["id"] == "pack:sat")
        self.assertEqual(sat["role"], "basemap")
        self.assertIn("stale", sat["status"]["states"])
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(bundle))

    def test_delta_plan_marks_missing_changed_stale_and_out_of_coverage(self):
        available = build_region_bundle(
            sample_catalog(),
            {
                "bundle_id": ["fiji"],
                "bbox": ["178.0,-18.0,178.5,-17.5"],
                "minzoom": ["7"],
                "maxzoom": ["7"],
                "include_tiles": ["0"],
            },
            generated_at="2026-06-29T00:00:00Z",
        )
        installed = copy.deepcopy(available)
        installed["components"] = [
            component for component in installed["components"] if component["id"] != "pack:sat"
        ]
        installed["components"][0]["fingerprint"] = "old"

        diff = diff_region_bundles(available, installed, generated_at="2026-06-29T00:00:00Z")
        self.assertEqual(diff["schema"], "helm.region_bundle.diff.v1")
        self.assertFalse(diff["current"])
        self.assertFalse(diff["coverage_complete"])
        self.assertEqual([item["id"] for item in diff["missing"]], ["pack:sat"])
        self.assertEqual([item["id"] for item in diff["changed"]], ["pack:chart"])
        self.assertEqual([item["id"] for item in diff["stale"]], ["pack:sat"])
        self.assertEqual([item["id"] for item in diff["out_of_coverage"]], ["pack:chart"])
        self.assertTrue(diff["summary"]["needs_update"])

    def test_cli_builds_bundle_from_catalog_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            catalog_path.write_text(json.dumps(sample_catalog()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--catalog",
                    str(catalog_path),
                    "--bundle-id",
                    "fiji",
                    "--title",
                    "Fiji Local Bundle",
                    "--bbox",
                    "178.0,-18.0,178.5,-17.5",
                    "--minzoom",
                    "7",
                    "--maxzoom",
                    "7",
                    "--packs",
                    "chart",
                ],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["schema"], "helm.region_bundle.manifest.v1")
            self.assertEqual(payload["id"], "fiji")
            self.assertEqual([c["id"] for c in payload["components"]], ["pack:chart"])
            self.assertNotIn(tmp, proc.stdout)


def chart_only_catalog():
    """A catalog whose only bbox-matching pack is a chart (no satellite basemap)."""
    return {"chart": sample_catalog()["chart"]}


def offset_sat_catalog():
    """Chart over the request bbox; the only satellite pack sits far away."""
    catalog = sample_catalog()
    catalog["sat"] = dict(catalog["sat"], bounds_array=[10.0, 10.0, 11.0, 11.0])
    return catalog


class SatFirstBundleProducerTest(unittest.TestCase):
    """OFFLINE-L-3: the download drawer's live estimate builds on ?profile=sat_first."""

    BBOX = "178.0,-18.0,178.5,-17.5"

    def _build(self, catalog, **extra):
        query = {
            "profile": [SAT_FIRST_PROFILE],
            "bbox": [self.BBOX],
            "minzoom": ["7"],
            "maxzoom": ["8"],
            "include_tiles": ["0"],
        }
        for key, value in extra.items():
            query[key] = [value]
        return build_region_bundle(catalog, query, generated_at="2026-06-29T00:00:00Z")

    def test_profile_drops_chart_and_marks_primary_basemap(self):
        bundle = self._build(sample_catalog())
        self.assertEqual(bundle["profile"], SAT_FIRST_PROFILE)
        self.assertEqual([c["id"] for c in bundle["components"]], ["pack:sat"])
        sat = bundle["components"][0]
        self.assertEqual(sat["role"], "basemap")
        self.assertTrue(sat["primary"])
        self.assertEqual(bundle["summary"]["roles"], {"basemap": 1})
        self.assertGreater(bundle["summary"].get("estimated_bytes", 0), 0)
        result = validate_sat_first_bundle(bundle, require_profile=True)
        self.assertTrue(result["valid"])
        self.assertEqual(result["primary_basemap_id"], "pack:sat")

    def test_include_chart_keeps_chart_as_non_primary_overlay(self):
        bundle = self._build(sample_catalog(), include_chart="1")
        self.assertEqual(sorted(c["id"] for c in bundle["components"]), ["pack:chart", "pack:sat"])
        chart = next(c for c in bundle["components"] if c["id"] == "pack:chart")
        self.assertNotEqual(chart.get("primary"), True)
        self.assertEqual(bundle["summary"]["roles"]["basemap"], 1)
        self.assertEqual(bundle["summary"]["roles"]["chart"], 1)
        validate_sat_first_bundle(bundle, require_profile=True)

    def test_missing_basemap_when_only_chart_matches(self):
        bundle = self._build(chart_only_catalog())
        self.assertEqual(bundle["components"], [])
        self.assertNotIn("basemap", bundle["summary"]["roles"])
        with self.assertRaises(SatFirstBundleError) as ctx:
            validate_sat_first_bundle(bundle, require_profile=True)
        self.assertIn("missing_basemap", str(ctx.exception))

    def test_missing_basemap_when_satellite_outside_bbox(self):
        # Chart covers the bbox but the satellite pack is elsewhere: sat-first must not
        # promote the chart to basemap even with include_chart=1.
        bundle = self._build(offset_sat_catalog(), include_chart="1")
        ids = [c["id"] for c in bundle["components"]]
        self.assertIn("pack:chart", ids)
        self.assertNotIn("pack:sat", ids)
        with self.assertRaises(SatFirstBundleError):
            validate_sat_first_bundle(bundle, require_profile=True)

    def test_unsupported_profile_is_rejected(self):
        with self.assertRaises(BundleError):
            build_region_bundle(sample_catalog(), {"profile": ["chart_first"], "bbox": [self.BBOX]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
