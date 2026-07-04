#!/usr/bin/env python3
"""Add semantic S-57/S-52 and provisional S-101 equivalence tables to the audit DB.

This script works from the normalized OpenCPN `chartsymbols.xml` import already
stored in `artifacts/opencpn_s52_portrayal.sqlite`. It mirrors the Icon Forge
FORGE-22/FORGE-23 policy: preserve OpenCPN/S-52 as reference metadata, disable
same-filename S-101 matching, and derive provisional S-101 equivalence from
feature/attribute semantics only.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("artifacts/opencpn_s52_portrayal.sqlite")
DEFAULT_APPROVAL_ROOT = Path(
    os.environ.get("HELM_ICONFORGE_APPROVAL_ROOT", "/private/tmp/helm-forge14/pipeline/iconforge")
)

COLOUR_CODES = {
    1: "white",
    2: "black",
    3: "red",
    4: "green",
    5: "blue",
    6: "yellow",
    7: "grey",
    8: "brown",
    9: "amber",
    10: "violet",
    11: "orange",
    12: "magenta",
    13: "pink",
}

BOY_SHAPES = {
    1: "conical",
    2: "can",
    3: "spherical",
    4: "pillar",
    5: "spar",
    6: "barrel",
    7: "super-buoy",
    8: "ice-buoy",
}

BEACON_SHAPES = {
    1: "stake_pole_perch_post",
    2: "withy",
    3: "tower",
    4: "lattice",
    5: "pile",
    6: "cairn",
    7: "buoyant_beacon",
}

COLPAT = {
    1: "horizontal_bands",
    2: "vertical_stripes",
    3: "diagonal_stripes",
    4: "squared",
    5: "stripes_direction_unknown",
    6: "bordered",
}

CATCAM = {
    1: "north_cardinal",
    2: "east_cardinal",
    3: "south_cardinal",
    4: "west_cardinal",
}

TOPMARK_BY_CATCAM = {
    1: "two_cones_points_up",
    2: "two_cones_base_to_base",
    3: "two_cones_points_down",
    4: "two_cones_point_to_point",
}

TOPSHP_DECODE = {
    1: ("cone. point up", "cone_point_up"),
    2: ("cone. point down", "cone_point_down"),
    3: ("sphere", "sphere"),
    4: ("2 spheres", "two_spheres"),
    5: ("cylinder (can)", "cylinder_can"),
    6: ("board", "board"),
    7: ("x-shape (St. Andrew's cross)", "x_shape_st_andrews_cross"),
    8: ("upright cross (St George's cross)", "upright_cross_st_georges_cross"),
    9: ("cube. point up", "cube_point_up"),
    10: ("2 cones. point to point", "two_cones_point_to_point"),
    11: ("2 cones. base to base", "two_cones_base_to_base"),
    12: ("rhombus", "rhombus"),
    13: ("2 cones (points upward)", "two_cones_points_up"),
    14: ("2 cones (points downward)", "two_cones_points_down"),
    15: ("besom. point up (broom or perch)", "besom_point_up"),
    16: ("besom. point down (broom or perch)", "besom_point_down"),
    17: ("flag", "flag"),
    18: ("sphere over rhombus", "sphere_over_rhombus"),
    19: ("square", "square"),
    20: ("rectangle. horizontal", "rectangle_horizontal"),
    21: ("rectangle. vertical", "rectangle_vertical"),
    22: ("trapezium. up", "trapezium_up"),
    23: ("trapezium. down", "trapezium_down"),
    24: ("triangle point up", "triangle_point_up"),
    25: ("triangle. point down", "triangle_point_down"),
    26: ("circle", "circle"),
    27: ("two upright crosses (one over the other)", "two_upright_crosses_one_over_other"),
    28: ("T-shape", "t_shape"),
    29: ("triangle pointing up over a circle", "triangle_point_up_over_circle"),
    30: ("upright cross over a circle", "upright_cross_over_circle"),
    31: ("rhombus over a circle", "rhombus_over_circle"),
    32: ("circle over a triangle pointing up", "circle_over_triangle_point_up"),
    33: ("other shape (see INFORM)", "other_shape_see_inform"),
}

TOPSHP_OPENCPN_SPECIALS = {
    98: (
        "OpenCPN fallback TOPSHP98 (ZZZZZZ01)",
        "opencpn_fallback_topshp98_zzzzzz01",
    ),
    99: (
        "OpenCPN fallback TOPSHP99 (ZZZZZZ01)",
        "opencpn_fallback_topshp99_zzzzzz01",
    ),
}

ALL_TOPSHP_DECODE = {**TOPSHP_DECODE, **TOPSHP_OPENCPN_SPECIALS}

BUOY_SHAPE_SET = set(BOY_SHAPES.values()) | {"buoy"}
BEACON_SHAPE_SET = set(BEACON_SHAPES.values()) | {"beacon", "stake", "tower", "lattice", "pile", "cairn"}

S52_COMMANDS = {
    "AC": "area_color",
    "AP": "area_pattern",
    "CS": "conditional_procedure",
    "LC": "line_complex",
    "LS": "line_style",
    "SY": "symbol",
    "TE": "text_expression",
    "TX": "text_literal",
}

S101_RESOLUTION_POLICY = (
    "semantic_tuple_only: do not infer S-101 absence from a missing identical "
    "filename; resolve S-101 equivalence through feature/attribute/rule evidence"
)

REFERENCE_POLICY = {
    "posture": "standards-reference-only",
    "bundled_iho_materials": False,
    "bundled_opencpn_materials": False,
    "direct_filename_rule": "disabled",
    "runtime_approval": "not_runtime_approved_pending_FORGE_25",
    "note": (
        "A missing same-named S-101 SVG or rule file is not evidence of no S-101 "
        "equivalent. Equivalence is resolved from semantic tuple plus "
        "feature/attribute/rule evidence."
    ),
}

STANDARDS_REFERENCES = [
    {
        "id": "iho-s65-annex-b-current",
        "title": "IHO S-65 Annex B: S-57 ENC to S-101 Conversion Guidance",
        "url": "https://iho.int/uploads/user/pubs/standards/s-65/S-65%20Annex%20B_Ed%202.0.0_FINAL_Clean.pdf",
        "role": "conversion_guidance",
        "source_boundary": "reference_only_not_bundled",
    },
    {
        "id": "s101-subwg-issue-115",
        "title": "S-101 Portrayal subWG issue 115: Easy guide on S-52/S-101 portrayal differences",
        "url": "https://github.com/S-101-Portrayal-subWG/Working-Documents/issues/115",
        "role": "human_review_shape",
        "source_boundary": "reference_only_not_bundled",
    },
    {
        "id": "iho-s52-s101-allowable-differences",
        "title": "IHO S-52/S-101 allowable portrayal differences paper",
        "url": "https://iho.int/uploads/user/Services%20and%20Standards/S-100WG/S-101PT11/S-101PT11_2023_08.2_EN_Allowable_Differences_Between_S-52_and_S-101_Portrayal_V2.pdf",
        "role": "acceptable_difference_review",
        "source_boundary": "reference_only_not_bundled",
    },
]


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def split_top_level_commands(instruction: str) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    errors: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    for index, char in enumerate(instruction):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                errors.append(f"unmatched_close_paren_at_{index}")
            else:
                depth -= 1
        elif char == ";" and depth == 0:
            item = instruction[start:index].strip()
            if item:
                commands.append(item)
            start = index + 1
    item = instruction[start:].strip()
    if item:
        commands.append(item)
    if quote:
        errors.append("unterminated_quote")
    if depth:
        errors.append(f"unclosed_paren_depth_{depth}")
    return commands, errors


def split_top_level_args(body: str) -> tuple[list[str], list[str]]:
    args: list[str] = []
    errors: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    for index, char in enumerate(body):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                errors.append(f"unmatched_close_paren_in_arg_at_{index}")
            else:
                depth -= 1
        elif char == "," and depth == 0:
            args.append(body[start:index].strip())
            start = index + 1
    args.append(body[start:].strip())
    if quote:
        errors.append("unterminated_quote_in_args")
    if depth:
        errors.append(f"unclosed_nested_paren_depth_{depth}")
    return args, errors


def normalize_arg(raw: str) -> dict[str, Any]:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
        return {"type": "string", "raw": raw, "value": raw[1:-1]}
    try:
        if "." in raw:
            return {"type": "number", "raw": raw, "value": float(raw)}
        return {"type": "number", "raw": raw, "value": int(raw)}
    except ValueError:
        return {"type": "token", "raw": raw, "value": raw}


def parse_command(command_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    name_end = 0
    while name_end < len(command_text) and command_text[name_end].isalpha():
        name_end += 1
    name = command_text[:name_end].upper()
    if not name:
        return None, [f"missing_command_name:{command_text}"]
    if name not in S52_COMMANDS:
        errors.append(f"unknown_command:{name}")
    remainder = command_text[name_end:].strip()
    if not remainder.startswith("(") or not remainder.endswith(")"):
        errors.append(f"malformed_command_parentheses:{name}")
        body = remainder[1:] if remainder.startswith("(") else remainder
    else:
        body = remainder[1:-1]
    raw_args, arg_errors = split_top_level_args(body)
    errors.extend(f"{name}:{error}" for error in arg_errors)
    args = [normalize_arg(arg) for arg in raw_args if arg != ""]
    return (
        {
            "command": name,
            "kind": S52_COMMANDS.get(name, "unknown"),
            "raw": command_text,
            "args": args,
        },
        errors,
    )


def first_arg_value(command: dict[str, Any]) -> str | None:
    return arg_value(command, 0)


def arg_value(command: dict[str, Any], index: int) -> str | None:
    args = command.get("args") or []
    if index >= len(args):
        return None
    value = args[index].get("value")
    return str(value) if value is not None else None


def arg_values(command: dict[str, Any]) -> list[str]:
    values = []
    for arg in command.get("args") or []:
        value = arg.get("value")
        values.append(str(value) if value is not None else "")
    return values


def parse_s52_instruction(instruction: str) -> dict[str, Any]:
    command_texts, errors = split_top_level_commands(instruction or "")
    commands: list[dict[str, Any]] = []
    for command_text in command_texts:
        command, command_errors = parse_command(command_text)
        if command:
            commands.append(command)
        errors.extend(command_errors)

    refs = {
        "symbols": [],
        "line_styles": [],
        "patterns": [],
        "colors": [],
        "conditionals": [],
        "texts": [],
    }
    for command in commands:
        name = command["command"]
        value = first_arg_value(command)
        if not value:
            continue
        if name == "SY":
            refs["symbols"].append(value)
        elif name in {"LS", "LC"}:
            refs["line_styles"].append(value)
            line_colour = arg_value(command, 2)
            if line_colour:
                refs["colors"].append(line_colour)
        elif name == "AP":
            refs["patterns"].append(value)
        elif name == "AC":
            refs["colors"].append(value)
        elif name == "CS":
            refs["conditionals"].append(value.split(";", 1)[0])
        elif name in {"TE", "TX"}:
            args = arg_values(command)
            text_ref = {
                "raw": command["raw"],
                "args": args,
                "template": args[0] if args else None,
                "attribute": args[1] if name == "TE" and len(args) > 1 else args[0] if args else None,
            }
            refs["texts"].append(text_ref)
            colour_arg = arg_value(command, 8 if name == "TE" else 7)
            if colour_arg:
                refs["colors"].append(colour_arg)

    parse_status = "complete" if not errors else "partial"
    return {
        "parse_status": parse_status,
        "command_count": len(commands),
        "command_sequence": [command["command"] for command in commands],
        "commands": commands,
        "resource_refs": refs,
        "parse_errors": errors,
    }


def attr_map(predicates: list[dict[str, Any]]) -> dict[str, list[Any]]:
    attrs: dict[str, list[Any]] = {}
    for predicate in predicates:
        key = str(predicate.get("attribute") or "").upper()
        if not key:
            raw = str(predicate.get("raw") or "")
            key = "".join(ch for ch in raw if ch.isalpha()).upper()
        attrs.setdefault(key, []).append(predicate.get("value"))
    return attrs


def first_scalar(values: list[Any] | None) -> Any:
    if not values:
        return None
    value = values[0]
    if isinstance(value, list):
        return value[0] if value else None
    return value


def as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def attr_numbers(attrs: dict[str, list[Any]], key: str) -> list[int]:
    values = attrs.get(key.upper()) or []
    if not values:
        return []
    value = values[0]
    raw_values = value if isinstance(value, list) else [value]
    numbers = [as_int(item) for item in raw_values]
    return [item for item in numbers if item is not None]


def colour_sequence(attrs: dict[str, list[Any]]) -> list[str]:
    return [COLOUR_CODES.get(code, f"unknown_colour_{code}") for code in attr_numbers(attrs, "COLOUR")]


def colour_pattern(attrs: dict[str, list[Any]], colours: list[str]) -> str | None:
    code = as_int(first_scalar(attrs.get("COLPAT")))
    if code is not None:
        return COLPAT.get(code, f"unknown_colpat_{code}")
    if len(colours) == 1:
        return "solid"
    if len(colours) > 1:
        return "ordered_sequence"
    return None


def normalized_object_class(row: sqlite3.Row) -> str:
    acronym = row["object_acronym"] or ""
    return acronym.upper()


def geometry(row: sqlite3.Row) -> str:
    primitive = row["primitive_type"]
    if primitive == "Point":
        return "point"
    if primitive == "Line":
        return "line"
    return "area"


def display_mode(row: sqlite3.Row) -> str:
    return {
        "Simplified": "simplified",
        "Paper": "full-chart",
        "Lines": "lines",
        "Plain": "plain-boundary",
        "Symbolized": "symbolized-boundary",
    }.get(row["lookup_table"], "unspecified")


def resource_refs(row: sqlite3.Row) -> dict[str, list[str]]:
    return {
        "symbols": json_loads(row["symbol_refs"], []),
        "line_styles": json_loads(row["line_style_refs"], []),
        "patterns": json_loads(row["pattern_refs"], []),
        "colors": json_loads(row["color_refs"], []),
        "conditionals": json_loads(row["conditional_refs"], []),
        "texts": json_loads(row["text_refs"], []),
    }


def primary_asset(refs: dict[str, list[str]]) -> tuple[str | None, str]:
    for key, kind in [
        ("symbols", "symbol"),
        ("line_styles", "line-style"),
        ("patterns", "pattern"),
        ("conditionals", "conditional-procedure"),
    ]:
        if refs[key]:
            return refs[key][0], kind
    if refs["texts"]:
        return None, "text-only"
    return None, "none"


def category(row: sqlite3.Row, object_class: str, refs: dict[str, list[str]], attrs: dict[str, list[Any]]) -> str:
    name = (row["object_name"] or "").lower()
    has_topshp = "TOPSHP" in attrs
    if object_class in {"BOYCAR", "BCNCAR"} or "cardinal" in name:
        return "cardinal_aid"
    if object_class in {"BOYLAT", "BCNLAT"} or "lateral" in name:
        return "lateral_aid"
    if object_class in {"BOYSAW", "BCNSAW"} or "safe water" in name:
        return "safe_water_aid"
    if object_class in {"BOYISD", "BCNISD"} or "isolated danger" in name:
        return "isolated_danger_aid"
    if object_class in {"BOYSPP", "BCNSPP"} or "special purpose" in name:
        return "special_purpose_aid"
    if object_class in {"WRECKS", "OBSTRN", "UWTROC"} or any(word in name for word in ["wreck", "rock", "obstruction"]):
        return "hazard_or_obstruction"
    if object_class == "TOPMAR" or "topmark" in name or "top mark" in name:
        return "topmark"
    if object_class == "DAYMAR" and has_topshp:
        return "daymark"
    if row["primitive_type"] == "Line" or object_class == "$LINES":
        return "line_style"
    if refs["patterns"]:
        return "area_pattern"
    if refs["conditionals"] and not refs["symbols"]:
        return "conditional_portrayal"
    if row["primitive_type"] == "Area":
        return "chart_area"
    return "chart_symbol"


def shape_for_row(row: sqlite3.Row, object_class: str, attrs: dict[str, list[Any]], asset: str | None, cat: str) -> str | None:
    boy_shape = as_int(first_scalar(attrs.get("BOYSHP")))
    if boy_shape is not None:
        return BOY_SHAPES.get(boy_shape, f"unknown_buoy_shape_{boy_shape}")
    bcn_shape = as_int(first_scalar(attrs.get("BCNSHP")))
    if bcn_shape is not None:
        return BEACON_SHAPES.get(bcn_shape, f"unknown_beacon_shape_{bcn_shape}")

    asset_upper = (asset or "").upper()
    if asset_upper.startswith("BOYCAN"):
        return "can"
    if asset_upper.startswith("BOYCON"):
        return "conical"
    if asset_upper.startswith("BOYSPH"):
        return "spherical"
    if asset_upper.startswith("BOYPIL"):
        return "pillar"
    if asset_upper.startswith("BOYBAR"):
        return "barrel"
    if object_class.startswith("BOY") or asset_upper.startswith("BOY"):
        return "buoy"
    if object_class.startswith("BCN") or asset_upper.startswith("BCN"):
        return "beacon"
    if object_class == "WRECKS":
        return "wreck"
    if object_class == "UWTROC":
        return "rock"
    if object_class == "OBSTRN":
        return "obstruction"
    if cat in {"topmark", "daymark"}:
        return "topmark"
    if row["primitive_type"] == "Line":
        return "line"
    if row["primitive_type"] == "Area":
        return "area"
    return None


def topmark_shape(attrs: dict[str, list[Any]], cat: str) -> dict[str, Any]:
    catcam = as_int(first_scalar(attrs.get("CATCAM")))
    if catcam is not None:
        normalized = TOPMARK_BY_CATCAM.get(catcam, CATCAM.get(catcam, f"unknown_cardinal_{catcam}"))
        return {
            "source_attribute": "CATCAM",
            "code": catcam,
            "label": CATCAM.get(catcam),
            "normalized": normalized,
        }
    topshp = as_int(first_scalar(attrs.get("TOPSHP")))
    if topshp is not None:
        label, normalized = ALL_TOPSHP_DECODE.get(
            topshp,
            (f"unknown TOPSHP {topshp}", f"unknown_topshp_{topshp}"),
        )
        return {
            "source_attribute": "TOPSHP",
            "code": topshp,
            "label": label,
            "normalized": normalized,
        }
    if cat in {"topmark", "daymark"}:
        return {
            "source_attribute": None,
            "code": None,
            "label": None,
            "normalized": "topmark_daymark_present_unspecified",
        }
    return {
        "source_attribute": None,
        "code": None,
        "label": None,
        "normalized": None,
    }


def status_condition(attrs: dict[str, list[Any]]) -> dict[str, Any]:
    names = {
        "CATCAM": "category_of_cardinal_mark",
        "CATLAM": "category_of_lateral_mark",
        "CATSPM": "category_of_special_purpose_mark",
        "CATOBS": "category_of_obstruction",
        "CATWRK": "category_of_wreck",
        "VALSOU": "value_of_sounding",
        "BOYSHP": "buoy_shape",
        "BCNSHP": "beacon_shape",
        "TOPSHP": "topmark_shape",
        "COLPAT": "colour_pattern",
        "COLOUR": "colour",
    }
    out: dict[str, Any] = {}
    for key, name in names.items():
        if key in attrs:
            value = attrs[key][0]
            out[name] = value if value is not None else True
    return out


def semantic_brief(row: sqlite3.Row, tuple_fields: dict[str, Any]) -> str:
    parts = [
        tuple_fields["category"].replace("_", " "),
        tuple_fields.get("shape") or "unknown shape",
    ]
    colours = tuple_fields.get("colour_sequence") or []
    if colours:
        parts.append("-".join(colours))
    if tuple_fields.get("colour_pattern"):
        parts.append(str(tuple_fields["colour_pattern"]).replace("_", " "))
    if tuple_fields.get("topmark"):
        parts.append(str(tuple_fields["topmark"]).replace("_", " "))
    name = row["object_name"] or row["object_acronym"]
    return f"{name}: " + ", ".join(parts)


def normalize_row(row: sqlite3.Row) -> dict[str, Any]:
    predicates = json_loads(row["attribute_predicates"], [])
    attrs = attr_map(predicates)
    refs = resource_refs(row)
    asset, asset_kind = primary_asset(refs)
    object_class = normalized_object_class(row)
    cat = category(row, object_class, refs, attrs)
    colours = colour_sequence(attrs)
    pattern = colour_pattern(attrs, colours)
    shp = shape_for_row(row, object_class, attrs, asset, cat)
    mark_shape = topmark_shape(attrs, cat)
    mark = mark_shape["normalized"]

    missing: list[str] = []
    if cat in {"lateral_aid", "safe_water_aid", "isolated_danger_aid", "special_purpose_aid"}:
        if not colours:
            missing.append("colour_sequence")
        if not shp:
            missing.append("shape")
    if cat == "cardinal_aid" and not mark:
        missing.append("topmark_cardinal_direction")
    if cat in {"topmark", "daymark"} and not mark_shape["code"]:
        missing.append("topmark_daymark_shape")
    if cat == "hazard_or_obstruction" and not shp:
        missing.append("shape")

    tuple_fields = {
        "object_class": object_class,
        "original_object_acronym": row["object_acronym"],
        "geometry": geometry(row),
        "s52_symbol_id": asset,
        "s52_asset_kind": asset_kind,
        "shape": shp,
        "colour_sequence": colours,
        "colour_pattern": pattern,
        "category": cat,
        "topmark": mark,
        "topmark_shape_code": mark_shape["code"] if mark_shape["source_attribute"] == "TOPSHP" else None,
        "topmark_shape_label": mark_shape["label"] if mark_shape["source_attribute"] == "TOPSHP" else None,
        "topmark_shape_source_attribute": mark_shape["source_attribute"],
        "topmark_context": cat if cat in {"topmark", "daymark"} else None,
        "status_condition": status_condition(attrs),
        "display_mode": display_mode(row),
    }
    tuple_fields["semantic_brief"] = semantic_brief(row, tuple_fields)

    row_key = f"{row['object_acronym']}_{asset or asset_kind}_{row['lookup_id']}_{row['rcid']}_{row['sequence_order']}"
    return {
        "row_key": row_key,
        "tuple_status": "complete" if not missing else "partial",
        "missing_data_reasons": sorted(set(missing)),
        "semantic_tuple": tuple_fields,
        "s101_resolution_policy": S101_RESOLUTION_POLICY,
        "source_refs": {
            "input": "artifacts/opencpn_s52_portrayal.sqlite:s52_portrayal_lookup",
            "opencpn": {
                "source_git_sha": row["source_git_sha"],
                "source_file": row["source_file"],
                "lookup_row_id": row["id"],
                "lookup_id": row["lookup_id"],
                "rcid": row["rcid"],
                "sequence_order": row["sequence_order"],
                "object_acronym": row["object_acronym"],
                "object_code": row["object_code"],
                "object_name": row["object_name"],
                "primitive_type": row["primitive_type"],
                "lookup_table": row["lookup_table"],
                "display_category": row["display_category"],
                "display_priority": row["display_priority"],
                "radar_priority": row["radar_priority"],
                "attribute_predicates": predicates,
                "instruction": row["instruction"],
                "resource_refs": refs,
                "comment_code": row["comment_code"],
            },
            "forge": {
                "generator": "scripts/augment-opencpn-s52-s101-semantics.py",
                "policy_basis": "FORGE-22/FORGE-23 semantic tuple and S-101 equivalence resolver shape",
            },
        },
    }


def feature_base(tuple_fields: dict[str, Any]) -> str | None:
    cat = tuple_fields.get("category")
    shape = tuple_fields.get("shape") or ""
    object_class = tuple_fields.get("object_class") or ""
    is_buoy = shape in BUOY_SHAPE_SET or object_class.startswith("BOY")
    is_beacon = shape in BEACON_SHAPE_SET or object_class.startswith("BCN")

    if cat == "lateral_aid":
        return "BuoyLateral" if is_buoy else "BeaconLateral" if is_beacon else None
    if cat == "cardinal_aid":
        return "BuoyCardinal" if is_buoy else "BeaconCardinal" if is_beacon else None
    if cat == "safe_water_aid":
        return "BuoySafeWater" if is_buoy else "BeaconSafeWater" if is_beacon else None
    if cat == "isolated_danger_aid":
        return "BuoyIsolatedDanger" if is_buoy else "BeaconIsolatedDanger" if is_beacon else None
    if cat == "special_purpose_aid":
        return "BuoySpecialPurposeGeneral" if is_buoy else "BeaconSpecialPurposeGeneral" if is_beacon else None
    if cat == "hazard_or_obstruction":
        if object_class == "WRECKS" or shape == "wreck":
            return "Wreck"
        if object_class == "UWTROC" or shape == "rock":
            return "UnderwaterAwashRock"
        if object_class == "OBSTRN" or shape == "obstruction":
            return "Obstruction"
    if cat == "topmark":
        return "Topmark"
    if cat == "daymark":
        return "Daymark"
    return None


def s101_attributes(tuple_fields: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    shape = tuple_fields.get("shape")
    if shape in BUOY_SHAPE_SET:
        attrs["buoyShape"] = shape
    elif shape in BEACON_SHAPE_SET:
        attrs["beaconShape"] = shape
    if tuple_fields.get("colour_sequence"):
        attrs["colour"] = tuple_fields["colour_sequence"]
    if tuple_fields.get("colour_pattern"):
        attrs["colourPattern"] = tuple_fields["colour_pattern"]
    if tuple_fields.get("topmark"):
        attrs["topmark"] = tuple_fields["topmark"]
    if tuple_fields.get("topmark_shape_code"):
        attrs["topmarkDaymarkShape"] = str(tuple_fields["topmark_shape_code"])
        attrs["topmarkShapeCode"] = tuple_fields["topmark_shape_code"]
        attrs["topmarkShapeLabel"] = tuple_fields["topmark_shape_label"]
        attrs["topmarkShapeSourceAttribute"] = tuple_fields["topmark_shape_source_attribute"]
    if tuple_fields.get("topmark_context"):
        attrs["topmarkContext"] = tuple_fields["topmark_context"]
    for key, value in (tuple_fields.get("status_condition") or {}).items():
        attrs[f"s57_{key}"] = value
    return attrs


def portrayal_evidence(feature_type: str, tuple_fields: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any]:
    display_mode_value = tuple_fields.get("display_mode") or "unspecified"
    display_profile = {
        "simplified": "s52_simplified_symbol_profile",
        "full-chart": "paper_chart_or_full_symbol_profile",
        "lines": "line_symbol_profile",
        "plain-boundary": "plain_area_boundary_profile",
        "symbolized-boundary": "symbolized_area_boundary_profile",
    }.get(display_mode_value, "unspecified_symbol_profile")
    return {
        "status": "provisional_rule_shape",
        "rule_file": f"{feature_type}.lua",
        "feature_type": feature_type,
        "display_mode": display_mode_value,
        "display_profile": display_profile,
        "attributes_used": sorted(attrs),
        "emitted_point_instructions": [
            f"feature={feature_type}",
            "symbolization derived from feature attributes",
            "palette behavior inherited from renderer palette tokens",
        ],
        "text_label_offsets": "pending_catalog_rule_ingest",
        "viewing_group": "pending_catalog_rule_ingest",
        "palette_behavior": "tokenized; no official IHO SVG or palette asset bundled",
        "source_note": "Provisional rule name only; replace with catalogue-derived rule evidence when official reference ingest is wired.",
        "reference_basis": [ref["id"] for ref in STANDARDS_REFERENCES],
    }


def resolve_equivalence(semantic_row: dict[str, Any]) -> dict[str, Any]:
    tuple_fields = semantic_row["semantic_tuple"]
    cat = tuple_fields.get("category")
    attrs = s101_attributes(tuple_fields)
    missing = list(semantic_row.get("missing_data_reasons") or [])

    if cat in {"line_style", "area_pattern", "conditional_portrayal"}:
        return {
            "row_key": semantic_row["row_key"],
            "s52_symbol_id": tuple_fields.get("s52_symbol_id"),
            "mapping_type": "semantic_only",
            "direct_asset_match": None,
            "s101": {"feature_type": None, "attributes": attrs, "portrayal_evidence": None},
            "unresolved_reasons": [f"{cat}_requires_catalog_rule_ingest"],
            "source_refs": semantic_row["source_refs"],
            "policy": REFERENCE_POLICY,
        }

    feature_type = feature_base(tuple_fields)
    if not feature_type:
        mapping_type = "semantic_only" if cat in {"chart_area", "chart_symbol"} else "unresolved"
        reasons = [f"{cat}_requires_catalog_rule_ingest"] if mapping_type == "semantic_only" else ["no_provisional_feature_rule_for_tuple"]
        return {
            "row_key": semantic_row["row_key"],
            "s52_symbol_id": tuple_fields.get("s52_symbol_id"),
            "mapping_type": mapping_type,
            "direct_asset_match": None,
            "s101": {"feature_type": None, "attributes": attrs, "portrayal_evidence": None},
            "unresolved_reasons": sorted(set(missing + reasons)),
            "source_refs": semantic_row["source_refs"],
            "policy": REFERENCE_POLICY,
        }

    required = []
    if feature_type.startswith("Buoy"):
        required.append("buoyShape")
    if feature_type.startswith("Beacon"):
        required.append("beaconShape")
    if feature_type.startswith(("Buoy", "Beacon")):
        required.append("colour")
    if feature_type in {"Topmark", "Daymark"}:
        required.append("topmarkDaymarkShape")
        if "colour" not in attrs:
            missing.append("missing_attribute_colour")
    for required_attr in required:
        if required_attr not in attrs:
            missing.append(f"missing_attribute_{required_attr}")

    return {
        "row_key": semantic_row["row_key"],
        "s52_symbol_id": tuple_fields.get("s52_symbol_id"),
        "mapping_type": "rule_derived_equivalent" if not missing else "acceptable_deviation",
        "direct_asset_match": {
            "checked": False,
            "reason": "disabled_by_policy_use_rule_equivalence_not_filename_matching",
        },
        "s101": {
            "feature_type": feature_type,
            "attributes": attrs,
            "portrayal_evidence": portrayal_evidence(feature_type, tuple_fields, attrs),
        },
        "unresolved_reasons": sorted(set(missing)),
        "source_refs": semantic_row["source_refs"],
        "policy": REFERENCE_POLICY,
    }


def create_tables(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        DROP VIEW IF EXISTS runtime_symbol_blocker_v1;
        DROP VIEW IF EXISTS runtime_symbol_portrayal_v1;
        DROP VIEW IF EXISTS runtime_symbol_candidate_v1;
        DROP TABLE IF EXISTS runtime_symbol_candidate;
        DROP TABLE IF EXISTS runtime_symbol_gate;
        DROP TABLE IF EXISTS iconforge_s52_lookup_link;
        DROP TABLE IF EXISTS iconforge_topmark_gate_row;
        DROP TABLE IF EXISTS iconforge_s101_resolver_row;
        DROP TABLE IF EXISTS iconforge_standard_source_row;
        DROP TABLE IF EXISTS iconforge_approval_metadata;
        DROP TABLE IF EXISTS s52_s101_import_audit;
        DROP TABLE IF EXISTS s52_instruction_ast;
        DROP TABLE IF EXISTS s101_portrayal_equivalence;
        DROP TABLE IF EXISTS s52_semantic_tuple;
        DROP TABLE IF EXISTS s52_topmark_shape_decode;

        CREATE TABLE s52_topmark_shape_decode (
          source_attribute TEXT NOT NULL DEFAULT 'TOPSHP',
          code INTEGER PRIMARY KEY,
          source_label TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          decode_status TEXT NOT NULL,
          is_standard_s57 INTEGER NOT NULL CHECK (is_standard_s57 IN (0, 1)),
          applies_to TEXT NOT NULL DEFAULT 'TOPMAR,topmar,DAYMAR',
          source_file TEXT NOT NULL,
          source_boundary TEXT NOT NULL DEFAULT 'OpenCPN/S-57 decode metadata'
        );

        CREATE TABLE s52_semantic_tuple (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          s52_lookup_id INTEGER NOT NULL REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          row_key TEXT NOT NULL,
          tuple_generator TEXT NOT NULL DEFAULT 'scripts/augment-opencpn-s52-s101-semantics.py',
          tuple_status TEXT NOT NULL CHECK (tuple_status IN ('complete', 'partial')),
          object_class TEXT NOT NULL,
          original_object_acronym TEXT NOT NULL,
          geometry TEXT NOT NULL CHECK (geometry IN ('point', 'line', 'area')),
          s52_symbol_id TEXT,
          s52_asset_kind TEXT NOT NULL,
          category TEXT NOT NULL,
          shape TEXT,
          colour_sequence TEXT NOT NULL CHECK (json_valid(colour_sequence)),
          colour_pattern TEXT,
          topmark TEXT,
          topmark_shape_code INTEGER REFERENCES s52_topmark_shape_decode(code),
          topmark_shape_label TEXT,
          topmark_shape_source_attribute TEXT,
          topmark_context TEXT CHECK (topmark_context IN ('topmark', 'daymark') OR topmark_context IS NULL),
          status_condition TEXT NOT NULL CHECK (json_valid(status_condition)),
          display_mode TEXT NOT NULL,
          missing_data_reasons TEXT NOT NULL CHECK (json_valid(missing_data_reasons)),
          semantic_tuple TEXT NOT NULL CHECK (json_valid(semantic_tuple)),
          source_refs TEXT NOT NULL CHECK (json_valid(source_refs)),
          s101_resolution_policy TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (s52_lookup_id)
        );

        CREATE TABLE s101_portrayal_equivalence (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          s52_semantic_tuple_id INTEGER NOT NULL REFERENCES s52_semantic_tuple(id) ON DELETE CASCADE,
          s52_lookup_id INTEGER NOT NULL REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          row_key TEXT NOT NULL,
          s52_symbol_id TEXT,
          mapping_type TEXT NOT NULL CHECK (mapping_type IN ('rule_derived_equivalent', 'acceptable_deviation', 'semantic_only', 'unresolved')),
          s101_feature_type TEXT,
          s101_attributes TEXT NOT NULL CHECK (json_valid(s101_attributes)),
          portrayal_evidence TEXT CHECK (portrayal_evidence IS NULL OR json_valid(portrayal_evidence)),
          direct_asset_match TEXT CHECK (direct_asset_match IS NULL OR json_valid(direct_asset_match)),
          unresolved_reasons TEXT NOT NULL CHECK (json_valid(unresolved_reasons)),
          policy TEXT NOT NULL CHECK (json_valid(policy)),
          standards_references TEXT NOT NULL CHECK (json_valid(standards_references)),
          source_refs TEXT NOT NULL CHECK (json_valid(source_refs)),
          source_boundary TEXT NOT NULL DEFAULT 'reference_only_not_bundled',
          runtime_eligible INTEGER NOT NULL DEFAULT 0 CHECK (runtime_eligible IN (0, 1)),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (s52_lookup_id)
        );

        CREATE TABLE s52_instruction_ast (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          s52_lookup_id INTEGER NOT NULL REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          raw_instruction TEXT NOT NULL,
          parser_version TEXT NOT NULL DEFAULT 's52-instruction-ast.v1',
          parse_status TEXT NOT NULL CHECK (parse_status IN ('complete', 'partial')),
          command_count INTEGER NOT NULL,
          command_sequence TEXT NOT NULL CHECK (json_valid(command_sequence)),
          ast TEXT NOT NULL CHECK (json_valid(ast)),
          symbol_refs TEXT NOT NULL CHECK (json_valid(symbol_refs)),
          line_style_refs TEXT NOT NULL CHECK (json_valid(line_style_refs)),
          pattern_refs TEXT NOT NULL CHECK (json_valid(pattern_refs)),
          color_refs TEXT NOT NULL CHECK (json_valid(color_refs)),
          conditional_refs TEXT NOT NULL CHECK (json_valid(conditional_refs)),
          text_refs TEXT NOT NULL CHECK (json_valid(text_refs)),
          parse_errors TEXT NOT NULL CHECK (json_valid(parse_errors)),
          source_boundary TEXT NOT NULL DEFAULT 'OpenCPN S-52 instruction grammar mirror',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (s52_lookup_id)
        );

        CREATE TABLE s52_s101_import_audit (
          check_name TEXT PRIMARY KEY,
          status TEXT NOT NULL CHECK (status IN ('pass', 'fail')),
          expected TEXT NOT NULL,
          actual TEXT NOT NULL,
          detail TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE iconforge_approval_metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          source_root TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE iconforge_standard_source_row (
          asset TEXT PRIMARY KEY,
          object_class TEXT,
          helm_catalog_id TEXT,
          candidate_status TEXT,
          s57_structure TEXT CHECK (s57_structure IS NULL OR json_valid(s57_structure)),
          row_json TEXT NOT NULL CHECK (json_valid(row_json)),
          source_root TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE iconforge_s101_resolver_row (
          asset TEXT PRIMARY KEY,
          helm_catalog_id TEXT,
          object_class TEXT,
          resolver_status TEXT NOT NULL,
          s101_mapping_type TEXT NOT NULL,
          s101_crosswalk_class TEXT,
          basis TEXT,
          runtime_scope TEXT,
          s101_feature_type TEXT,
          s101_rule_file TEXT,
          s101_direct_symbol_id TEXT,
          exact_filename_match INTEGER CHECK (exact_filename_match IN (0, 1)),
          false_filename_gap INTEGER CHECK (false_filename_gap IN (0, 1)),
          s101_attributes TEXT NOT NULL CHECK (json_valid(s101_attributes)),
          portrayal_evidence TEXT NOT NULL CHECK (json_valid(portrayal_evidence)),
          semantic_tuple TEXT CHECK (semantic_tuple IS NULL OR json_valid(semantic_tuple)),
          unresolved_reasons TEXT NOT NULL CHECK (json_valid(unresolved_reasons)),
          raw_json TEXT NOT NULL CHECK (json_valid(raw_json)),
          source_root TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE iconforge_topmark_gate_row (
          asset TEXT PRIMARY KEY,
          gate_status TEXT NOT NULL,
          recommended_status TEXT,
          candidate_status TEXT,
          expected_shape_code INTEGER,
          expected_shape_id TEXT,
          expected_shape_name TEXT,
          primary_s101_symbol_id TEXT,
          primary_s101_description TEXT,
          finding_codes TEXT NOT NULL CHECK (json_valid(finding_codes)),
          raw_json TEXT NOT NULL CHECK (json_valid(raw_json)),
          source_root TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE iconforge_s52_lookup_link (
          asset TEXT NOT NULL,
          s52_lookup_id INTEGER NOT NULL REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          link_reason TEXT NOT NULL,
          PRIMARY KEY (asset, s52_lookup_id, link_reason)
        );

        CREATE TABLE runtime_symbol_gate (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          s52_lookup_id INTEGER NOT NULL REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          gate_name TEXT NOT NULL,
          gate_status TEXT NOT NULL CHECK (gate_status IN ('pass', 'warn', 'pending', 'blocked')),
          severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'blocker')),
          detail TEXT NOT NULL,
          evidence TEXT NOT NULL CHECK (json_valid(evidence)),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (s52_lookup_id, gate_name)
        );

        CREATE TABLE runtime_symbol_candidate (
          s52_lookup_id INTEGER PRIMARY KEY REFERENCES s52_portrayal_lookup(id) ON DELETE CASCADE,
          row_key TEXT NOT NULL,
          object_class TEXT NOT NULL,
          s52_symbol_id TEXT,
          s52_asset_kind TEXT NOT NULL,
          category TEXT NOT NULL,
          geometry TEXT NOT NULL,
          display_mode TEXT NOT NULL,
          candidate_status TEXT NOT NULL CHECK (candidate_status IN ('runtime_eligible', 'review_candidate', 'blocked')),
          runtime_eligible INTEGER NOT NULL CHECK (runtime_eligible IN (0, 1)),
          blocking_gate_count INTEGER NOT NULL,
          pending_gate_count INTEGER NOT NULL,
          warning_gate_count INTEGER NOT NULL,
          gate_summary TEXT NOT NULL CHECK (json_valid(gate_summary)),
          semantic_tuple TEXT NOT NULL CHECK (json_valid(semantic_tuple)),
          s101_feature_type TEXT,
          s101_attributes TEXT NOT NULL CHECK (json_valid(s101_attributes)),
          s52_instruction TEXT NOT NULL,
          source_refs TEXT NOT NULL CHECK (json_valid(source_refs)),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIEW runtime_symbol_candidate_v1 AS
        SELECT
          c.s52_lookup_id,
          c.row_key,
          c.object_class,
          c.s52_symbol_id,
          c.s52_asset_kind,
          c.category,
          c.geometry,
          c.display_mode,
          c.candidate_status,
          c.runtime_eligible,
          c.blocking_gate_count,
          c.pending_gate_count,
          c.warning_gate_count,
          c.gate_summary,
          c.semantic_tuple,
          c.s101_feature_type,
          c.s101_attributes,
          c.s52_instruction,
          c.source_refs
        FROM runtime_symbol_candidate c;

        CREATE VIEW runtime_symbol_portrayal_v1 AS
        SELECT *
        FROM runtime_symbol_candidate_v1
        WHERE runtime_eligible = 1;

        CREATE VIEW runtime_symbol_blocker_v1 AS
        SELECT
          g.s52_lookup_id,
          l.object_acronym,
          c.s52_symbol_id,
          c.category,
          g.gate_name,
          g.gate_status,
          g.severity,
          g.detail,
          g.evidence
        FROM runtime_symbol_gate g
        JOIN s52_portrayal_lookup l ON l.id = g.s52_lookup_id
        JOIN runtime_symbol_candidate c ON c.s52_lookup_id = g.s52_lookup_id
        WHERE g.gate_status IN ('blocked', 'pending');

        CREATE INDEX s52_semantic_tuple_lookup_idx ON s52_semantic_tuple (s52_lookup_id);
        CREATE INDEX s52_semantic_tuple_object_idx ON s52_semantic_tuple (object_class);
        CREATE INDEX s52_semantic_tuple_category_idx ON s52_semantic_tuple (category);
        CREATE INDEX s101_equivalence_lookup_idx ON s101_portrayal_equivalence (s52_lookup_id);
        CREATE INDEX s101_equivalence_mapping_idx ON s101_portrayal_equivalence (mapping_type);
        CREATE INDEX s101_equivalence_feature_idx ON s101_portrayal_equivalence (s101_feature_type);
        CREATE INDEX s52_instruction_ast_lookup_idx ON s52_instruction_ast (s52_lookup_id);
        CREATE INDEX s52_instruction_ast_status_idx ON s52_instruction_ast (parse_status);
        CREATE INDEX iconforge_resolver_status_idx ON iconforge_s101_resolver_row (resolver_status);
        CREATE INDEX iconforge_resolver_crosswalk_idx ON iconforge_s101_resolver_row (s101_crosswalk_class);
        CREATE INDEX iconforge_topmark_gate_status_idx ON iconforge_topmark_gate_row (gate_status);
        CREATE INDEX iconforge_lookup_link_lookup_idx ON iconforge_s52_lookup_link (s52_lookup_id);
        CREATE INDEX runtime_symbol_gate_lookup_idx ON runtime_symbol_gate (s52_lookup_id);
        CREATE INDEX runtime_symbol_gate_name_status_idx ON runtime_symbol_gate (gate_name, gate_status);
        CREATE INDEX runtime_symbol_candidate_status_idx ON runtime_symbol_candidate (candidate_status);
        """
    )
    con.executemany(
        """
        INSERT INTO s52_topmark_shape_decode (
          code, source_label, normalized_name, decode_status, is_standard_s57, source_file
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                code,
                label,
                normalized,
                "standard_s57_attdecode",
                1,
                "data/s57data/attdecode.csv",
            )
            for code, (label, normalized) in sorted(TOPSHP_DECODE.items())
        ]
        + [
            (
                code,
                label,
                normalized,
                "opencpn_special_fallback_not_in_attdecode",
                0,
                "data/s57data/chartsymbols.xml",
            )
            for code, (label, normalized) in sorted(TOPSHP_OPENCPN_SPECIALS.items())
        ],
    )


def load_rows(con: sqlite3.Connection) -> tuple[Counter[str], Counter[str]]:
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM s52_portrayal_lookup ORDER BY id").fetchall()
    semantic_counts: Counter[str] = Counter()
    mapping_counts: Counter[str] = Counter()

    for row in rows:
        semantic = normalize_row(row)
        tuple_fields = semantic["semantic_tuple"]
        con.execute(
            """
            INSERT INTO s52_semantic_tuple (
              s52_lookup_id, row_key, tuple_status, object_class, original_object_acronym,
              geometry, s52_symbol_id, s52_asset_kind, category, shape, colour_sequence,
              colour_pattern, topmark, topmark_shape_code, topmark_shape_label,
              topmark_shape_source_attribute, topmark_context, status_condition,
              display_mode, missing_data_reasons,
              semantic_tuple, source_refs, s101_resolution_policy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                semantic["row_key"],
                semantic["tuple_status"],
                tuple_fields["object_class"],
                tuple_fields["original_object_acronym"],
                tuple_fields["geometry"],
                tuple_fields["s52_symbol_id"],
                tuple_fields["s52_asset_kind"],
                tuple_fields["category"],
                tuple_fields["shape"],
                json_dumps(tuple_fields["colour_sequence"]),
                tuple_fields["colour_pattern"],
                tuple_fields["topmark"],
                tuple_fields["topmark_shape_code"],
                tuple_fields["topmark_shape_label"],
                tuple_fields["topmark_shape_source_attribute"],
                tuple_fields["topmark_context"],
                json_dumps(tuple_fields["status_condition"]),
                tuple_fields["display_mode"],
                json_dumps(semantic["missing_data_reasons"]),
                json_dumps(tuple_fields),
                json_dumps(semantic["source_refs"]),
                semantic["s101_resolution_policy"],
            ),
        )
        semantic_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        equivalence = resolve_equivalence(semantic)
        s101 = equivalence["s101"]
        con.execute(
            """
            INSERT INTO s101_portrayal_equivalence (
              s52_semantic_tuple_id, s52_lookup_id, row_key, s52_symbol_id,
              mapping_type, s101_feature_type, s101_attributes, portrayal_evidence,
              direct_asset_match, unresolved_reasons, policy, standards_references,
              source_refs
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                semantic_id,
                row["id"],
                equivalence["row_key"],
                equivalence["s52_symbol_id"],
                equivalence["mapping_type"],
                s101["feature_type"],
                json_dumps(s101["attributes"]),
                json_dumps(s101["portrayal_evidence"]) if s101["portrayal_evidence"] else None,
                json_dumps(equivalence["direct_asset_match"]) if equivalence["direct_asset_match"] else None,
                json_dumps(equivalence["unresolved_reasons"]),
                json_dumps(equivalence["policy"]),
                json_dumps(STANDARDS_REFERENCES),
                json_dumps(equivalence["source_refs"]),
            ),
        )
        semantic_counts[semantic["tuple_status"]] += 1
        mapping_counts[equivalence["mapping_type"]] += 1

    return semantic_counts, mapping_counts


def load_instruction_ast(con: sqlite3.Connection) -> Counter[str]:
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, instruction FROM s52_portrayal_lookup ORDER BY id").fetchall()
    counts: Counter[str] = Counter()
    for row in rows:
        parsed = parse_s52_instruction(row["instruction"])
        refs = parsed["resource_refs"]
        con.execute(
            """
            INSERT INTO s52_instruction_ast (
              s52_lookup_id, raw_instruction, parse_status, command_count,
              command_sequence, ast, symbol_refs, line_style_refs, pattern_refs,
              color_refs, conditional_refs, text_refs, parse_errors
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["instruction"],
                parsed["parse_status"],
                parsed["command_count"],
                json_dumps(parsed["command_sequence"]),
                json_dumps(parsed["commands"]),
                json_dumps(refs["symbols"]),
                json_dumps(refs["line_styles"]),
                json_dumps(refs["patterns"]),
                json_dumps(refs["colors"]),
                json_dumps(refs["conditionals"]),
                json_dumps(refs["texts"]),
                json_dumps(parsed["parse_errors"]),
            ),
        )
        counts[parsed["parse_status"]] += 1
    return counts


def read_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def source_catalog_id(row: dict[str, Any]) -> str:
    s57 = row.get("s57_structure") or {}
    return "_".join(
        [
            str(s57.get("object_class") or "UNKNOWN"),
            str(row.get("asset") or "UNKNOWN"),
            str(s57.get("lookup_id") or "UNKNOWN"),
        ]
    )


def import_iconforge_approval(con: sqlite3.Connection, approval_root: Path | None) -> dict[str, Any]:
    if approval_root is None:
        return {"loaded": False, "reason": "no_approval_root"}
    root = approval_root.resolve()
    if not root.exists():
        return {"loaded": False, "reason": "approval_root_missing", "source_root": str(root)}

    catalog = root / "catalog"
    proof = root / "proof"
    standard_source = read_json_if_exists(catalog / "standard_source_table.json")
    resolver = read_json_if_exists(catalog / "standards_s101_resolver.json")
    mapping_audit = read_json_if_exists(catalog / "s101_mapping_audit.json")
    alignment_gate = read_json_if_exists(catalog / "standards_alignment_gate.json")
    topmark_gate = read_json_if_exists(catalog / "topmark_contradiction_gate.json")
    manifest = read_json_if_exists(proof / "manifest.json")

    metadata: dict[str, Any] = {
        "loaded": True,
        "source_root": str(root),
        "standard_source_table_path": str(catalog / "standard_source_table.json"),
        "standards_s101_resolver_path": str(catalog / "standards_s101_resolver.json"),
        "s101_mapping_audit_path": str(catalog / "s101_mapping_audit.json"),
        "standards_alignment_gate_path": str(catalog / "standards_alignment_gate.json"),
        "topmark_contradiction_gate_path": str(catalog / "topmark_contradiction_gate.json"),
        "proof_manifest_path": str(proof / "manifest.json"),
    }

    for label, payload in [
        ("standard_source_table", standard_source),
        ("standards_s101_resolver", resolver),
        ("s101_mapping_audit", mapping_audit),
        ("standards_alignment_gate", alignment_gate),
        ("topmark_contradiction_gate", topmark_gate),
        ("proof_manifest", manifest),
    ]:
        metadata[f"{label}_present"] = payload is not None
        if isinstance(payload, dict):
            metadata[f"{label}_status"] = payload.get("status")
            if "coverage" in payload:
                metadata[f"{label}_coverage"] = payload.get("coverage")
            if "summary" in payload:
                metadata[f"{label}_summary"] = payload.get("summary")
            if label == "standards_alignment_gate":
                metadata[f"{label}_review_state"] = payload.get("review_state")
                metadata[f"{label}_topmark_standards"] = payload.get("topmark_standards")
            if label == "proof_manifest":
                metadata[f"{label}_source"] = payload.get("source")
                metadata[f"{label}_approval_workflow"] = payload.get("approval_workflow")

    for key, value in metadata.items():
        con.execute(
            """
            INSERT INTO iconforge_approval_metadata (key, value, source_root)
            VALUES (?, ?, ?)
            """,
            (key, json_dumps(value), str(root)),
        )

    standard_rows = []
    if isinstance(standard_source, dict):
        standard_rows = list(standard_source.get("rows") or [])
        for row in standard_rows:
            asset = row.get("asset")
            if not asset:
                continue
            s57 = row.get("s57_structure") or {}
            con.execute(
                """
                INSERT OR REPLACE INTO iconforge_standard_source_row (
                  asset, object_class, helm_catalog_id, candidate_status,
                  s57_structure, row_json, source_root
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset,
                    s57.get("object_class") or row.get("object_class"),
                    source_catalog_id(row),
                    row.get("candidate_status"),
                    json_dumps(s57),
                    json_dumps(row),
                    str(root),
                ),
            )

    resolver_rows = []
    if isinstance(resolver, dict):
        resolver_rows = list(resolver.get("rows") or [])
        for row in resolver_rows:
            asset = row.get("s52_symbol_id")
            if not asset:
                continue
            evidence = row.get("portrayal_evidence") or {}
            classification = row.get("s101_crosswalk_classification") or {}
            direct = evidence.get("direct_symbol") or {}
            attrs = evidence.get("attributes") or {}
            con.execute(
                """
                INSERT OR REPLACE INTO iconforge_s101_resolver_row (
                  asset, helm_catalog_id, object_class, resolver_status,
                  s101_mapping_type, s101_crosswalk_class, basis, runtime_scope,
                  s101_feature_type, s101_rule_file, s101_direct_symbol_id,
                  exact_filename_match, false_filename_gap, s101_attributes,
                  portrayal_evidence, semantic_tuple, unresolved_reasons,
                  raw_json, source_root
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset,
                    row.get("helm_catalog_id"),
                    row.get("object_class"),
                    row.get("resolver_status"),
                    row.get("s101_mapping_type"),
                    classification.get("class"),
                    classification.get("basis"),
                    classification.get("runtime_scope"),
                    evidence.get("feature_type"),
                    evidence.get("feature_rule_file"),
                    direct.get("symbol_id"),
                    int(bool(row.get("exact_filename_match"))),
                    int(bool(row.get("false_filename_gap"))),
                    json_dumps(attrs),
                    json_dumps(evidence),
                    json_dumps(row.get("semantic_tuple")) if row.get("semantic_tuple") is not None else None,
                    json_dumps(row.get("unresolved_reasons") or []),
                    json_dumps(row),
                    str(root),
                ),
            )

    topmark_rows = []
    if isinstance(topmark_gate, dict):
        topmark_rows = list(topmark_gate.get("rows") or [])
        for row in topmark_rows:
            asset = row.get("asset")
            if not asset:
                continue
            expected = row.get("expected_shape") or {}
            primary = row.get("primary_s101_witness") or {}
            finding_codes = [finding.get("code") for finding in row.get("findings") or [] if finding.get("code")]
            con.execute(
                """
                INSERT OR REPLACE INTO iconforge_topmark_gate_row (
                  asset, gate_status, recommended_status, candidate_status,
                  expected_shape_code, expected_shape_id, expected_shape_name,
                  primary_s101_symbol_id, primary_s101_description,
                  finding_codes, raw_json, source_root
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset,
                    row.get("gate_status"),
                    row.get("recommended_status"),
                    row.get("candidate_status"),
                    expected.get("shape_code"),
                    expected.get("shape_id"),
                    expected.get("shape_name"),
                    primary.get("id"),
                    primary.get("description"),
                    json_dumps(finding_codes),
                    json_dumps(row),
                    str(root),
                ),
            )

    link_specs = [
        ("symbol_refs", "symbol_refs"),
        ("conditional_refs", "conditional_refs"),
        ("pattern_refs", "pattern_refs"),
        ("line_style_refs", "line_style_refs"),
    ]
    for column, reason in link_specs:
        con.execute(
            f"""
            INSERT OR IGNORE INTO iconforge_s52_lookup_link (asset, s52_lookup_id, link_reason)
            SELECT r.asset, l.id, ?
            FROM iconforge_s101_resolver_row r
            JOIN s52_portrayal_lookup l
              ON EXISTS (
                SELECT 1 FROM json_each(l.{column})
                WHERE json_each.value = r.asset
              )
            """,
            (reason,),
        )

    metadata.update(
        {
            "standard_source_rows_loaded": len(standard_rows),
            "resolver_rows_loaded": len(resolver_rows),
            "topmark_gate_rows_loaded": len(topmark_rows),
            "lookup_links_loaded": con.execute("SELECT COUNT(*) FROM iconforge_s52_lookup_link").fetchone()[0],
        }
    )
    for key in [
        "standard_source_rows_loaded",
        "resolver_rows_loaded",
        "topmark_gate_rows_loaded",
        "lookup_links_loaded",
    ]:
        con.execute(
            "INSERT OR REPLACE INTO iconforge_approval_metadata (key, value, source_root) VALUES (?, ?, ?)",
            (key, json_dumps(metadata[key]), str(root)),
        )
    return metadata


def metadata_json(con: sqlite3.Connection, key: str, default: Any) -> Any:
    row = con.execute("SELECT value FROM iconforge_approval_metadata WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    return json.loads(row[0])


def linked_iconforge_rows(con: sqlite3.Connection, s52_lookup_id: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT r.*
        FROM iconforge_s52_lookup_link link
        JOIN iconforge_s101_resolver_row r ON r.asset = link.asset
        WHERE link.s52_lookup_id = ?
        ORDER BY r.asset
        """,
        (s52_lookup_id,),
    ).fetchall()


def linked_topmark_gate_rows(con: sqlite3.Connection, s52_lookup_id: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT DISTINCT g.*
        FROM iconforge_s52_lookup_link link
        JOIN iconforge_topmark_gate_row g ON g.asset = link.asset
        WHERE link.s52_lookup_id = ?
        ORDER BY g.asset
        """,
        (s52_lookup_id,),
    ).fetchall()


def add_gate(
    gates: list[dict[str, Any]],
    name: str,
    status: str,
    detail: str,
    evidence: dict[str, Any],
    severity: str | None = None,
) -> None:
    if severity is None:
        severity = "blocker" if status in {"blocked", "pending"} else "warning" if status == "warn" else "info"
    gates.append(
        {
            "gate_name": name,
            "gate_status": status,
            "severity": severity,
            "detail": detail,
            "evidence": evidence,
        }
    )


def s101_crosswalk_gate(
    con: sqlite3.Connection,
    s52_lookup_id: int,
    equivalence: sqlite3.Row,
) -> tuple[str, str, dict[str, Any], str | None]:
    resolver_rows = linked_iconforge_rows(con, s52_lookup_id)
    if resolver_rows:
        statuses = [row["resolver_status"] for row in resolver_rows]
        classes = [row["s101_crosswalk_class"] for row in resolver_rows if row["s101_crosswalk_class"]]
        mapping_types = [row["s101_mapping_type"] for row in resolver_rows]
        evidence = {
            "source": "iconforge_s101_resolver_row",
            "assets": [row["asset"] for row in resolver_rows],
            "resolver_statuses": statuses,
            "s101_crosswalk_classes": classes,
            "s101_mapping_types": mapping_types,
        }
        if any(status in {"resolved_direct", "resolved_rule", "resolved_rule_catalogue"} for status in statuses):
            return "pass", "S-101 resolver evidence exists for at least one linked asset.", evidence, None
        if any(status == "resolved_with_deviation" for status in statuses):
            return "warn", "S-101 resolver evidence exists, but as an acceptable/documented deviation.", evidence, "warning"
        return "pending", "Linked assets are classified but not S-101 feature-equivalent runtime portrayal.", evidence, None

    mapping_type = equivalence["mapping_type"]
    evidence = {
        "source": "s101_portrayal_equivalence",
        "mapping_type": mapping_type,
        "s101_feature_type": equivalence["s101_feature_type"],
        "unresolved_reasons": json_loads(equivalence["unresolved_reasons"], []),
    }
    if mapping_type == "rule_derived_equivalent":
        return "pending", "Only provisional rule-derived S-101 evidence exists; catalogue resolver evidence is still required.", evidence, None
    if mapping_type == "acceptable_deviation":
        return "pending", "Only provisional acceptable-deviation evidence exists; human/catalogue evidence is still required.", evidence, None
    return "pending", "No runtime-grade S-101 crosswalk evidence exists yet.", evidence, None


def topmark_daymark_gate(
    con: sqlite3.Connection,
    s52_lookup_id: int,
    tuple_row: sqlite3.Row,
) -> tuple[str, str, dict[str, Any], str | None]:
    category_value = tuple_row["category"]
    topmark_code = tuple_row["topmark_shape_code"]
    if category_value not in {"topmark", "daymark"} and topmark_code is None:
        return "pass", "Not a topmark/daymark row.", {"applicable": False}, None

    gate_rows = linked_topmark_gate_rows(con, s52_lookup_id)
    evidence = {
        "applicable": True,
        "category": category_value,
        "topmark_shape_code": topmark_code,
        "topmark": tuple_row["topmark"],
        "linked_gate_assets": [row["asset"] for row in gate_rows],
        "linked_gate_statuses": [row["gate_status"] for row in gate_rows],
    }
    if topmark_code in (98, 99):
        return (
            "blocked",
            "OpenCPN TOPSHP98/TOPSHP99 is a non-standard fallback using ZZZZZZ01 and requires explicit manual mapping.",
            evidence,
            None,
        )
    if any(row["gate_status"] == "manual_review_required" for row in gate_rows):
        evidence["manual_review_assets"] = [
            row["asset"] for row in gate_rows if row["gate_status"] == "manual_review_required"
        ]
        return "blocked", "Icon Forge topmark contradiction gate requires manual review.", evidence, None
    if gate_rows and all(row["gate_status"] == "no_contradiction_detected" for row in gate_rows):
        return "pass", "Topmark/daymark witness gate has no detected contradiction.", evidence, None
    return "pending", "Topmark/daymark row has no final special-pass gate evidence yet.", evidence, None


def build_runtime_candidates(con: sqlite3.Connection) -> Counter[str]:
    manifest_coverage = metadata_json(con, "proof_manifest_coverage", {})
    accepted_count = int(manifest_coverage.get("accepted") or 0)
    manifest_gate_status = manifest_coverage.get("gate_status")
    manifest_blockers = manifest_coverage.get("gate_blockers") or []
    rows = con.execute(
        """
        SELECT
          t.*,
          e.mapping_type,
          e.s101_feature_type,
          e.s101_attributes,
          e.unresolved_reasons,
          ast.parse_status AS instruction_parse_status,
          ast.command_count AS instruction_command_count,
          ast.command_sequence AS instruction_command_sequence,
          ast.parse_errors AS instruction_parse_errors,
          l.instruction,
          l.source_git_sha
        FROM s52_semantic_tuple t
        JOIN s101_portrayal_equivalence e ON e.s52_lookup_id = t.s52_lookup_id
        JOIN s52_instruction_ast ast ON ast.s52_lookup_id = t.s52_lookup_id
        JOIN s52_portrayal_lookup l ON l.id = t.s52_lookup_id
        ORDER BY t.s52_lookup_id
        """
    ).fetchall()

    status_counts: Counter[str] = Counter()
    for row in rows:
        gates: list[dict[str, Any]] = []
        add_gate(
            gates,
            "source_provenance",
            "pass",
            "OpenCPN source repository, commit, file path, and chartsymbols hash are recorded.",
            {"source_git_sha": row["source_git_sha"]},
        )
        add_gate(
            gates,
            "s57_semantic_tuple",
            "pass" if row["tuple_status"] == "complete" else "blocked",
            "S-57 semantic tuple is complete." if row["tuple_status"] == "complete" else "S-57 semantic tuple is partial and blocks runtime promotion.",
            {
                "tuple_status": row["tuple_status"],
                "missing_data_reasons": json_loads(row["missing_data_reasons"], []),
            },
        )
        add_gate(
            gates,
            "s52_instruction_ast",
            "pass" if row["instruction_parse_status"] == "complete" else "blocked",
            "S-52 instruction parsed into normalized AST."
            if row["instruction_parse_status"] == "complete"
            else "S-52 instruction parser found malformed command syntax and blocks runtime promotion.",
            {
                "instruction": row["instruction"],
                "parse_status": row["instruction_parse_status"],
                "command_count": row["instruction_command_count"],
                "command_sequence": json_loads(row["instruction_command_sequence"], []),
                "parse_errors": json_loads(row["instruction_parse_errors"], []),
            },
        )
        s101_status, s101_detail, s101_evidence, s101_severity = s101_crosswalk_gate(con, row["s52_lookup_id"], row)
        add_gate(gates, "s101_crosswalk_evidence", s101_status, s101_detail, s101_evidence, s101_severity)
        top_status, top_detail, top_evidence, top_severity = topmark_daymark_gate(con, row["s52_lookup_id"], row)
        add_gate(gates, "topmark_daymark_special_cases", top_status, top_detail, top_evidence, top_severity)
        add_gate(
            gates,
            "visual_approval",
            "pending",
            "No row is final-approved for runtime export yet; approval package is still review_required.",
            {
                "manifest_gate_status": manifest_gate_status,
                "accepted_count": accepted_count,
                "gate_blockers": manifest_blockers,
                "required_next_step": "row_level_human_signoff_and_golden_visual_diff",
            },
        )

        for gate in gates:
            con.execute(
                """
                INSERT INTO runtime_symbol_gate (
                  s52_lookup_id, gate_name, gate_status, severity, detail, evidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["s52_lookup_id"],
                    gate["gate_name"],
                    gate["gate_status"],
                    gate["severity"],
                    gate["detail"],
                    json_dumps(gate["evidence"]),
                ),
            )

        blocking = sum(1 for gate in gates if gate["gate_status"] == "blocked")
        pending = sum(1 for gate in gates if gate["gate_status"] == "pending")
        warnings = sum(1 for gate in gates if gate["gate_status"] == "warn")
        runtime_eligible = 1 if blocking == 0 and pending == 0 else 0
        candidate_status = "runtime_eligible" if runtime_eligible else "blocked" if blocking else "review_candidate"
        gate_summary = {
            "gate_count": len(gates),
            "blocking_gate_count": blocking,
            "pending_gate_count": pending,
            "warning_gate_count": warnings,
            "gates": [
                {
                    "gate_name": gate["gate_name"],
                    "gate_status": gate["gate_status"],
                    "severity": gate["severity"],
                    "detail": gate["detail"],
                }
                for gate in gates
            ],
        }
        con.execute(
            """
            INSERT INTO runtime_symbol_candidate (
              s52_lookup_id, row_key, object_class, s52_symbol_id, s52_asset_kind,
              category, geometry, display_mode, candidate_status, runtime_eligible,
              blocking_gate_count, pending_gate_count, warning_gate_count,
              gate_summary, semantic_tuple, s101_feature_type, s101_attributes,
              s52_instruction, source_refs
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["s52_lookup_id"],
                row["row_key"],
                row["object_class"],
                row["s52_symbol_id"],
                row["s52_asset_kind"],
                row["category"],
                row["geometry"],
                row["display_mode"],
                candidate_status,
                runtime_eligible,
                blocking,
                pending,
                warnings,
                json_dumps(gate_summary),
                row["semantic_tuple"],
                row["s101_feature_type"],
                row["s101_attributes"],
                row["instruction"],
                row["source_refs"],
            ),
        )
        status_counts[candidate_status] += 1
    return status_counts


def audit(con: sqlite3.Connection) -> None:
    def scalar(query: str) -> Any:
        return con.execute(query).fetchone()[0]

    metadata = dict(con.execute("SELECT key, value FROM s52_source_metadata").fetchall())
    lookup_count = scalar("SELECT COUNT(*) FROM s52_portrayal_lookup")
    semantic_count = scalar("SELECT COUNT(*) FROM s52_semantic_tuple")
    equivalence_count = scalar("SELECT COUNT(*) FROM s101_portrayal_equivalence")
    disabled_count = scalar(
        """
        SELECT COUNT(*) FROM s101_portrayal_equivalence
        WHERE json_extract(policy, '$.direct_filename_rule') = 'disabled'
        """
    )
    bundled_count = scalar(
        """
        SELECT COUNT(*) FROM s101_portrayal_equivalence
        WHERE json_extract(policy, '$.bundled_iho_materials') != 0
           OR json_extract(policy, '$.bundled_opencpn_materials') != 0
        """
    )
    runtime_count = scalar("SELECT COUNT(*) FROM s101_portrayal_equivalence WHERE runtime_eligible = 1")
    boundary_count = scalar(
        "SELECT COUNT(*) FROM s101_portrayal_equivalence WHERE source_boundary = 'reference_only_not_bundled'"
    )
    topmark_decode_count = scalar("SELECT COUNT(*) FROM s52_topmark_shape_decode")
    standard_topmark_decode_count = scalar(
        "SELECT COUNT(*) FROM s52_topmark_shape_decode WHERE is_standard_s57 = 1"
    )
    special_topmark_decode_count = scalar(
        """
        SELECT COUNT(*) FROM s52_topmark_shape_decode
        WHERE decode_status = 'opencpn_special_fallback_not_in_attdecode'
        """
    )
    topshp_lookup_count = scalar(
        """
        SELECT COUNT(*) FROM s52_portrayal_lookup
        WHERE EXISTS (
          SELECT 1 FROM json_each(attribute_predicates)
          WHERE upper(json_extract(json_each.value, '$.attribute')) = 'TOPSHP'
        )
        """
    )
    topshp_semantic_count = scalar(
        """
        SELECT COUNT(*) FROM s52_semantic_tuple
        WHERE topmark_shape_code IS NOT NULL
        """
    )
    unknown_topshp_count = scalar(
        """
        SELECT COUNT(*) FROM s52_semantic_tuple
        WHERE topmark_shape_code IS NOT NULL
          AND topmark LIKE 'unknown_topshp_%'
        """
    )
    special_topshp_count = scalar(
        """
        SELECT COUNT(*) FROM s52_semantic_tuple
        WHERE topmark_shape_code IN (98, 99)
        """
    )
    iconforge_loaded = scalar(
        """
        SELECT COUNT(*) FROM iconforge_approval_metadata
        WHERE key = 'loaded' AND value = 'true'
        """
    )
    iconforge_resolver_rows = scalar("SELECT COUNT(*) FROM iconforge_s101_resolver_row")
    iconforge_source_rows = scalar("SELECT COUNT(*) FROM iconforge_standard_source_row")
    iconforge_topmark_rows = scalar("SELECT COUNT(*) FROM iconforge_topmark_gate_row")
    iconforge_topmark_manual_rows = scalar(
        "SELECT COUNT(*) FROM iconforge_topmark_gate_row WHERE gate_status = 'manual_review_required'"
    )
    iconforge_lookup_links = scalar("SELECT COUNT(*) FROM iconforge_s52_lookup_link")
    runtime_candidate_count = scalar("SELECT COUNT(*) FROM runtime_symbol_candidate")
    runtime_candidate_view_count = scalar("SELECT COUNT(*) FROM runtime_symbol_candidate_v1")
    runtime_portrayal_view_count = scalar("SELECT COUNT(*) FROM runtime_symbol_portrayal_v1")
    runtime_gate_subject_count = scalar("SELECT COUNT(DISTINCT s52_lookup_id) FROM runtime_symbol_gate")
    runtime_gate_count = scalar("SELECT COUNT(*) FROM runtime_symbol_gate")
    runtime_eligible_count = scalar("SELECT COUNT(*) FROM runtime_symbol_candidate WHERE runtime_eligible = 1")
    instruction_ast_count = scalar("SELECT COUNT(*) FROM s52_instruction_ast")
    instruction_complete_count = scalar(
        "SELECT COUNT(*) FROM s52_instruction_ast WHERE parse_status = 'complete'"
    )
    instruction_partial_count = scalar(
        "SELECT COUNT(*) FROM s52_instruction_ast WHERE parse_status = 'partial'"
    )
    visual_pending_count = scalar(
        "SELECT COUNT(*) FROM runtime_symbol_gate WHERE gate_name = 'visual_approval' AND gate_status = 'pending'"
    )
    instruction_pending_count = scalar(
        "SELECT COUNT(*) FROM runtime_symbol_gate WHERE gate_name = 's52_instruction_ast' AND gate_status = 'pending'"
    )
    instruction_gate_pass_count = scalar(
        "SELECT COUNT(*) FROM runtime_symbol_gate WHERE gate_name = 's52_instruction_ast' AND gate_status = 'pass'"
    )
    instruction_gate_blocked_count = scalar(
        "SELECT COUNT(*) FROM runtime_symbol_gate WHERE gate_name = 's52_instruction_ast' AND gate_status = 'blocked'"
    )
    topmark_blocked_count = scalar(
        """
        SELECT COUNT(*)
        FROM runtime_symbol_gate
        WHERE gate_name = 'topmark_daymark_special_cases'
          AND gate_status = 'blocked'
        """
    )
    iconforge_audit_status = con.execute(
        "SELECT value FROM iconforge_approval_metadata WHERE key = 's101_mapping_audit_status'"
    ).fetchone()
    iconforge_manifest_coverage = con.execute(
        "SELECT value FROM iconforge_approval_metadata WHERE key = 'proof_manifest_coverage'"
    ).fetchone()
    iconforge_alignment_review = con.execute(
        "SELECT value FROM iconforge_approval_metadata WHERE key = 'standards_alignment_gate_review_state'"
    ).fetchone()
    audit_status_value = json.loads(iconforge_audit_status[0]) if iconforge_audit_status else None
    manifest_coverage = json.loads(iconforge_manifest_coverage[0]) if iconforge_manifest_coverage else {}
    alignment_review = json.loads(iconforge_alignment_review[0]) if iconforge_alignment_review else {}
    manifest_blockers = manifest_coverage.get("gate_blockers") or []
    alignment_blockers = alignment_review.get("blockers") or []

    checks = [
        (
            "opencpn_source_metadata_present",
            bool(metadata.get("source_repo", "").endswith("OpenCPN.git"))
            and len(metadata.get("source_git_sha", "")) == 40
            and len(metadata.get("chartsymbols_sha256", "")) == 64,
            "OpenCPN repo URL, 40-char git SHA, 64-char chartsymbols hash",
            json_dumps(metadata),
            "source provenance captured before semantic augmentation",
        ),
        (
            "all_lookup_rows_have_semantic_tuple",
            lookup_count == semantic_count,
            str(lookup_count),
            str(semantic_count),
            "every imported OpenCPN lookup row has one semantic tuple",
        ),
        (
            "all_semantic_rows_have_s101_equivalence",
            semantic_count == equivalence_count,
            str(semantic_count),
            str(equivalence_count),
            "every semantic tuple has one S-101 equivalence row",
        ),
        (
            "direct_filename_rule_disabled",
            disabled_count == equivalence_count,
            str(equivalence_count),
            str(disabled_count),
            "same-filename S-101 matching is disabled by policy",
        ),
        (
            "no_bundled_iho_or_opencpn_s101_materials",
            bundled_count == 0,
            "0",
            str(bundled_count),
            "S-101 references are reference-only and not bundled",
        ),
        (
            "reference_only_source_boundary",
            boundary_count == equivalence_count,
            str(equivalence_count),
            str(boundary_count),
            "all equivalence rows are marked reference_only_not_bundled",
        ),
        (
            "no_runtime_eligible_rows_until_forge_25",
            runtime_count == 0,
            "0",
            str(runtime_count),
            "runtime export remains blocked pending FORGE-25",
        ),
        (
            "topshp_standard_decode_table_complete",
            standard_topmark_decode_count == len(TOPSHP_DECODE),
            str(len(TOPSHP_DECODE)),
            str(standard_topmark_decode_count),
            "all standard OpenCPN data/s57data/attdecode.csv TOPSHP values are loaded",
        ),
        (
            "topshp_opencpn_special_fallbacks_loaded",
            special_topmark_decode_count == len(TOPSHP_OPENCPN_SPECIALS),
            str(len(TOPSHP_OPENCPN_SPECIALS)),
            str(special_topmark_decode_count),
            "OpenCPN chartsymbols.xml TOPSHP98/TOPSHP99 fallback rows are explicit non-standard decode entries",
        ),
        (
            "topshp_rows_have_semantic_shape_code",
            topshp_lookup_count == topshp_semantic_count,
            str(topshp_lookup_count),
            str(topshp_semantic_count),
            "every lookup row with TOPSHP has a decoded topmark/daymark shape code",
        ),
        (
            "topshp_no_unknown_decode_values",
            unknown_topshp_count == 0,
            "0",
            str(unknown_topshp_count),
            "TOPSHP values in the OpenCPN lookup rows all decode to known labels",
        ),
        (
            "topshp_special_fallback_rows_flagged",
            special_topshp_count == 2,
            "2",
            str(special_topshp_count),
            "OpenCPN TOPSHP98/TOPSHP99 ZZZZZZ01 fallback lookup rows are preserved as non-standard special cases",
        ),
        (
            "iconforge_approval_artifacts_loaded",
            iconforge_loaded == 1,
            "approval root present with loaded=true",
            str(bool(iconforge_loaded)),
            "current approval-server mapping artifacts were imported as evidence tables",
        ),
        (
            "iconforge_source_and_resolver_rows_match",
            iconforge_resolver_rows == iconforge_source_rows and iconforge_resolver_rows > 0,
            str(iconforge_source_rows),
            str(iconforge_resolver_rows),
            "approval standard source rows reconcile with S-101 resolver rows",
        ),
        (
            "iconforge_mapping_audit_pass_preserved",
            audit_status_value == "pass",
            "pass",
            str(audit_status_value),
            "Forge S-101 mapping audit status is recorded; this is evidence accounting, not runtime approval",
        ),
        (
            "iconforge_manifest_gate_still_review_required",
            manifest_coverage.get("gate_status") == "review_required"
            and "topmark_unresolved_rows_not_empty" in manifest_blockers,
            "review_required with topmark_unresolved_rows_not_empty",
            json_dumps({"gate_status": manifest_coverage.get("gate_status"), "gate_blockers": manifest_blockers}),
            "the approval package gate remains blocked for topmark review and is not canonical runtime approval",
        ),
        (
            "iconforge_topmark_contradiction_gate_preserved",
            iconforge_topmark_rows > 0
            and iconforge_topmark_manual_rows > 0
            and "topmark_unresolved_rows_not_empty" in alignment_blockers,
            "topmark rows plus manual-review blockers",
            json_dumps(
                {
                    "topmark_rows": iconforge_topmark_rows,
                    "manual_review_required": iconforge_topmark_manual_rows,
                    "alignment_blockers": alignment_blockers,
                }
            ),
            "topmark/TOPSHP witness contradictions are imported as manual-review evidence",
        ),
        (
            "iconforge_rows_link_back_to_opencpn_when_possible",
            iconforge_lookup_links > 0,
            ">0",
            str(iconforge_lookup_links),
            "resolver assets with matching OpenCPN lookup resource refs are linked",
        ),
        (
            "runtime_candidates_cover_all_lookup_rows",
            runtime_candidate_count == lookup_count and runtime_candidate_view_count == lookup_count,
            str(lookup_count),
            json_dumps({"table": runtime_candidate_count, "view": runtime_candidate_view_count}),
            "runtime_symbol_candidate_v1 is the broad review/browse surface over every OpenCPN lookup row",
        ),
        (
            "runtime_gates_cover_all_lookup_rows",
            runtime_gate_subject_count == lookup_count and runtime_gate_count >= lookup_count * 6,
            f"{lookup_count} subjects and at least {lookup_count * 6} gates",
            json_dumps({"subjects": runtime_gate_subject_count, "gates": runtime_gate_count}),
            "every lookup row has row-level provenance, semantic, S-52, S-101, topmark, and visual gates",
        ),
        (
            "s52_instruction_ast_covers_all_lookup_rows",
            instruction_ast_count == lookup_count,
            str(lookup_count),
            str(instruction_ast_count),
            "every OpenCPN lookup row has a parsed S-52 instruction AST row",
        ),
        (
            "s52_instruction_ast_gate_reflects_parser_status",
            instruction_pending_count == 0
            and instruction_gate_pass_count == instruction_complete_count
            and instruction_gate_blocked_count == instruction_partial_count,
            "no pending AST gates; pass=complete and blocked=partial",
            json_dumps(
                {
                    "complete": instruction_complete_count,
                    "partial": instruction_partial_count,
                    "gate_pass": instruction_gate_pass_count,
                    "gate_blocked": instruction_gate_blocked_count,
                    "gate_pending": instruction_pending_count,
                }
            ),
            "runtime S-52 instruction gate is driven by parser output, not a hardcoded pending state",
        ),
        (
            "s52_instruction_ast_partial_rows_visible",
            instruction_partial_count > 0 and instruction_gate_blocked_count == instruction_partial_count,
            ">0 visible parser blockers",
            str(instruction_partial_count),
            "malformed/edge S-52 instruction rows remain visible blockers instead of silent runtime assumptions",
        ),
        (
            "strict_runtime_view_empty_until_approved",
            runtime_portrayal_view_count == 0 and runtime_eligible_count == 0,
            "0",
            json_dumps({"runtime_symbol_portrayal_v1": runtime_portrayal_view_count, "runtime_eligible": runtime_eligible_count}),
            "runtime_symbol_portrayal_v1 must remain empty until parser, mapping, visual, and edge-case gates pass",
        ),
        (
            "visual_approval_blocks_all_runtime_rows",
            visual_pending_count == lookup_count,
            str(lookup_count),
            str(visual_pending_count),
            "no row has final visual/golden approval imported yet",
        ),
        (
            "s52_instruction_ast_has_no_pending_rows",
            instruction_pending_count == 0,
            "0",
            str(instruction_pending_count),
            "S-52 instruction AST gate now passes or blocks based on parser output",
        ),
        (
            "topmark_manual_review_blocks_are_visible",
            topmark_blocked_count > 0,
            ">0",
            str(topmark_blocked_count),
            "TOPSHP/topmark/daymark special cases that need manual review are visible runtime blockers",
        ),
    ]

    for name, ok, expected, actual, detail in checks:
        con.execute(
            """
            INSERT INTO s52_s101_import_audit (check_name, status, expected, actual, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, "pass" if ok else "fail", expected, actual, detail),
        )


def update_metadata(
    con: sqlite3.Connection,
    semantic_counts: Counter[str],
    mapping_counts: Counter[str],
    instruction_counts: Counter[str],
    runtime_counts: Counter[str],
) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    values = {
        "semantic_s101_generator": "scripts/augment-opencpn-s52-s101-semantics.py",
        "semantic_s101_generated_at": generated_at,
        "semantic_s101_scope": "provisional_reference_only_not_runtime_approved",
        "semantic_tuple_status_counts": json_dumps(dict(sorted(semantic_counts.items()))),
        "s101_mapping_type_counts": json_dumps(dict(sorted(mapping_counts.items()))),
        "s52_instruction_ast_status_counts": json_dumps(dict(sorted(instruction_counts.items()))),
        "s101_reference_policy": json_dumps(REFERENCE_POLICY),
        "s101_standards_references": json_dumps(STANDARDS_REFERENCES),
        "runtime_candidate_status_counts": json_dumps(dict(sorted(runtime_counts.items()))),
        "runtime_contract": "runtime_symbol_candidate_v1 is browse/review evidence; runtime_symbol_portrayal_v1 is strict serving surface",
        "topshp_decode_source": "OpenCPN data/s57data/attdecode.csv TOPSHP row",
        "topshp_standard_decode_count": str(len(TOPSHP_DECODE)),
        "topshp_opencpn_special_fallback_count": str(len(TOPSHP_OPENCPN_SPECIALS)),
        "topshp_total_decode_count": str(len(ALL_TOPSHP_DECODE)),
    }
    for key, value in values.items():
        con.execute(
            "INSERT OR REPLACE INTO s52_source_metadata (key, value) VALUES (?, ?)",
            (key, value),
        )


def augment(db_path: Path, approval_root: Path | None) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        create_tables(con)
        semantic_counts, mapping_counts = load_rows(con)
        instruction_counts = load_instruction_ast(con)
        import_metadata = import_iconforge_approval(con, approval_root)
        runtime_counts = build_runtime_candidates(con)
        update_metadata(con, semantic_counts, mapping_counts, instruction_counts, runtime_counts)
        con.execute(
            "INSERT OR REPLACE INTO s52_source_metadata (key, value) VALUES (?, ?)",
            ("iconforge_approval_import", json_dumps(import_metadata)),
        )
        audit(con)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--approval-root",
        type=Path,
        default=DEFAULT_APPROVAL_ROOT,
        help="Icon Forge approval-server worktree root to import as evidence tables.",
    )
    args = parser.parse_args()
    augment(args.db, args.approval_root)
    print(f"augmented {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
