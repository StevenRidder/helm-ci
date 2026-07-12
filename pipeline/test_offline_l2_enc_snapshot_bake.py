#!/usr/bin/env python3
"""OFFLINE-L-2: prove a real baked ENC snapshot satisfies the sat-first profile.

pipeline/bake_s52_region_pack.py (OFFLINE-6) already bakes live S-52 chart tiles
into a stamped PMTiles pack, and pipeline/region_bundle_sat_first.py (OFFLINE-L-1)
already validates bundle manifests against the sat-first profile — but only against
synthetic fixtures (test_region_bundle.sample_catalog()). This test closes the loop:
bake a real ENC snapshot PMTiles pack, mount it next to a satellite basemap pack
through the same catalog builder mbtiles_server/helm-packd use, assemble a region
bundle from that real catalog, and assert the result is a valid sat-first bundle
where the chart snapshot is an optional non-primary overlay.
"""
from __future__ import annotations

import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "pipeline"
BAKER = PIPELINE / "bake_s52_region_pack.py"
sys.path.insert(0, str(PIPELINE))


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


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
        if query.get("p") not in {"day", "dusk", "night"} or query.get("cat") != "std":
            self.send_response(400)
            self.end_headers()
            return
        body = b"\x89PNG\r\n\x1a\noffline-l2-fixture"
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _write_synthetic_sat_pmtiles(out: Path) -> None:
    """Build a minimal satellite basemap PMTiles fixture (no live source needed)."""
    from bake_s52_region_pack import write_mbtiles
    import make_pmtiles

    tile_blob = b"\xff\xd8\xff\xe0offline-l2-sat-fixture"
    rows = [(0, 0, 0, tile_blob)]
    metadata = {
        "name": "OFFLINE-L-2 fixture satellite",
        "format": "jpg",
        "kind": "satellite",
        "source": "fixture",
        "license": "CC-BY-4.0",
        "bounds": "-1,-1,1,1",
        "minzoom": 0,
        "maxzoom": 0,
    }
    with tempfile.NamedTemporaryFile(prefix="offline-l2-sat-", suffix=".mbtiles", delete=False) as tmp:
        mbtiles_path = Path(tmp.name)
    try:
        write_mbtiles(mbtiles_path, rows, metadata)
        make_pmtiles.main(str(mbtiles_path), str(out), bbox=(-1.0, -1.0, 1.0, 1.0))
    finally:
        mbtiles_path.unlink(missing_ok=True)


class OfflineL2EncSnapshotBakeTest(unittest.TestCase):
    def test_real_baked_enc_snapshot_joins_sat_first_bundle_as_optional_chart(self):
        TileHandler.seen = []
        port = free_port()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), TileHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        old_dir = os.environ.get("HELM_MBTILES_DIR")
        old_packs = os.environ.get("HELM_MBTILES_PACKS")
        try:
            with tempfile.TemporaryDirectory() as td:
                pack_dir = Path(td)
                chart_out = pack_dir / "offlinel2-chart.pmtiles"
                sat_out = pack_dir / "offlinel2-sat.pmtiles"

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
                    str(chart_out),
                    "--name",
                    "OFFLINE-L-2 fixture ENC snapshot",
                    "--palette",
                    "day",
                    "--display-category",
                    "std",
                    "--edition",
                    "offline-l2-fixture-edition",
                    "--render-date",
                    "2026-07-01T00:00:00Z",
                ]
                run = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertTrue(chart_out.exists(), "ENC snapshot bake must produce a PMTiles file")

                _write_synthetic_sat_pmtiles(sat_out)
                self.assertTrue(sat_out.exists())

                self.assertEqual(len(TileHandler.seen), 1, "the baker must fetch exactly the one requested tile")

                os.environ.pop("HELM_MBTILES_PACKS", None)
                os.environ["HELM_MBTILES_DIR"] = str(pack_dir)

                sys.modules.pop("mbtiles_server", None)
                import mbtiles_server  # noqa: E402  (imported after env is set so it scans pack_dir)

                catalog = mbtiles_server._catalog("http://127.0.0.1:9999")
                self.assertIn("offlinel2-chart", catalog)
                self.assertIn("offlinel2-sat", catalog)
                self.assertEqual(catalog["offlinel2-chart"]["renderer"], "s52")
                self.assertEqual(catalog["offlinel2-chart"]["container"], "pmtiles")
                self.assertEqual(catalog["offlinel2-sat"]["kind"], "satellite")
                self.assertEqual(catalog["offlinel2-sat"]["type"], "raster")

                from region_bundle import build_region_bundle
                from region_bundle_sat_first import (
                    annotate_sat_first_bundle,
                    validate_sat_first_bundle,
                )

                bundle = build_region_bundle(
                    catalog,
                    {
                        "packs": ["offlinel2-sat,offlinel2-chart"],
                        "bbox": ["-1,-1,1,1"],
                        "minzoom": ["0"],
                        "maxzoom": ["0"],
                        "bundle_id": ["offline-l2-fixture"],
                        "title": ["OFFLINE-L-2 real-bake sat-first proof"],
                    },
                )
                bundle = annotate_sat_first_bundle(bundle)
                result = validate_sat_first_bundle(bundle, require_profile=True)
        finally:
            server.shutdown()
            server.server_close()
            if old_dir is None:
                os.environ.pop("HELM_MBTILES_DIR", None)
            else:
                os.environ["HELM_MBTILES_DIR"] = old_dir
            if old_packs is None:
                os.environ.pop("HELM_MBTILES_PACKS", None)
            else:
                os.environ["HELM_MBTILES_PACKS"] = old_packs
            sys.modules.pop("mbtiles_server", None)

        self.assertTrue(result["valid"])
        self.assertEqual(result["basemap_count"], 1)
        self.assertEqual(result["primary_basemap_id"], "pack:offlinel2-sat")
        self.assertEqual(result["chart_count"], 1)
        self.assertEqual(result["warnings"], [])

        chart_component = next(
            c for c in bundle["components"] if c.get("role") == "chart"
        )
        self.assertEqual(chart_component["renderer"], "s52")
        self.assertIsNot(chart_component.get("primary"), True)
        self.assertEqual(chart_component["pack_id"], "offlinel2-chart")


if __name__ == "__main__":
    unittest.main(verbosity=2)
