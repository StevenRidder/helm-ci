#!/usr/bin/env python3
"""Register customer chart folders and index recognized charts in place.

This is the control/pipeline half of ``helm.chart_intake.register.v1``.  It owns
the durable root registry and a privacy-safe, deterministic index artifact.  It
does not serve chart bytes: helm-server, helm-packd, and the user-layer loader
remain the type-specific consumers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Iterable


ROOTS_SCHEMA = "helm.chart_intake.roots.v1"
INDEX_SCHEMA = "helm.chart_intake.index.v1"
INDEXER_VERSION = 2
RECOGNIZED = {".mbtiles": "tile_pack", ".pmtiles": "tile_pack", ".000": "enc", ".geojson": "overlay"}
CHART_CLASSES = [
    {"chart_type": "tile_pack", "extensions": [".mbtiles", ".pmtiles"], "consumer": "helm-packd"},
    {"chart_type": "enc", "extensions": [".000"], "consumer": "helm-server"},
    {"chart_type": "overlay", "extensions": [".geojson"], "consumer": "layer-manifest"},
]

# INTAKE-7 — ENC-4 depth extraction wired into the index flow. Same layer set, GDAL
# options, and provenance schema as pipeline/extract_depth.sh and
# scripts/extract-enc-depth-pyogrio.py; per-cell output under the served user-data root.
DEPTH_PROVENANCE_SCHEMA = "helm.depth_provenance.v1"
DEPTH_DIR = "enc-depth"
DEPTH_S57_LAYERS = {"depare": "DEPARE", "depcnt": "DEPCNT", "soundg": "SOUNDG"}
DEPTH_TITLES = {"depare": "Depth areas", "depcnt": "Depth contours", "soundg": "Soundings"}
DEPTH_KINDS = {"depare": "polygons", "depcnt": "lines", "soundg": "points"}
OGR_S57_OPTIONS = "SPLIT_MULTIPOINT=ON,ADD_SOUNDG_DEPTH=ON,RETURN_PRIMITIVES=OFF,RETURN_LINKAGES=OFF,LNAM_REFS=OFF"


class IntakeError(ValueError):
    """A named, user-actionable chart-intake failure."""


class DepthExtractError(RuntimeError):
    """A named per-cell depth-extraction failure (fails loud in the catalog)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_paths() -> tuple[Path, Path, Path]:
    config_dir = Path(os.environ.get("HELM_CONFIG", "~/.helm/config")).expanduser()
    roots_file = Path(os.environ.get("HELM_CHART_ROOTS_FILE", config_dir / "chart-roots.json")).expanduser()
    index_file = Path(os.environ.get("HELM_CHART_INDEX_FILE", config_dir / "chart-index.json")).expanduser()
    default_root = Path(os.environ.get("HELM_DEFAULT_CHART_ROOT", "~/.helm/charts")).expanduser()
    return roots_file, index_file, default_root


def _atomic_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IntakeError(f"missing registry: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeError(f"cannot read registry {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise IntakeError(f"registry {path.name} must be a JSON object")
    return value


def _secure_private_file(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError as exc:
        raise IntakeError(f"cannot secure private file {path.name}: {exc}") from exc


def _root_id(path: Path) -> str:
    return "root-" + hashlib.sha256(os.fsencode(str(path))).hexdigest()[:16]


def _canonical(path: Path, *, must_exist: bool) -> Path:
    path = path.expanduser()
    try:
        return path.resolve(strict=must_exist)
    except OSError as exc:
        raise IntakeError(f"chart root is unavailable: {path}") from exc


def _validate_registry(registry: dict[str, Any], filename: str) -> None:
    if registry.get("schema") != ROOTS_SCHEMA or not isinstance(registry.get("roots"), list):
        raise IntakeError(f"registry {filename} is not {ROOTS_SCHEMA}")
    ids: set[str] = set()
    paths: set[str] = set()
    for root in registry["roots"]:
        if not isinstance(root, dict) or not all(isinstance(root.get(key), str) and root[key] for key in ("id", "label", "path")):
            raise IntakeError(f"registry {filename} has a malformed root record")
        if not root["id"].startswith("root-") or root["id"] in ids:
            raise IntakeError(f"registry {filename} has a duplicate or invalid root id")
        if not Path(root["path"]).is_absolute() or root["path"] in paths:
            raise IntakeError(f"registry {filename} has a duplicate or non-absolute root path")
        if _looks_private_path(root["label"]):
            raise IntakeError(f"registry {filename} has a path-shaped public label")
        ids.add(root["id"])
        paths.add(root["path"])


def ensure_registry(roots_file: Path, default_root: Path) -> dict[str, Any]:
    if roots_file.exists():
        registry = _read_json(roots_file)
        _validate_registry(registry, roots_file.name)
        _secure_private_file(roots_file)
        return registry

    root = _canonical(default_root, must_exist=False)
    root.mkdir(parents=True, exist_ok=True)
    now = _utc_now()
    registry = {
        "schema": ROOTS_SCHEMA,
        "updated_at": now,
        "roots": [{"id": _root_id(root), "label": "Default charts", "path": str(root), "default": True, "added_at": now}],
    }
    _atomic_json(roots_file, registry)
    return registry


def load_registry_readonly(roots_file: Path, default_root: Path) -> dict[str, Any]:
    """Read the registry without creating or mutating anything on disk.

    When no registry file exists yet the default root is synthesized in memory
    only — first-run GET surfaces must not flip a daemon onto a file registry
    (or mkdir roots) as a side effect of being looked at.
    """
    if roots_file.exists():
        registry = _read_json(roots_file)
        _validate_registry(registry, roots_file.name)
        return registry
    root = _canonical(default_root, must_exist=False)
    now = _utc_now()
    return {
        "schema": ROOTS_SCHEMA,
        "updated_at": now,
        "roots": [{"id": _root_id(root), "label": "Default charts", "path": str(root), "default": True, "added_at": now}],
    }


def register_root(roots_file: Path, default_root: Path, path: Path, label: str | None = None) -> tuple[dict[str, Any], bool]:
    registry = ensure_registry(roots_file, default_root)
    root_path = _canonical(path, must_exist=True)
    if not root_path.is_dir():
        raise IntakeError(f"chart root is not a directory: {path}")
    chosen_label = (label if label is not None else (root_path.name or "Charts")).strip()
    if not chosen_label:
        raise IntakeError("chart root label cannot be empty")
    if _looks_private_path(chosen_label):
        raise IntakeError("chart root label must not contain a private filesystem path")
    for root in registry["roots"]:
        if _canonical(Path(root["path"]), must_exist=False) == root_path:
            if label is None:
                return root, False
            changed = root.get("label") != chosen_label
            if changed:
                root["label"] = chosen_label
                registry["updated_at"] = _utc_now()
                _atomic_json(roots_file, registry)
            return root, changed
    now = _utc_now()
    root = {"id": _root_id(root_path), "label": chosen_label, "path": str(root_path), "default": False, "added_at": now}
    registry["roots"].append(root)
    registry["roots"].sort(key=lambda item: (not bool(item.get("default")), str(item.get("label", "")).lower(), item["id"]))
    registry["updated_at"] = now
    _atomic_json(roots_file, registry)
    return root, True


def unregister_root(roots_file: Path, default_root: Path, root_or_path: str) -> dict[str, Any]:
    registry = ensure_registry(roots_file, default_root)
    path_match = _canonical(Path(root_or_path), must_exist=False) if not root_or_path.startswith("root-") else None
    for index, root in enumerate(registry["roots"]):
        matches = root["id"] == root_or_path
        if path_match is not None:
            matches = matches or _canonical(Path(root["path"]), must_exist=False) == path_match
        if not matches:
            continue
        if root.get("default"):
            raise IntakeError("the default chart root cannot be unregistered")
        removed = registry["roots"].pop(index)
        registry["updated_at"] = _utc_now()
        _atomic_json(roots_file, registry)
        return removed
    raise IntakeError(f"unknown chart root: {root_or_path}")


def public_roots(registry: dict[str, Any], show_paths: bool = False) -> dict[str, Any]:
    roots = []
    for root in registry["roots"]:
        item = {key: root[key] for key in ("id", "label", "default", "added_at") if key in root}
        item["status"] = "available" if Path(root["path"]).is_dir() else "unavailable"
        if show_paths:
            item["path"] = root["path"]
        roots.append(item)
    return {"schema": ROOTS_SCHEMA, "roots": roots}


def _valid_bbox(value: Any) -> list[float] | None:
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        bbox = [float(part) for part in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(part) for part in bbox):
        return None
    if not (-180 <= bbox[0] <= 180 and -90 <= bbox[1] <= 90 and -180 <= bbox[2] <= 180 and -90 <= bbox[3] <= 90):
        return None
    if bbox[1] > bbox[3]:
        return None
    return bbox


def _looks_private_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    lowered = text.lower()
    private_fragments = ("file://", "/users/", "/home/", "/private/", "/volumes/", "/tmp/", "\\users\\")
    return (
        text.startswith(("/", "~/"))
        or any(fragment in lowered for fragment in private_fragments)
        or (len(text) > 2 and text[1:3] in (":\\", ":/"))
    )


def _sidecar(path: Path) -> tuple[dict[str, Any], list[dict[str, str]], Path | None]:
    candidate = path.with_suffix(".metadata.json")
    if not candidate.is_file():
        return {}, [], None
    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, [{"code": "invalid_sidecar", "message": "metadata sidecar is not valid JSON"}], candidate
    if not isinstance(raw, dict):
        return {}, [{"code": "invalid_sidecar", "message": "metadata sidecar must be a JSON object"}], candidate

    public: dict[str, Any] = {}
    warnings: list[dict[str, str]] = []
    for key in ("id", "label", "title", "license", "attribution"):
        value = raw.get(key)
        if isinstance(value, (str, int, float, bool)) and not _looks_private_path(value):
            public[key] = value
        elif value is not None and _looks_private_path(value):
            warnings.append({"code": "private_sidecar_value_omitted", "message": f"private path omitted from sidecar field {key}"})
    source = raw.get("source")
    if isinstance(source, str) and not _looks_private_path(source):
        public["source"] = source
    elif isinstance(source, dict):
        safe_source = {
            key: value for key, value in source.items()
            if key in {"id", "label", "license"} and isinstance(value, (str, int, float, bool)) and not _looks_private_path(value)
        }
        if safe_source:
            public["source"] = safe_source
    elif source is not None and _looks_private_path(source):
        warnings.append({"code": "private_sidecar_value_omitted", "message": "private path omitted from sidecar field source"})
    bbox = _valid_bbox(raw.get("bounds") or raw.get("bbox"))
    if bbox:
        public["bbox"] = bbox
    public["sidecar_name"] = candidate.name
    return public, warnings, candidate


def _mercator_lat(y: int, zoom: int) -> float:
    n = 2.0**zoom
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))


def _mbtiles_bbox(conn: sqlite3.Connection, metadata: dict[str, str]) -> list[float] | None:
    explicit = _valid_bbox(metadata.get("bounds"))
    if explicit:
        return explicit
    row = conn.execute(
        "SELECT zoom_level, MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row) "
        "FROM tiles GROUP BY zoom_level ORDER BY zoom_level DESC LIMIT 1"
    ).fetchone()
    if not row or any(value is None for value in row):
        return None
    zoom, min_x, max_x, min_tms_y, max_tms_y = map(int, row)
    n = 2**zoom
    west = min_x / n * 360.0 - 180.0
    east = (max_x + 1) / n * 360.0 - 180.0
    min_xyz_y = n - 1 - max_tms_y
    max_xyz_y = n - 1 - min_tms_y
    return [west, _mercator_lat(max_xyz_y + 1, zoom), east, _mercator_lat(min_xyz_y, zoom)]


def _validation(status: str, code: str, message: str, bbox: list[float] | None = None) -> tuple[list[float] | None, dict[str, str]]:
    return bbox, {"status": status, "code": code, "message": message}


def _read_prefix(path: Path, length: int) -> bytes:
    # Chart packs are routinely multi-gigabyte. Never materialize the archive just
    # to inspect its fixed-size header.
    with path.open("rb") as stream:
        return stream.read(length)


def _validate_mbtiles(path: Path, sidecar_bbox: list[float] | None) -> tuple[list[float] | None, dict[str, str]]:
    try:
        header = _read_prefix(path, 16)
    except OSError:
        return _validation("error", "invalid_container", "MBTiles container could not be opened")
    if header.startswith(b"PMTiles"):
        return _validation("error", "contents_extension_mismatch", "file declares .mbtiles but contains PMTiles")
    if header != b"SQLite format 3\x00":
        return _validation("error", "contents_extension_mismatch", "file declares .mbtiles but is not SQLite")
    try:
        uri = "file:" + urllib.parse.quote(str(path), safe="/") + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            if "tiles" not in tables:
                return _validation("error", "invalid_schema", "MBTiles container has no tiles table")
            metadata = dict(conn.execute("SELECT name, value FROM metadata")) if "metadata" in tables else {}
            bbox = _mbtiles_bbox(conn, metadata) or sidecar_bbox
    except (OSError, sqlite3.DatabaseError):
        return _validation("error", "invalid_container", "MBTiles container could not be opened")
    if not bbox:
        return _validation("error", "bbox_unavailable", "MBTiles coverage bbox could not be derived")
    return _validation("valid", "ok", "MBTiles container and coverage are valid", bbox)


def _validate_pmtiles(path: Path, sidecar_bbox: list[float] | None) -> tuple[list[float] | None, dict[str, str]]:
    try:
        header = _read_prefix(path, 127)
    except OSError:
        return _validation("error", "invalid_container", "PMTiles container could not be opened")
    if header.startswith(b"SQLite format 3\x00"):
        return _validation("error", "contents_extension_mismatch", "file declares .pmtiles but contains SQLite")
    if len(header) < 127 or header[:7] != b"PMTiles":
        return _validation("error", "contents_extension_mismatch", "file declares .pmtiles but has no PMTiles header")
    if header[7] != 3:
        return _validation("error", "unsupported_container_version", f"PMTiles version {header[7]} is unsupported")
    bbox = [struct.unpack_from("<i", header, offset)[0] / 1e7 for offset in (102, 106, 110, 114)]
    bbox = _valid_bbox(bbox) or sidecar_bbox
    if not bbox:
        return _validation("error", "bbox_unavailable", "PMTiles coverage bbox could not be derived")
    return _validation("valid", "ok", "PMTiles v3 container and coverage are valid", bbox)


def _coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(part, (int, float)) and not isinstance(part, bool) for part in value[:2]):
            yield float(value[0]), float(value[1])
        else:
            for child in value:
                yield from _coordinate_pairs(child)


def _geojson_bbox(value: dict[str, Any]) -> list[float] | None:
    explicit = _valid_bbox(value.get("bbox"))
    if explicit:
        return explicit
    geometries: list[Any] = []
    kind = value.get("type")
    if kind == "FeatureCollection":
        geometries = [(feature or {}).get("geometry") for feature in value.get("features", []) if isinstance(feature, dict)]
    elif kind == "Feature":
        geometries = [value.get("geometry")]
    else:
        geometries = [value]
    pairs = []
    for geometry in geometries:
        if isinstance(geometry, dict):
            if geometry.get("type") == "GeometryCollection":
                for child in geometry.get("geometries", []):
                    if isinstance(child, dict):
                        pairs.extend(_coordinate_pairs(child.get("coordinates")))
            else:
                pairs.extend(_coordinate_pairs(geometry.get("coordinates")))
    pairs = [(lon, lat) for lon, lat in pairs if math.isfinite(lon) and math.isfinite(lat)]
    if not pairs:
        return None
    lons, lats = zip(*pairs)
    return _valid_bbox([min(lons), min(lats), max(lons), max(lats)])


def _validate_geojson(path: Path, sidecar_bbox: list[float] | None) -> tuple[list[float] | None, dict[str, str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _validation("error", "contents_extension_mismatch", "file declares .geojson but is not valid JSON")
    allowed = {"FeatureCollection", "Feature", "Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon", "GeometryCollection"}
    if not isinstance(value, dict) or value.get("type") not in allowed:
        return _validation("error", "contents_extension_mismatch", "file declares .geojson but has no GeoJSON type")
    if value.get("type") == "FeatureCollection" and not isinstance(value.get("features"), list):
        return _validation("error", "invalid_schema", "GeoJSON FeatureCollection has no features array")
    bbox = _geojson_bbox(value) or sidecar_bbox
    if not bbox:
        return _validation("error", "bbox_unavailable", "GeoJSON coverage bbox could not be derived")
    return _validation("valid", "ok", "GeoJSON schema and coverage are valid", bbox)


def _validate_s57(path: Path, sidecar_bbox: list[float] | None) -> tuple[list[float] | None, dict[str, str]]:
    try:
        header = _read_prefix(path, 24)
    except OSError:
        return _validation("error", "invalid_container", "S-57 cell could not be opened")
    if header.startswith((b"SQLite format 3\x00", b"PMTiles", b"{")):
        return _validation("error", "contents_extension_mismatch", "file declares .000 but contains another container type")
    try:
        import pyogrio  # type: ignore
        layers = pyogrio.list_layers(path)
        bounds: list[tuple[float, float, float, float]] = []
        for row in layers:
            try:
                _, values = pyogrio.read_bounds(path, layer=str(row[0]))
            except Exception:
                continue
            if getattr(values, "size", 0):
                candidate = tuple(float(part) for part in (values[0].min(), values[1].min(), values[2].max(), values[3].max()))
                if _valid_bbox(candidate):
                    bounds.append(candidate)
        bbox = _valid_bbox([
            min(item[0] for item in bounds), min(item[1] for item in bounds),
            max(item[2] for item in bounds), max(item[3] for item in bounds),
        ]) if bounds else sidecar_bbox
        if not bbox:
            return _validation("error", "bbox_unavailable", "S-57 cell opened but no coverage bbox could be derived")
        return _validation("valid", "ok", "S-57 cell and coverage are valid", bbox)
    except ImportError:
        leader_ok = len(header) == 24 and header[:5].isdigit() and header[12:17].isdigit()
        if not leader_ok:
            return _validation("error", "contents_extension_mismatch", "file declares .000 but has no ISO 8211 leader")
        if sidecar_bbox:
            return _validation("warning", "s57_driver_unavailable", "S-57 leader is valid; coverage came from metadata because pyogrio is unavailable", sidecar_bbox)
        return _validation("error", "bbox_validation_unavailable", "S-57 leader is valid but pyogrio is unavailable for required bbox validation")
    except Exception:
        return _validation("error", "contents_extension_mismatch", "file declares .000 but the S-57 driver could not open it")


def _validate_chart(path: Path, sidecar_bbox: list[float] | None) -> tuple[list[float] | None, dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".mbtiles":
        return _validate_mbtiles(path, sidecar_bbox)
    if suffix == ".pmtiles":
        return _validate_pmtiles(path, sidecar_bbox)
    if suffix == ".geojson":
        return _validate_geojson(path, sidecar_bbox)
    return _validate_s57(path, sidecar_bbox)


def _chart_id(root_id: str, relative: str) -> str:
    digest = hashlib.sha256(f"{root_id}\0{relative}".encode("utf-8", "surrogateescape")).hexdigest()[:20]
    return "chart-" + digest


def _capability_fingerprint() -> str:
    try:
        import pyogrio  # type: ignore
        return f"pyogrio:{pyogrio.__version__}"
    except ImportError:
        return "pyogrio:unavailable"


def default_depth_root() -> Path:
    """The served user-data root (depth/overlays), mirroring web/serve.py and
    helm_server's /user-data resolution — NOT default_paths' HELM_CONFIG config dir."""
    explicit = os.environ.get("HELM_USER_DATA_ROOT")
    if explicit:
        return Path(explicit).expanduser()
    config = os.environ.get("HELM_CONFIG")
    if config:
        return Path(config).expanduser() / "data"
    return Path("~/.helm/data").expanduser()


def _depth_extract_enabled() -> bool:
    return os.environ.get("HELM_INTAKE_DEPTH_EXTRACT", "1").strip().lower() not in ("0", "false", "no", "off")


def _depth_extractor() -> str | None:
    """Same preference and gating as scripts/extract-user-depth.sh (ENC-4)."""
    if shutil.which("ogr2ogr"):
        return "gdal"
    try:
        import geopandas  # type: ignore  # noqa: F401
        import pyogrio  # type: ignore  # noqa: F401
        return "pyogrio"
    except ImportError:
        return None


def _enc_fingerprint(base: Path, updates: list[Path]) -> str:
    digest = hashlib.sha256(f"enc-depth:{INDEXER_VERSION}\n".encode())
    for path in [base, *sorted(updates)]:
        stat = path.stat()
        digest.update(f"{path.name}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8", "surrogateescape"))
    return "sha256:" + digest.hexdigest()


# Absolute/home/file-URL/Windows paths with >=2 components — GDAL error text echoes the
# customer's datasource path, which must never enter the privacy-safe index or sidecars.
_ABS_PATH_RE = re.compile(
    r"""(?:file://)?/(?:[^\s/'"]+/)+[^\s'"]*   # unix absolute path, >=2 components
      | [A-Za-z]:\\(?:[^\s\\'"]+\\?)+           # windows path
      | ~/[^\s'"]+                               # home-relative path
    """,
    re.VERBOSE,
)


def _scrub_message(text: Any, limit: int = 280) -> str:
    """Redact filesystem paths from a tool/exception message, keeping only basenames so
    the error stays actionable ("cannot open US5FJ001.000") without leaking the tree."""
    value = text if isinstance(text, str) else str(text)

    def _basename(match: "re.Match[str]") -> str:
        token = match.group(0).rstrip("/\\")
        base = re.split(r"[/\\]", token)[-1] if token else ""
        return f"<path>/{base}" if base else "<path>"

    scrubbed = _ABS_PATH_RE.sub(_basename, value).strip()
    return scrubbed[-limit:] if len(scrubbed) > limit else scrubbed


def _run_ogr(cmd: list[str], what: str) -> subprocess.CompletedProcess:
    """Run a GDAL tool. A timeout or spawn failure becomes a named DepthExtractError so a
    single stuck cell fails loud per-cell instead of aborting the whole rescan."""
    env = dict(os.environ)
    env.setdefault("OGR_S57_OPTIONS", OGR_S57_OPTIONS)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
    except subprocess.TimeoutExpired as exc:
        raise DepthExtractError("depth_extract_timeout", f"{what} timed out after 600s") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise DepthExtractError("depth_extract_failed", f"{what} could not run: {_scrub_message(exc)}") from exc


def _list_enc_layers(enc: Path, extractor: str) -> list[str]:
    if extractor == "gdal":
        proc = _run_ogr(["ogrinfo", "-ro", "-q", str(enc)], "ogrinfo")
        if proc.returncode != 0:
            raise DepthExtractError("depth_cell_unreadable", f"ogrinfo could not open the cell: {_scrub_message(proc.stderr)}")
        return re.findall(r"^\d+:\s+(\S+)", proc.stdout, flags=re.MULTILINE)
    try:
        import pyogrio  # type: ignore
        return [str(row[0]) for row in pyogrio.list_layers(str(enc))]
    except Exception as exc:
        raise DepthExtractError("depth_cell_unreadable", f"pyogrio could not open the cell: {exc}") from exc


def _enc_render_date(enc: Path, extractor: str) -> str | None:
    """ENC data-valid-as-of date from the cell's DSID (UADT else ISDT), for the
    CAT-1 freshness contract. None when not derivable — never fabricated."""
    raw: dict[str, str] = {}
    try:
        if extractor == "gdal":
            proc = _run_ogr(["ogrinfo", "-ro", "-q", str(enc), "DSID"], "ogrinfo")
            if proc.returncode != 0:
                return None
            for key, value in re.findall(r"DSID_(UADT|ISDT) \(String\) = (\d{8})", proc.stdout):
                raw[key] = value
        else:
            from pyogrio import read_dataframe  # type: ignore
            frame = read_dataframe(str(enc), layer="DSID", read_geometry=False)
            for key in ("UADT", "ISDT"):
                column = f"DSID_{key}"
                if column in frame.columns and len(frame):
                    value = str(frame[column].iloc[0]).strip()
                    if re.fullmatch(r"\d{8}", value):
                        raw[key] = value
    except Exception:
        return None
    value = raw.get("UADT") or raw.get("ISDT")
    return f"{value[0:4]}-{value[4:6]}-{value[6:8]}" if value else None


def _extract_cell(enc: Path, out_dir: Path, extractor: str) -> dict[str, Any]:
    """Run the ENC-4 extraction (ogr2ogr, else pyogrio+geopandas) per present layer.
    Writes <stem>.geojson atomically into out_dir; raises DepthExtractError loudly."""
    names = _list_enc_layers(enc, extractor)
    present = [stem for stem, s57 in DEPTH_S57_LAYERS.items() if s57 in names]
    if not present:
        raise DepthExtractError("no_depth_layers_in_cell", "cell has none of DEPARE/DEPCNT/SOUNDG")
    out_dir.mkdir(parents=True, exist_ok=True)
    layers: dict[str, Any] = {}
    for stem in present:
        s57 = DEPTH_S57_LAYERS[stem]
        dst = out_dir / f"{stem}.geojson"
        tmp = out_dir / f".{stem}.geojson.tmp"
        try:
            if extractor == "gdal":
                tmp.unlink(missing_ok=True)
                proc = _run_ogr(["ogr2ogr", "-f", "GeoJSON", "-t_srs", "EPSG:4326", str(tmp), str(enc), s57], f"ogr2ogr {s57}")
                if proc.returncode != 0:
                    raise DepthExtractError("depth_extract_failed", f"ogr2ogr {s57}: {_scrub_message(proc.stderr)}")
                layers[stem] = {}
            else:
                from pyogrio import read_dataframe, write_dataframe  # type: ignore
                os.environ.setdefault("OGR_S57_OPTIONS", OGR_S57_OPTIONS)
                frame = read_dataframe(str(enc), layer=s57)
                if frame.crs and frame.crs.to_epsg() != 4326:
                    frame = frame.to_crs(4326)
                write_dataframe(frame, str(tmp), driver="GeoJSON")
                layers[stem] = {"features": int(len(frame))}
            os.replace(tmp, dst)
        except DepthExtractError:
            tmp.unlink(missing_ok=True)
            raise
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise DepthExtractError("depth_extract_failed", f"{extractor} {s57}: {_scrub_message(exc)}") from exc
    return {"layers": layers, "render_date": _enc_render_date(enc, extractor)}


def _remove_depth_outputs(out_dir: Path) -> None:
    """Remove this cell's managed depth outputs so a failed/errored cell never leaves
    stale or partial GeoJSON that the /layer-manifest producers would serve as valid."""
    if not out_dir.is_dir():
        return
    names = [f"{stem}.geojson" for stem in DEPTH_S57_LAYERS] + \
            [f"{stem}.metadata.json" for stem in DEPTH_S57_LAYERS] + ["depth-provenance.json"]
    for name in names:
        try:
            (out_dir / name).unlink(missing_ok=True)
        except OSError:
            pass
    try:
        out_dir.rmdir()  # only succeeds if we left nothing behind (never force customer files)
    except OSError:
        pass


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        if path.is_file() and path.read_text(encoding="utf-8") == data:
            return
    except (OSError, UnicodeDecodeError):
        pass
    path.write_text(data, encoding="utf-8")


def _write_depth_sidecars(out_dir: Path, cell: str, present: list[str], render_date: str | None) -> None:
    """Per-layer .metadata.json consumed by the /layer-manifest producers (decision #10:
    render_date = the ENC edition/issue date so CAT-1 freshness is honest, never fabricated)."""
    for stem in DEPTH_S57_LAYERS:
        sidecar = out_dir / f"{stem}.metadata.json"
        if stem not in present:
            (out_dir / f"{stem}.geojson").unlink(missing_ok=True)
            sidecar.unlink(missing_ok=True)
            continue
        payload: dict[str, Any] = {
            "id": f"enc-depth-{_slug(cell)}-{stem}",
            "title": f"{cell} {DEPTH_TITLES[stem]}",
            "kind": DEPTH_KINDS[stem],
            "tier": "enc",
            "source": {"label": "enc", "id": cell, "license": "enc-local"},
        }
        if render_date:
            payload["freshness"] = {"render_date": render_date}
        _write_json_if_changed(sidecar, payload)


def _slug(text: str) -> str:
    # Same rule as pipeline/layer_inventory.py _slug so sidecar ids and the
    # manifest producers' sidecar-less defaults can never diverge.
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "cell"


def _depth_dir_name(cell: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", cell).strip("-.")
    return name or "cell"


def _read_depth_provenance(out_dir: Path) -> dict[str, Any] | None:
    try:
        value = json.loads((out_dir / "depth-provenance.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == DEPTH_PROVENANCE_SCHEMA else None


def _depth_outputs_current(out_dir: Path, provenance: dict[str, Any] | None, enc_fingerprint: str) -> bool:
    if not provenance or provenance.get("enc_fingerprint") != enc_fingerprint:
        return False
    layers = provenance.get("layers")
    if not isinstance(layers, dict) or not layers:
        return False
    for stem in layers:
        if stem not in DEPTH_S57_LAYERS:
            return False
        if not (out_dir / f"{stem}.geojson").is_file() or not (out_dir / f"{stem}.metadata.json").is_file():
            return False
    return True


def _depth_state_for_fingerprint(depth_root: Path, cells: list[str]) -> list[dict[str, Any]]:
    """Deterministic depth-output state folded into the index fingerprint, so deleted or
    hand-edited outputs honestly invalidate a previously green index."""
    state = []
    for cell in sorted(cells):
        out_dir = depth_root / DEPTH_DIR / cell
        files = []
        for name in sorted([f"{stem}.geojson" for stem in DEPTH_S57_LAYERS] + [f"{stem}.metadata.json" for stem in DEPTH_S57_LAYERS] + ["depth-provenance.json"]):
            path = out_dir / name
            if path.is_file():
                stat = path.stat()
                files.append([name, stat.st_size, stat.st_mtime_ns])
        state.append({"cell": cell, "files": files})
    return state


def _customer_depth_sidecar(cell_path: Path, payload: dict[str, Any], warnings: list[dict[str, str]], root_id: str, relative: str) -> None:
    """Deposit the depth-provenance sidecar alongside the customer's cell (chart-intake-v1:
    the ENC depth extract is one of the two writers allowed into a chart root)."""
    sidecar = cell_path.with_suffix(".depth-provenance.json")
    try:
        _write_json_if_changed(sidecar, payload)
    except OSError as exc:
        warnings.append({
            "code": "depth_sidecar_unwritable",
            "root_id": root_id,
            "relative_path": relative,
            "message": f"cannot write depth-provenance sidecar next to the cell: {exc.strerror or exc}",
        })


def _depth_pass(
    enc_cells: list[tuple[dict[str, Any], Path, list[Path]]],
    depth_root: Path,
    extract_depth: bool,
    scan_warnings: list[dict[str, str]],
) -> int:
    """INTAKE-7: run the ENC-4 depth extraction for every indexed .000 cell.
    Mutates each chart item with a public `depth` record; returns the error count.
    Idempotent via enc_fingerprint; failures are named in the item, the scan
    warnings, and the customer-side sidecar — never a silent skip."""
    errors = 0
    extractor = _depth_extractor()
    seen_cells: dict[str, str] = {}
    for item, cell_path, update_paths in enc_cells:
        cell = cell_path.name[: -len(".000")]
        dir_name = _depth_dir_name(cell)
        output_rel = f"{DEPTH_DIR}/{dir_name}/"
        if item["validation"]["status"] == "error":
            item["depth"] = {"status": "skipped", "code": "chart_invalid",
                             "message": "cell failed chart validation; depth extraction not attempted"}
            continue
        if dir_name in seen_cells:
            item["depth"] = {"status": "skipped", "code": "duplicate_enc_cell",
                             "message": f"cell already extracted from {seen_cells[dir_name]}"}
            scan_warnings.append({"code": "duplicate_enc_cell_depth_skipped", "root_id": item["root_id"],
                                  "relative_path": item["relative_path"],
                                  "message": "duplicate ENC cell; depth extracted once from the first indexed copy"})
            continue
        seen_cells[dir_name] = item["relative_path"]

        out_dir = depth_root / DEPTH_DIR / dir_name
        enc_fingerprint = _enc_fingerprint(cell_path, update_paths)
        provenance = _read_depth_provenance(out_dir)
        depth: dict[str, Any]
        sidecar_payload: dict[str, Any] | None = None
        if _depth_outputs_current(out_dir, provenance, enc_fingerprint):
            depth = {"status": "ok", "code": "up_to_date", "output": output_rel,
                     "layers": sorted(provenance["layers"]), "extracted_at": provenance.get("extracted_at")}
            if provenance.get("render_date"):
                depth["render_date"] = provenance["render_date"]
        elif not extract_depth:
            depth = {"status": "skipped", "code": "depth_extract_disabled",
                     "message": "depth extraction disabled (HELM_INTAKE_DEPTH_EXTRACT=0 or --no-depth-extract)"}
            scan_warnings.append({"code": "depth_extract_disabled", "root_id": item["root_id"],
                                  "relative_path": item["relative_path"],
                                  "message": "ENC cell indexed without depth extraction; depth-on-sat will be missing or stale"})
        elif extractor is None:
            depth = {"status": "error", "code": "depth_extractor_unavailable",
                     "message": "no ENC depth extractor — install GDAL (ogr2ogr) or pip3 install pyogrio geopandas"}
        else:
            try:
                result = _extract_cell(cell_path, out_dir, extractor)
                render_date = result.get("render_date")
                present = sorted(result["layers"])
                _write_depth_sidecars(out_dir, cell, present, render_date)
                provenance_payload: dict[str, Any] = {
                    "schema": DEPTH_PROVENANCE_SCHEMA,
                    "source": "enc",
                    "cell": cell,
                    "root_id": item["root_id"],
                    "relative_path": item["relative_path"],
                    "enc_mtime": int(cell_path.stat().st_mtime),
                    "enc_fingerprint": enc_fingerprint,
                    "update_count": len(update_paths),
                    "extractor": extractor,
                    "extracted_at": _utc_now(),
                    "layers": result["layers"],
                }
                if render_date:
                    provenance_payload["render_date"] = render_date
                else:
                    scan_warnings.append({"code": "enc_render_date_unavailable", "root_id": item["root_id"],
                                          "relative_path": item["relative_path"],
                                          "message": "cell DSID has no usable ISDT/UADT; manifest freshness falls back to file dates"})
                _write_json_if_changed(out_dir / "depth-provenance.json", provenance_payload)
                depth = {"status": "ok", "code": "extracted", "output": output_rel,
                         "layers": present, "extracted_at": provenance_payload["extracted_at"]}
                if render_date:
                    depth["render_date"] = render_date
            except DepthExtractError as exc:
                depth = {"status": "error", "code": exc.code, "message": _scrub_message(exc)}
            except OSError as exc:
                depth = {"status": "error", "code": "depth_output_unwritable",
                         "message": f"cannot write depth output under {DEPTH_DIR}/: {_scrub_message(exc.strerror or exc)}"}
            except Exception as exc:
                # Defense in depth: no single cell may abort the whole rescan with an
                # unhandled traceback — it fails loud per-cell like every other error.
                depth = {"status": "error", "code": "depth_unexpected_error",
                         "message": f"unexpected extraction error: {_scrub_message(exc)}"}
        if depth["status"] == "error":
            errors += 1
            # A cell we could not extract must not leave stale/partial GeoJSON that the
            # manifest would serve as valid — show the honest enc gap instead.
            _remove_depth_outputs(out_dir)
            scan_warnings.append({"code": depth["code"], "root_id": item["root_id"],
                                  "relative_path": item["relative_path"], "message": depth["message"]})
            sidecar_payload = {"schema": DEPTH_PROVENANCE_SCHEMA, "source": "enc", "cell": cell,
                               "status": "error", "error": {"code": depth["code"], "message": depth["message"]},
                               "enc_fingerprint": enc_fingerprint}
        elif depth["status"] == "ok":
            sidecar_payload = {"schema": DEPTH_PROVENANCE_SCHEMA, "source": "enc", "cell": cell,
                               "status": "ok", "output": output_rel, "enc_fingerprint": enc_fingerprint,
                               "extracted_at": depth.get("extracted_at")}
            if depth.get("render_date"):
                sidecar_payload["render_date"] = depth["render_date"]
        item["depth"] = depth
        if sidecar_payload is not None:
            _customer_depth_sidecar(cell_path, sidecar_payload, scan_warnings, item["root_id"], item["relative_path"])
    return errors


def _scan_roots(registry: dict[str, Any], fingerprint: "hashlib._Hash") -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], Path, list[Path]]], list[dict[str, Any]], list[dict[str, str]]]:
    """Shared structural scan: walk every registered root, fold registry rows and
    file stats into ``fingerprint`` (order-stable), and return
    ``(charts, enc_cells, public_root_rows, scan_warnings)``. No writes and no
    depth extraction — both the read-only build_index and the write-bearing
    rescan build on this, so the two never diverge on structure or fingerprint
    for a depth-free library."""
    charts: list[dict[str, Any]] = []
    enc_cells: list[tuple[dict[str, Any], Path, list[Path]]] = []
    public_root_rows: list[dict[str, Any]] = []
    scan_warnings: list[dict[str, str]] = []

    for root in registry["roots"]:
        root_id = str(root["id"])
        root_path = Path(root["path"])
        root_row: dict[str, Any] = {"id": root_id, "label": str(root.get("label", "Charts")), "default": bool(root.get("default")), "status": "available"}
        root_charts: list[dict[str, Any]] = []
        # Registry metadata is part of the derived public index. A label/default
        # change must invalidate the index even when every chart byte is unchanged.
        fingerprint.update(json.dumps({
            "id": root_id,
            "label": root_row["label"],
            "default": root_row["default"],
        }, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        fingerprint.update(b"\n")
        if not root_path.is_dir():
            root_row["status"] = "unavailable"
            root_row["reason"] = "registered_root_missing"
            fingerprint.update(b"missing\n")
            scan_warnings.append({"code": "registered_root_missing", "root_id": root_id, "message": "a registered chart root is unavailable"})
            root_row.update({"chart_count": 0, "group_count": 0})
            public_root_rows.append(root_row)
            continue

        candidates: list[tuple[Path, str]] = []
        updates: dict[str, list[int]] = {}
        for current, dirs, files in os.walk(root_path, followlinks=False):
            current_path = Path(current)
            symlink_dirs = [name for name in dirs if (current_path / name).is_symlink()]
            dirs[:] = sorted(name for name in dirs if name not in symlink_dirs)
            for name in symlink_dirs:
                rel = (current_path / name).relative_to(root_path).as_posix()
                scan_warnings.append({"code": "symlink_directory_ignored", "root_id": root_id, "relative_path": rel, "message": "symlinked directories are not scanned"})
            for name in sorted(files):
                path = current_path / name
                suffix = path.suffix.lower()
                numeric_suffix = suffix[1:].isdigit() and len(suffix) == 4
                is_sidecar = name.lower().endswith(".metadata.json")
                if path.is_symlink():
                    if suffix not in RECOGNIZED and not numeric_suffix and not is_sidecar:
                        continue
                    relative = path.relative_to(root_path).as_posix()
                    try:
                        target = path.resolve(strict=True)
                        target.relative_to(root_path)
                    except (OSError, ValueError):
                        scan_warnings.append({
                            "code": "external_symlink_file_ignored",
                            "root_id": root_id,
                            "relative_path": relative,
                            "message": "symlinked chart or metadata outside the registered root is not indexed",
                        })
                        continue
                    if not target.is_file():
                        continue
                if not path.is_file():
                    continue
                relative = path.relative_to(root_path).as_posix()
                if suffix in RECOGNIZED or numeric_suffix or is_sidecar:
                    stat = path.stat()
                    fingerprint.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8", "surrogateescape"))
                if numeric_suffix and suffix != ".000":
                    updates.setdefault(path.with_suffix("").relative_to(root_path).as_posix(), []).append(int(suffix[1:]))
                elif suffix in RECOGNIZED:
                    candidates.append((path, relative))

        base_stems = {path.with_suffix("").relative_to(root_path).as_posix() for path, _ in candidates if path.suffix.lower() == ".000"}
        for stem in sorted(set(updates) - base_stems):
            scan_warnings.append({"code": "orphan_enc_update", "root_id": root_id, "relative_path": stem, "message": "S-57 update has no matching .000 base cell"})

        for path, relative in sorted(candidates, key=lambda item: item[1].lower()):
            stat = path.stat()
            metadata, metadata_warnings, sidecar_path = _sidecar(path)
            bbox, validation = _validate_chart(path, metadata.get("bbox"))
            if any(item["code"] == "invalid_sidecar" for item in metadata_warnings):
                validation = {"status": "error", "code": "invalid_sidecar", "message": "chart metadata sidecar is invalid"}
            group = relative.split("/", 1)[0] if "/" in relative else "."
            item: dict[str, Any] = {
                "id": _chart_id(root_id, relative),
                "root_id": root_id,
                "relative_path": relative,
                "filename": path.name,
                "group": group,
                "chart_type": RECOGNIZED[path.suffix.lower()],
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_at": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "validation": validation,
                "warnings": metadata_warnings,
            }
            if bbox:
                item["bbox"] = bbox
            if metadata:
                item["metadata"] = metadata
            if sidecar_path:
                item["sidecar"] = sidecar_path.name
            if path.suffix.lower() == ".000":
                enc_updates = sorted(updates.get(path.with_suffix("").relative_to(root_path).as_posix(), []))
                item["update_count"] = len(enc_updates)
                if enc_updates:
                    item["latest_update"] = max(enc_updates)
                update_paths = [path.with_suffix(f".{number:03d}") for number in enc_updates]
                enc_cells.append((item, path, [update for update in update_paths if update.is_file()]))
            root_charts.append(item)

        charts.extend(root_charts)
        root_row["chart_count"] = len(root_charts)
        root_row["group_count"] = len({item["group"] for item in root_charts})
        public_root_rows.append(root_row)
    return charts, enc_cells, public_root_rows, scan_warnings


def build_index(registry: dict[str, Any]) -> dict[str, Any]:
    """Compute the ``helm.chart_intake.index.v1`` document for a registry.

    Pure read: scans the registered roots but never writes the registry, the
    index artifact, or any depth output. INTAKE-7's ENC depth extraction is a
    write-bearing, rescan-only augmentation and is intentionally NOT run here —
    that keeps GET /chart-index side-effect-free and in parity with the C++
    helm-packd producer, which has no S-57 depth pipeline. For a library with no
    ENC cells this returns byte-for-byte what ``rescan`` computes (the depth pass
    is then a no-op)."""
    fingerprint = hashlib.sha256(f"chart-intake:{INDEXER_VERSION}:{_capability_fingerprint()}\n".encode())
    charts, _enc_cells, public_root_rows, scan_warnings = _scan_roots(registry, fingerprint)
    fingerprint_value = "sha256:" + fingerprint.hexdigest()
    invalid_count = sum(item["validation"]["status"] == "error" for item in charts)
    warning_count = sum(item["validation"]["status"] == "warning" or bool(item["warnings"]) for item in charts) + len(scan_warnings)
    status = "error" if invalid_count else ("warning" if warning_count else "ok")
    return {
        "schema": INDEX_SCHEMA,
        "indexer_version": INDEXER_VERSION,
        "chart_classes": CHART_CLASSES,
        "generated_at": _utc_now(),
        "fingerprint": fingerprint_value,
        "status": status,
        "chart_count": len(charts),
        "invalid_count": invalid_count,
        "warning_count": warning_count,
        "roots": public_root_rows,
        "charts": charts,
        "warnings": scan_warnings,
    }


def rescan(roots_file: Path, index_file: Path, default_root: Path, *, depth_root: Path | None = None, extract_depth: bool | None = None) -> tuple[dict[str, Any], bool]:
    registry = ensure_registry(roots_file, default_root)
    resolved_depth_root = Path(depth_root).expanduser() if depth_root else default_depth_root()
    resolved_extract = _depth_extract_enabled() if extract_depth is None else bool(extract_depth)
    fingerprint = hashlib.sha256(f"chart-intake:{INDEXER_VERSION}:{_capability_fingerprint()}\n".encode())
    charts, enc_cells, public_root_rows, scan_warnings = _scan_roots(registry, fingerprint)
    # INTAKE-7: indexing an ENC also produces its depth-on-sat GeoJSON. The pass runs
    # before the fingerprint is sealed so the depth outcome (and the output files
    # themselves) invalidate a stale index instead of hiding behind one.
    depth_error_count = _depth_pass(enc_cells, resolved_depth_root, resolved_extract, scan_warnings)
    for entry in _depth_state_for_fingerprint(resolved_depth_root, sorted({_depth_dir_name(path.name[: -len(".000")]) for _, path, _ in enc_cells})):
        fingerprint.update(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        fingerprint.update(b"\n")
    for item, _, _ in enc_cells:
        # Normalized: a fresh "extracted" and a later "up_to_date" describe the same
        # outputs, and extracted_at is already pinned by the provenance file stats above —
        # only real outcome changes (ok/skipped/error, layers, errors) reshape the index.
        normalized = {key: value for key, value in item["depth"].items() if key != "extracted_at"}
        if normalized.get("status") == "ok":
            normalized["code"] = "ok"
        fingerprint.update(json.dumps({"depth": normalized}, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        fingerprint.update(b"\n")

    fingerprint_value = "sha256:" + fingerprint.hexdigest()
    invalid_count = sum(item["validation"]["status"] == "error" for item in charts)
    warning_count = sum(item["validation"]["status"] == "warning" or bool(item["warnings"]) for item in charts) + len(scan_warnings)
    status = "error" if invalid_count or depth_error_count else ("warning" if warning_count else "ok")
    payload = {
        "schema": INDEX_SCHEMA,
        "indexer_version": INDEXER_VERSION,
        "chart_classes": CHART_CLASSES,
        "generated_at": _utc_now(),
        "fingerprint": fingerprint_value,
        "status": status,
        "chart_count": len(charts),
        "invalid_count": invalid_count,
        "warning_count": warning_count,
        "depth_error_count": depth_error_count,
        "roots": public_root_rows,
        "charts": charts,
        "warnings": scan_warnings,
    }

    if index_file.exists():
        try:
            previous = json.loads(index_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            previous = None
        if isinstance(previous, dict) and previous.get("schema") == INDEX_SCHEMA and previous.get("fingerprint") == fingerprint_value:
            _secure_private_file(index_file)
            return previous, False
    _atomic_json(index_file, payload)
    return payload, True


def _summary(index: dict[str, Any], changed: bool) -> dict[str, Any]:
    return {
        "schema": INDEX_SCHEMA,
        "changed": changed,
        "fingerprint": index["fingerprint"],
        "status": index["status"],
        "chart_count": index["chart_count"],
        "invalid_count": index["invalid_count"],
        "warning_count": index["warning_count"],
        "depth_error_count": index.get("depth_error_count", 0),
    }


def _parser() -> argparse.ArgumentParser:
    roots_file, index_file, default_root = default_paths()
    parser = argparse.ArgumentParser(description="Register and index chart folders in place")
    parser.add_argument("--roots-file", type=Path, default=roots_file)
    parser.add_argument("--index-file", type=Path, default=index_file)
    parser.add_argument("--default-root", type=Path, default=default_root)
    parser.add_argument("--depth-root", type=Path, default=None,
                        help="user-data root for extracted ENC depth GeoJSON (default: HELM_USER_DATA_ROOT / HELM_CONFIG/data / ~/.helm/data)")
    parser.add_argument("--no-depth-extract", action="store_true",
                        help="index without running the INTAKE-7 ENC depth extraction (skips are named in the catalog)")
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", help="register an existing chart folder and rescan")
    register.add_argument("path", type=Path)
    register.add_argument("--label")
    unregister = commands.add_parser("unregister", help="unregister a root without deleting customer files")
    unregister.add_argument("root_or_path")
    listing = commands.add_parser("list", help="list registered roots")
    listing.add_argument("--show-paths", action="store_true", help="explicitly show private local paths")
    commands.add_parser("rescan", help="recursively rebuild the in-place chart index")
    commands.add_parser("catalog", help="print the current public chart index")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    depth_options = {"depth_root": args.depth_root, "extract_depth": False if args.no_depth_extract else None}
    try:
        if args.command == "register":
            root, registry_changed = register_root(args.roots_file, args.default_root, args.path, args.label)
            index, index_changed = rescan(args.roots_file, args.index_file, args.default_root, **depth_options)
            result = _summary(index, index_changed)
            result.update({"registered": {key: root[key] for key in ("id", "label", "default")}, "registry_changed": registry_changed})
        elif args.command == "unregister":
            removed = unregister_root(args.roots_file, args.default_root, args.root_or_path)
            index, changed = rescan(args.roots_file, args.index_file, args.default_root, **depth_options)
            result = _summary(index, changed)
            result["unregistered"] = {key: removed[key] for key in ("id", "label", "default")}
        elif args.command == "list":
            result = public_roots(ensure_registry(args.roots_file, args.default_root), args.show_paths)
        elif args.command == "catalog":
            if not args.index_file.exists():
                result, _ = rescan(args.roots_file, args.index_file, args.default_root, **depth_options)
            else:
                _secure_private_file(args.index_file)
                result = json.loads(args.index_file.read_text(encoding="utf-8"))
        else:
            index, changed = rescan(args.roots_file, args.index_file, args.default_root, **depth_options)
            result = _summary(index, changed)
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1 if isinstance(result, dict) and result.get("status") == "error" else 0
    except IntakeError as exc:
        print(json.dumps({"error": "chart_intake_error", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
