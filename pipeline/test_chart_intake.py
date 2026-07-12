#!/usr/bin/env python3
"""Contract tests for INTAKE-2's in-place chart-root registry and index."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import struct
import tempfile
import time
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("chart_intake.py")
SPEC = importlib.util.spec_from_file_location("chart_intake", MODULE_PATH)
assert SPEC and SPEC.loader
chart_intake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chart_intake)


def write_mbtiles(path: Path, *, bounds: str | None = "178,-18,179,-17") -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    if bounds:
        conn.execute("INSERT INTO metadata VALUES ('bounds', ?)", (bounds,))
    conn.execute("INSERT INTO tiles VALUES (2, 3, 2, ?)", (b"tile",))
    conn.commit()
    conn.close()


def write_pmtiles(path: Path) -> None:
    header = bytearray(127)
    header[:7] = b"PMTiles"
    header[7] = 3
    header[99] = 2
    header[100] = 0
    header[101] = 12
    for offset, value in zip((102, 106, 110, 114), (178.0, -18.0, 179.0, -17.0)):
        struct.pack_into("<i", header, offset, int(value * 1e7))
    path.write_bytes(header + b"fixture")


def write_geojson(path: Path, lon: float = 178.2, lat: float = -17.8) -> None:
    path.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {}}],
    }), encoding="utf-8")


class ChartIntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.roots_file = self.base / "config" / "chart-roots.json"
        self.index_file = self.base / "config" / "chart-index.json"
        self.default_root = self.base / "default-charts"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_root_is_created_and_registry_is_private(self) -> None:
        registry = chart_intake.ensure_registry(self.roots_file, self.default_root)
        self.assertTrue(self.default_root.is_dir())
        self.assertEqual(registry["schema"], chart_intake.ROOTS_SCHEMA)
        self.assertTrue(registry["roots"][0]["default"])
        self.assertEqual(os.stat(self.roots_file).st_mode & 0o777, 0o600)
        public = chart_intake.public_roots(registry)
        self.assertNotIn(str(self.default_root), json.dumps(public))

    def test_existing_registry_and_unchanged_index_permissions_are_repaired(self) -> None:
        chart_intake.ensure_registry(self.roots_file, self.default_root)
        index, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        os.chmod(self.roots_file, 0o644)
        os.chmod(self.index_file, 0o644)
        chart_intake.ensure_registry(self.roots_file, self.default_root)
        unchanged, changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertFalse(changed)
        self.assertEqual(index, unchanged)
        self.assertEqual(os.stat(self.roots_file).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.index_file).st_mode & 0o777, 0o600)

    def test_recursive_mixed_index_preserves_files_and_sanitizes_sidecar(self) -> None:
        root = self.base / "customer-library"
        fiji = root / "FIJI" / "west"
        tonga = root / "TONGA"
        fiji.mkdir(parents=True)
        tonga.mkdir(parents=True)
        mbtiles = fiji / "sat #1.mbtiles"
        pmtiles = tonga / "chart.pmtiles"
        geojson = root / "anchorages.geojson"
        write_mbtiles(mbtiles)
        write_pmtiles(pmtiles)
        write_geojson(geojson)
        (fiji / "sat #1.metadata.json").write_text(json.dumps({
            "source": {"id": "fixture", "label": "Owned source", "license": "private-use", "token": "secret", "url": "file:///private/source"},
            "license": "private-use",
            "title": "source at /Users/customer/Charts",
            "private_path": "/Users/customer/Charts",
        }), encoding="utf-8")
        before = {path.relative_to(root): (path.stat().st_ino, path.read_bytes()) for path in root.rglob("*") if path.is_file()}

        registered, changed = chart_intake.register_root(self.roots_file, self.default_root, root, "Voyage charts")
        self.assertTrue(changed)
        index, index_changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertTrue(index_changed)
        self.assertEqual(index["chart_count"], 3)
        self.assertEqual(index["invalid_count"], 0)
        self.assertEqual({item["chart_type"] for item in index["chart_classes"]}, {"tile_pack", "enc", "overlay"})
        self.assertEqual({item["group"] for item in index["charts"]}, {"FIJI", "TONGA", "."})
        self.assertEqual({item["chart_type"] for item in index["charts"]}, {"tile_pack", "overlay"})
        self.assertTrue(all(item["validation"]["status"] == "valid" for item in index["charts"]))
        sat = next(item for item in index["charts"] if item["filename"] == "sat #1.mbtiles")
        self.assertEqual(sat["metadata"]["source"], {"id": "fixture", "label": "Owned source", "license": "private-use"})
        public_json = json.dumps(index)
        self.assertNotIn(str(root), public_json)
        self.assertNotIn("token", public_json)
        self.assertNotIn("private_path", public_json)
        self.assertNotIn("file:///", public_json)
        self.assertNotIn("/Users/customer", public_json)
        after = {path.relative_to(root): (path.stat().st_ino, path.read_bytes()) for path in root.rglob("*") if path.is_file()}
        self.assertEqual(before, after, "indexing must never move, rename, or rewrite customer files")
        self.assertEqual(registered["id"], next(row["id"] for row in index["roots"] if row["label"] == "Voyage charts"))

    def test_idempotent_register_and_rescan_preserve_index_bytes(self) -> None:
        root = self.base / "charts"
        root.mkdir()
        write_pmtiles(root / "voyage.pmtiles")
        first_root, first_changed = chart_intake.register_root(self.roots_file, self.default_root, root)
        second_root, second_changed = chart_intake.register_root(self.roots_file, self.default_root, root)
        self.assertTrue(first_changed)
        self.assertFalse(second_changed)
        self.assertEqual(first_root["id"], second_root["id"])
        first, changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertTrue(changed)
        first_bytes = self.index_file.read_bytes()
        second, changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertFalse(changed)
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, self.index_file.read_bytes())

    def test_root_label_change_invalidates_index_without_implicit_relabel(self) -> None:
        root = self.base / "charts"
        root.mkdir()
        write_pmtiles(root / "voyage.pmtiles")
        chart_intake.register_root(self.roots_file, self.default_root, root, "Voyage charts")
        first, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)

        unchanged, registry_changed = chart_intake.register_root(self.roots_file, self.default_root, root)
        self.assertFalse(registry_changed)
        self.assertEqual(unchanged["label"], "Voyage charts")

        chart_intake.register_root(self.roots_file, self.default_root, root, "Renamed charts")
        second, index_changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertTrue(index_changed)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        row = next(item for item in second["roots"] if item["id"] == unchanged["id"])
        self.assertEqual(row["label"], "Renamed charts")

    def test_tree_change_rebuilds_fingerprint(self) -> None:
        root = self.base / "charts"
        root.mkdir()
        write_geojson(root / "one.geojson")
        chart_intake.register_root(self.roots_file, self.default_root, root)
        first, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        time.sleep(0.01)
        write_geojson(root / "two.geojson", 179.0, -18.0)
        second, changed = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertTrue(changed)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(second["chart_count"], first["chart_count"] + 1)

    def test_mismatch_invalid_schema_and_missing_bbox_are_loud(self) -> None:
        root = self.base / "bad-charts"
        root.mkdir()
        (root / "wrong.mbtiles").write_bytes(b"PMTiles" + bytes(120))
        (root / "bad.geojson").write_text("not json", encoding="utf-8")
        conn = sqlite3.connect(root / "schema.mbtiles")
        conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
        conn.commit()
        conn.close()
        write_geojson(root / "empty.geojson")
        (root / "empty.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
        chart_intake.register_root(self.roots_file, self.default_root, root)
        index, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        codes = {item["filename"]: item["validation"]["code"] for item in index["charts"]}
        self.assertEqual(codes["wrong.mbtiles"], "contents_extension_mismatch")
        self.assertEqual(codes["bad.geojson"], "contents_extension_mismatch")
        self.assertEqual(codes["schema.mbtiles"], "invalid_schema")
        self.assertEqual(codes["empty.geojson"], "bbox_unavailable")
        self.assertEqual(index["status"], "error")
        self.assertEqual(index["invalid_count"], 4)

    def test_mbtiles_bbox_is_derived_when_metadata_omits_it(self) -> None:
        root = self.base / "charts"
        root.mkdir()
        write_mbtiles(root / "derived.mbtiles", bounds=None)
        chart_intake.register_root(self.roots_file, self.default_root, root)
        index, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        chart = next(item for item in index["charts"] if item["filename"] == "derived.mbtiles")
        self.assertEqual(chart["validation"]["status"], "valid")
        self.assertEqual(len(chart["bbox"]), 4)

    def test_disappeared_root_stays_visible_and_unavailable(self) -> None:
        root = self.base / "removable"
        root.mkdir()
        chart_intake.register_root(self.roots_file, self.default_root, root)
        root.rmdir()
        index, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        row = next(item for item in index["roots"] if item["label"] == "removable")
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(row["reason"], "registered_root_missing")
        self.assertIn("registered_root_missing", {item["code"] for item in index["warnings"]})

    def test_unregister_never_deletes_customer_files(self) -> None:
        root = self.base / "owned"
        root.mkdir()
        write_geojson(root / "notes.geojson")
        registered, _ = chart_intake.register_root(self.roots_file, self.default_root, root)
        removed = chart_intake.unregister_root(self.roots_file, self.default_root, registered["id"])
        self.assertEqual(removed["id"], registered["id"])
        self.assertTrue((root / "notes.geojson").is_file())

    def test_external_symlink_is_ignored_with_named_warning(self) -> None:
        root = self.base / "owned"
        outside = self.base / "outside.pmtiles"
        root.mkdir()
        write_pmtiles(outside)
        (root / "linked.pmtiles").symlink_to(outside)
        chart_intake.register_root(self.roots_file, self.default_root, root)
        index, _ = chart_intake.rescan(self.roots_file, self.index_file, self.default_root)
        self.assertFalse(any(item["filename"] == "linked.pmtiles" for item in index["charts"]))
        self.assertIn("external_symlink_file_ignored", {item["code"] for item in index["warnings"]})

    def test_path_shaped_public_label_is_rejected(self) -> None:
        root = self.base / "owned"
        root.mkdir()
        with self.assertRaises(chart_intake.IntakeError):
            chart_intake.register_root(self.roots_file, self.default_root, root, "/Users/customer/private")


if __name__ == "__main__":
    unittest.main()
