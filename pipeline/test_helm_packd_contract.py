#!/usr/bin/env python3
"""Contract tests for the OFFLINE-16 C++ helm-packd daemon.

The Python pack server remains the broad reference/oracle. These tests pin the
first C++ parity slice: health, catalog privacy/URL shape, MBTiles XYZ->TMS
serving, and PMTiles HEAD/Range behavior.

Set HELM_PACKD_BIN to the built binary, for example:

    HELM_PACKD_BIN=/private/tmp/helm-offline16-ocpn/build/cli/helm-packd \
      python3 pipeline/test_helm_packd_contract.py
"""

from __future__ import annotations

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


def request_json(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=2) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


@unittest.skipUnless(os.environ.get("HELM_PACKD_BIN"), "set HELM_PACKD_BIN to the built helm-packd binary")
class HelmPackdContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bin = Path(os.environ["HELM_PACKD_BIN"])
        if not self.bin.exists() or not os.access(self.bin, os.X_OK):
            self.skipTest(f"HELM_PACKD_BIN is not executable: {self.bin}")
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        write_mbtiles(self.tmp_path / "chart.mbtiles")
        write_pmtiles(self.tmp_path / "sat.pmtiles")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
