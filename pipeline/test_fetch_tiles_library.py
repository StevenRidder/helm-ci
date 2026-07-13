#!/usr/bin/env python3
"""INTAKE-8: the download drawer's fetch_tiles.py deposits into the chart library.

Proves the two intake doors converged: a lasso-download lands in the DEFAULT
REGISTERED chart root (next to hand-placed packs) with a provenance sidecar
(source label, license, bbox, download date, render_date), and the recursive
discovery surfaces it in a RUNNING pack server's /catalog with no rescan step.
"""

import base64
import http.server
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / "pipeline" / "fetch_tiles.py"
SERVER = ROOT / "pipeline" / "mbtiles_server.py"
sys.path.insert(0, str(ROOT / "pipeline"))
import chart_intake  # noqa: E402

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
BBOX = "178.0,-18.0,178.5,-17.5"


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _TileHandler(http.server.BaseHTTPRequestHandler):
    status = 200

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.status != 200:
            self.send_response(self.status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(PNG_1X1)))
        self.end_headers()
        self.wfile.write(PNG_1X1)


def start_tile_stub(status=200):
    handler = type("Handler", (_TileHandler,), {"status": status})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/t/{{z}}/{{x}}/{{y}}.png"


def write_hand_placed_mbtiles(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
    conn.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [("name", "Hand Placed Chart"), ("format", "png"), ("bounds", BBOX), ("minzoom", "0"), ("maxzoom", "1")],
    )
    conn.execute("INSERT INTO tiles VALUES (0, 0, 0, ?)", (PNG_1X1,))
    conn.commit()
    conn.close()


def request_json(url):
    with urllib.request.urlopen(url, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class FetchTilesLibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.config_dir = self.home / "config"
        self.charts_root = self.home / "charts"
        self.env = os.environ.copy()
        self.env["HELM_CONFIG"] = str(self.config_dir)
        self.env["HELM_DEFAULT_CHART_ROOT"] = str(self.charts_root)
        self.env.pop("HELM_CHART_ROOTS_FILE", None)
        self.env.pop("HELM_CHART_ROOTS", None)
        self.env.pop("HELM_MBTILES_PACKS", None)
        self.stubs = []
        self.procs = []

    def tearDown(self):
        for stub in self.stubs:
            stub.shutdown()
            stub.server_close()
        for proc in self.procs:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            if proc.stdout:
                proc.stdout.close()
        self.tmp.cleanup()

    def _tile_stub(self, status=200):
        server, template = start_tile_stub(status)
        self.stubs.append(server)
        return template

    def _run_fetch(self, template, extra=None):
        cmd = [
            sys.executable, str(FETCH),
            "--source", template,
            "--bbox", BBOX,
            "--minzoom", "1", "--maxzoom", "2",
            "--name", "Fiji Test Download",
            "--source-label", "NOAA ENC charts",
            "--license", "Public domain (NOAA)",
            "--filename", "fiji-test-download.mbtiles",
            "--delay", "0",
        ] + (extra or [])
        return subprocess.run(cmd, env=self.env, capture_output=True, text=True, timeout=60)

    def _start_pack_server(self, roots_file):
        port = free_port()
        env = dict(self.env)
        env["HELM_CHART_ROOTS_FILE"] = str(roots_file)
        proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(port)],
            cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.procs.append(proc)
        deadline = time.time() + 5
        while time.time() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                self.fail(f"pack server exited early with {proc.returncode}: {out}")
            try:
                status, _ = request_json(f"http://127.0.0.1:{port}/catalog")
                if status == 200:
                    return port
            except OSError:
                time.sleep(0.05)
        self.fail("pack server did not become ready")

    def test_download_deposits_into_registered_root_with_sidecar(self):
        template = self._tile_stub()
        result = self._run_fetch(template)
        self.assertEqual(result.returncode, 0, result.stderr)

        pack = self.charts_root / "DOWNLOADS" / "fiji-test-download.mbtiles"
        sidecar = self.charts_root / "DOWNLOADS" / "fiji-test-download.metadata.json"
        self.assertTrue(pack.is_file(), "pack must land in the default registered root")
        self.assertTrue(sidecar.is_file(), "sidecar must land next to the pack")
        self.assertIn("library: deposited in registered chart root", result.stdout)

        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(meta["source"], "NOAA ENC charts")
        self.assertEqual(meta["license"], "Public domain (NOAA)")
        self.assertEqual(meta["bounds"], BBOX)
        self.assertEqual(meta["coverage_status"], "complete")
        for key in ("source_downloaded", "render_date"):
            self.assertRegex(meta[key], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

        # the root the pack landed in is the REGISTERED default root
        roots_file = self.config_dir / "chart-roots.json"
        registry = json.loads(roots_file.read_text(encoding="utf-8"))
        self.assertEqual(registry["schema"], "helm.chart_intake.roots.v1")
        default = [r for r in registry["roots"] if r.get("default")][0]
        self.assertEqual(Path(default["path"]), self.charts_root.resolve())

        # the INTAKE-2 chart index sees it in place, with the sidecar metadata honored
        index, _ = chart_intake.rescan(roots_file, self.config_dir / "chart-index.json", self.charts_root)
        rows = {c["relative_path"]: c for c in index["charts"]}
        row = rows["DOWNLOADS/fiji-test-download.mbtiles"]
        self.assertEqual(row["validation"]["status"], "valid")
        self.assertEqual(row["group"], "DOWNLOADS")
        self.assertEqual(row["metadata"]["license"], "Public domain (NOAA)")
        self.assertEqual(row["metadata"]["source"], "NOAA ENC charts")

    def test_lasso_download_appears_in_running_catalog_without_rescan(self):
        # a customer library already exists: registry + one hand-placed pack
        roots_file = self.config_dir / "chart-roots.json"
        chart_intake.ensure_registry(roots_file, self.charts_root)
        fiji = self.charts_root / "FIJI"
        fiji.mkdir(parents=True, exist_ok=True)
        write_hand_placed_mbtiles(fiji / "hand-placed.mbtiles")
        port = self._start_pack_server(roots_file)

        status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
        self.assertEqual(status, 200)
        self.assertIn("hand-placed", catalog)
        self.assertNotIn("fiji-test-download", catalog)

        template = self._tile_stub()
        result = self._run_fetch(template)
        self.assertEqual(result.returncode, 0, result.stderr)

        # no POST /rescan, no restart: the next catalog request discovers the download
        status, catalog = request_json(f"http://127.0.0.1:{port}/catalog")
        self.assertEqual(status, 200)
        self.assertIn("fiji-test-download", catalog, "download must appear with no extra step")
        self.assertIn("hand-placed", catalog, "downloaded and hand-placed packs share one tree")

        rec = catalog["fiji-test-download"]
        self.assertEqual(rec["title"], "Fiji Test Download")
        self.assertEqual(rec["license"], "Public domain (NOAA)")
        self.assertEqual(rec["source_info"]["label"], "NOAA ENC charts")
        self.assertIn("downloaded", rec["source_info"])
        self.assertEqual(rec["staleness"]["status"], "fresh")
        self.assertEqual(rec["coverage"]["status"], "complete")
        self.assertTrue(rec["tile_url"].endswith("/fiji-test-download/{z}/{x}/{y}.png"))
        self.assertNotIn(self.tmp.name, json.dumps(catalog), "catalog must not leak private paths")

        # the advertised tile URL actually serves the downloaded bytes (toggleable layer)
        tile_url = rec["tile_url"].replace("{z}", "1").replace("{x}", "1").replace("{y}", "1")
        with urllib.request.urlopen(tile_url, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), PNG_1X1)

    def test_zero_tile_download_fails_loud_and_deposits_nothing(self):
        template = self._tile_stub(status=404)
        result = self._run_fetch(template)
        self.assertEqual(result.returncode, 3)
        self.assertIn("no_tiles_fetched", result.stderr)
        downloads = self.charts_root / "DOWNLOADS"
        leftovers = list(downloads.glob("*")) if downloads.is_dir() else []
        self.assertEqual(leftovers, [], "a failed download must not deposit into the library")

    def test_explicit_out_override_keeps_sidecar_and_skips_library(self):
        template = self._tile_stub()
        out = self.home / "elsewhere" / "explicit.mbtiles"
        out.parent.mkdir(parents=True)
        result = self._run_fetch(template, extra=["--out", str(out)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out.is_file())
        self.assertTrue((self.home / "elsewhere" / "explicit.metadata.json").is_file())
        self.assertNotIn("library: deposited", result.stdout)
        self.assertFalse((self.charts_root / "DOWNLOADS").exists())

    def test_filename_with_directories_is_rejected(self):
        template = self._tile_stub()
        result = self._run_fetch(template, extra=["--filename", "../escape.mbtiles"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("--filename must be a bare filename", result.stderr)


if __name__ == "__main__":
    unittest.main()
