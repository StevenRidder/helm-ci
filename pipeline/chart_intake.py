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
import sqlite3
import struct
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Iterable


ROOTS_SCHEMA = "helm.chart_intake.roots.v1"
INDEX_SCHEMA = "helm.chart_intake.index.v1"
INDEXER_VERSION = 1
RECOGNIZED = {".mbtiles": "tile_pack", ".pmtiles": "tile_pack", ".000": "enc", ".geojson": "overlay"}
CHART_CLASSES = [
    {"chart_type": "tile_pack", "extensions": [".mbtiles", ".pmtiles"], "consumer": "helm-packd"},
    {"chart_type": "enc", "extensions": [".000"], "consumer": "helm-server"},
    {"chart_type": "overlay", "extensions": [".geojson"], "consumer": "layer-manifest"},
]


class IntakeError(ValueError):
    """A named, user-actionable chart-intake failure."""


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


def rescan(roots_file: Path, index_file: Path, default_root: Path) -> tuple[dict[str, Any], bool]:
    registry = ensure_registry(roots_file, default_root)
    fingerprint = hashlib.sha256(f"chart-intake:{INDEXER_VERSION}:{_capability_fingerprint()}\n".encode())
    charts: list[dict[str, Any]] = []
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
            root_charts.append(item)

        charts.extend(root_charts)
        root_row["chart_count"] = len(root_charts)
        root_row["group_count"] = len({item["group"] for item in root_charts})
        public_root_rows.append(root_row)

    fingerprint_value = "sha256:" + fingerprint.hexdigest()
    invalid_count = sum(item["validation"]["status"] == "error" for item in charts)
    warning_count = sum(item["validation"]["status"] == "warning" or bool(item["warnings"]) for item in charts) + len(scan_warnings)
    status = "error" if invalid_count else ("warning" if warning_count else "ok")
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
    }


def _parser() -> argparse.ArgumentParser:
    roots_file, index_file, default_root = default_paths()
    parser = argparse.ArgumentParser(description="Register and index chart folders in place")
    parser.add_argument("--roots-file", type=Path, default=roots_file)
    parser.add_argument("--index-file", type=Path, default=index_file)
    parser.add_argument("--default-root", type=Path, default=default_root)
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
    try:
        if args.command == "register":
            root, registry_changed = register_root(args.roots_file, args.default_root, args.path, args.label)
            index, index_changed = rescan(args.roots_file, args.index_file, args.default_root)
            result = _summary(index, index_changed)
            result.update({"registered": {key: root[key] for key in ("id", "label", "default")}, "registry_changed": registry_changed})
        elif args.command == "unregister":
            removed = unregister_root(args.roots_file, args.default_root, args.root_or_path)
            index, changed = rescan(args.roots_file, args.index_file, args.default_root)
            result = _summary(index, changed)
            result["unregistered"] = {key: removed[key] for key in ("id", "label", "default")}
        elif args.command == "list":
            result = public_roots(ensure_registry(args.roots_file, args.default_root), args.show_paths)
        elif args.command == "catalog":
            if not args.index_file.exists():
                result, _ = rescan(args.roots_file, args.index_file, args.default_root)
            else:
                _secure_private_file(args.index_file)
                result = json.loads(args.index_file.read_text(encoding="utf-8"))
        else:
            index, changed = rescan(args.roots_file, args.index_file, args.default_root)
            result = _summary(index, changed)
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 1 if isinstance(result, dict) and result.get("status") == "error" else 0
    except IntakeError as exc:
        print(json.dumps({"error": "chart_intake_error", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
