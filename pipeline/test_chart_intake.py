#!/usr/bin/env python3
"""Contract tests for INTAKE-2's in-place chart-root registry and index."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import struct
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


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


def write_enc_cell(path: Path) -> None:
    """A .000 with a syntactically valid ISO 8211 leader (validation stubbed in tests)."""
    header = bytearray(b"0" * 24)
    header[12:17] = b"12345"
    path.write_bytes(bytes(header) + b"enc-fixture")


class ChartIntakeDepthTest(unittest.TestCase):
    """INTAKE-7: indexing an ENC runs the ENC-4 depth extraction — idempotent, loud on failure."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.roots_file = self.base / "config" / "chart-roots.json"
        self.index_file = self.base / "config" / "chart-index.json"
        self.default_root = self.base / "default-charts"
        self.depth_root = self.base / "user-data"
        self.extract_calls: list[str] = []
        self._saved = (chart_intake._depth_extractor, chart_intake._extract_cell, chart_intake._validate_s57)
        chart_intake._depth_extractor = lambda: "stub"
        chart_intake._extract_cell = self._fake_extract
        chart_intake._validate_s57 = self._fake_validate

    def tearDown(self) -> None:
        chart_intake._depth_extractor, chart_intake._extract_cell, chart_intake._validate_s57 = self._saved
        self.tmp.cleanup()

    def _fake_validate(self, path: Path, sidecar_bbox):
        if path.name.startswith("BAD"):
            return None, {"status": "error", "code": "contents_extension_mismatch", "message": "stub invalid cell"}
        return [178.0, -18.0, 179.0, -17.0], {"status": "valid", "code": "ok", "message": "stub valid cell"}

    def _fake_extract(self, enc: Path, out_dir: Path, extractor: str):
        self.extract_calls.append(enc.name)
        out_dir.mkdir(parents=True, exist_ok=True)
        for stem in ("depare", "depcnt", "soundg"):
            (out_dir / f"{stem}.geojson").write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [178.5, -17.6]}, "properties": {}}],
            }), encoding="utf-8")
        return {"layers": {"depare": {}, "depcnt": {}, "soundg": {}}, "render_date": "2026-05-01"}

    def _rescan(self, **kwargs):
        kwargs.setdefault("depth_root", self.depth_root)
        return chart_intake.rescan(self.roots_file, self.index_file, self.default_root, **kwargs)

    def _register_cell_root(self, cell: str = "US5FJ001") -> Path:
        root = self.base / "charts"
        (root / "FIJI").mkdir(parents=True, exist_ok=True)
        write_enc_cell(root / "FIJI" / f"{cell}.000")
        chart_intake.register_root(self.roots_file, self.default_root, root)
        return root

    def test_indexing_an_enc_extracts_depth_with_sidecars(self) -> None:
        root = self._register_cell_root()
        index, changed = self._rescan()
        self.assertTrue(changed)
        self.assertEqual(index["status"], "ok")
        self.assertEqual(index["depth_error_count"], 0)
        self.assertEqual(self.extract_calls, ["US5FJ001.000"])
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "ok")
        self.assertEqual(item["depth"]["code"], "extracted")
        self.assertEqual(item["depth"]["output"], "enc-depth/US5FJ001/")
        self.assertEqual(item["depth"]["layers"], ["depare", "depcnt", "soundg"])
        self.assertEqual(item["depth"]["render_date"], "2026-05-01")
        out_dir = self.depth_root / "enc-depth" / "US5FJ001"
        for stem in ("depare", "depcnt", "soundg"):
            self.assertTrue((out_dir / f"{stem}.geojson").is_file())
            sidecar = json.loads((out_dir / f"{stem}.metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["id"], f"enc-depth-us5fj001-{stem}")
            self.assertEqual(sidecar["tier"], "enc")
            self.assertEqual(sidecar["source"], {"label": "enc", "id": "US5FJ001", "license": "enc-local"})
            self.assertEqual(sidecar["freshness"], {"render_date": "2026-05-01"})
        provenance = json.loads((out_dir / "depth-provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["schema"], "helm.depth_provenance.v1")
        self.assertEqual(provenance["relative_path"], "FIJI/US5FJ001.000")
        # The depth-provenance sidecar is deposited alongside the customer's cell.
        customer = json.loads((root / "FIJI" / "US5FJ001.depth-provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(customer["status"], "ok")
        self.assertEqual(customer["output"], "enc-depth/US5FJ001/")
        self.assertEqual(customer["enc_fingerprint"], provenance["enc_fingerprint"])
        blob = json.dumps(index) + json.dumps(provenance) + json.dumps(customer)
        self.assertNotIn(str(self.base), blob, "no private absolute paths in any depth artifact")

    def test_depth_is_idempotent_and_refreshes_on_change(self) -> None:
        root = self._register_cell_root()
        self._rescan()
        _, changed = self._rescan()
        self.assertFalse(changed, "unchanged tree + outputs must not rewrite the index")
        self.assertEqual(len(self.extract_calls), 1, "up-to-date outputs must not re-extract")

        cell = root / "FIJI" / "US5FJ001.000"
        stamp = cell.stat().st_mtime + 5
        os.utime(cell, (stamp, stamp))
        index, changed = self._rescan()
        self.assertTrue(changed)
        self.assertEqual(len(self.extract_calls), 2, "a changed cell must re-extract")

        (self.depth_root / "enc-depth" / "US5FJ001" / "depare.geojson").unlink()
        index, changed = self._rescan()
        self.assertTrue(changed, "deleted outputs must invalidate the index")
        self.assertEqual(len(self.extract_calls), 3, "missing outputs must re-extract")
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "ok")

    def test_depth_survives_index_file_loss_without_reextracting(self) -> None:
        self._register_cell_root()
        self._rescan()
        self.index_file.unlink()
        index, changed = self._rescan()
        self.assertTrue(changed)
        self.assertEqual(len(self.extract_calls), 1, "provenance match must skip extraction")
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["code"], "up_to_date")

    def test_enc_update_cell_triggers_reextract(self) -> None:
        root = self._register_cell_root()
        self._rescan()
        (root / "FIJI" / "US5FJ001.001").write_bytes(b"update-fixture")
        index, changed = self._rescan()
        self.assertTrue(changed)
        self.assertEqual(len(self.extract_calls), 2, "a new ENC update cell must re-extract depth")
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["update_count"], 1)
        self.assertEqual(item["depth"]["status"], "ok")

    def test_extraction_failure_is_loud_in_catalog_and_sidecar(self) -> None:
        def boom(enc, out_dir, extractor):
            raise chart_intake.DepthExtractError("depth_extract_failed", "stub: cell exploded")
        chart_intake._extract_cell = boom
        root = self._register_cell_root()
        index, _ = self._rescan()
        self.assertEqual(index["status"], "error", "a failed extraction must fail the index LOUD")
        self.assertEqual(index["depth_error_count"], 1)
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"], {"status": "error", "code": "depth_extract_failed", "message": "stub: cell exploded"})
        self.assertIn("depth_extract_failed", {warning["code"] for warning in index["warnings"]})
        customer = json.loads((root / "FIJI" / "US5FJ001.depth-provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(customer["status"], "error")
        self.assertEqual(customer["error"]["code"], "depth_extract_failed")

    def test_missing_extractor_is_a_named_error(self) -> None:
        chart_intake._depth_extractor = lambda: None
        self._register_cell_root()
        index, _ = self._rescan()
        self.assertEqual(index["status"], "error")
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "error")
        self.assertEqual(item["depth"]["code"], "depth_extractor_unavailable")

    def test_disabled_extraction_is_a_named_skip_never_silent(self) -> None:
        self._register_cell_root()
        index, _ = self._rescan(extract_depth=False)
        self.assertEqual(self.extract_calls, [])
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "skipped")
        self.assertEqual(item["depth"]["code"], "depth_extract_disabled")
        self.assertIn("depth_extract_disabled", {warning["code"] for warning in index["warnings"]})
        self.assertEqual(index["status"], "warning")

    def test_invalid_cell_skips_depth_with_named_reason(self) -> None:
        root = self.base / "charts"
        root.mkdir()
        write_enc_cell(root / "BADCELL.000")
        chart_intake.register_root(self.roots_file, self.default_root, root)
        index, _ = self._rescan()
        self.assertEqual(self.extract_calls, [])
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["validation"]["status"], "error")
        self.assertEqual(item["depth"], {"status": "skipped", "code": "chart_invalid",
                                         "message": "cell failed chart validation; depth extraction not attempted"})

    def test_duplicate_cell_extracts_once_with_named_warning(self) -> None:
        root = self.base / "charts"
        (root / "A").mkdir(parents=True)
        (root / "B").mkdir(parents=True)
        write_enc_cell(root / "A" / "US5FJ001.000")
        write_enc_cell(root / "B" / "US5FJ001.000")
        chart_intake.register_root(self.roots_file, self.default_root, root)
        index, _ = self._rescan()
        self.assertEqual(len(self.extract_calls), 1)
        statuses = sorted(chart["depth"]["code"] for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(statuses, ["duplicate_enc_cell", "extracted"])
        self.assertIn("duplicate_enc_cell_depth_skipped", {warning["code"] for warning in index["warnings"]})

    def test_unwritable_customer_root_warns_but_extracts(self) -> None:
        root = self._register_cell_root()
        (root / "FIJI").chmod(0o500)
        try:
            index, _ = self._rescan()
        finally:
            (root / "FIJI").chmod(0o700)
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "ok", "sidecar trouble must not fail the extraction")
        self.assertIn("depth_sidecar_unwritable", {warning["code"] for warning in index["warnings"]})
        self.assertTrue((self.depth_root / "enc-depth" / "US5FJ001" / "depare.geojson").is_file())

    def test_run_ogr_timeout_becomes_named_error_not_traceback(self) -> None:
        """A hung GDAL tool must fail loud per-cell, never crash the whole rescan."""
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ogrinfo", timeout=600)):
            with self.assertRaises(chart_intake.DepthExtractError) as ctx:
                chart_intake._run_ogr(["ogrinfo", "-ro", "-q", "/x.000"], "ogrinfo")
        self.assertEqual(ctx.exception.code, "depth_extract_timeout")

    def test_unexpected_extractor_exception_is_named_not_fatal(self) -> None:
        """A raw (non-DepthExtractError, non-OSError) exception from one cell is caught,
        named, and does NOT abort indexing of the other cells in the same rescan."""
        root = self.base / "charts"
        (root / "A").mkdir(parents=True)
        (root / "B").mkdir(parents=True)
        write_enc_cell(root / "A" / "US5AAA01.000")
        write_enc_cell(root / "B" / "US5BBB02.000")
        chart_intake.register_root(self.roots_file, self.default_root, root)

        def flaky(enc: Path, out_dir: Path, extractor: str):
            if enc.name.startswith("US5AAA01"):
                raise subprocess.TimeoutExpired(cmd="ogr2ogr", timeout=600)  # not OSError/DepthExtractError
            return self._fake_extract(enc, out_dir, extractor)
        chart_intake._extract_cell = flaky

        index, _ = self._rescan()  # must NOT raise
        by_cell = {chart["filename"]: chart["depth"] for chart in index["charts"] if chart["chart_type"] == "enc"}
        self.assertEqual(by_cell["US5AAA01.000"]["status"], "error")
        self.assertEqual(by_cell["US5AAA01.000"]["code"], "depth_unexpected_error")
        self.assertEqual(by_cell["US5BBB02.000"]["status"], "ok", "one cell's failure must not abort the sibling")
        self.assertEqual(index["status"], "error")

    def test_gdal_error_message_never_leaks_absolute_paths(self) -> None:
        """GDAL echoes the customer's datasource path in errors; it must be scrubbed out of
        the privacy-safe index, warnings, and the customer-side sidecar."""
        leak = "ERROR 1: Unable to open datasource '/Users/skipper/Charts/FIJI/US5FJ001.000' with driver S57"
        def boom(enc, out_dir, extractor):
            raise chart_intake.DepthExtractError("depth_extract_failed", leak)
        chart_intake._extract_cell = boom
        root = self._register_cell_root()
        index, _ = self._rescan()
        blob = json.dumps(index)
        customer = (root / "FIJI" / "US5FJ001.depth-provenance.json").read_text(encoding="utf-8")
        for secret in ("/Users/skipper", "/Users/skipper/Charts/FIJI"):
            self.assertNotIn(secret, blob)
            self.assertNotIn(secret, customer)
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "error")
        self.assertIn("US5FJ001.000", item["depth"]["message"], "basename kept so the error stays actionable")

    def test_scrub_message_redacts_paths_keeps_basename(self) -> None:
        cases = {
            "cannot open '/Users/x/Charts/a b/US5FJ001.000'": ("/Users/x", "US5FJ001.000"),
            "file:///private/tmp/enc/US5.000 failed": ("/private/tmp", "US5.000"),
            "C:\\Users\\x\\enc\\US5.000 bad": ("C:\\Users", "US5.000"),
            "~/charts/deep/US5.000 missing": ("~/charts", "US5.000"),
        }
        for message, (secret, keep) in cases.items():
            scrubbed = chart_intake._scrub_message(message)
            self.assertNotIn(secret, scrubbed, message)
            self.assertIn(keep, scrubbed, message)
        # A non-path message with an incidental "/" is left intact.
        self.assertEqual(chart_intake._scrub_message("3/4 layers failed"), "3/4 layers failed")

    def test_failed_reextract_removes_stale_partial_outputs(self) -> None:
        """After a cell previously succeeded, a re-extraction failure must not leave stale
        or partial GeoJSON that the /layer-manifest producers would still serve as valid."""
        import layer_inventory  # sibling module under pipeline/
        root = self._register_cell_root()
        self._rescan()
        out_dir = self.depth_root / "enc-depth" / "US5FJ001"
        self.assertTrue((out_dir / "depare.geojson").is_file())

        cell = root / "FIJI" / "US5FJ001.000"
        stamp = cell.stat().st_mtime + 10
        os.utime(cell, (stamp, stamp))

        def partial(enc: Path, out_dir2: Path, extractor: str):
            out_dir2.mkdir(parents=True, exist_ok=True)
            (out_dir2 / "depare.geojson").write_text('{"type":"FeatureCollection","features":[{"stale":1}]}')
            raise chart_intake.DepthExtractError("depth_extract_failed", "depcnt blew up")
        chart_intake._extract_cell = partial
        index, _ = self._rescan()
        item = next(chart for chart in index["charts"] if chart["chart_type"] == "enc")
        self.assertEqual(item["depth"]["status"], "error")
        self.assertFalse(out_dir.exists(), "errored cell must leave no served depth outputs")
        manifest = layer_inventory.build_layer_manifest(str(self.depth_root))
        self.assertEqual(manifest["enc"]["cells"], [], "manifest must show the honest gap, not stale depth")
        self.assertFalse(any(str(layer["id"]).startswith("enc-depth-us5fj001") for layer in manifest["layers"]))


if __name__ == "__main__":
    unittest.main()
