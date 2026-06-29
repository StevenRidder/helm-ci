#!/usr/bin/env python3
"""Helm local pack server for BYO offline MBTiles and PMTiles chart packs.

  GET /{name}/{z}/{x}/{y}.{ext}   -> MBTiles tile_data (TMS y is flipped)
  GET /{name}.pmtiles             -> PMTiles archive with HTTP Range support
  HEAD /{name}.pmtiles            -> PMTiles headers for protocol probes
  GET /catalog                    -> JSON of available packs + bounds/zoom/URLs

Offline-first: everything is local and read-only. Bind 0.0.0.0 so an iPad or
phone on the boat LAN can load the same packs through the boat server.

Configuration:
  HELM_MBTILES_DIR=/path/to/local/packs
  HELM_MBTILES_PACKS='{"chart":"my-chart.mbtiles","sat":"my-sat.pmtiles"}'

If HELM_MBTILES_PACKS is omitted, every *.mbtiles and *.pmtiles file in
HELM_MBTILES_DIR is exposed by its filename stem. Keep license-bound commercial
packs local; do not commit them.
"""
from __future__ import annotations

import datetime as _dt
import glob
import gzip
import http.server
import json
import os
import re
import socketserver
import sqlite3
import struct
import sys
import threading
from typing import Optional, Tuple
import urllib.parse

BASE = os.path.abspath(os.path.expanduser(os.environ.get("HELM_MBTILES_DIR", "web/data")))

PMTILE_TYPES = {
    1: ("mvt", "vector"),
    2: ("png", "raster"),
    3: ("jpg", "raster"),
    4: ("webp", "raster"),
    5: ("avif", "raster"),
}

CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "avif": "image/avif",
    "mvt": "application/vnd.mapbox-vector-tile",
    "pbf": "application/vnd.mapbox-vector-tile",
    "pmtiles": "application/vnd.pmtiles",
}


def _pack_map() -> dict[str, str]:
    raw = os.environ.get("HELM_MBTILES_PACKS", "").strip()
    if raw:
        try:
            packs = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"FATAL: HELM_MBTILES_PACKS is not valid JSON: {e}", file=sys.stderr)
            sys.exit(2)
        return {str(name): str(filename) for name, filename in packs.items()}

    packs: dict[str, str] = {}
    for pattern in ("*.mbtiles", "*.pmtiles"):
        for path in sorted(glob.glob(os.path.join(BASE, pattern))):
            name = os.path.splitext(os.path.basename(path))[0]
            packs[name] = os.path.basename(path)
    return packs


def _pack_path(filename: str) -> str:
    expanded = os.path.abspath(os.path.expanduser(filename))
    if os.path.isabs(filename) or filename.startswith("~"):
        return expanded
    return os.path.abspath(os.path.join(BASE, filename))


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bounds_array(bounds):
    if bounds is None:
        return None
    if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
        try:
            return [float(v) for v in bounds]
        except (TypeError, ValueError):
            return None
    if isinstance(bounds, str):
        parts = [p.strip() for p in bounds.split(",")]
        if len(parts) == 4:
            try:
                return [float(p) for p in parts]
            except ValueError:
                return None
    return None


def _bounds_string(bounds) -> Optional[str]:
    arr = _bounds_array(bounds)
    if not arr:
        return None
    return ",".join(f"{v:.7g}" for v in arr)


def _mtime_iso(path: str) -> str:
    ts = os.path.getmtime(path)
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _etag(path: str) -> str:
    st = os.stat(path)
    return f'"{st.st_mtime_ns:x}-{st.st_size:x}"'


def _kind_for(name: str, title: str, fmt: str, pack_type: str) -> str:
    text = f"{name} {title} {fmt}".lower()
    if any(term in text for term in ("sat", "sentinel", "bing", "google", "arcgis", "imagery", "photo")):
        return "satellite"
    if any(term in text for term in ("chart", "navionics", "noaa", "kap", "rnc", "enc")):
        return "chart"
    return "vector" if pack_type == "vector" else "raster"


def _content_type(ext: str) -> str:
    return CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _read_sqlite_metadata(conn: sqlite3.Connection) -> dict[str, str]:
    try:
        return dict(conn.execute("SELECT name, value FROM metadata").fetchall())
    except sqlite3.DatabaseError:
        return {}


def _parse_pmtiles_metadata(path: str) -> dict:
    with open(path, "rb") as f:
        header = f.read(127)
        if len(header) < 127 or header[0:7] != b"PMTiles":
            raise ValueError("not a PMTiles v3 archive")

        version = header[7]
        metadata_offset = struct.unpack_from("<Q", header, 24)[0]
        metadata_length = struct.unpack_from("<Q", header, 32)[0]
        addressed_tiles = struct.unpack_from("<Q", header, 72)[0]
        tile_entries = struct.unpack_from("<Q", header, 80)[0]
        tile_contents = struct.unpack_from("<Q", header, 88)[0]
        internal_compression = header[97]
        tile_compression = header[98]
        tile_type = header[99]
        minzoom = header[100]
        maxzoom = header[101]
        bounds = [
            struct.unpack_from("<i", header, 102)[0] / 1e7,
            struct.unpack_from("<i", header, 106)[0] / 1e7,
            struct.unpack_from("<i", header, 110)[0] / 1e7,
            struct.unpack_from("<i", header, 114)[0] / 1e7,
        ]
        center = [
            struct.unpack_from("<i", header, 119)[0] / 1e7,
            struct.unpack_from("<i", header, 123)[0] / 1e7,
            header[118],
        ]

        metadata = {}
        if metadata_offset and metadata_length:
            f.seek(metadata_offset)
            blob = f.read(metadata_length)
            if internal_compression == 2:
                blob = gzip.decompress(blob)
            elif internal_compression not in (0, 1):
                blob = b"{}"
            try:
                metadata = json.loads(blob.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                metadata = {}

    fmt, pack_type = PMTILE_TYPES.get(tile_type, ("bin", "raster"))
    return {
        "version": version,
        "format": fmt,
        "type": metadata.get("type") or pack_type,
        "minzoom": _safe_int(metadata.get("minzoom"), minzoom),
        "maxzoom": _safe_int(metadata.get("maxzoom"), maxzoom),
        "bounds_array": _bounds_array(metadata.get("bounds")) or bounds,
        "center": metadata.get("center") or center,
        "attribution": metadata.get("attribution"),
        "description": metadata.get("description"),
        "name": metadata.get("name"),
        "tile_compression": tile_compression,
        "addressed_tiles": addressed_tiles,
        "tile_entries": tile_entries,
        "tile_contents": tile_contents,
    }


def _base_record(name: str, path: str, fmt: str, pack_type: str, title: str, metadata: dict) -> dict:
    bounds_arr = _bounds_array(metadata.get("bounds_array") or metadata.get("bounds"))
    rec = {
        "id": name,
        "name": name,
        "title": title or name,
        "format": fmt,
        "extension": "jpg" if fmt == "jpeg" else fmt,
        "type": pack_type,
        "kind": _kind_for(name, title or name, fmt, pack_type),
        "source": "local",
        "size_bytes": os.path.getsize(path),
        "modified": _mtime_iso(path),
        "modified_epoch": int(os.path.getmtime(path)),
        "license": metadata.get("license") or "local-user-owned",
    }
    if bounds_arr:
        rec["bounds_array"] = bounds_arr
        rec["bounds"] = _bounds_string(bounds_arr)
    for key in ("minzoom", "maxzoom", "attribution", "description", "center", "scheme"):
        if metadata.get(key) is not None:
            rec[key] = metadata[key]
    return rec


def _build_pack_records():
    records, conns, locks = {}, {}, {}
    for name, filename in _pack_map().items():
        path = _pack_path(filename)
        if not os.path.exists(path):
            print(f"warning: pack {name!r} not found at {path}", file=sys.stderr)
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext == ".mbtiles":
            try:
                conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
                m = _read_sqlite_metadata(conn)
            except sqlite3.DatabaseError as e:
                print(f"warning: cannot open MBTiles pack {name!r}: {e}", file=sys.stderr)
                continue
            fmt = (m.get("format") or "png").lower()
            if fmt == "jpeg":
                fmt = "jpg"
            pack_type = "vector" if fmt in ("pbf", "mvt") else "raster"
            title = m.get("name") or name
            metadata = {
                "bounds": m.get("bounds"),
                "minzoom": _safe_int(m.get("minzoom"), 0),
                "maxzoom": _safe_int(m.get("maxzoom"), 17),
                "attribution": m.get("attribution"),
                "description": m.get("description"),
                "scheme": m.get("scheme", "tms"),
            }
            rec = _base_record(name, path, fmt, pack_type, title, metadata)
            rec["container"] = "mbtiles"
            rec["_path"] = path
            records[name] = rec
            conns[name] = conn
            locks[name] = threading.Lock()
        elif ext == ".pmtiles":
            try:
                pm = _parse_pmtiles_metadata(path)
            except (OSError, ValueError, struct.error, gzip.BadGzipFile) as e:
                print(f"warning: cannot open PMTiles pack {name!r}: {e}", file=sys.stderr)
                continue
            fmt = pm["format"]
            pack_type = "vector" if pm["type"] == "vector" or fmt == "mvt" else "raster"
            title = pm.get("name") or name
            rec = _base_record(name, path, fmt, pack_type, title, pm)
            rec["container"] = "pmtiles"
            rec["range"] = True
            rec["pmtiles_version"] = pm["version"]
            rec["addressed_tiles"] = pm["addressed_tiles"]
            rec["tile_entries"] = pm["tile_entries"]
            rec["tile_contents"] = pm["tile_contents"]
            rec["_path"] = path
            records[name] = rec
        else:
            print(f"warning: unsupported pack extension for {name!r}: {path}", file=sys.stderr)
    return records, conns, locks


PACKS, CONNS, LOCKS = _build_pack_records()


def _origin(handler: http.server.BaseHTTPRequestHandler) -> str:
    proto = handler.headers.get("X-Forwarded-Proto", "http").split(",")[0].strip() or "http"
    host = handler.headers.get("Host") or f"127.0.0.1:{handler.server.server_port}"
    return f"{proto}://{host}"


def _catalog(origin: str) -> dict:
    catalog = {}
    for name, rec in sorted(PACKS.items()):
        item = {k: v for k, v in rec.items() if not k.startswith("_")}
        quoted = urllib.parse.quote(name, safe="")
        if rec["container"] == "mbtiles":
            item["tile_url"] = f"{origin}/{quoted}/{{z}}/{{x}}/{{y}}.{rec['extension']}"
            item["url"] = item["tile_url"]
        else:
            pmtiles_url = f"{origin}/{quoted}.pmtiles"
            item["pmtiles_url"] = pmtiles_url
            item["protocol_url"] = f"pmtiles://{pmtiles_url}"
            item["url"] = pmtiles_url
        catalog[name] = item
    return catalog


def _parse_range(value: Optional[str], size: int) -> Optional[Tuple[int, int]]:
    if not value:
        return None
    match = re.match(r"^bytes=(\d*)-(\d*)$", value.strip())
    if not match:
        raise ValueError("unsupported range")
    start_s, end_s = match.groups()
    if not start_s and not end_s:
        raise ValueError("empty range")
    if not start_s:
        suffix_len = int(end_s)
        if suffix_len <= 0:
            raise ValueError("empty suffix range")
        start = max(0, size - suffix_len)
        end = size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
    if start >= size or start > end:
        raise ValueError("unsatisfiable range")
    return start, min(end, size - 1)


def _copy_bytes(wfile, path: str, start: int, length: int) -> None:
    remaining = length
    with open(path, "rb") as f:
        f.seek(start)
        while remaining > 0:
            chunk = f.read(min(1024 * 256, remaining))
            if not chunk:
                break
            wfile.write(chunk)
            remaining -= len(chunk)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", "Accept-Ranges, Content-Length, Content-Range, ETag")

    def _empty(self, code: int, *, content_range: Optional[str] = None):
        self.send_response(code)
        self._cors()
        if content_range:
            self.send_header("Content-Range", content_range)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _catalog_response(self):
        body = json.dumps(_catalog(_origin(self)), sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_mbtiles(self, name: str, parts: list[str]):
        if len(parts) != 4 or name not in CONNS:
            self._empty(404)
            return
        try:
            z, x = int(parts[1]), int(parts[2])
            y = int(parts[3].split(".")[0])
        except ValueError:
            self._empty(404)
            return
        tms_y = (1 << z) - 1 - y
        with LOCKS[name]:
            row = CONNS[name].execute(
                "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (z, x, tms_y),
            ).fetchone()
        if not row:
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        fmt = PACKS[name]["extension"]
        self.send_response(200)
        self.send_header("Content-Type", _content_type(fmt))
        self._cors()
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(row[0])))
        self.end_headers()
        self.wfile.write(row[0])

    def _serve_pmtiles(self, name: str, head_only: bool = False):
        if name not in PACKS or PACKS[name]["container"] != "pmtiles":
            self._empty(404)
            return
        path = PACKS[name]["_path"]
        size = os.path.getsize(path)
        try:
            rng = _parse_range(self.headers.get("Range"), size)
        except ValueError:
            self._empty(416, content_range=f"bytes */{size}")
            return
        if rng:
            start, end = rng
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            start, length = 0, size
            self.send_response(200)
        self.send_header("Content-Type", _content_type("pmtiles"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("ETag", _etag(path))
        self._cors()
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if not head_only:
            _copy_bytes(self.wfile, path, start, length)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        path = urllib.parse.urlparse(self.path).path.strip("/")
        if path.endswith(".pmtiles"):
            name = urllib.parse.unquote(path[:-8])
            self._serve_pmtiles(name, head_only=True)
            return
        if path == "catalog":
            body = json.dumps(_catalog(_origin(self)), sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return
        self._empty(404)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.strip("/")
        if path == "catalog":
            self._catalog_response()
            return
        if path.endswith(".pmtiles"):
            name = urllib.parse.unquote(path[:-8])
            self._serve_pmtiles(name)
            return
        parts = [urllib.parse.unquote(p) for p in path.split("/") if p]
        if not parts:
            self._empty(404)
            return
        self._serve_mbtiles(parts[0], parts)


class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8091
    if not PACKS:
        print(f"FATAL: no .mbtiles or .pmtiles packs found under {BASE}", file=sys.stderr)
        print("Set HELM_MBTILES_DIR or HELM_MBTILES_PACKS to point at your local packs.", file=sys.stderr)
        sys.exit(1)
    print(f"local pack server :{port} - packs: {list(PACKS.keys())}")
    for k, v in PACKS.items():
        zoom = f"z{v.get('minzoom', 0)}-{v.get('maxzoom', 17)}"
        print(f"  {k}: {v['title']}  {v['container']}  {zoom}  {v['format']}")
    TS(("0.0.0.0", port), H).serve_forever()
