#!/usr/bin/env python3
"""Smoke test for S-52 region pack baking."""

import gzip
import http.server
import json
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAKER = ROOT / "pipeline" / "bake_s52_region_pack.py"


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def read_pmtiles_metadata(path: Path):
    with path.open("rb") as f:
        header = f.read(127)
        if header[0:7] != b"PMTiles":
            raise AssertionError("not a PMTiles archive")
        meta_offset = struct.unpack_from("<Q", header, 24)[0]
        meta_length = struct.unpack_from("<Q", header, 32)[0]
        compression = header[97]
        f.seek(meta_offset)
        blob = f.read(meta_length)
    if compression == 2:
        blob = gzip.decompress(blob)
    return json.loads(blob.decode("utf-8"))


class TileHandler(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *_):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        TileHandler.seen.append(parsed)
        if parsed.path != "/chart/0/0/0.png":
            self.send_response(404)
            self.end_headers()
            return
        query = dict(urllib.parse.parse_qsl(parsed.query))
        if query.get("p") != "night" or query.get("cat") != "std":
            self.send_response(400)
            self.end_headers()
            return
        body = b"\x89PNG\r\n\x1a\ns52-fixture"
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class S52RegionPackTest(unittest.TestCase):
    def test_bakes_pmtiles_with_s52_stamp_metadata(self):
        TileHandler.seen = []
        port = free_port()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), TileHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "test-s52.pmtiles"
                cmd = [
                    sys.executable,
                    str(BAKER),
                    "--source",
                    f"http://127.0.0.1:{port}/chart/{{z}}/{{x}}/{{y}}.png",
                    "--bbox=-1,-1,1,1",
                    "--minzoom",
                    "0",
                    "--maxzoom",
                    "0",
                    "--out",
                    str(out),
                    "--name",
                    "Fixture S-52",
                    "--palette",
                    "night",
                    "--display-category",
                    "std",
                    "--edition",
                    "fixture-edition",
                    "--chart-epoch",
                    "fixture-epoch",
                    "--render-date",
                    "2026-06-29T00:00:00Z",
                ]
                run = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue(out.exists())
                meta = read_pmtiles_metadata(out)
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(len(TileHandler.seen), 1)
        self.assertEqual(meta["name"], "Fixture S-52")
        self.assertEqual(meta["helm_pack_schema"], "helm.offline.region.v1")
        self.assertEqual(meta["pack_role"], "s52-chart")
        self.assertEqual(meta["renderer"], "s52")
        self.assertEqual(meta["palette"], "night")
        self.assertEqual(meta["display_category"], "std")
        self.assertEqual(meta["chart_edition"], "fixture-edition")
        self.assertEqual(meta["chart_epoch"], "fixture-epoch")
        self.assertEqual(meta["render_date"], "2026-06-29T00:00:00Z")
        self.assertEqual(meta["z_range"], "0-0")
        self.assertEqual(meta["tile_count"], 1)
        self.assertEqual(meta["tile_count_expected"], 1)
        self.assertEqual(meta["bounds"], [-1.0, -1.0, 1.0, 1.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
