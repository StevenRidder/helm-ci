#!/usr/bin/env python3
"""Contract tests for INTAKE-6's first-run chart-library bootstrap script.

Runs scripts/helm-first-run.sh end-to-end against a sandboxed HELM_CONFIG /
default root: registry + index creation, in-place registration of an existing
customer folder (files never move), idempotent reruns, per-persona summary,
and loud failures for missing roots and invalid charts.
"""

from __future__ import annotations

import json
import os
import sqlite3
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "helm-first-run.sh"
UNREACHABLE_PACKD = "http://127.0.0.1:59991"


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
    header[101] = 12
    for offset, value in zip((102, 106, 110, 114), (178.0, -18.0, 179.0, -17.0)):
        struct.pack_into("<i", header, offset, int(value * 1e7))
    path.write_bytes(header + b"fixture")


def write_geojson(path: Path) -> None:
    path.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [178.2, -17.8]}, "properties": {}}],
    }), encoding="utf-8")


class FirstRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.config = self.base / "config"
        self.default_root = self.base / "charts"
        self.customer = self.base / "customer"
        (self.customer / "FIJI").mkdir(parents=True)
        write_mbtiles(self.customer / "FIJI" / "reef.mbtiles")
        write_pmtiles(self.customer / "FIJI" / "sat.pmtiles")
        write_geojson(self.customer / "anchorages.geojson")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(SCRIPT),
             "--config-dir", str(self.config),
             "--default-root", str(self.default_root),
             "--packd-url", UNREACHABLE_PACKD,
             *args],
            capture_output=True, text=True, check=False,
        )

    def index(self) -> dict:
        return json.loads((self.config / "chart-index.json").read_text(encoding="utf-8"))

    def test_bootstrap_registers_roots_in_place_and_summarizes_personas(self) -> None:
        before = sorted((path, path.stat().st_mtime_ns) for path in self.customer.rglob("*") if path.is_file())
        result = self.run_script("--root", str(self.customer), "--label", "Voyage charts")
        self.assertEqual(result.returncode, 0, result.stderr)

        registry_file = self.config / "chart-roots.json"
        self.assertEqual(os.stat(registry_file).st_mode & 0o777, 0o600)
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
        self.assertEqual(registry["schema"], "helm.chart_intake.roots.v1")
        self.assertEqual(len(registry["roots"]), 2)
        self.assertTrue(self.default_root.is_dir())

        index = self.index()
        by_type = {}
        for chart in index["charts"]:
            by_type[chart["chart_type"]] = by_type.get(chart["chart_type"], 0) + 1
        self.assertEqual(by_type, {"tile_pack": 2, "overlay": 1})
        self.assertEqual({chart["group"] for chart in index["charts"]}, {"FIJI", "."})

        # The customer's files were indexed in place — never moved or rewritten.
        after = sorted((path, path.stat().st_mtime_ns) for path in self.customer.rglob("*") if path.is_file())
        self.assertEqual(before, after)

        self.assertIn("tile packs     : 2", result.stdout)
        self.assertIn("overlays       : 1", result.stdout)
        self.assertIn("Voyage charts", result.stdout)
        self.assertIn("registry takes effect on its next start", result.stdout)

    def test_rerun_is_idempotent(self) -> None:
        first = self.run_script("--root", str(self.customer))
        self.assertEqual(first.returncode, 0, first.stderr)
        fingerprint = self.index()["fingerprint"]
        again = self.run_script()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.index()["fingerprint"], fingerprint)

    def test_no_packd_flag_skips_the_live_poke(self) -> None:
        result = self.run_script("--no-packd")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipping live helm-packd rescan", result.stdout)

    def test_missing_root_fails_loud(self) -> None:
        result = self.run_script("--root", str(self.base / "does-not-exist"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("chart root is unavailable", result.stderr)

    def test_invalid_chart_fails_loud_with_named_cause(self) -> None:
        (self.customer / "FIJI" / "broken.mbtiles").write_bytes(b"this is not sqlite")
        result = self.run_script("--root", str(self.customer))
        self.assertEqual(result.returncode, 1)
        self.assertIn("INDEX STATUS: error", result.stderr)
        self.assertIn("contents_extension_mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
