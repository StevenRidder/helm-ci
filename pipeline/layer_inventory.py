#!/usr/bin/env python3
"""Build Helm's local maritime layer inventory.

The layer inventory is the boat-local catalog above raw packs and region
bundles. It describes what data is present, where it came from, what it covers,
how fresh it is, and which sample/probe handle can answer a tap. It does not
parse charts, fetch tiles, or own renderer semantics.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional

from region_bundle import BundleError, build_region_bundle


LAYER_INVENTORY_SCHEMA = "helm.maritime_layer_inventory.v1"
LAYER_MANIFEST_SCHEMA = "helm.layer.manifest.v1"
DEFAULT_INVENTORY_ID = "local-maritime-layers"
DEFAULT_TITLE = "Local Maritime Layer Inventory"

VALID_MANIFEST_TIERS = frozenset({"basemap", "enc", "overlay", "weather", "nav"})

ENC_GEOJSON_LAYERS = {
    "depare": {"kind": "polygons", "tier": "enc", "title": "Depth areas"},
    "depcnt": {"kind": "lines", "tier": "enc", "title": "Depth contours"},
    "soundg": {"kind": "points", "tier": "enc", "title": "Soundings"},
}

PRIVATE_KEYS = {
    "_path",
    "path",
    "file_path",
    "filepath",
    "local_path",
    "private_path",
    "directory",
    "dir",
}

LINK_KEYS = (
    "url",
    "tile_url",
    "pmtiles_url",
    "protocol_url",
    "source_url",
    "service_url",
    "content_url",
)

SAMPLE_BY_ROLE = {
    "chart": "chart.objects",
    "depth": "depth",
    "bathymetry": "depth",
    "places": "places",
    "weather": "weather",
    "currents": "tides",
    "surface_current": "tides",
    "water_level": "tides",
    "navigation_warning": "warnings.navigation",
    "warnings": "warnings.navigation",
    "under_keel_clearance": "pass.ukc",
    "cruiser": "cruiser.layers",
    "vector": "vector.features",
    "environmental_bundle": "weather.bundle",
}


class LayerInventoryError(ValueError):
    pass


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _first(query: dict, name: str, default=None):
    value = query.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


def _json_safe(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _public_json(value):
    if isinstance(value, dict):
        public = {}
        for key, child in value.items():
            key_text = str(key)
            if key_text.startswith("_") or key_text.lower() in PRIVATE_KEYS:
                continue
            public[key] = _public_json(child)
        return public
    if isinstance(value, list):
        return [_public_json(child) for child in value]
    return _json_safe(value)


def _drop_none(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def _as_list(value) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _bounds_array(value) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            west, south, east, north = [float(v) for v in value]
        except (TypeError, ValueError):
            return None
    elif isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        if len(parts) != 4:
            return None
        try:
            west, south, east, north = [float(p) for p in parts]
        except ValueError:
            return None
    else:
        return None
    if west >= east or south >= north:
        return None
    return [west, south, east, north]


def _env_bbox(value) -> Optional[dict]:
    """Parse helm.env.bundle.v1 bbox objects, including antimeridian spans."""
    if isinstance(value, dict):
        try:
            west = float(value["west"])
            south = float(value["south"])
            east = float(value["east"])
            north = float(value["north"])
        except (KeyError, TypeError, ValueError):
            return None
        crosses = bool(value.get("crossesAntimeridian")) or west > east
        return {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "crossesAntimeridian": crosses,
            "crosses_antimeridian": crosses,
        }
    bbox = _bounds_array(value)
    if not bbox:
        return None
    west, south, east, north = bbox
    return {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "crossesAntimeridian": False,
        "crosses_antimeridian": False,
    }


def _bbox_polygon(bbox: Optional[List[float]]) -> Optional[List[List[float]]]:
    if not bbox:
        return None
    west, south, east, north = bbox
    return [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]


def _slug(text: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug or "layer"


def _source_info(component: dict) -> dict:
    info = component.get("source_info") if isinstance(component.get("source_info"), dict) else {}
    source = {
        "label": info.get("label") or component.get("source") or component.get("producer_code") or "local",
        "id": info.get("id") or component.get("source_id"),
        "kind": info.get("kind") or component.get("kind"),
        "format": info.get("format") or component.get("format"),
        "license": info.get("license") or component.get("license"),
        "attribution": info.get("attribution") or component.get("attribution"),
        "modified": info.get("modified") or component.get("modified"),
        "updated": info.get("updated") or component.get("updated"),
        "ref": info.get("ref") or component.get("source_ref"),
        "confidence": info.get("confidence") or component.get("confidence"),
    }
    return _drop_none(_public_json(source))


def _links(component: dict) -> List[dict]:
    links = []
    for key in LINK_KEYS:
        value = component.get(key)
        if value:
            links.append({"rel": key, "href": value})
    for item in component.get("source_links") or []:
        if isinstance(item, dict) and item.get("href"):
            links.append(_public_json(item))
    return links


def _coverage(component: dict) -> dict:
    coverage = component.get("coverage") if isinstance(component.get("coverage"), dict) else {}
    bbox = _bounds_array(coverage.get("bbox") or component.get("bounds_array") or component.get("bounds"))
    payload = {
        "status": coverage.get("status") or component.get("coverage_status") or ("area" if bbox else "unknown"),
        "bbox": bbox,
        "polygon": coverage.get("polygon") or _bbox_polygon(bbox),
        "region": coverage.get("region"),
        "tile_count": coverage.get("tile_count"),
        "tile_count_expected": coverage.get("tile_count_expected"),
        "gap_count": coverage.get("gap_count"),
        "gap_ratio": coverage.get("gap_ratio"),
        "warning": coverage.get("warning"),
    }
    return _drop_none(_public_json(payload))


def _freshness(component: dict) -> dict:
    staleness = component.get("staleness") if isinstance(component.get("staleness"), dict) else {}
    source = component.get("source_info") if isinstance(component.get("source_info"), dict) else {}
    payload = {
        "status": component.get("freshness") or staleness.get("status") or source.get("freshness") or "unknown",
        "render_date": staleness.get("render_date") or component.get("render_date"),
        "stale_at": staleness.get("stale_at") or component.get("stale_at"),
        "age_days": staleness.get("age_days"),
        "updated": source.get("updated") or component.get("source_updated") or component.get("updated"),
        "reference_date": component.get("dataset_reference_date") or component.get("reference_date"),
        "warning": staleness.get("warning"),
    }
    return _drop_none(_public_json(payload))


def _confidence(component: dict) -> str:
    source = component.get("source_info") if isinstance(component.get("source_info"), dict) else {}
    return str(component.get("confidence") or source.get("confidence") or "unknown")


def _product_identifier(component: dict, role: str) -> str:
    explicit = component.get("product_identifier") or component.get("product_id")
    if explicit:
        return str(explicit)
    renderer = str(component.get("renderer") or "").lower()
    container = str(component.get("container") or "").lower()
    kind = str(component.get("kind") or "").lower()
    if renderer == "s52":
        return "S-52"
    if role in ("depth", "bathymetry") or kind == "depth":
        return "S-102-style"
    if role in ("currents", "surface_current"):
        return "S-111-style"
    if role in ("water_level", "tides"):
        return "S-104-style"
    if role in ("navigation_warning", "warnings"):
        return "S-124-style"
    if role == "under_keel_clearance":
        return "S-129-style"
    if role == "weather":
        return "weather.model-run"
    if role == "places":
        return "places.local"
    if role == "cruiser":
        return "cruiser.layer"
    if container == "pmtiles":
        return "PMTiles"
    if container == "mbtiles":
        return "MBTiles"
    return "helm.layer"


def _dataset_edition(component: dict) -> Optional[str]:
    source = component.get("source_info") if isinstance(component.get("source_info"), dict) else {}
    value = (
        component.get("dataset_edition")
        or component.get("chart_edition")
        or source.get("chart_edition")
        or source.get("edition")
        or component.get("edition")
    )
    return str(value) if value is not None else None


def _dataset_reference_date(component: dict) -> Optional[str]:
    source = component.get("source_info") if isinstance(component.get("source_info"), dict) else {}
    value = (
        component.get("dataset_reference_date")
        or component.get("reference_date")
        or source.get("updated")
        or source.get("render_date")
        or component.get("render_date")
        or component.get("modified")
    )
    return str(value) if value is not None else None


def _probe_handle(component: dict, role: str) -> Optional[str]:
    sample = component.get("sample") if isinstance(component.get("sample"), dict) else {}
    explicit = component.get("probe_handle") or sample.get("probe_handle")
    if explicit:
        return str(explicit)
    inspection = component.get("inspection") if isinstance(component.get("inspection"), dict) else {}
    if inspection.get("tap_action") == "show_pack_source_metadata":
        return None
    return SAMPLE_BY_ROLE.get(role)


def _z_range(component: dict) -> Optional[dict]:
    if component.get("minzoom") is None and component.get("maxzoom") is None:
        return None
    return _drop_none({"min": component.get("minzoom"), "max": component.get("maxzoom")})


def _time_range(component: dict) -> Optional[dict]:
    value = component.get("time_range")
    if isinstance(value, dict):
        return _public_json(value)
    valid = component.get("valid_time") or component.get("validTime")
    if valid:
        return {"valid": valid}
    return None


def _sample_contract(handle: Optional[str]) -> dict:
    return {
        "status": "available" if handle else "unavailable",
        "probe_handle": handle,
        "contract": "sample(lat, lon, t)" if handle else None,
    }


def _layer_from_component(component: dict) -> dict:
    role = str(component.get("role") or component.get("kind") or "layer")
    product = _product_identifier(component, role)
    source = _source_info(component)
    handle = _probe_handle(component, role)
    layer = {
        "id": "layer:%s" % _slug(component.get("id") or component.get("title") or product),
        "component_id": component.get("id"),
        "role": role,
        "product_identifier": product,
        "product_id": product,
        "dataset_name": component.get("dataset_name") or component.get("title") or component.get("name") or component.get("id"),
        "dataset_edition": _dataset_edition(component),
        "dataset_reference_date": _dataset_reference_date(component),
        "producer_code": component.get("producer_code") or source.get("label"),
        "source": source,
        "links": _links(component),
        "coverage": _coverage(component),
        "z_range": _z_range(component),
        "time_range": _time_range(component),
        "pack": _drop_none({
            "container": component.get("container"),
            "format": component.get("format"),
            "type": component.get("type"),
            "size_bytes": component.get("size_bytes"),
        }),
        "freshness": _freshness(component),
        "confidence": _confidence(component),
        "sample": _drop_none(_sample_contract(handle)),
        "inspection": _public_json(component.get("inspection")) if component.get("inspection") else None,
        "warnings": _public_json(component.get("warnings")) if component.get("warnings") else [],
        "renderer": component.get("renderer"),
        "style": _drop_none({
            "palette": component.get("palette"),
            "display_category": component.get("display_category"),
        }),
        "not_for_navigation": True,
        "advisory_label": "Local Helm layer inventory; verify official sources for navigation.",
    }
    return _drop_none(_public_json(layer))


def _layer_from_dataset(dataset: dict, default_role: str, default_product: str) -> dict:
    record = dict(dataset)
    record.setdefault("role", default_role)
    record.setdefault("product_identifier", default_product)
    return _layer_from_component(record)


def _layer_from_s100_record(record: dict) -> dict:
    target = record.get("target_contract") if isinstance(record.get("target_contract"), dict) else {}
    role = target.get("role") or record.get("role") or "s100"
    component = {
        "id": "s100:%s:%s" % (str(record.get("product_identifier", "s100")).lower(), _slug(record.get("probe_handle") or record.get("dataset_name"))),
        "role": role,
        "product_identifier": record.get("product_identifier"),
        "product_id": record.get("product_identifier"),
        "dataset_name": record.get("dataset_name"),
        "dataset_edition": record.get("dataset_edition"),
        "dataset_reference_date": record.get("dataset_reference_date"),
        "producer_code": record.get("producer_code"),
        "source": "s100-local",
        "source_links": record.get("source_links"),
        "coverage": record.get("coverage"),
        "time_range": record.get("time_range"),
        "freshness": record.get("freshness"),
        "confidence": record.get("confidence"),
        "probe_handle": record.get("probe_handle"),
        "sample": {"probe_handle": record.get("probe_handle")},
        "target_contract": target,
        "not_for_navigation": record.get("not_for_navigation", True),
        "advisory_label": record.get("advisory_label"),
    }
    layer = _layer_from_component(component)
    if target:
        layer["target_contract"] = _public_json(target)
    return layer


def _env_bundle_manifests(value) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_env_bundle_manifests(item))
        return out
    if not isinstance(value, dict):
        return []
    if value.get("schema") == "helm.env.bundle.v1":
        return [value]
    if isinstance(value.get("bundles"), list):
        # Index entries are useful only when they carry an embedded manifest. A URL-only
        # index is a discovery surface, not enough to build an offline inventory record.
        out = []
        for item in value["bundles"]:
            if isinstance(item, dict):
                out.extend(_env_bundle_manifests(item.get("manifestObject") or item.get("bundle") or item))
        return out
    return []


def _env_bundle_id(manifest: dict) -> str:
    return str(manifest.get("bundleId") or manifest.get("id") or "environmental-bundle")


def _env_bundle_source(manifest: dict) -> dict:
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    return _drop_none(_public_json({
        "label": source.get("provider") or source.get("label") or "environmental-model",
        "id": source.get("provider") or source.get("id"),
        "kind": "environmental-bundle",
        "format": manifest.get("encoding"),
        "license": source.get("license"),
        "attribution": source.get("attribution"),
        "updated": run.get("runTime") or manifest.get("generatedAt"),
        "ref": manifest.get("bundleId"),
        "confidence": "forecast-advisory",
        "model": run.get("model"),
        "marine_model": run.get("marineModel"),
        "official_product": False,
    }))


def _env_bundle_coverage(manifest: dict) -> dict:
    coverage = manifest.get("coverage") if isinstance(manifest.get("coverage"), dict) else {}
    bbox = _env_bbox(coverage.get("bbox"))
    if not bbox:
        return {"status": "unknown"}
    arr = [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    payload = {
        "status": "area",
        "bbox": arr,
        "bbox_object": bbox,
        "polygon": None if bbox["crossesAntimeridian"] else _bbox_polygon(arr),
        "region": coverage.get("regionId") or coverage.get("homeWaters"),
        "wrap": coverage.get("wrap") or ("antimeridian" if bbox["crossesAntimeridian"] else "none"),
        "warning": coverage.get("warning"),
    }
    return _drop_none(_public_json(payload))


def _env_bundle_z_range(manifest: dict) -> Optional[dict]:
    lod = manifest.get("lod") if isinstance(manifest.get("lod"), dict) else {}
    if lod.get("dataMinZoom") is not None or lod.get("dataMaxZoom") is not None:
        return _drop_none({"min": lod.get("dataMinZoom"), "max": lod.get("dataMaxZoom")})
    mins, maxs = [], []
    levels = lod.get("levels") if isinstance(lod.get("levels"), dict) else {}
    for level in levels.values():
        if not isinstance(level, dict):
            continue
        if level.get("minzoom") is not None:
            mins.append(level.get("minzoom"))
        if level.get("maxzoom") is not None:
            maxs.append(level.get("maxzoom"))
    if not mins and not maxs:
        return None
    return _drop_none({"min": min(mins) if mins else None, "max": max(maxs) if maxs else None})


def _env_bundle_time_range(manifest: dict) -> Optional[dict]:
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    valid = [str(v) for v in (run.get("validTimes") or [])]
    payload = {
        "start": valid[0] if valid else run.get("runTime"),
        "end": valid[-1] if valid else run.get("runTime"),
        "valid_times": valid,
        "frames": run.get("frames"),
        "run_time": run.get("runTime"),
    }
    return _drop_none(_public_json(payload)) or None


def _env_bundle_freshness(manifest: dict) -> dict:
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    cache = manifest.get("cacheState") if isinstance(manifest.get("cacheState"), dict) else {}
    state = str(cache.get("state") or "").lower()
    if state in ("expired", "stale", "fresh", "refreshing", "partial"):
        status = state
    elif cache.get("offlineReady"):
        status = "fresh"
    elif manifest.get("generatedAt") or run.get("runTime"):
        status = "unknown"
    else:
        status = "unknown"
    return _drop_none(_public_json({
        "status": status,
        "render_date": cache.get("materializedAt") or manifest.get("generatedAt"),
        "updated": run.get("runTime") or manifest.get("generatedAt"),
        "stale_at": cache.get("staleAt"),
        "warning": cache.get("warning"),
    }))


def _env_bundle_product_for_layer(name: str, layer: dict) -> str:
    s100 = layer.get("s100") if isinstance(layer.get("s100"), dict) else {}
    return str(s100.get("productIdentifier") or ("S-111" if name == "current" else "S-413"))


def _env_bundle_record(manifest: dict, manifest_url: Optional[str]) -> dict:
    bundle_id = _env_bundle_id(manifest)
    run = manifest.get("run") if isinstance(manifest.get("run"), dict) else {}
    policy = manifest.get("cachePolicy") if isinstance(manifest.get("cachePolicy"), dict) else {}
    cache = manifest.get("cacheState") if isinstance(manifest.get("cacheState"), dict) else {}
    layers = manifest.get("layers") if isinstance(manifest.get("layers"), dict) else {}
    source = _env_bundle_source(manifest)
    links = [{"rel": "manifest", "href": manifest_url}] if manifest_url else []
    return _drop_none(_public_json({
        "id": "env-bundle:%s" % _slug(bundle_id),
        "component_id": bundle_id,
        "role": "environmental_bundle",
        "product_identifier": manifest.get("schema") or "helm.env.bundle.v1",
        "product_id": manifest.get("schema") or "helm.env.bundle.v1",
        "dataset_name": manifest.get("title") or bundle_id,
        "dataset_edition": run.get("runLabel"),
        "dataset_reference_date": run.get("runTime") or manifest.get("generatedAt"),
        "producer_code": source.get("label"),
        "source": source,
        "links": links,
        "coverage": _env_bundle_coverage(manifest),
        "z_range": _env_bundle_z_range(manifest),
        "time_range": _env_bundle_time_range(manifest),
        "pack": {
            "container": "environmental-bundle",
            "schema": manifest.get("schema"),
            "format": manifest.get("encoding"),
            "size_bytes": manifest.get("sizeBytes") or manifest.get("size_bytes"),
        },
        "freshness": _env_bundle_freshness(manifest),
        "confidence": "forecast-advisory",
        "sample": _sample_contract("weather.bundle"),
        "environmental_bundle": {
            "bundleId": bundle_id,
            "layers": sorted(layers.keys()),
            "validTimes": run.get("validTimes") or [],
            "model": run.get("model"),
            "marineModel": run.get("marineModel"),
            "cacheOnlyReplay": bool(policy.get("cacheOnlyReplay", True)),
            "upstreamFetchesAllowedDuringGesture": bool(policy.get("upstreamFetchesAllowedDuringGesture", False)),
            "offlineReady": bool(cache.get("offlineReady")),
            "state": cache.get("state"),
        },
        "cachePolicy": policy,
        "cacheState": cache,
        "warnings": [],
        "not_for_navigation": True,
        "advisory_label": "Forecast/advisory met-ocean data. Cross-reference official sources.",
    }))


def _env_layer_record(manifest: dict, name: str, layer: dict, manifest_url: Optional[str]) -> dict:
    bundle_id = _env_bundle_id(manifest)
    source = _env_bundle_source(manifest)
    product = _env_bundle_product_for_layer(name, layer)
    role = "surface_current" if name == "current" else "weather"
    links = [{"rel": "manifest", "href": manifest_url}] if manifest_url else []
    return _drop_none(_public_json({
        "id": "env:%s:%s" % (_slug(bundle_id), _slug(name)),
        "component_id": bundle_id,
        "role": role,
        "product_identifier": product,
        "product_id": product,
        "dataset_name": "%s · %s" % (manifest.get("title") or bundle_id, name),
        "dataset_edition": (manifest.get("run") or {}).get("runLabel") if isinstance(manifest.get("run"), dict) else None,
        "dataset_reference_date": (manifest.get("run") or {}).get("runTime") if isinstance(manifest.get("run"), dict) else manifest.get("generatedAt"),
        "producer_code": source.get("label"),
        "source": source,
        "links": links,
        "coverage": _env_bundle_coverage(manifest),
        "z_range": _env_bundle_z_range(manifest),
        "time_range": _env_bundle_time_range(manifest),
        "pack": {
            "container": "environmental-bundle",
            "schema": manifest.get("schema"),
            "format": manifest.get("encoding"),
        },
        "freshness": _env_bundle_freshness(manifest),
        "confidence": "forecast-advisory",
        "sample": _sample_contract("weather.%s" % name),
        "environmental_bundle": {
            "bundleId": bundle_id,
            "layer": name,
            "kind": layer.get("kind"),
            "unit": layer.get("unit"),
            "fieldTiles": layer.get("fieldTiles"),
            "vectorField": layer.get("vectorField"),
        },
        "s100": layer.get("s100") if isinstance(layer.get("s100"), dict) else None,
        "not_for_navigation": True,
        "advisory_label": "Forecast/advisory met-ocean data. Cross-reference official sources.",
    }))


def _layers_from_environmental_bundles(environmental_bundles) -> list[dict]:
    out: list[dict] = []
    for manifest in _env_bundle_manifests(environmental_bundles):
        manifest_url = manifest.get("manifest") or manifest.get("manifest_url")
        out.append(_env_bundle_record(manifest, manifest_url))
        layers = manifest.get("layers") if isinstance(manifest.get("layers"), dict) else {}
        for name, layer in sorted(layers.items()):
            if isinstance(layer, dict):
                out.append(_env_layer_record(manifest, str(name), layer, manifest_url))
    return out


def _summary(layers: list[dict]) -> dict:
    roles: Dict[str, int] = {}
    products: Dict[str, int] = {}
    stale = 0
    out_of_coverage = 0
    sample_handles = []
    for layer in layers:
        role = str(layer.get("role") or "unknown")
        product = str(layer.get("product_identifier") or "unknown")
        roles[role] = roles.get(role, 0) + 1
        products[product] = products.get(product, 0) + 1
        if layer.get("freshness", {}).get("status") == "stale":
            stale += 1
        if layer.get("coverage", {}).get("status") not in (None, "complete", "area", "unknown"):
            out_of_coverage += 1
        handle = layer.get("sample", {}).get("probe_handle")
        if handle:
            sample_handles.append(handle)
    return {
        "layers": len(layers),
        "roles": roles,
        "products": products,
        "stale": stale,
        "out_of_coverage": out_of_coverage,
        "sample_handles": sorted(set(sample_handles)),
    }


def _inventory_coverage(bundle: dict) -> dict:
    corridor = bundle.get("corridor") if isinstance(bundle.get("corridor"), dict) else {}
    bbox = _bounds_array(corridor.get("bbox") or bundle.get("coverage", {}).get("bbox"))
    return _drop_none({
        "status": "area" if bbox else "unknown",
        "bbox": bbox,
        "polygon": _bbox_polygon(bbox),
    })


def _s100_records(s100_inventory: dict | list | None) -> list[dict]:
    if isinstance(s100_inventory, dict):
        return _as_list(s100_inventory.get("layers"))
    return _as_list(s100_inventory)


def _humanize_slug(stem: str) -> str:
    text = re.sub(r"[_\-]+", " ", stem).strip()
    return text[:1].upper() + text[1:] if text else stem


def _load_sidecar_dict(path: str) -> dict:
    base, _ = os.path.splitext(path)
    for candidate in (
        base + ".metadata.json",
        base + ".sidecar.json",
        path + ".metadata.json",
        path + ".sidecar.json",
    ):
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return _public_json(payload)
    return {}


def _walk_coordinates(value, bbox: list[float], *, limit: int) -> int:
    if limit <= 0:
        return 0
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (int, float)) and len(value) >= 2:
            lon = float(value[0])
            lat = float(value[1])
            bbox[0] = min(bbox[0], lon)
            bbox[1] = min(bbox[1], lat)
            bbox[2] = max(bbox[2], lon)
            bbox[3] = max(bbox[3], lat)
            return 1
        used = 0
        for child in value:
            used += _walk_coordinates(child, bbox, limit=limit - used)
            if used >= limit:
                break
        return used
    return 0


def _geojson_bbox(doc: dict, sidecar: Optional[dict] = None) -> Optional[List[float]]:
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    for source in (sidecar, metadata, doc):
        if not isinstance(source, dict):
            continue
        for key in ("bounds_array", "bounds", "bbox"):
            bbox = _bounds_array(source.get(key))
            if bbox:
                return bbox
    features = doc.get("features")
    if not isinstance(features, list) or not features:
        return None
    bbox = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    used = 0
    for feature in features[:32]:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            continue
        coords = geometry.get("coordinates")
        if coords is None:
            continue
        used += _walk_coordinates(coords, bbox, limit=256 - used)
        if used >= 256:
            break
    if used == 0 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        return None
    return bbox


def _manifest_source(doc: dict, sidecar: dict, *, default_label: str, default_license: str) -> dict:
    for source in (sidecar.get("source"), doc.get("metadata", {}).get("source") if isinstance(doc.get("metadata"), dict) else None):
        if isinstance(source, dict):
            payload = _drop_none({
                "label": source.get("label"),
                "license": source.get("license"),
                "id": source.get("id"),
            })
            if payload:
                return _public_json(payload)
        if isinstance(source, str) and source:
            label = "enc" if source == "enc" else source
            license_value = "enc-local" if source == "enc" else default_license
            cell = None
            metadata = doc.get("metadata")
            if isinstance(metadata, dict):
                cell = metadata.get("cell")
            payload = {"label": label, "license": license_value}
            if cell:
                payload["id"] = str(cell)
            return payload
    return {"label": default_label, "license": default_license}


def _iso_from_epoch(epoch: float) -> str:
    return (
        _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _epoch_from_iso(value: Optional[str]) -> Optional[float]:
    """Parse an ISO-8601 UTC timestamp to epoch seconds, or None if unparseable.

    Mirrors the C++ helm_packd epoch_from_iso: accepts "YYYY-MM-DDTHH:MM:SSZ" and
    date-only "YYYY-MM-DD". Returns None rather than fabricating a date so callers
    report freshness as unknown instead of guessing.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().rstrip("Z")
    for length, fmt in ((19, "%Y-%m-%dT%H:%M:%S"), (10, "%Y-%m-%d")):
        try:
            parsed = _dt.datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=_dt.timezone.utc).timestamp()
    return None


def _manifest_freshness(path: str, sidecar: dict) -> dict:
    freshness = sidecar.get("freshness") if isinstance(sidecar.get("freshness"), dict) else {}
    status = freshness.get("status")
    if not status:
        status = "ok" if os.path.isfile(path) else "unknown"
    status = str(status)

    now = _dt.datetime.now(_dt.timezone.utc).timestamp()
    mtime: Optional[float] = None
    if os.path.isfile(path):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
    updated = freshness.get("updated")
    if not updated and mtime is not None:
        updated = _iso_from_epoch(mtime)

    # Age is measured from an explicit sidecar render_date when present, else the file mtime.
    render_date = freshness.get("render_date")
    ref_epoch = _epoch_from_iso(render_date)
    if ref_epoch is None:
        ref_epoch = mtime

    # A layer is "stale" only when its sidecar declares a window (stale_at, or
    # render_date + stale_after_days) and that deadline has passed. We never fabricate it.
    stale_at = freshness.get("stale_at")
    stale_at_epoch = _epoch_from_iso(stale_at)
    stale_after = freshness.get("stale_after_days")
    if (
        stale_at_epoch is None
        and render_date
        and isinstance(stale_after, int)
        and not isinstance(stale_after, bool)  # reject bool/str/float, mirroring C++ rj_int64
        and stale_after > 0
    ):
        rd = _epoch_from_iso(render_date)
        if rd is not None:
            stale_at_epoch = rd + stale_after * 86400
            stale_at = _iso_from_epoch(stale_at_epoch)
    computed_stale = stale_at_epoch is not None and now >= stale_at_epoch
    # An expired window is stale regardless of a non-forced sidecar status (matches C++).
    if computed_stale:
        status = "stale"

    payload: dict = {"status": status}
    if updated:
        payload["updated"] = updated
    if ref_epoch is not None:
        payload["age_days"] = max(0, int((now - ref_epoch) // 86400))
    if stale_at:
        payload["stale_at"] = stale_at
    warning = freshness.get("warning")
    if computed_stale and not warning:
        warning = "Layer render date is older than the configured freshness window."
    if warning:
        payload["warning"] = str(warning)
    return _drop_none(payload)


def _manifest_inspection(sidecar: dict) -> dict:
    inspection = sidecar.get("inspection") if isinstance(sidecar.get("inspection"), dict) else {}
    mode = inspection.get("mode") or "feature-properties"
    return _drop_none(_public_json({"mode": mode, **{k: v for k, v in inspection.items() if k != "mode"}}))


def _layer_from_geojson_file(
    root: str,
    rel_path: str,
    *,
    layer_id: Optional[str] = None,
    title: Optional[str] = None,
    kind: Optional[str] = None,
    tier: Optional[str] = None,
    default_label: str = "owned",
    default_license: str = "private-local",
) -> Optional[dict]:
    abs_path = os.path.join(root, rel_path)
    if not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict):
        return None
    sidecar = _load_sidecar_dict(abs_path)
    stem = os.path.splitext(os.path.basename(rel_path))[0]
    resolved_id = str(sidecar.get("id") or layer_id or _slug(stem))
    resolved_title = str(sidecar.get("title") or title or _humanize_slug(stem))
    resolved_kind = str(sidecar.get("kind") or kind or "geojson")
    resolved_tier = str(sidecar.get("tier") or tier or "overlay")
    if resolved_tier not in VALID_MANIFEST_TIERS:
        resolved_tier = "overlay"
    bbox = _geojson_bbox(doc, sidecar)
    payload = _drop_none({
        "id": resolved_id,
        "title": resolved_title,
        "kind": resolved_kind,
        "format": "geojson",
        "tier": resolved_tier,
        "url": "/user-data/" + rel_path.replace(os.sep, "/"),
        "bbox": bbox,
        "source": _manifest_source(doc, sidecar, default_label=default_label, default_license=default_license),
        "freshness": _manifest_freshness(abs_path, sidecar),
        "inspection": _manifest_inspection(sidecar),
    })
    return payload


def _overlay_geojson_paths(root: str) -> list[str]:
    layers_dir = os.path.join(root, "layers")
    if not os.path.isdir(layers_dir):
        return []
    paths = []
    for name in sorted(os.listdir(layers_dir)):
        if name.startswith(".") or not name.lower().endswith(".geojson"):
            continue
        paths.append(os.path.join("layers", name))
    return paths


def _default_user_data_root() -> str:
    explicit = os.environ.get("HELM_USER_DATA_ROOT")
    if explicit:
        return os.path.expanduser(explicit)
    config = os.environ.get("HELM_CONFIG")
    if config:
        return os.path.join(os.path.expanduser(config), "data")
    return os.path.join(os.path.expanduser("~"), ".helm", "data")


def build_layer_manifest(user_data_root: Optional[str] = None) -> dict:
    """Build helm.layer.manifest.v1 from local user-data GeoJSON overlays."""

    root = os.path.expanduser(user_data_root or _default_user_data_root())
    layers: list[dict] = []
    enc_expected: list[str] = []
    enc_present: list[str] = []
    enc_missing: list[str] = []
    for stem, spec in ENC_GEOJSON_LAYERS.items():
        layer = _layer_from_geojson_file(
            root,
            f"{stem}.geojson",
            layer_id=stem,
            title=spec["title"],
            kind=spec["kind"],
            tier=spec["tier"],
            default_label="enc",
            default_license="enc-local",
        )
        enc_expected.append(stem)
        if layer:
            layers.append(layer)
            enc_present.append(stem)
        else:
            enc_missing.append(stem)
    for rel_path in _overlay_geojson_paths(root):
        layer = _layer_from_geojson_file(root, rel_path)
        if layer:
            layers.append(layer)
    layers.sort(key=lambda item: (str(item.get("tier")), str(item.get("id"))))
    return {
        "schema": LAYER_MANIFEST_SCHEMA,
        "layers": layers,
        # Honest coverage of the expected ENC set so CAT-2 can surface an "enc gap"
        # without inventing placeholder layers. present + missing partition expected.
        "enc": {"expected": enc_expected, "present": enc_present, "missing": enc_missing},
    }


def build_layer_inventory(
    catalog: dict,
    query: Optional[dict] = None,
    *,
    generated_at: Optional[str] = None,
    bundle: Optional[dict] = None,
    places: list[dict] | dict | None = None,
    depth: list[dict] | dict | None = None,
    weather: list[dict] | dict | None = None,
    environmental_bundles: list[dict] | dict | None = None,
    cruiser_layers: list[dict] | dict | None = None,
    s100_inventory: dict | list | None = None,
) -> dict:
    """Build a local maritime inventory from the pack catalog and layer descriptors."""

    query = dict(query or {})
    try:
        bundle = bundle or build_region_bundle(catalog, query, places=places, depth=depth)
    except BundleError as e:
        raise LayerInventoryError(str(e))

    layers = [_layer_from_component(component) for component in bundle.get("components", [])]
    layers.extend(_layer_from_dataset(item, "weather", "weather.model-run") for item in _as_list(weather))
    layers.extend(_layers_from_environmental_bundles(environmental_bundles))
    layers.extend(_layer_from_dataset(item, "cruiser", "cruiser.layer") for item in _as_list(cruiser_layers))
    layers.extend(_layer_from_s100_record(record) for record in _s100_records(s100_inventory))
    layers.sort(key=lambda item: (str(item.get("role")), str(item.get("id"))))

    return {
        "schema": LAYER_INVENTORY_SCHEMA,
        "id": str(_first(query, "inventory_id", _first(query, "id", DEFAULT_INVENTORY_ID))),
        "title": str(_first(query, "title", DEFAULT_TITLE)),
        "generated_at": generated_at or _utcnow_iso(),
        "advisory": True,
        "not_for_navigation": True,
        "source": {
            "kind": "local-boat-server",
            "name": "Helm local maritime layer inventory",
        },
        "request": bundle.get("request", {}),
        "coverage": _inventory_coverage(bundle),
        "bundle": {
            "schema": bundle.get("schema"),
            "id": bundle.get("id"),
            "title": bundle.get("title"),
            "summary": bundle.get("summary", {}),
        },
        "layers": layers,
        "summary": _summary(layers),
    }


def _read_json_source(source: str):
    if source == "-":
        return json.load(sys.stdin)
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(os.path.expanduser(source), "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(payload: dict, output: Optional[str]) -> None:
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output:
        with open(os.path.expanduser(output), "w", encoding="utf-8") as f:
            f.write(data)
        return
    sys.stdout.write(data)


def _load_optional_json(path: Optional[str]):
    return _read_json_source(path) if path else None


def _load_optional_json_many(paths: Optional[list[str]]):
    if not paths:
        return None
    return [_read_json_source(path) for path in paths]


def _query_from_args(args) -> dict:
    query = {
        "inventory_id": [args.inventory_id],
        "title": [args.title],
        "minzoom": [str(args.minzoom)],
        "maxzoom": [str(args.maxzoom)],
        "radius_nm": [str(args.radius_nm)],
        "include_tiles": ["1" if args.include_tiles else "0"],
    }
    if args.bbox:
        query["bbox"] = [args.bbox]
    if args.route:
        query["route"] = [args.route]
    if args.packs:
        query["packs"] = [args.packs]
    return query


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build Helm local maritime layer inventory manifests.")
    ap.add_argument("--catalog", required=True, help="Path/URL to a /catalog JSON document, or '-' for stdin.")
    ap.add_argument("--inventory-id", default=DEFAULT_INVENTORY_ID)
    ap.add_argument("--title", default=DEFAULT_TITLE)
    ap.add_argument("--bbox", help="W,S,E,N corridor; defaults to the union of selected pack bounds.")
    ap.add_argument("--route", help="lon,lat;lon,lat route corridor.")
    ap.add_argument("--radius-nm", type=float, default=2.0)
    ap.add_argument("--minzoom", type=int, default=0)
    ap.add_argument("--maxzoom", type=int, default=12)
    ap.add_argument("--packs", help="Comma-separated pack ids to include.")
    ap.add_argument("--include-tiles", action="store_true", help="Include explicit z/x/y tile URLs in bundle data.")
    ap.add_argument("--places-json", help="Optional public places dataset descriptor JSON.")
    ap.add_argument("--depth-json", help="Optional public depth dataset descriptor JSON.")
    ap.add_argument("--weather-json", help="Optional public weather/model-run descriptor JSON.")
    ap.add_argument("--env-bundle-json", action="append",
                    help="Optional helm.env.bundle.v1 manifest JSON. May be repeated.")
    ap.add_argument("--cruiser-json", help="Optional public cruiser-layer descriptor JSON.")
    ap.add_argument("--s100-json", help="Optional S-100-style layer inventory JSON.")
    ap.add_argument("--output", help="Write JSON here instead of stdout.")
    args = ap.parse_args(argv)

    try:
        payload = build_layer_inventory(
            _read_json_source(args.catalog),
            _query_from_args(args),
            places=_load_optional_json(args.places_json),
            depth=_load_optional_json(args.depth_json),
            weather=_load_optional_json(args.weather_json),
            environmental_bundles=_load_optional_json_many(args.env_bundle_json),
            cruiser_layers=_load_optional_json(args.cruiser_json),
            s100_inventory=_load_optional_json(args.s100_json),
        )
        _write_json(payload, args.output)
        return 0
    except (OSError, json.JSONDecodeError, LayerInventoryError) as e:
        print(f"layer_inventory: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
