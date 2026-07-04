"""Build full-catalog standards tuples from the FORGE-14 source table.

This is the standards-aligned successor to the scale125 semantic tuple scaffold.
It consumes the current `catalog/standard_source_table.json` and
`catalog/s52_s57_s101_crosswalk.json` evidence so FORGE-22/23/24 can work from
the same 824-row source of truth as FORGE-14.

Run:  python -m forge.standards_tuple_alignment
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SOURCE_TABLE = ROOT / "catalog" / "standard_source_table.json"
CROSSWALK = ROOT / "catalog" / "s52_s57_s101_crosswalk.json"
DEFAULT_OUT = ROOT / "catalog" / "standards_tuple_alignment.json"
DEFAULT_MD = ROOT / "catalog" / "standards_tuple_alignment.md"

COLOUR_CODES = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "7": "grey",
    "8": "brown",
    "9": "amber",
    "10": "violet",
    "11": "orange",
    "12": "magenta",
    "13": "pink",
}

BOY_SHAPES = {
    "1": "conical",
    "2": "can",
    "3": "spherical",
    "4": "pillar",
    "5": "spar",
    "6": "barrel",
    "7": "super-buoy",
    "8": "ice-buoy",
}

COLPAT = {
    "1": "horizontal_bands",
    "2": "vertical_stripes",
    "3": "diagonal_stripes",
    "4": "squared",
    "5": "stripes_direction_unknown",
}

CATCAM_TOPMARK = {
    "1": "two_cones_points_up",
    "2": "two_cones_base_to_base",
    "3": "two_cones_points_down",
    "4": "two_cones_point_to_point",
}

BUOY_SHAPE_SET = {"buoy", "can", "conical", "pillar", "spar", "barrel", "spherical", "super-buoy", "ice-buoy"}
BEACON_SHAPE_SET = {"beacon", "tower", "stake"}

S101_FEATURE_OVERRIDES = {
    "ACHPNT": "AnchorBerth",
    "ARCSLN": "ArchipelagicSeaLaneArea",
    "BOYINB": "InstallationBuoy",
    "DAYMAR": "Daymark",
    "DISMAR": "DistanceMark",
    "DWRTCL": "DeepWaterRouteCentreline",
    "DWRTPT": "DeepWaterRoutePart",
    "ICEARE": "IceArea",
    "LNDARE": "LandArea",
    "LNDRGN": "LandRegion",
    "M_COVR": "DataCoverage",
    "RDOSTA": "RadioStation",
    "SNDWAV": "Sandwave",
    "TOWERS": "Landmark",
}

S101_SYMBOL_FEATURE_OVERRIDES = {
    "NEWOBJ 01": "Chart1Feature",
    "NEWOBJ01": "Chart1Feature",
    "SYMINS01": "Chart1Feature",
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _condition_value(conditions: list[str], prefix: str) -> str | None:
    for condition in conditions:
        if condition.startswith(prefix):
            return condition[len(prefix):]
    return None


def _conditions(row: dict[str, Any]) -> list[str]:
    s57 = row.get("s57") or row.get("s57_structure") or {}
    values = s57.get("conditions") or []
    return values if isinstance(values, list) else [str(values)]


def _text(row: dict[str, Any]) -> str:
    s52 = _s52(row)
    s57 = _s57(row)
    semantic = row.get("semantic_brief") or {}
    brief = semantic.get("brief") if isinstance(semantic, dict) else semantic
    return " ".join([
        str(s52.get("asset", "")),
        str(s52.get("description", "")),
        str(s52.get("family", "")),
        str(row.get("name", "")),
        str(brief or ""),
        str(s57.get("object_class", "")),
        " ".join(_conditions(row)),
    ])


def _s52(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("s52"):
        return row["s52"]
    return {
        "asset": row.get("asset"),
        "asset_kind": row.get("kind"),
        "description": row.get("name"),
        "family": row.get("family"),
        "instruction": (row.get("s57_structure") or {}).get("s52_instruction"),
    }


def _s57(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("s57"):
        return row["s57"]
    s57 = row.get("s57_structure") or {}
    return {
        "conditions": s57.get("conditions") or [],
        "lookup_id": s57.get("lookup_id"),
        "object_class": s57.get("object_class"),
        "rcid": s57.get("lookup_rcid") or s57.get("rcid"),
        "s52_instruction": s57.get("s52_instruction"),
    }


def _helm_catalog_id(row: dict[str, Any]) -> str:
    if row.get("helm_catalog_id"):
        return row["helm_catalog_id"]
    s52 = _s52(row)
    s57 = _s57(row)
    return "_".join([
        str(s57.get("object_class") or "UNKNOWN"),
        str(s52.get("asset") or "UNKNOWN"),
        str(s57.get("lookup_id") or "UNKNOWN"),
    ])


def _colours(row: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    raw = _condition_value(_conditions(row), "COLOUR")
    if raw:
        return [
            COLOUR_CODES.get(code.strip(), f"unknown_colour_{code.strip()}")
            for code in raw.split(",")
            if code.strip()
        ], missing
    lowered = _text(row).lower()
    colours = []
    for name in ["red", "green", "yellow", "black", "white", "orange", "magenta"]:
        if re.search(rf"\b{name}\b", lowered):
            colours.append(name)
    if not colours:
        missing.append("colour_sequence")
    return colours, missing


def _pattern(row: dict[str, Any], colours: list[str]) -> tuple[str | None, list[str]]:
    raw = _condition_value(_conditions(row), "COLPAT")
    if raw:
        return COLPAT.get(raw, f"unknown_colpat_{raw}"), []
    lowered = _text(row).lower()
    if len(colours) <= 1:
        return ("solid" if colours else None), ([] if colours else ["colour_pattern"])
    if "vertical" in lowered:
        return "vertical_stripes", []
    if any(token in lowered for token in ["grg", "rgr", "rw", "rg", "red-white", "green-white"]):
        return "horizontal_bands", []
    return None, ["colour_pattern"]


def _shape(row: dict[str, Any]) -> tuple[str | None, list[str]]:
    s52 = _s52(row)
    raw = _condition_value(_conditions(row), "BOYSHP")
    if raw:
        return BOY_SHAPES.get(raw, f"unknown_buoy_shape_{raw}"), []
    lowered = _text(row).lower()
    for needle, shape in [
        ("can", "can"),
        ("conical", "conical"),
        ("cone", "conical"),
        ("spar", "spar"),
        ("barrel", "barrel"),
        ("pillar", "pillar"),
        ("spherical", "spherical"),
        ("buoy", "buoy"),
        ("tower", "tower"),
        ("stake", "stake"),
        ("beacon", "beacon"),
        ("topmark", "topmark"),
        ("wreck", "wreck"),
        ("rock", "rock"),
        ("obstruction", "obstruction"),
        ("line", "line"),
        ("pattern", "pattern"),
        ("area", "area"),
    ]:
        if needle in lowered:
            return shape, []
    kind = s52.get("asset_kind")
    if kind == "line-style":
        return "line", []
    if kind == "pattern":
        return "area_pattern", []
    if kind == "conditional-procedure":
        return "conditional_procedure", []
    return None, ["shape"]


def _geometry(row: dict[str, Any]) -> str:
    kind = _s52(row).get("asset_kind")
    if kind == "line-style":
        return "line"
    if kind == "pattern":
        return "area"
    if kind == "conditional-procedure":
        return "conditional"
    return "point"


def _category(row: dict[str, Any]) -> str:
    obj = _s57(row).get("object_class") or ""
    text = _text(row).lower()
    if obj in {"BOYCAR", "BCNCAR"} or "cardinal" in text:
        return "cardinal_aid"
    if obj in {"BOYLAT", "BCNLAT"} or "lateral" in text:
        return "lateral_aid"
    if obj == "BOYSAW" or "safe water" in text:
        return "safe_water_aid"
    if obj == "BOYISD" or "isolated danger" in text:
        return "isolated_danger_aid"
    if obj == "BOYSPP" or "special" in text:
        return "special_purpose_aid"
    if obj in {"WRECKS", "OBSTRN", "UWTROC"} or any(k in text for k in ["wreck", "rock", "obstruction", "foul"]):
        return "hazard_or_obstruction"
    kind = _s52(row).get("asset_kind")
    if kind == "line-style":
        return "line_style"
    if kind == "pattern":
        return "area_pattern"
    if kind == "conditional-procedure":
        return "conditional_portrayal"
    return "chart_symbol"


def _topmark(row: dict[str, Any]) -> tuple[str | None, list[str]]:
    raw = _condition_value(_conditions(row), "CATCAM")
    if raw:
        return CATCAM_TOPMARK.get(raw, f"unknown_cardinal_topmark_{raw}"), []
    return None, []


def _status_condition(row: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for condition in _conditions(row):
        for prefix, name in [
            ("CATCAM", "category_of_cardinal_mark"),
            ("CATLAM", "category_of_lateral_mark"),
            ("CATSPM", "category_of_special_purpose_mark"),
            ("CATOBS", "category_of_obstruction"),
            ("VALSOU", "value_of_sounding"),
        ]:
            if condition.startswith(prefix):
                result[name] = condition[len(prefix):] or True
    return result


def _feature_type(category: str, shape: str | None, object_class: str | None, symbol_id: str | None = None) -> str | None:
    shape = shape or ""
    object_class = object_class or ""
    symbol_id = symbol_id or ""
    if symbol_id in S101_SYMBOL_FEATURE_OVERRIDES:
        return S101_SYMBOL_FEATURE_OVERRIDES[symbol_id]
    if object_class in S101_FEATURE_OVERRIDES:
        return S101_FEATURE_OVERRIDES[object_class]
    is_buoy = shape in BUOY_SHAPE_SET or object_class.startswith("BOY")
    is_beacon = shape in BEACON_SHAPE_SET or object_class.startswith("BCN")
    if category == "lateral_aid":
        return "BuoyLateral" if is_buoy else "BeaconLateral" if is_beacon else None
    if category == "cardinal_aid":
        return "BuoyCardinal" if is_buoy else "BeaconCardinal" if is_beacon else None
    if category == "safe_water_aid":
        return "BuoySafeWater" if is_buoy else "BeaconSafeWater" if is_beacon else None
    if category == "isolated_danger_aid":
        return "BuoyIsolatedDanger" if is_buoy else "BeaconIsolatedDanger" if is_beacon else None
    if category == "special_purpose_aid":
        return "BuoySpecialPurposeGeneral" if is_buoy else "BeaconSpecialPurposeGeneral" if is_beacon else None
    if category == "hazard_or_obstruction":
        if object_class == "WRECKS" or shape == "wreck":
            return "Wreck"
        if object_class == "UWTROC" or shape == "rock":
            return "UnderwaterAwashRock"
        if object_class == "OBSTRN" or shape == "obstruction":
            return "Obstruction"
    return None


def _attrs(tuple_: dict[str, Any]) -> dict[str, Any]:
    attrs = {}
    shape = tuple_.get("shape")
    if shape in BUOY_SHAPE_SET:
        attrs["buoyShape"] = shape
    if shape in BEACON_SHAPE_SET:
        attrs["beaconShape"] = shape
    if tuple_.get("colour_sequence"):
        attrs["colour"] = tuple_["colour_sequence"]
    if tuple_.get("colour_pattern"):
        attrs["colourPattern"] = tuple_["colour_pattern"]
    if tuple_.get("topmark"):
        attrs["topmark"] = tuple_["topmark"]
    attrs.update(tuple_.get("status_condition") or {})
    return attrs


def _crosswalk_by_id(crosswalk: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["helm_catalog_id"]: row for row in crosswalk["rows"]}


def _mapping_type(feature_type: str | None, crosswalk_row: dict[str, Any] | None, tuple_missing: list[str]) -> str:
    if crosswalk_row and (crosswalk_row.get("s101") or {}).get("exact_symbol_match"):
        return "direct_asset_match"
    if feature_type and not tuple_missing:
        return "rule_derived_equivalent"
    if feature_type:
        return "acceptable_deviation"
    return "unresolved"


def normalize_row(row: dict[str, Any], crosswalk_row: dict[str, Any] | None) -> dict[str, Any]:
    colours, colour_missing = _colours(row)
    pattern, pattern_missing = _pattern(row, colours)
    shape, shape_missing = _shape(row)
    topmark, topmark_missing = _topmark(row)
    missing = sorted(set(colour_missing + pattern_missing + shape_missing + topmark_missing))
    s52 = _s52(row)
    s57 = _s57(row)
    category = _category(row)
    semantic = row.get("semantic_brief") or {}
    if isinstance(semantic, dict):
        semantic_brief = semantic.get("brief")
    else:
        semantic_brief = semantic
    tuple_ = {
        "object_class": s57.get("object_class"),
        "geometry": _geometry(row),
        "s52_symbol_id": s52.get("asset"),
        "shape": shape,
        "colour_sequence": colours,
        "colour_pattern": pattern,
        "category": category,
        "topmark": topmark,
        "status_condition": _status_condition(row),
        "display_mode": "simplified" if "simplified" in _text(row).lower() else "full-chart" if "full-chart" in _text(row).lower() else "unspecified",
        "semantic_brief": semantic_brief or s52.get("description") or s52.get("asset"),
    }
    feature_type = _feature_type(category, shape, s57.get("object_class"), s52.get("asset"))
    mapping = _mapping_type(feature_type, crosswalk_row, missing)
    s101 = (crosswalk_row or {}).get("s101") or {}
    return {
        "helm_catalog_id": _helm_catalog_id(row),
        "source_table_id": row.get("source_table_id"),
        "tuple_status": "complete" if not missing else "partial",
        "missing_data_reasons": missing,
        "semantic_tuple": tuple_,
        "s101_mapping_type": mapping,
        "s101": {
            "feature_type": s101.get("feature_rule") or feature_type,
            "feature_rule_file": s101.get("feature_rule_file") or (f"PortrayalCatalog/Rules/{feature_type}.lua" if feature_type else None),
            "symbol_id": s101.get("symbol_id"),
            "symbol_file": s101.get("symbol_file"),
            "attributes": _attrs(tuple_),
            "license_status": s101.get("license_status", "reference_only_not_bundled"),
            "rule_instruction_refs": s101.get("rule_instruction_refs", []),
        },
        "source_refs": {
            "standard_source_table": "catalog/standard_source_table.json",
            "s52_s57_s101_crosswalk": "catalog/s52_s57_s101_crosswalk.json",
            "s52": s52,
            "s57": s57,
            "reference_providers": row.get("reference_providers") or {},
            "provenance": row.get("provenance") or {},
            "chart1_parity_gate": row.get("chart1_parity_gate") or {},
        },
    }


def build() -> dict[str, Any]:
    source = _read(SOURCE_TABLE)
    crosswalk = _read(CROSSWALK)
    crosswalk_rows = _crosswalk_by_id(crosswalk)
    rows = [normalize_row(row, crosswalk_rows.get(_helm_catalog_id(row))) for row in source["rows"]]
    tuple_counts = Counter(row["tuple_status"] for row in rows)
    mapping_counts = Counter(row["s101_mapping_type"] for row in rows)
    category_counts = Counter(row["semantic_tuple"]["category"] for row in rows)
    return {
        "schema": "helm.forge.standards-tuple-alignment.v1",
        "status": "provisional_standards_alignment_ready",
        "source": {
            "standard_source_table": "catalog/standard_source_table.json",
            "s52_s57_s101_crosswalk": "catalog/s52_s57_s101_crosswalk.json",
        },
        "clean_room_boundary": {
            "references_only": ["S-52/S-57 vocabulary", "S-101 feature/rule references", "Chart No.1 reference metadata"],
            "not_bundled_as_source_artwork": ["OpenCPN GPL rasters", "official IHO SVGs", "IHO catalogue XML", "IHO Lua rules"],
        },
        "coverage": {
            "rows": len(rows),
            "tuple_status_counts": dict(sorted(tuple_counts.items())),
            "s101_mapping_type_counts": dict(sorted(mapping_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Standards Tuple Alignment",
        "",
        f"Status: `{result['status']}`",
        "",
        "Full-catalog semantic tuple and S-101 equivalence scaffold built from",
        "`standard_source_table.json` plus `s52_s57_s101_crosswalk.json`.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- tuple_status_counts: `{coverage['tuple_status_counts']}`",
        f"- s101_mapping_type_counts: `{coverage['s101_mapping_type_counts']}`",
        f"- category_counts: `{coverage['category_counts']}`",
        "",
        "This output is standards-aligned but still provisional until the",
        "FORGE-14 visual approval/hard-pile gate is closed or explicitly waived.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = build()
    _write(args.out, result)
    args.md.write_text(_md(result))
    print(f"standards tuple alignment -> {args.out}")
    print(f"standards tuple summary -> {args.md}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
