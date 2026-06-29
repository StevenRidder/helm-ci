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
            ("helm_pack_schema", "helm.offline.region.v1"),
            ("pack_role", "s52-chart"),
            ("renderer", "s52"),
            ("palette", "day"),
            ("display_category", "std"),
            ("chart_edition", "fixture-edition-1"),
            ("render_date", "2026-06-29T00:00:00Z"),
        ],
    )
    conn.execute("INSERT INTO tiles VALUES (0, 0, 0, ?)", (b"\x89PNG\r\n\x1a\nfixture",))
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
                "helm_pack_schema": "helm.offline.region.v1",
                "pack_role": "s52-chart",
                "renderer": "s52",
                "palette": "night",
                "display_category": "std",
                "chart_edition": "fixture-edition-2",
                "render_date": "2026-06-29T00:00:00Z",
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


class PackServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        write_mbtiles(self.tmp_path / "chart.mbtiles")
        write_pmtiles(self.tmp_path / "sat.pmtiles")
        self.port = free_port()
        env = os.environ.copy()
        env["HELM_MBTILES_DIR"] = self.tmp.name
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
        self.assertEqual(catalog["sat"]["container"], "pmtiles")
        self.assertTrue(catalog["sat"]["range"])
        self.assertEqual(catalog["sat"]["renderer"], "s52")
        self.assertEqual(catalog["sat"]["palette"], "night")
        self.assertEqual(catalog["sat"]["chart_edition"], "fixture-edition-2")
        self.assertEqual(catalog["sat"]["pmtiles_url"], f"http://127.0.0.1:{self.port}/sat.pmtiles")
        self.assertEqual(catalog["sat"]["protocol_url"], f"pmtiles://http://127.0.0.1:{self.port}/sat.pmtiles")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
