#!/usr/bin/env python3
"""Smoke tests for the local MBTiles/PMTiles pack server."""

import gzip
import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "pipeline" / "mbtiles_server.py"
ENV_FIXTURE = ROOT / "services" / "wx" / "fixtures" / "fiji-env-bundle-v1.json"


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_mbtiles(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    conn.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [
            ("name", "Demo Chart"),
            ("format", "png"),
            ("bounds", "178.0,-18.0,179.0,-17.0"),
            ("minzoom", "0"),
            ("maxzoom", "1"),
            ("attribution", "test fixture"),
            ("source", "NOAA ENC fixture"),
            ("source_id", "US5FIXTURE"),
            ("source_url", "https://charts.noaa.gov/fixture"),
            ("source_format", "S-57"),
            ("source_updated", "2026-06-01T00:00:00Z"),
            ("source_confidence", "official-fixture"),
            ("license", "public-domain-fixture"),
            ("helm_pack_schema", "helm.offline.region.v1"),
            ("pack_role", "s52-chart"),
            ("renderer", "s52"),
            ("palette", "day"),
            ("display_category", "std"),
            ("chart_edition", "fixture-edition-1"),
            ("render_date", "2026-06-29T00:00:00Z"),
            ("stale_after_days", "36500"),
            ("tile_count", "1"),
            ("tile_count_expected", "3"),
            ("no_coverage_tile_count", "1"),
            ("missing_tile_count", "1"),
            ("coverage_status", "partial"),
            ("coverage_warning", "fixture coverage gap"),
            ("palette_pack_group", "fixture-s52"),
            ("palette_pack_count", "2"),
            ("palette_variants", '["day","night"]'),
        ],
    )
    conn.execute("INSERT INTO tiles VALUES (0, 0, 0, ?)", (b"\x89PNG\r\n\x1a\nfixture",))
    conn.commit()
    conn.close()


def write_depth_mbtiles(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    conn.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [
            ("name", "Demo Depth"),
            ("format", "png"),
            ("kind", "depth"),
            ("bounds", "178.0,-18.0,179.0,-17.0"),
            ("minzoom", "0"),
            ("maxzoom", "1"),
            ("attribution", "test fixture"),
            ("source", "survey fixture"),
            ("source_id", "DEPTH-FIXTURE"),
            ("source_confidence", "surveyed-fixture"),
            ("render_date", "2026-06-29T00:00:00Z"),
            ("stale_after_days", "36500"),
        ],
    )
    conn.commit()
    conn.close()


def write_pmtiles(path):
    metadata = gzip.compress(
        json.dumps(
            {
                "name": "Demo Satellite",
                "type": "raster",
                "bounds": [178.0, -18.0, 179.0, -17.0],
                "minzoom": 0,
                "maxzoom": 2,
                "attribution": "test fixture",
                "source": "Sentinel-2 fixture",
                "source_id": "S2-FIXTURE",
                "source_updated": "2000-01-01T00:00:00Z",
                "source_confidence": "stale-fixture",
                "license": "CC-BY-4.0-fixture",
                "helm_pack_schema": "helm.offline.region.v1",
                "pack_role": "s52-chart",
                "renderer": "s52",
                "palette": "night",
                "display_category": "std",
                "chart_edition": "fixture-edition-2",
                "render_date": "2000-01-01T00:00:00Z",
                "stale_after_days": 1,
                "tile_count": 1,
                "tile_count_expected": 1,
                "no_coverage_tile_count": 0,
                "missing_tile_count": 0,
                "coverage_status": "complete",
                "palette_pack_group": "fixture-s52",
                "palette_pack_count": 2,
                "palette_variants": ["day", "night"],
            }
        ).encode("utf-8")
    )
    header = bytearray(127)
    header[0:7] = b"PMTiles"
    header[7] = 3
    struct.pack_into("<Q", header, 24, 127)
    struct.pack_into("<Q", header, 32, len(metadata))
    struct.pack_into("<Q", header, 72, 0)
    struct.pack_into("<Q", header, 80, 0)
    struct.pack_into("<Q", header, 88, 0)
    header[97] = 2
    header[98] = 1
    header[99] = 2
    header[100] = 0
    header[101] = 2
    struct.pack_into("<i", header, 102, int(178.0 * 1e7))
    struct.pack_into("<i", header, 106, int(-18.0 * 1e7))
    struct.pack_into("<i", header, 110, int(179.0 * 1e7))
    struct.pack_into("<i", header, 114, int(-17.0 * 1e7))
    header[118] = 1
    struct.pack_into("<i", header, 119, int(178.5 * 1e7))
    struct.pack_into("<i", header, 123, int(-17.5 * 1e7))
    path.write_bytes(bytes(header) + metadata + b"tile-data")


def request_json(url):
    with urllib.request.urlopen(url, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def post_json(url):
    request = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def request_json_allow_error(url):
    """Like request_json but returns (status, body) for 4xx/5xx instead of raising."""
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class PackServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        write_mbtiles(self.tmp_path / "chart.mbtiles")
        (self.tmp_path / "chart.metadata.json").write_text(
            json.dumps(
                {
                    "source_ref": "fixture-sidecar-ref",
                    "coverage_note": "sidecar coverage note",
                    "inspection": {
                        "mode": "sidecar_metadata",
                        "semantic_objects": "sidecar",
                        "tap_action": "show_sidecar_then_pack_metadata",
                        "message": "Curated hints only; raster pixels remain non-semantic.",
                        "private_path": self.tmp.name,
                    },
                    "private_path": self.tmp.name,
                }
            ),
            encoding="utf-8",
        )
        write_depth_mbtiles(self.tmp_path / "depth.mbtiles")
        write_pmtiles(self.tmp_path / "sat.pmtiles")
        self.port = free_port()
        env = os.environ.copy()
        env["HELM_MBTILES_DIR"] = self.tmp.name
        env["HELM_ENV_BUNDLE_MANIFESTS"] = str(ENV_FIXTURE)
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(self.port)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + 5
        last = None
        while time.time() < deadline:
            if self.proc.poll() is not None:
                out = self.proc.stdout.read() if self.proc.stdout else ""
                self.fail(f"server exited early with {self.proc.returncode}: {out}")
            try:
                status, data = request_json(f"http://127.0.0.1:{self.port}/catalog")
                if status == 200 and "chart" in data and "sat" in data:
                    return
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.05)
        self.fail(f"server did not become ready: {last}")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()
        self.tmp.cleanup()

    def test_catalog_exposes_mbtiles_and_pmtiles_without_paths(self):
        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(catalog["chart"]["container"], "mbtiles")
        self.assertEqual(catalog["chart"]["tile_url"], f"http://127.0.0.1:{self.port}/chart/{{z}}/{{x}}/{{y}}.png")
        self.assertEqual(catalog["chart"]["renderer"], "s52")
        self.assertEqual(catalog["chart"]["palette"], "day")
        self.assertEqual(catalog["chart"]["chart_edition"], "fixture-edition-1")
        self.assertEqual(catalog["chart"]["palette_pack_group"], "fixture-s52")
        self.assertEqual(catalog["chart"]["license"], "public-domain-fixture")
        self.assertEqual(catalog["chart"]["source_info"]["label"], "NOAA ENC fixture")
        self.assertEqual(catalog["chart"]["source_info"]["id"], "US5FIXTURE")
        self.assertEqual(catalog["chart"]["source_info"]["format"], "S-57")
        self.assertEqual(catalog["chart"]["source_info"]["updated"], "2026-06-01T00:00:00Z")
        self.assertEqual(catalog["chart"]["source_info"]["confidence"], "official-fixture")
        self.assertEqual(catalog["chart"]["source_info"]["ref"], "fixture-sidecar-ref")
        self.assertEqual(catalog["chart"]["source_info"]["coverage_note"], "sidecar coverage note")
        self.assertEqual(catalog["chart"]["coverage"]["status"], "partial")
        self.assertEqual(catalog["chart"]["coverage"]["gap_count"], 2)
        self.assertEqual(catalog["chart"]["coverage"]["warning"], "fixture coverage gap")
        self.assertEqual(catalog["chart"]["staleness"]["status"], "fresh")
        self.assertTrue(catalog["chart"]["inspection"]["sidecar_metadata"])
        self.assertEqual(catalog["chart"]["inspection"]["mode"], "sidecar_metadata")
        self.assertEqual(catalog["chart"]["inspection"]["semantic_objects"], "sidecar")
        self.assertEqual(catalog["chart"]["inspection"]["tap_action"], "show_sidecar_then_pack_metadata")
        self.assertEqual(catalog["chart"]["inspection"]["chart_object_query"], "use_live_CHART_10_query_when_source_ENC_is_mounted")
        self.assertEqual(catalog["chart"]["inspection"]["sidecar_name"], "chart.metadata.json")
        self.assertNotIn("private_path", catalog["chart"]["inspection"])
        self.assertIn("pack_out_of_coverage", [w["code"] for w in catalog["chart"]["warnings"]])
        self.assertEqual(catalog["sat"]["container"], "pmtiles")
        self.assertTrue(catalog["sat"]["range"])
        self.assertEqual(catalog["sat"]["renderer"], "s52")
        self.assertEqual(catalog["sat"]["palette"], "night")
        self.assertEqual(catalog["sat"]["chart_edition"], "fixture-edition-2")
        self.assertEqual(catalog["sat"]["license"], "CC-BY-4.0-fixture")
        self.assertEqual(catalog["sat"]["source_info"]["label"], "Sentinel-2 fixture")
        self.assertEqual(catalog["sat"]["source_info"]["id"], "S2-FIXTURE")
        self.assertEqual(catalog["sat"]["source_info"]["updated"], "2000-01-01T00:00:00Z")
        self.assertEqual(catalog["sat"]["inspection"]["mode"], "raster_metadata")
        self.assertEqual(catalog["sat"]["inspection"]["semantic_objects"], "unavailable")
        self.assertEqual(catalog["sat"]["inspection"]["tap_action"], "show_pack_source_metadata")
        self.assertEqual(catalog["sat"]["coverage"]["status"], "complete")
        self.assertEqual(catalog["sat"]["staleness"]["status"], "stale")
        self.assertIn("pack_stale", [w["code"] for w in catalog["sat"]["warnings"]])
        self.assertEqual(catalog["sat"]["pmtiles_url"], f"http://127.0.0.1:{self.port}/sat.pmtiles")
        self.assertEqual(catalog["sat"]["protocol_url"], f"pmtiles://http://127.0.0.1:{self.port}/sat.pmtiles")
        self.assertEqual(catalog["depth"]["inspection"]["mode"], "depth_sample")
        self.assertEqual(catalog["depth"]["inspection"]["semantic_objects"], "depth_values")
        self.assertEqual(catalog["depth"]["inspection"]["tap_action"], "show_depth_source_confidence")
        self.assertEqual(catalog["depth"]["source_info"]["confidence"], "surveyed-fixture")
        self.assertNotIn(self.tmp.name, json.dumps(catalog))

    def test_mbtiles_tile_endpoint_still_serves_xyz(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/chart/0/0/0.png", timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "image/png")
            self.assertEqual(resp.read(), b"\x89PNG\r\n\x1a\nfixture")

    def test_pmtiles_endpoint_supports_range_and_head(self):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/sat.pmtiles",
            headers={"Range": "bytes=0-6"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(resp.headers.get("Accept-Ranges"), "bytes")
            self.assertEqual(resp.headers.get("Content-Range"), "bytes 0-6/" + resp.headers.get("Content-Range").split("/")[-1])
            self.assertEqual(resp.read(), b"PMTiles")

        head = urllib.request.Request(f"http://127.0.0.1:{self.port}/sat.pmtiles", method="HEAD")
        with urllib.request.urlopen(head, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertGreater(int(resp.headers.get("Content-Length", "0")), 127)
            self.assertEqual(resp.read(), b"")

    def test_recursive_discovery_auto_refresh_and_explicit_rescan(self):
        nested = self.tmp_path / "FIJI" / "SAT"
        nested.mkdir(parents=True)
        write_mbtiles(nested / "lagoon.mbtiles")
        (nested / "lagoon.metadata.json").write_text(
            json.dumps({"title": "Fiji Lagoon", "license": "fixture-license"}),
            encoding="utf-8",
        )

        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(catalog["lagoon"]["title"], "Fiji Lagoon")
        self.assertEqual(catalog["lagoon"]["license"], "fixture-license")
        self.assertNotIn(self.tmp.name, json.dumps(catalog))

        (nested / "lagoon.metadata.json").write_text(
            json.dumps({"title": "Fiji Lagoon Updated", "license": "fixture-license"}),
            encoding="utf-8",
        )
        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(catalog["lagoon"]["title"], "Fiji Lagoon Updated")

        status, rescan = post_json(f"http://127.0.0.1:{self.port}/rescan")
        self.assertEqual(status, 200)
        self.assertEqual(rescan["schema"], "helm.chart_index.rescan.v1")
        self.assertFalse(rescan["changed"])
        self.assertEqual(rescan["packs"], 4)
        self.assertRegex(rescan["fingerprint"], r"^[0-9a-f]{64}$")

    def test_registered_roots_file_scans_multiple_roots_and_preserves_collisions(self):
        with tempfile.TemporaryDirectory() as extra_tmp:
            extra_root = Path(extra_tmp)
            write_mbtiles(extra_root / "chart.mbtiles")
            registry = self.tmp_path / "chart-roots.json"
            registry.write_text(json.dumps({
                "schema": "helm.chart_intake.roots.v1",
                "roots": [
                    {"id": "root-one", "path": self.tmp.name},
                    {"id": "root-two", "path": extra_tmp},
                ],
            }), encoding="utf-8")
            port = free_port()
            env = os.environ.copy()
            env["HELM_MBTILES_DIR"] = self.tmp.name
            env["HELM_CHART_ROOTS_FILE"] = str(registry)
            proc = subprocess.Popen(
                [sys.executable, str(SERVER), str(port)],
                cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
            )
            try:
                deadline = time.time() + 5
                catalog = None
                while time.time() < deadline:
                    if proc.poll() is not None:
                        output = proc.stdout.read() if proc.stdout else ""
                        self.fail(f"multi-root server exited early: {output}")
                    try:
                        _, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
                        if "chart--r2" in catalog:
                            break
                    except (OSError, urllib.error.URLError, json.JSONDecodeError):
                        time.sleep(0.05)
                self.assertIsNotNone(catalog)
                self.assertIn("chart", catalog)
                self.assertIn("chart--r2", catalog)
                self.assertEqual(len(catalog), 4)
                self.assertNotIn(extra_tmp, json.dumps(catalog))
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                if proc.stdout:
                    proc.stdout.close()

    def test_empty_library_starts_and_discovers_first_pack_without_restart(self):
        with tempfile.TemporaryDirectory() as empty_tmp:
            port = free_port()
            env = os.environ.copy()
            env["HELM_MBTILES_DIR"] = empty_tmp
            env.pop("HELM_CHART_ROOTS", None)
            env.pop("HELM_CHART_ROOTS_FILE", None)
            proc = subprocess.Popen(
                [sys.executable, str(SERVER), str(port)],
                cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
            )
            try:
                deadline = time.time() + 5
                while True:
                    try:
                        status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
                        break
                    except (OSError, urllib.error.URLError, json.JSONDecodeError):
                        if time.time() >= deadline:
                            self.fail("empty-library server did not become ready")
                        time.sleep(0.05)
                self.assertEqual(status, 200)
                self.assertEqual(catalog, {})
                write_mbtiles(Path(empty_tmp) / "first.mbtiles")
                _, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
                self.assertIn("first", catalog)
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                if proc.stdout:
                    proc.stdout.close()

    def test_explicit_pack_map_remains_an_advanced_override(self):
        port = free_port()
        env = os.environ.copy()
        env["HELM_MBTILES_DIR"] = self.tmp.name
        env["HELM_MBTILES_PACKS"] = json.dumps({"selected": "chart.mbtiles"})
        proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(port)], cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            deadline = time.time() + 5
            while True:
                try:
                    _, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
                    break
                except (OSError, urllib.error.URLError, json.JSONDecodeError):
                    if time.time() >= deadline:
                        self.fail("override server did not become ready")
                    time.sleep(0.05)
            self.assertEqual(list(catalog), ["selected"])
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            if proc.stdout:
                proc.stdout.close()

    def test_bundle_endpoint_groups_catalog_and_prefetch_metadata(self):
        status, bundle = request_json(
            f"http://127.0.0.1:{self.port}/bundle?bbox=178.0,-18.0,178.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0"
        )
        self.assertEqual(status, 200)
        self.assertEqual(bundle["schema"], "helm.region_bundle.manifest.v1")
        self.assertEqual(bundle["prefetch"]["schema"], "helm.prefetch.manifest.v1")
        self.assertEqual(bundle["summary"]["roles"]["chart"], 1)
        self.assertEqual(bundle["summary"]["roles"]["basemap"], 1)
        self.assertEqual(bundle["summary"]["roles"]["depth"], 1)
        self.assertEqual(bundle["corridor"]["bbox"], [178.0, -18.0, 178.5, -17.5])
        chart = next(c for c in bundle["components"] if c["id"] == "pack:chart")
        self.assertEqual(chart["source_info"]["id"], "US5FIXTURE")
        self.assertIn("out_of_coverage", chart["status"]["states"])
        self.assertNotIn(self.tmp.name, json.dumps(bundle))

    def test_layers_endpoint_exposes_local_maritime_inventory(self):
        status, inventory = request_json(
            f"http://127.0.0.1:{self.port}/layers?bbox=178.0,-18.0,178.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0"
        )
        self.assertEqual(status, 200)
        self.assertEqual(inventory["schema"], "helm.maritime_layer_inventory.v1")
        self.assertEqual(inventory["coverage"]["bbox"], [178.0, -18.0, 178.5, -17.5])
        self.assertEqual(inventory["summary"]["roles"]["chart"], 1)
        self.assertEqual(inventory["summary"]["roles"]["basemap"], 1)
        self.assertEqual(inventory["summary"]["roles"]["depth"], 1)
        self.assertEqual(inventory["summary"]["roles"]["environmental_bundle"], 1)
        self.assertIn("weather.bundle", inventory["summary"]["sample_handles"])
        chart = next(layer for layer in inventory["layers"] if layer["component_id"] == "pack:chart")
        self.assertEqual(chart["product_identifier"], "S-52")
        self.assertEqual(chart["dataset_name"], "Demo Chart")
        self.assertEqual(chart["producer_code"], "NOAA ENC fixture")
        self.assertEqual(chart["source"]["id"], "US5FIXTURE")
        self.assertEqual(chart["sample"]["status"], "available")
        self.assertEqual(chart["sample"]["probe_handle"], "chart.objects")
        self.assertEqual(chart["pack"]["container"], "mbtiles")
        sat = next(layer for layer in inventory["layers"] if layer["component_id"] == "pack:sat")
        self.assertEqual(sat["product_identifier"], "S-52")
        self.assertEqual(sat["freshness"]["status"], "stale")
        env_bundle = next(layer for layer in inventory["layers"] if layer["role"] == "environmental_bundle")
        self.assertEqual(env_bundle["product_identifier"], "helm.env.bundle.v1")
        self.assertEqual(env_bundle["coverage"]["bbox_object"]["crossesAntimeridian"], True)
        env_current = next(layer for layer in inventory["layers"] if layer["role"] == "surface_current")
        self.assertEqual(env_current["product_identifier"], "S-111")
        self.assertNotIn(self.tmp.name, json.dumps(inventory))
        self.assertNotIn(str(ENV_FIXTURE), json.dumps(inventory))

    def test_bundle_sat_first_profile_returns_basemap_estimate(self):
        # OFFLINE-L-3: the download drawer requests ?profile=sat_first for a live estimate.
        status, bundle = request_json(
            f"http://127.0.0.1:{self.port}/bundle?"
            "bbox=178.0,-18.0,178.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0&profile=sat_first"
        )
        self.assertEqual(status, 200)
        self.assertEqual(bundle["profile"], "sat_first")
        # chart packs are dropped from the sat-first estimate; the satellite basemap stays.
        self.assertNotIn("chart", bundle["summary"]["roles"])
        self.assertEqual(bundle["summary"]["roles"]["basemap"], 1)
        self.assertIsNotNone(bundle["summary"].get("estimated_bytes"))
        basemap = next(c for c in bundle["components"] if c["role"] == "basemap")
        self.assertEqual(basemap["pack_id"], "sat")
        self.assertTrue(basemap["primary"])

    def test_bundle_sat_first_missing_basemap_returns_422(self):
        # A bbox with no satellite coverage must fail closed, not return a basemap-less "ok".
        status, body = request_json_allow_error(
            f"http://127.0.0.1:{self.port}/bundle?"
            "bbox=170.0,-18.0,170.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0&profile=sat_first"
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "missing_basemap")
        self.assertEqual(body["profile"], "sat_first")


def post_json_body(url, payload):
    """POST a JSON object; returns (status, body) for 2xx and 4xx/5xx alike."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class ChartIntakeEndpointsTest(unittest.TestCase):
    """INTAKE-5: /chart-index + /chart-roots HTTP seam over the INTAKE-2 registry."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.library = Path(self.tmp.name) / "library"
        (self.library / "FIJI").mkdir(parents=True)
        (self.library / "TONGA").mkdir(parents=True)
        write_mbtiles(self.library / "FIJI" / "lagoon.mbtiles")
        (self.library / "FIJI" / "passage.geojson").write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [178.2, -17.8]}, "properties": {}}],
        }), encoding="utf-8")
        write_pmtiles(self.library / "TONGA" / "reef.pmtiles")
        (self.library / "cell.000").write_bytes(b"not a real S-57 leader")
        (self.library / "cell.001").write_bytes(b"junk update")
        self.config_dir = Path(self.tmp.name) / "config"
        self.config_dir.mkdir()
        self.proc = None

    def tearDown(self):
        self._stop()
        self.tmp.cleanup()

    def _stop(self):
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()
        self.proc = None

    def _boot(self, extra_env=None):
        port = free_port()
        env = os.environ.copy()
        env.pop("HELM_CHART_ROOTS", None)
        env.pop("HELM_CHART_ROOTS_FILE", None)
        env["HELM_MBTILES_DIR"] = str(self.library)
        env["HELM_CONFIG"] = str(self.config_dir)
        env.update(extra_env or {})
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(port)],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        )
        deadline = time.time() + 5
        last = None
        while time.time() < deadline:
            if self.proc.poll() is not None:
                out = self.proc.stdout.read() if self.proc.stdout else ""
                self.fail(f"server exited early with {self.proc.returncode}: {out}")
            try:
                status, _ = request_json(f"http://127.0.0.1:{port}/catalog")
                if status == 200:
                    return port
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.05)
        self.fail(f"server did not become ready: {last}")

    def test_chart_index_serves_library_inventory_read_only(self):
        port = self._boot()
        status, index = request_json(f"http://127.0.0.1:{port}/chart-index")
        self.assertEqual(status, 200)
        self.assertEqual(index["schema"], "helm.chart_intake.index.v1")
        by_name = {item["filename"]: item for item in index["charts"]}
        self.assertEqual(by_name["lagoon.mbtiles"]["chart_type"], "tile_pack")
        self.assertEqual(by_name["lagoon.mbtiles"]["group"], "FIJI")
        self.assertEqual(by_name["passage.geojson"]["chart_type"], "overlay")
        self.assertEqual(by_name["reef.pmtiles"]["group"], "TONGA")
        self.assertEqual(by_name["cell.000"]["chart_type"], "enc")
        self.assertEqual(by_name["cell.000"]["group"], ".")
        self.assertEqual(by_name["cell.000"]["update_count"], 1)
        self.assertEqual(by_name["cell.000"]["validation"]["status"], "error")
        self.assertEqual(len(index["roots"]), 1)
        self.assertTrue(index["roots"][0]["default"])
        self.assertEqual(index["roots"][0]["status"], "available")
        # Privacy: labels + relative paths only, never the absolute library path.
        self.assertNotIn(self.tmp.name, json.dumps(index))
        # Read-only: looking at the index must not create registry/index files.
        self.assertFalse((self.config_dir / "chart-roots.json").exists())
        self.assertFalse((self.config_dir / "chart-index.json").exists())

    def test_chart_roots_register_refresh_and_remove_over_http(self):
        port = self._boot()
        with tempfile.TemporaryDirectory() as extra_tmp:
            extra = Path(extra_tmp) / "ChartLocker"
            extra.mkdir()
            write_mbtiles(extra / "harbor.mbtiles")

            status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots", {"path": str(extra)})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "ok")
            self.assertTrue(body["changed"])
            self.assertEqual(body["root"]["label"], "ChartLocker")
            self.assertNotIn("path", body["root"])
            added_id = body["root"]["id"]
            self.assertTrue((self.config_dir / "chart-roots.json").exists())

            status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
            self.assertEqual(status, 200)
            self.assertIn("harbor", catalog)
            self.assertIn("lagoon", catalog)

            status, roots = request_json(f"http://127.0.0.1:{port}/chart-roots")
            self.assertEqual(status, 200)
            self.assertEqual(roots["source"], "file")
            self.assertEqual(len(roots["roots"]), 2)
            self.assertNotIn(extra_tmp, json.dumps(roots))

            status, index = request_json(f"http://127.0.0.1:{port}/chart-index")
            self.assertEqual(status, 200)
            self.assertIn("harbor.mbtiles", {item["filename"] for item in index["charts"]})

            # Idempotent re-register of the same path reports changed=false.
            status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots", {"path": str(extra)})
            self.assertEqual(status, 200)
            self.assertFalse(body["changed"])

            status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots/remove", {"id": added_id})
            self.assertEqual(status, 200)
            self.assertEqual(body["removed"]["id"], added_id)
            self.assertTrue((extra / "harbor.mbtiles").is_file())  # unregister never deletes files

            status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
            self.assertEqual(status, 200)
            self.assertNotIn("harbor", catalog)

    def test_chart_roots_rejections_are_named(self):
        port = self._boot()
        status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots", {"path": str(self.library / "missing-dir")})
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "chart_root_rejected")

        status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots", {"label": "no path"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad_chart_root_request")

        # The default root row protects /catalog continuity; removing it is refused.
        status, roots = request_json(f"http://127.0.0.1:{port}/chart-roots")
        self.assertEqual(status, 200)
        default_id = next(row["id"] for row in roots["roots"] if row["default"])
        status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots/remove", {"id": default_id})
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "chart_root_rejected")

        status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots/remove", {"id": "root-does-not-exist"})
        self.assertEqual(status, 422)

    def test_env_managed_roots_are_visible_but_not_mutable(self):
        port = self._boot({"HELM_CHART_ROOTS": json.dumps([str(self.library)])})
        status, roots = request_json(f"http://127.0.0.1:{port}/chart-roots")
        self.assertEqual(status, 200)
        self.assertEqual(roots["source"], "env")
        self.assertEqual(roots["roots"][0]["label"], "library")

        status, index = request_json(f"http://127.0.0.1:{port}/chart-index")
        self.assertEqual(status, 200)
        self.assertIn("lagoon.mbtiles", {item["filename"] for item in index["charts"]})

        status, body = post_json_body(f"http://127.0.0.1:{port}/chart-roots", {"path": str(self.library)})
        self.assertEqual(status, 409)
        self.assertEqual(body["error"], "chart_roots_env_managed")
        self.assertFalse((self.config_dir / "chart-roots.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
