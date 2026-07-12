#!/usr/bin/env python3
"""Contract tests for the OFFLINE-16/17 C++ helm-packd daemon.

The Python pack server remains the broad reference/oracle. These tests pin the
runtime C++ parity slice: health, catalog privacy/URL shape, MBTiles XYZ->TMS,
PMTiles HEAD/Range, and OFFLINE-17 `/layers`/`/prefetch`/`/bundle` metadata.

Set HELM_PACKD_BIN to the built binary, for example:

    HELM_PACKD_BIN=/private/tmp/helm-offline16-ocpn/build/cli/helm-packd \
      python3 pipeline/test_helm_packd_contract.py
"""

from __future__ import annotations

import datetime as dt
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
ENV_FIXTURE = ROOT / "services" / "wx" / "fixtures" / "fiji-env-bundle-v1.json"


def _iso_days_ago(days: float) -> str:
    moment = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def write_mbtiles(path: Path) -> None:
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
            ("license", "public-domain-fixture"),
        ],
    )
    conn.execute("INSERT INTO tiles VALUES (0, 0, 0, ?)", (b"\x89PNG\r\n\x1a\nfixture",))
    conn.commit()
    conn.close()


def write_pmtiles(path: Path) -> None:
    metadata = gzip.compress(
        json.dumps(
            {
                "name": "Demo Satellite",
                "type": "raster",
                "bounds": [178.0, -18.0, 179.0, -17.0],
                "minzoom": 0,
                "maxzoom": 2,
                "attribution": "test fixture",
            }
        ).encode("utf-8")
    )
    header = bytearray(127)
    header[0:7] = b"PMTiles"
    header[7] = 3
    struct.pack_into("<Q", header, 24, 127)
    struct.pack_into("<Q", header, 32, len(metadata))
    struct.pack_into("<Q", header, 72, 1)
    struct.pack_into("<Q", header, 80, 1)
    struct.pack_into("<Q", header, 88, 1)
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


def write_sidecar(path: Path) -> None:
    """Write public pack metadata plus one private field that must not leak."""

    path.write_text(
        json.dumps(
            {
                "renderer": "s52",
                "palette": "day",
                "display_category": "std",
                "chart_edition": "FJ-2026",
                "render_date": "2026-06-29T00:00:00Z",
                "staleness_status": "fresh",
                "tile_count": 1,
                "tile_count_expected": 2,
                "no_coverage_tile_count": 1,
                "coverage_status": "partial",
                "coverage_warning": "Fixture coverage gap.",
                "source_id": "FJ-FIXTURE",
                "source_updated": "2026-06-01T00:00:00Z",
                "source_confidence": "fixture",
                "inspection": {
                    "mode": "raster_metadata",
                    "semantic_objects": "unavailable",
                    "tap_action": "show_pack_source_metadata",
                    "private_path": "/private/tmp/should-not-leak",
                },
                "private_path": "/private/tmp/should-not-leak",
            }
        ),
        encoding="utf-8",
    )


def write_user_data_fixtures(user_root: Path) -> None:
    (user_root / "depare.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {"source": "enc", "cell": "FJ-FIXTURE"},
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[178.0, -18.0], [178.5, -18.0], [178.5, -17.5], [178.0, -17.5], [178.0, -18.0]]],
                        },
                        "properties": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    layers_dir = user_root / "layers"
    layers_dir.mkdir()
    (layers_dir / "anchorages.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [178.2, -17.8]},
                        "properties": {"name": "Fixture Anchorage"},
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
                "source": {
                    "label": "owned",
                    "license": "private-local",
                    "api_key": "do-not-publish",
                    "token": "also-secret",
                    "url": "file:///private/tmp/source",
                },
                "private_path": "/private/tmp/should-not-leak",
            }
        ),
        encoding="utf-8",
    )
    # An overlay whose sidecar declares a freshness window that has already expired, so the
    # manifest must report it as honestly stale (drives CAT-2's "stale overlay" banner).
    (layers_dir / "stale_note.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [178.3, -17.7]},
                        "properties": {"name": "Stale note"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (layers_dir / "stale_note.metadata.json").write_text(
        json.dumps(
            {
                "id": "stale-note",
                "title": "Stale note",
                "freshness": {"render_date": _iso_days_ago(400), "stale_after_days": 1},
            }
        ),
        encoding="utf-8",
    )


def request_json(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def post_json(url: str) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def request_json_allow_error(url: str) -> tuple[int, dict]:
    """Like request_json but returns (status, body) for 4xx/5xx instead of raising."""
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def spawn_packd(bin_path, mbtiles_dir, extra_env):
    """Start a helm-packd with the given env, wait for /health, return (proc, port)."""
    port = free_port()
    env = os.environ.copy()
    env["HELM_MBTILES_DIR"] = str(mbtiles_dir)
    env["HELM_BIND"] = "127.0.0.1"
    env.update(extra_env)
    proc = subprocess.Popen(
        [str(bin_path), str(port)], cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise AssertionError(f"helm-packd exited early: {out}")
        try:
            status, data = request_json(f"http://127.0.0.1:{port}/health")
            if status == 200 and data.get("engine") == "helm-packd":
                return proc, port
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            time.sleep(0.05)
    raise AssertionError("helm-packd did not become ready")


@unittest.skipUnless(os.environ.get("HELM_PACKD_BIN"), "set HELM_PACKD_BIN to the built helm-packd binary")
class HelmPackdContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bin = Path(os.environ["HELM_PACKD_BIN"])
        if not self.bin.exists() or not os.access(self.bin, os.X_OK):
            self.skipTest(f"HELM_PACKD_BIN is not executable: {self.bin}")
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.user_data = self.tmp_path / "user-data"
        self.user_data.mkdir()
        write_user_data_fixtures(self.user_data)
        write_mbtiles(self.tmp_path / "chart.mbtiles")
        write_sidecar(self.tmp_path / "chart.metadata.json")
        write_pmtiles(self.tmp_path / "sat.pmtiles")
        self.port = free_port()
        env = os.environ.copy()
        env["HELM_MBTILES_DIR"] = self.tmp.name
        env["HELM_USER_DATA_ROOT"] = str(self.user_data)
        env["HELM_ENV_BUNDLE_MANIFESTS"] = str(ENV_FIXTURE)
        env["HELM_BIND"] = "127.0.0.1"
        self.proc = subprocess.Popen(
            [str(self.bin), str(self.port)],
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
                self.fail(f"helm-packd exited early with {self.proc.returncode}: {out}")
            try:
                status, data = request_json(f"http://127.0.0.1:{self.port}/health")
                if status == 200 and data.get("engine") == "helm-packd":
                    return
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.05)
        self.fail(f"helm-packd did not become ready: {last}")

    def tearDown(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()
        self.tmp.cleanup()

    def test_health_and_catalog_do_not_leak_filesystem_paths(self) -> None:
        status, health = request_json(f"http://127.0.0.1:{self.port}/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["packs"], 2)

        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(catalog["chart"]["container"], "mbtiles")
        self.assertEqual(catalog["chart"]["title"], "Demo Chart")
        self.assertEqual(catalog["chart"]["format"], "png")
        self.assertEqual(catalog["chart"]["minzoom"], 0)
        self.assertEqual(catalog["chart"]["maxzoom"], 1)
        self.assertEqual(
            catalog["chart"]["tile_url"],
            f"http://127.0.0.1:{self.port}/chart/{{z}}/{{x}}/{{y}}.png",
        )
        self.assertEqual(catalog["sat"]["container"], "pmtiles")
        self.assertTrue(catalog["sat"]["range"])
        self.assertEqual(catalog["sat"]["pmtiles_version"], 3)
        self.assertEqual(catalog["sat"]["minzoom"], 0)
        self.assertEqual(catalog["sat"]["maxzoom"], 2)
        self.assertEqual(catalog["sat"]["pmtiles_url"], f"http://127.0.0.1:{self.port}/sat.pmtiles")
        self.assertNotIn(self.tmp.name, json.dumps(catalog))

    def test_catalog_applies_sidecar_metadata_without_private_paths(self) -> None:
        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)
        chart = catalog["chart"]
        self.assertEqual(chart["renderer"], "s52")
        self.assertEqual(chart["palette"], "day")
        self.assertEqual(chart["source_info"]["id"], "FJ-FIXTURE")
        self.assertEqual(chart["coverage"]["status"], "partial")
        self.assertEqual(chart["staleness"]["status"], "fresh")
        self.assertEqual(chart["inspection"]["mode"], "raster_metadata")
        self.assertEqual(chart["inspection"]["chart_object_query"], "use_live_CHART_10_query_when_source_ENC_is_mounted")
        self.assertEqual(chart["warnings"][0]["code"], "pack_out_of_coverage")
        self.assertNotIn("private_path", json.dumps(chart))
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(chart))

    def test_mbtiles_tile_endpoint_serves_xyz_with_tms_flip(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/chart/0/0/0.png", timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "image/png")
            self.assertEqual(resp.read(), b"\x89PNG\r\n\x1a\nfixture")

    def test_pmtiles_endpoint_supports_range_and_head(self) -> None:
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

        # OFFLINE-18: the warm-mmap path maps the archive once, then serves every slice as a
        # memcpy from the mapped region. Verify it stays byte-identical across many sequential
        # ranges — including mid-file offsets and the last byte — against the full body (which
        # itself exercises the no-Range mmap read).
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/sat.pmtiles", timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            full = resp.read()
        self.assertGreater(len(full), 200)
        end = len(full) - 1
        for start, stop in [(0, 6), (7, 20), (100, 149), (end - 9, end), (end, end)]:
            r = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/sat.pmtiles",
                headers={"Range": f"bytes={start}-{stop}"},
            )
            with urllib.request.urlopen(r, timeout=2) as resp:
                self.assertEqual(resp.status, 206, f"range {start}-{stop}")
                self.assertEqual(resp.read(), full[start:stop + 1], f"range {start}-{stop} bytes")

    def test_recursive_discovery_auto_refresh_and_explicit_rescan(self) -> None:
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
        self.assertEqual(rescan["packs"], 3)
        self.assertRegex(rescan["fingerprint"], r"^[0-9a-f]{16}$")

    def test_registered_roots_file_scans_multiple_roots_and_preserves_collisions(self) -> None:
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
            proc, port = spawn_packd(self.bin, self.tmp_path, {
                "HELM_CHART_ROOTS_FILE": str(registry),
            })
            try:
                status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
                self.assertEqual(status, 200)
                self.assertIn("chart", catalog)
                self.assertIn("chart--r2", catalog)
                self.assertEqual(len(catalog), 3)
                self.assertNotIn(extra_tmp, json.dumps(catalog))
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                if proc.stdout:
                    proc.stdout.close()

    def test_empty_library_starts_and_discovers_first_pack_without_restart(self) -> None:
        with tempfile.TemporaryDirectory() as empty_tmp:
            proc, port = spawn_packd(self.bin, Path(empty_tmp), {})
            try:
                status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
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

    def test_explicit_pack_map_remains_an_advanced_override(self) -> None:
        proc, port = spawn_packd(self.bin, self.tmp_path, {
            "HELM_MBTILES_PACKS": json.dumps({"selected": "chart.mbtiles"}),
        })
        try:
            status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
            self.assertEqual(status, 200)
            self.assertEqual(list(catalog), ["selected"])
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            if proc.stdout:
                proc.stdout.close()

    def test_offline17_layers_prefetch_and_bundle_endpoints(self) -> None:
        status, layers = request_json(
            f"http://127.0.0.1:{self.port}/layers?"
            "bbox=178.0,-18.0,178.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0"
        )
        self.assertEqual(status, 200)
        self.assertEqual(layers["schema"], "helm.maritime_layer_inventory.v1")
        self.assertIn("weather.bundle", layers["summary"]["sample_handles"])
        chart_layer = next(layer for layer in layers["layers"] if layer.get("component_id") == "pack:chart")
        self.assertEqual(chart_layer["product_identifier"], "S-52")
        self.assertEqual(chart_layer["sample"]["status"], "unavailable")
        self.assertEqual(chart_layer["inspection"]["mode"], "raster_metadata")
        env_bundle = next(layer for layer in layers["layers"] if layer["role"] == "environmental_bundle")
        self.assertEqual(env_bundle["product_identifier"], "helm.env.bundle.v1")
        self.assertFalse(env_bundle["environmental_bundle"]["upstreamFetchesAllowedDuringGesture"])
        wind = next(layer for layer in layers["layers"] if layer["id"].endswith(":wind"))
        self.assertEqual(wind["sample"]["probe_handle"], "weather.wind")
        current = next(layer for layer in layers["layers"] if layer["id"].endswith(":current"))
        self.assertEqual(current["product_identifier"], "S-111")
        self.assertNotIn(self.tmp.name, json.dumps(layers))
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(layers))

        status, prefetch = request_json(
            f"http://127.0.0.1:{self.port}/prefetch?"
            "bbox=178.0,-18.0,178.2,-17.8&minzoom=0&maxzoom=1&packs=chart,sat&env_layers=wind,current"
        )
        self.assertEqual(status, 200)
        self.assertEqual(prefetch["schema"], "helm.prefetch.manifest.v1")
        self.assertEqual(prefetch["totals"]["packs"], 2)
        self.assertEqual(prefetch["totals"]["environmental_layers"], 2)
        self.assertEqual(prefetch["packs"][0]["tiles"][0]["url"], f"http://127.0.0.1:{self.port}/chart/0/0/0.png")
        self.assertFalse(prefetch["environmental_bundles"][0]["upstream_fetches_allowed_during_gesture"])
        self.assertNotIn(self.tmp.name, json.dumps(prefetch))

        status, bundle = request_json(
            f"http://127.0.0.1:{self.port}/bundle?"
            "bundle_id=fiji&bbox=178.0,-18.0,178.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0"
        )
        self.assertEqual(status, 200)
        self.assertEqual(bundle["schema"], "helm.region_bundle.manifest.v1")
        chart_component = next(component for component in bundle["components"] if component["id"] == "pack:chart")
        self.assertIn("out_of_coverage", chart_component["status"]["states"])
        self.assertEqual(len(chart_component["fingerprint"]), 64)
        self.assertNotIn(self.tmp.name, json.dumps(bundle))
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(bundle))

    def test_bundle_sat_first_profile_returns_basemap_estimate(self) -> None:
        # OFFLINE-L-4: C++ /bundle honors ?profile=sat_first for the download drawer's live estimate.
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

    def test_bundle_sat_first_missing_basemap_returns_422(self) -> None:
        # A bbox with no satellite coverage must fail closed, not return a basemap-less "ok".
        status, body = request_json_allow_error(
            f"http://127.0.0.1:{self.port}/bundle?"
            "bbox=170.0,-18.0,170.5,-17.5&minzoom=0&maxzoom=1&include_tiles=0&profile=sat_first"
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "missing_basemap")
        self.assertEqual(body["profile"], "sat_first")

    def test_startup_writes_user_layers_readme(self) -> None:
        # LAYER-6: helm-packd self-heals the drop folder on startup. The server in setUp ran with
        # HELM_USER_DATA_ROOT=self.user_data (which already has a layers/), so it wrote the README.
        readme = self.user_data / "layers" / "README.md"
        self.assertTrue(readme.is_file())
        self.assertIn("helm-user-layers-readme", readme.read_text())

    def test_startup_seeds_user_layers_on_fresh_root(self) -> None:
        # A fresh boat (no layers folder yet) gets the folder + README + a working sample, and the
        # sample renders through /layer-manifest.
        with tempfile.TemporaryDirectory() as fresh:
            proc, port = spawn_packd(self.bin, self.tmp_path, {"HELM_USER_DATA_ROOT": fresh})
            try:
                layers = Path(fresh) / "layers"
                self.assertTrue((layers / "README.md").is_file())
                self.assertTrue((layers / "example-harbor-notes.geojson").is_file())
                self.assertTrue((layers / "example-harbor-notes.metadata.json").is_file())
                status, manifest = request_json(f"http://127.0.0.1:{port}/layer-manifest")
                self.assertEqual(status, 200)
                layer = next(l for l in manifest["layers"] if l["id"] == "example-harbor-notes")
                self.assertEqual(layer["tier"], "overlay")
                self.assertEqual(layer["format"], "geojson")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                if proc.stdout:
                    proc.stdout.close()

    def test_layer_manifest_endpoint(self) -> None:
        status, manifest = request_json(f"http://127.0.0.1:{self.port}/layer-manifest")
        self.assertEqual(status, 200)
        self.assertEqual(manifest["schema"], "helm.layer.manifest.v1")
        depare = next(layer for layer in manifest["layers"] if layer["id"] == "depare")
        self.assertEqual(depare["tier"], "enc")
        self.assertEqual(depare["format"], "geojson")
        self.assertEqual(depare["url"], "/user-data/depare.geojson")
        overlay = next(layer for layer in manifest["layers"] if layer["id"] == "owned-anchorage-notes")
        self.assertEqual(overlay["tier"], "overlay")
        self.assertEqual(overlay["inspection"]["mode"], "feature-properties")
        self.assertEqual(overlay["source"], {"label": "owned", "license": "private-local"})
        # CAT-1: honest enc coverage summary (present depare; depcnt/soundg are the enc gap).
        self.assertEqual(manifest["enc"]["expected"], ["depare", "depcnt", "soundg"])
        self.assertEqual(manifest["enc"]["present"], ["depare"])
        self.assertEqual(manifest["enc"]["missing"], ["depcnt", "soundg"])
        self.assertEqual(depare["freshness"]["status"], "ok")
        self.assertIn("age_days", depare["freshness"])
        # CAT-1: an overlay past its declared freshness window is honestly reported stale.
        stale_overlay = next(layer for layer in manifest["layers"] if layer["id"] == "stale-note")
        self.assertEqual(stale_overlay["freshness"]["status"], "stale")
        self.assertGreaterEqual(stale_overlay["freshness"]["age_days"], 300)
        self.assertIn("warning", stale_overlay["freshness"])
        self.assertNotIn("do-not-publish", json.dumps(manifest))
        self.assertNotIn("also-secret", json.dumps(manifest))
        self.assertNotIn("file:///private/tmp/source", json.dumps(manifest))
        self.assertNotIn(self.tmp.name, json.dumps(manifest))
        self.assertNotIn(str(self.user_data), json.dumps(manifest))
        self.assertNotIn("/private/tmp/should-not-leak", json.dumps(manifest))

        head = urllib.request.Request(f"http://127.0.0.1:{self.port}/layer-manifest", method="HEAD")
        with urllib.request.urlopen(head, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertGreater(int(resp.headers.get("Content-Length", "0")), 10)
            self.assertEqual(resp.read(), b"")


@unittest.skipUnless(os.environ.get("HELM_PACKD_BIN"), "set HELM_PACKD_BIN to the built helm-packd binary")
class HelmPackdCatalogStalenessTest(unittest.TestCase):
    """CAT-1: /catalog reports honest, COMPUTED staleness for packs (satellite/enc/overlay share
    this daemon path). A pack past its own declared freshness window is stale even when no sidecar
    pre-stamped the flag; a render_date without a window stays fresh; no render_date is unknown
    (never a fabricated 'fresh')."""

    PACKS = {
        "stalewin": {"render_date": _iso_days_ago(400), "stale_after_days": 90},
        "freshwin": {"render_date": _iso_days_ago(5), "stale_after_days": 90},
        "staleat": {"render_date": _iso_days_ago(10), "stale_at": _iso_days_ago(2)},
        "nowindow": {"render_date": _iso_days_ago(5)},
        "nodate": {"chart_edition": "NO-RENDER-DATE"},
    }

    def setUp(self) -> None:
        self.bin = Path(os.environ["HELM_PACKD_BIN"])
        if not self.bin.exists() or not os.access(self.bin, os.X_OK):
            self.skipTest(f"HELM_PACKD_BIN is not executable: {self.bin}")
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        for stem, meta in self.PACKS.items():
            write_mbtiles(base / f"{stem}.mbtiles")
            (base / f"{stem}.metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        self.port = free_port()
        env = os.environ.copy()
        env["HELM_MBTILES_DIR"] = self.tmp.name
        env["HELM_BIND"] = "127.0.0.1"
        self.proc = subprocess.Popen(
            [str(self.bin), str(self.port)],
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
                self.fail(f"helm-packd exited early with {self.proc.returncode}: {out}")
            try:
                status, data = request_json(f"http://127.0.0.1:{self.port}/health")
                if status == 200 and data.get("engine") == "helm-packd":
                    return
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.05)
        self.fail(f"helm-packd did not become ready: {last}")

    def tearDown(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stdout:
            self.proc.stdout.close()
        self.tmp.cleanup()

    def test_catalog_staleness_is_computed_from_declared_window(self) -> None:
        status, catalog = request_json(f"http://127.0.0.1:{self.port}/catalog")
        self.assertEqual(status, 200)

        # Past render_date + stale_after_days -> honestly stale, though nothing pre-stamped it.
        stale = catalog["stalewin"]["staleness"]
        self.assertEqual(stale["status"], "stale")
        self.assertGreaterEqual(stale["age_days"], 300)
        self.assertIn("stale_at", stale)  # derived deadline is exposed
        self.assertIn("warning", stale)
        self.assertTrue(any(w["code"] == "pack_stale" for w in catalog["stalewin"]["warnings"]))

        # Within the window -> fresh, with an honest age and no warning.
        fresh = catalog["freshwin"]["staleness"]
        self.assertEqual(fresh["status"], "fresh")
        self.assertLessEqual(fresh["age_days"], 60)
        self.assertNotIn("warning", fresh)

        # Explicit stale_at already in the past -> stale.
        self.assertEqual(catalog["staleat"]["staleness"]["status"], "stale")

        # render_date but NO declared window -> fresh (we do not fabricate staleness) + age.
        nowindow = catalog["nowindow"]["staleness"]
        self.assertEqual(nowindow["status"], "fresh")
        self.assertIn("age_days", nowindow)

        # No render_date -> unknown, never a fabricated "fresh"; no age emitted.
        nodate = catalog["nodate"]["staleness"]
        self.assertEqual(nodate["status"], "unknown")
        self.assertNotIn("age_days", nodate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
