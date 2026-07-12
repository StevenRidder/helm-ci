#!/usr/bin/env python3
"""Tests for OFFLINE-14 local maritime layer inventory manifests."""

import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pipeline" / "layer_inventory.py"
ENV_FIXTURE = ROOT / "services" / "wx" / "fixtures" / "fiji-env-bundle-v1.json"
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "backend"))

from labs.s100_spike import build_fixture_inventory
from layer_inventory import LAYER_INVENTORY_SCHEMA, LAYER_MANIFEST_SCHEMA, build_layer_inventory, build_layer_manifest


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
            "coverage": {"status": "complete"},
            "staleness": {"status": "fresh", "render_date": "2026-06-29T00:00:00Z"},
            "inspection": {
                "mode": "raster_metadata",
                "semantic_objects": "unavailable",
                "tap_action": "show_pack_source_metadata",
                "private_path": "/private/tmp/should-not-leak",
            },
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
                "confidence": "stale-fixture",
            },
            "coverage": {"status": "complete"},
            "staleness": {"status": "stale", "render_date": "2000-01-01T00:00:00Z"},
            "tile_url": "http://127.0.0.1:9120/sat/{z}/{x}/{y}.jpg",
            "url": "http://127.0.0.1:9120/sat/{z}/{x}/{y}.jpg",
        },
    }


class LayerInventoryTest(unittest.TestCase):
    def test_builds_local_inventory_for_packs_and_domain_layers(self):
        env_bundle = json.loads(ENV_FIXTURE.read_text(encoding="utf-8"))
        inventory = build_layer_inventory(
            sample_catalog(),
            {
                "inventory_id": ["fiji-layers"],
                "title": ["Fiji Local Layers"],
                "bbox": ["178.0,-18.0,178.5,-17.5"],
                "minzoom": ["7"],
                "maxzoom": ["8"],
                "include_tiles": ["0"],
            },
            generated_at="2026-06-29T00:00:00Z",
            places={
                "id": "places",
                "title": "Fiji Places",
                "source_info": {"label": "OpenStreetMap fixture", "confidence": "community"},
                "coverage": {"status": "complete", "bbox": [178.0, -18.0, 179.0, -17.0]},
            },
            depth={
                "id": "depth",
                "title": "Fiji Depth",
                "source_info": {"label": "Survey fixture", "confidence": "fixture"},
                "coverage": {"status": "unknown", "bbox": [178.0, -18.0, 179.0, -17.0]},
            },
            weather={
                "id": "gfs-fiji",
                "title": "GFS Fiji model run",
                "dataset_reference_date": "2026-06-29T00:00:00Z",
                "coverage": {"status": "area", "bbox": [170.0, -25.0, 185.0, -10.0]},
                "time_range": {"start": "2026-06-29T00:00:00Z", "end": "2026-07-01T00:00:00Z"},
                "freshness": "fresh",
                "confidence": "forecast",
                "probe_handle": "weather",
            },
            environmental_bundles=env_bundle,
            cruiser_layers={
                "id": "fiji-pass-notes",
                "title": "Fiji Pass Notes",
                "coverage": {"status": "area", "bbox": [178.0, -18.0, 179.0, -17.0]},
                "confidence": "community",
                "probe_handle": "cruiser.layers",
            },
            s100_inventory=build_fixture_inventory(),
        )

        self.assertEqual(inventory["schema"], LAYER_INVENTORY_SCHEMA)
        self.assertEqual(inventory["id"], "fiji-layers")
        self.assertTrue(inventory["advisory"])
        self.assertEqual(inventory["coverage"]["bbox"], [178.0, -18.0, 178.5, -17.5])
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(inventory))

        layers_by_product = {layer["product_identifier"]: layer for layer in inventory["layers"]}
        self.assertEqual(layers_by_product["S-52"]["dataset_name"], "Fiji S-52 Day")
        self.assertEqual(layers_by_product["S-52"]["pack"]["container"], "pmtiles")
        self.assertEqual(layers_by_product["S-52"]["sample"]["status"], "unavailable")
        self.assertEqual(layers_by_product["S-111"]["sample"]["probe_handle"], "s111.surface_current")
        self.assertEqual(layers_by_product["S-111"]["target_contract"]["name"], "tides.current")
        self.assertEqual(layers_by_product["S-129"]["target_contract"]["name"], "pass.ukc")
        self.assertEqual(layers_by_product["weather.model-run"]["sample"]["probe_handle"], "weather")
        env_bundle_layer = next(layer for layer in inventory["layers"] if layer["role"] == "environmental_bundle")
        self.assertEqual(env_bundle_layer["product_identifier"], "helm.env.bundle.v1")
        self.assertEqual(env_bundle_layer["coverage"]["bbox_object"]["crossesAntimeridian"], True)
        self.assertEqual(env_bundle_layer["sample"]["probe_handle"], "weather.bundle")
        self.assertFalse(env_bundle_layer["environmental_bundle"]["upstreamFetchesAllowedDuringGesture"])
        env_wind = next(layer for layer in inventory["layers"] if layer["id"].endswith(":wind"))
        self.assertEqual(env_wind["product_identifier"], "S-413")
        self.assertEqual(env_wind["sample"]["probe_handle"], "weather.wind")
        env_current = next(layer for layer in inventory["layers"] if layer["id"].endswith(":current"))
        self.assertEqual(env_current["role"], "surface_current")
        self.assertEqual(env_current["product_identifier"], "S-111")
        self.assertIn("s111.surface_current", inventory["summary"]["sample_handles"])
        self.assertIn("weather.bundle", inventory["summary"]["sample_handles"])
        self.assertEqual(inventory["summary"]["products"]["S-124"], 1)
        self.assertEqual(inventory["summary"]["roles"]["environmental_bundle"], 1)
        self.assertEqual(inventory["summary"]["roles"]["weather"], 11)

    def test_cli_builds_inventory_from_catalog_and_s100_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            catalog_path = tmp_path / "catalog.json"
            s100_path = tmp_path / "s100.json"
            env_path = tmp_path / "env.json"
            catalog_path.write_text(json.dumps(sample_catalog()), encoding="utf-8")
            s100_path.write_text(json.dumps(build_fixture_inventory()), encoding="utf-8")
            env_path.write_text(ENV_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--catalog",
                    str(catalog_path),
                    "--inventory-id",
                    "fiji-layers",
                    "--bbox",
                    "178.0,-18.0,178.5,-17.5",
                    "--minzoom",
                    "7",
                    "--maxzoom",
                    "7",
                    "--s100-json",
                    str(s100_path),
                    "--env-bundle-json",
                    str(env_path),
                ],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["schema"], LAYER_INVENTORY_SCHEMA)
            self.assertEqual(payload["id"], "fiji-layers")
            self.assertIn("S-102", payload["summary"]["products"])
            self.assertIn("helm.env.bundle.v1", payload["summary"]["products"])
            self.assertNotIn(tmp, proc.stdout)


class LayerManifestTest(unittest.TestCase):
    def test_empty_user_data_returns_schema_with_no_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = build_layer_manifest(tmp)
            self.assertEqual(payload["schema"], LAYER_MANIFEST_SCHEMA)
            self.assertEqual(payload["layers"], [])
            self.assertEqual(payload["enc"]["present"], [])
            self.assertEqual(payload["enc"]["missing"], ["depare", "depcnt", "soundg"])

    def test_enc_and_overlay_geojson_are_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "depare.geojson").write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "metadata": {"source": "enc", "cell": "FJ-FIXTURE"},
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Polygon", "coordinates": [[[178.0, -18.0], [178.5, -18.0], [178.5, -17.5], [178.0, -17.5], [178.0, -18.0]]]},
                                "properties": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            layers_dir = root / "layers"
            layers_dir.mkdir()
            (layers_dir / "anchorages.geojson").write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [178.2, -17.8]},
                                "properties": {"name": "Test Anchorage"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (layers_dir / "anchorages.metadata.json").write_text(
                json.dumps(
                    {
                        "id": "owned-anchorage-notes",
                        "title": "Owned anchorage notes",
                        "source": {"label": "owned", "license": "private-local"},
                        "private_path": "/private/tmp/should-not-leak",
                    }
                ),
                encoding="utf-8",
            )
            payload = build_layer_manifest(tmp)
            self.assertEqual(payload["schema"], LAYER_MANIFEST_SCHEMA)
            depare = next(layer for layer in payload["layers"] if layer["id"] == "depare")
            self.assertEqual(depare["tier"], "enc")
            self.assertEqual(depare["kind"], "polygons")
            self.assertEqual(depare["url"], "/user-data/depare.geojson")
            self.assertEqual(depare["source"]["label"], "enc")
            self.assertEqual(depare["bbox"], [178.0, -18.0, 178.5, -17.5])
            overlay = next(layer for layer in payload["layers"] if layer["id"] == "owned-anchorage-notes")
            self.assertEqual(overlay["tier"], "overlay")
            self.assertEqual(overlay["url"], "/user-data/layers/anchorages.geojson")
            # Honest enc coverage: depare present, depcnt/soundg missing (the enc gap CAT-2 renders).
            self.assertEqual(
                payload["enc"],
                {"expected": ["depare", "depcnt", "soundg"], "present": ["depare"], "missing": ["depcnt", "soundg"]},
            )
            self.assertEqual(depare["freshness"]["status"], "ok")
            self.assertIn("age_days", depare["freshness"])
            self.assertNotIn(tmp, json.dumps(payload))
            self.assertNotIn("/private/tmp/should-not-leak", json.dumps(payload))

    def test_manifest_freshness_flags_declared_window_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_dir = Path(tmp) / "layers"
            layers_dir.mkdir()
            (layers_dir / "note.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
            )
            old = (
                (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=400))
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
            (layers_dir / "note.metadata.json").write_text(
                json.dumps({"id": "note", "freshness": {"render_date": old, "stale_after_days": 1}}),
                encoding="utf-8",
            )
            payload = build_layer_manifest(tmp)
            note = next(layer for layer in payload["layers"] if layer["id"] == "note")
            self.assertEqual(note["freshness"]["status"], "stale")
            self.assertGreaterEqual(note["freshness"]["age_days"], 300)
            self.assertIn("stale_at", note["freshness"])
            self.assertIn("warning", note["freshness"])

    def test_manifest_freshness_without_window_stays_ok_with_age(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_dir = Path(tmp) / "layers"
            layers_dir.mkdir()
            (layers_dir / "plain.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
            )
            payload = build_layer_manifest(tmp)
            plain = next(layer for layer in payload["layers"] if layer["id"] == "plain")
            self.assertEqual(plain["freshness"]["status"], "ok")
            self.assertIn("age_days", plain["freshness"])  # derived from file mtime
            self.assertNotIn("warning", plain["freshness"])

    def test_manifest_freshness_edge_cases_are_honest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_dir = Path(tmp) / "layers"
            layers_dir.mkdir()
            old = (
                (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=400))
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

            def write(stem: str, sidecar: dict) -> None:
                (layers_dir / f"{stem}.geojson").write_text(
                    json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
                )
                (layers_dir / f"{stem}.metadata.json").write_text(json.dumps(sidecar), encoding="utf-8")

            # Explicit non-stale sidecar status + an expired window -> honestly stale (no
            # contradictory "fresh"+warning), matching the /catalog rule.
            write("forced", {"id": "forced", "freshness": {"status": "fresh", "render_date": old, "stale_after_days": 1}})
            # A stringified window is NOT a window (parity with strict C++ rj_int64) -> stays ok.
            write("strwin", {"id": "strwin", "freshness": {"render_date": old, "stale_after_days": "1"}})
            # A malformed render_date is rejected, never fabricating staleness -> ok, age from mtime.
            write("baddate", {"id": "baddate", "freshness": {"render_date": "2026-02-30", "stale_after_days": 1}})

            layers = {layer["id"]: layer for layer in build_layer_manifest(tmp)["layers"]}
            self.assertEqual(layers["forced"]["freshness"]["status"], "stale")
            self.assertEqual(layers["strwin"]["freshness"]["status"], "ok")
            self.assertNotIn("stale_at", layers["strwin"]["freshness"])
            self.assertEqual(layers["baddate"]["freshness"]["status"], "ok")
            self.assertIn("age_days", layers["baddate"]["freshness"])  # from mtime, not the bad date


if __name__ == "__main__":
    unittest.main(verbosity=2)
