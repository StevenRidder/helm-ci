#!/usr/bin/env python3
"""Helm mbtiles tile server — serves the user's own chart packs (Navionics / satellite)
straight from .mbtiles to MapLibre as XYZ raster tiles, no conversion.

  GET /{name}/{z}/{x}/{y}.{ext}   ->  tile_data (mbtiles is TMS, so we flip y)
  GET /catalog                    ->  JSON of available packs + bounds/zoom

Offline-first: everything is local SQLite, no network. Bind 0.0.0.0 so the iPad/phone
on the boat LAN can load the same charts. Read-only + immutable so it can't touch the file.
"""
import sqlite3, http.server, socketserver, threading, os, json, sys

BASE = os.path.expanduser("~/Library/CloudStorage/Dropbox/COS/Charts/South Pacific/Fiji")
PACKS = {
    "navionics": "Fiji_TCL2407_Navionics_Z8-16,18.mbtiles",
    "googlesat": "Fiji_TCL2407_GoogleSat_Z8-16,18.mbtiles",
    "bingsat":   "Fiji_TCL2407_BingSat_Z8-16,18.mbtiles",
    "arcgis":    "Fiji_TCL2407_ArcGIS_Z8-16,18.mbtiles",
}
conns, locks, meta = {}, {}, {}
for name, fn in PACKS.items():
    path = os.path.join(BASE, fn)
    if not os.path.exists(path):
        continue
    c = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    conns[name] = c
    locks[name] = threading.Lock()
    m = dict(c.execute("SELECT name, value FROM metadata").fetchall())
    meta[name] = {"format": m.get("format", "png"), "bounds": m.get("bounds"),
                  "minzoom": int(m.get("minzoom", 0)), "maxzoom": int(m.get("maxzoom", 17)),
                  "title": m.get("name", name)}

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
    def do_GET(self):
        p = self.path.split("?")[0].strip("/")
        if p == "catalog":
            body = json.dumps(meta).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self._cors(); self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body); return
        parts = p.split("/")
        try:
            name, z, x = parts[0], int(parts[1]), int(parts[2])
            y = int(parts[3].split(".")[0])
        except (IndexError, ValueError):
            self.send_response(404); self.end_headers(); return
        if name not in conns:
            self.send_response(404); self.end_headers(); return
        tms_y = (1 << z) - 1 - y                      # mbtiles stores TMS (origin bottom-left)
        with locks[name]:
            row = conns[name].execute(
                "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (z, x, tms_y)).fetchone()
        if row:
            ct = "image/jpeg" if meta[name]["format"] in ("jpg", "jpeg") else "image/png"
            self.send_response(200); self.send_header("Content-Type", ct)
            self._cors(); self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(row[0]))); self.end_headers()
            self.wfile.write(row[0])
        else:
            self.send_response(204); self._cors(); self.end_headers()   # no tile here — transparent gap

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8091
    if not conns:
        print(f"FATAL: no mbtiles found under {BASE}", file=sys.stderr); sys.exit(1)
    print(f"mbtiles server :{port} — packs: {list(conns.keys())}")
    for k, v in meta.items():
        print(f"  {k}: {v['title']}  z{v['minzoom']}-{v['maxzoom']}  {v['format']}")
    TS(("0.0.0.0", port), H).serve_forever()
