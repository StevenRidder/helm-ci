"""Build the FORGE-28 Helm symbol recipe contract.

The recipe contract is the small vocabulary between semantic evidence and
rendering. It does not approve runtime export; it only states what a backend
has resolved for shape family, colors, pattern, style, and palette.

Run:
  python3 -m forge.symbol_recipe_contract
"""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import style_contract


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

DEFAULT_OUT = CATALOG / "helm_symbol_recipe_contract.json"
DEFAULT_MD = CATALOG / "helm_symbol_recipe_contract.md"

RECIPE_VERSION = "helm_symbol_recipe_v1"
PALETTE_VERSION = "helm_palette_v1"
PATTERN_VERSION = "helm_pattern_v1"
SHAPE_FAMILY_VERSION = "helm_shape_family_v1"
STYLE_VERSION = "helm_style_contract_v1"

STYLE_DEFAULTS = {
    "viewbox": "0 0 64 64",
    "nominal_px": 64,
    "padding_px": 6,
    "optical_center": [32, 32],
    "stroke_width": style_contract.OPENBRIDGE_STROKE_WIDTH,
    "linecap": "round",
    "linejoin": "round",
    "outline_policy": "thin_black_outside_edge_for_chart_aids",
    "small_size_rule": "preserve silhouette, color order, and black edge before decorative detail",
}

COLOUR_TOKEN_ALIASES = {
    "grey": "gray",
    "ink": "black",
    "CHBLK": "black",
    "CHWHT": "white",
    "CHRED": "red",
    "CHGRN": "green",
    "CHYLW": "yellow",
    "CHMGD": "magenta",
    "CHMGF": "magenta",
    "CHBRN": "brown",
    "CHGRD": "gray",
    "CHGRF": "gray",
    "DEPDW": "blue",
    "DEPVS": "blue",
    "LANDA": "brown",
    "LANDF": "brown",
    "TRFCD": "magenta",
    "CSTLN": "gray",
    "NODTA": "blue",
}

SUPPORTED_COLOUR_TOKENS = set(style_contract.OPENBRIDGE_NAV_PALETTES["day"])

PATTERN_ALIASES = {
    "solid": "solid",
    "horizontal_bands": "horizontal_bands",
    "vertical_stripes": "vertical_stripes",
    "diagonal_stripes": "diagonal_stripes",
    "squared": "squared",
    "SOLD": "line_solid",
    "DASH": "line_dash",
    "DOTT": "line_dot",
}

PATTERN_DEFINITIONS = {
    "solid": {"requires_order": False, "orientation": None},
    "ordered_sequence": {"requires_order": True, "orientation": "vertical_sequence"},
    "horizontal_bands": {"requires_order": True, "orientation": "horizontal"},
    "vertical_stripes": {"requires_order": True, "orientation": "vertical"},
    "diagonal_stripes": {"requires_order": True, "orientation": "diagonal"},
    "squared": {"requires_order": True, "orientation": "checker"},
    "notice_pictogram": {"requires_order": True, "orientation": "sign_box"},
    "line_solid": {"requires_order": False, "orientation": "line"},
    "line_dash": {"requires_order": False, "orientation": "line"},
    "line_dot": {"requires_order": False, "orientation": "line"},
}

SHAPE_FAMILY_DEFINITIONS = {
    "buoy_can": {"kind": "point", "physical": True},
    "buoy_cone": {"kind": "point", "physical": True},
    "buoy_pillar": {"kind": "point", "physical": True},
    "buoy_spar": {"kind": "point", "physical": True},
    "buoy_sphere": {"kind": "point", "physical": True},
    "buoy_barrel": {"kind": "point", "physical": True},
    "buoy_super": {"kind": "point", "physical": True},
    "buoy_generic": {"kind": "point", "physical": True},
    "beacon_general": {"kind": "point", "physical": True},
    "beacon_stake": {"kind": "point", "physical": True},
    "beacon_tower": {"kind": "point", "physical": True},
    "tower_lighthouse": {"kind": "point", "physical": True},
    "daymark_panel": {"kind": "point", "physical": True},
    "topmark_standard": {"kind": "point", "physical": True},
    "notice_mark": {"kind": "point", "physical": False},
    "anchoring_symbol": {"kind": "point", "physical": False},
    "isolated_danger_mark": {"kind": "point", "physical": False},
    "wreck_symbol": {"kind": "point", "physical": False},
    "rock_symbol": {"kind": "point", "physical": False},
    "area_pattern": {"kind": "area", "physical": False},
    "line_style": {"kind": "line", "physical": False},
    "conditional_portrayal": {"kind": "conditional", "physical": False},
    "ais_target": {"kind": "runtime", "physical": False},
    "generic_chart_symbol": {"kind": "point", "physical": False},
}


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _canon_colour_token(token: Any) -> str | None:
    if token is None:
        return None
    raw = str(token).strip().strip("'")
    if not raw:
        return None
    return COLOUR_TOKEN_ALIASES.get(raw, COLOUR_TOKEN_ALIASES.get(raw.upper(), raw.lower()))


def _colour_tokens(row: dict[str, Any]) -> tuple[list[str], list[str], str]:
    reasons: list[str] = []
    source = "missing"
    s57_tuple = row.get("s57_attribute_tuple") or {}
    s101_attrs = row.get("s101_attributes") or {}
    ast = row.get("s52_instruction_ast") or {}

    raw_tokens = s57_tuple.get("colour_sequence") or []
    if raw_tokens:
        source = "s57_attribute_tuple.colour_sequence"
        description = str(row.get("s57_description") or "").lower()
        if raw_tokens == ["unknown_colour_2.3.2"] and "black, red, black" in description:
            raw_tokens = ["black", "red", "black"]
            source = "s57_description.required_colours_repair"
    elif s101_attrs.get("colour"):
        raw_tokens = s101_attrs.get("colour") or []
        source = "s101_attributes.colour"
    elif ast.get("area_colours"):
        raw_tokens = ast.get("area_colours") or []
        source = "s52_instruction_ast.area_colours"
    else:
        line_styles = ast.get("line_styles") or []
        raw_tokens = [
            item.get("colour_token")
            for item in line_styles
            if item.get("colour_token")
        ]
        if raw_tokens:
            source = "s52_instruction_ast.line_styles"

    tokens: list[str] = []
    for raw in raw_tokens:
        token = _canon_colour_token(raw)
        if not token:
            continue
        if token not in SUPPORTED_COLOUR_TOKENS:
            reasons.append(f"unsupported_color_token:{raw}")
        else:
            tokens.append(token)

    # Color order and repetition are safety-relevant for bands such as
    # black-red-black isolated-danger marks. Do not deduplicate.
    return tokens, sorted(set(reasons)), source


def _shape_family(row: dict[str, Any]) -> tuple[str | None, list[str]]:
    reasons: list[str] = []
    symbol_id = str(row.get("symbol_id") or "")
    s57_tuple = row.get("s57_attribute_tuple") or {}
    s57_object = row.get("s57_object") or {}
    shape = str(s57_tuple.get("shape") or "").lower()
    category = str(s57_tuple.get("category") or row.get("kind") or "").lower()
    object_class = str(s57_object.get("object_class") or "").upper()

    if symbol_id.startswith("AIS"):
        return "ais_target", reasons
    if category == "isolated_danger_aid" or symbol_id.startswith("ISODGR"):
        return "isolated_danger_mark", reasons
    if category == "line_style" or object_class == "$LINES":
        return "line_style", reasons
    if category == "area_pattern" or object_class == "$AREAS":
        return "area_pattern", reasons
    if category == "conditional_portrayal" or shape == "conditional_procedure":
        return "conditional_portrayal", reasons
    if object_class == "NOTMRK" or str(s57_object.get("object_class") or "") == "notmrk":
        return "notice_mark", reasons
    if symbol_id.startswith(("ACH", "ANK")):
        return "anchoring_symbol", reasons
    if symbol_id.startswith("TOPMA") or object_class == "TOPMAR":
        return "topmark_standard", reasons
    if symbol_id.startswith(("TOPSHP", "TOPSHQ")) or object_class == "DAYMAR":
        return "daymark_panel", reasons
    if object_class == "BCNSTK" or shape == "stake":
        return "beacon_stake", reasons
    if object_class in {"BCNTOW"}:
        return "beacon_tower", reasons
    if shape == "tower" or object_class in {"TOWERS", "LNDMRK"}:
        return "tower_lighthouse", reasons
    if shape == "beacon" or object_class.startswith("BCN"):
        return "beacon_general", reasons

    shape_map = {
        "can": "buoy_can",
        "conical": "buoy_cone",
        "cone": "buoy_cone",
        "pillar": "buoy_pillar",
        "spar": "buoy_spar",
        "spherical": "buoy_sphere",
        "sphere": "buoy_sphere",
        "barrel": "buoy_barrel",
        "super-buoy": "buoy_super",
        "buoy": "buoy_generic",
        "wreck": "wreck_symbol",
        "rock": "rock_symbol",
        "area": "area_pattern",
        "line": "line_style",
    }
    if shape in shape_map:
        return shape_map[shape], reasons
    if category == "hazard_or_obstruction":
        return "generic_chart_symbol", reasons
    if category == "chart_symbol":
        return "generic_chart_symbol", ["shape_family_generic_chart_symbol"]
    return None, ["shape_family_missing"]


def _pattern_token(row: dict[str, Any], colour_tokens: list[str], shape_family: str | None) -> tuple[str | None, list[str], str]:
    reasons: list[str] = []
    source = "derived"
    s57_tuple = row.get("s57_attribute_tuple") or {}
    ast = row.get("s52_instruction_ast") or {}
    raw_pattern = s57_tuple.get("colour_pattern")

    if shape_family == "notice_mark":
        return "notice_pictogram", reasons, "shape_family.notice_mark"
    if shape_family == "line_style":
        line_styles = ast.get("line_styles") or []
        if line_styles and line_styles[0].get("pattern"):
            raw_pattern = line_styles[0]["pattern"]
            source = "s52_instruction_ast.line_styles.pattern"

    if raw_pattern:
        if str(raw_pattern).lower() == "solid" and len(colour_tokens) > 1:
            return "horizontal_bands", reasons, "derived_multi_colour_sequence_overrides_solid"
        pattern = PATTERN_ALIASES.get(str(raw_pattern), PATTERN_ALIASES.get(str(raw_pattern).lower()))
        if pattern:
            return pattern, reasons, source if source != "derived" else "s57_attribute_tuple.colour_pattern"
        return None, [f"unsupported_pattern_token:{raw_pattern}"], "s57_attribute_tuple.colour_pattern"

    if len(colour_tokens) > 1:
        if shape_family and shape_family.startswith(("buoy_", "beacon_")):
            return "horizontal_bands", reasons, "derived_multi_colour_buoy_or_beacon"
        return "ordered_sequence", reasons, "derived_from_colour_sequence"
    if colour_tokens:
        return "solid", reasons, "default_single_colour"
    return None, ["pattern_missing"], "missing"


def recipe_for_row(row: dict[str, Any]) -> dict[str, Any]:
    shape_family, shape_reasons = _shape_family(row)
    colour_tokens, colour_reasons, colour_source = _colour_tokens(row)
    pattern_token, pattern_reasons, pattern_source = _pattern_token(row, colour_tokens, shape_family)
    reasons = sorted(set(shape_reasons + colour_reasons + pattern_reasons))

    if not shape_family:
        status = "shape_family_missing"
    elif any(reason.startswith("unsupported_") for reason in reasons):
        status = "recipe_missing"
    elif not colour_tokens:
        status = "manual_exception_required"
        reasons.append("colour_sequence_missing_or_reference_defined")
    elif not pattern_token:
        status = "recipe_missing"
    else:
        status = "recipe_ready"

    if row.get("s101_crosswalk_class") == "non_s101_runtime_construct":
        reasons.append("non_s101_runtime_construct_runtime_profile_required")
    elif row.get("s101_crosswalk_class") == "non_s101_or_inland_extension":
        reasons.append("non_s101_or_extension_profile_required")

    recipe = {
        "version": RECIPE_VERSION,
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "shape_family": shape_family,
        "shape_family_version": SHAPE_FAMILY_VERSION,
        "color_tokens": colour_tokens,
        "color_source": colour_source,
        "pattern_token": pattern_token,
        "pattern_version": PATTERN_VERSION,
        "pattern_source": pattern_source,
        "palette_version": PALETTE_VERSION,
        "style_version": STYLE_VERSION,
        "style_contract_id": style_contract.OPENBRIDGE_STYLE_ID,
        "render_defaults": dict(STYLE_DEFAULTS),
        "backend_resolved": True,
        "browser_business_logic_allowed": False,
        "runtime_export_allowed": False,
        "source_fields": {
            "s57_attribute_tuple": "s57_attribute_tuple",
            "s101_attributes": "s101_attributes",
            "s52_instruction_ast": "s52_instruction_ast",
        },
    }
    return recipe


def _body_shape(shape_family: str) -> str:
    if shape_family == "buoy_can":
        return "M22 14 H42 L39 50 H25 Z"
    if shape_family == "buoy_cone":
        return "M32 12 L46 50 H18 Z"
    if shape_family == "buoy_pillar":
        return "M23 14 H41 V50 H23 Z"
    if shape_family == "buoy_spar":
        return "M28 12 H36 V52 H28 Z"
    if shape_family == "buoy_sphere":
        return "M32 16 A16 16 0 1 1 31.9 16 Z"
    if shape_family == "buoy_barrel":
        return "M22 18 Q32 10 42 18 V46 Q32 54 22 46 Z"
    if shape_family in {"beacon_general", "beacon_stake", "beacon_tower", "tower_lighthouse"}:
        return "M26 12 H38 L42 50 H22 Z"
    if shape_family == "daymark_panel":
        return "M18 14 H46 V46 H18 Z"
    if shape_family == "topmark_standard":
        return "M32 14 L46 38 H18 Z"
    if shape_family == "notice_mark":
        return "M14 14 H50 V50 H14 Z"
    if shape_family == "isolated_danger_mark":
        return "M20 32 A12 12 0 1 1 19.9 32 M44 32 A12 12 0 1 1 43.9 32"
    if shape_family == "anchoring_symbol":
        return "M32 14 V42 M22 28 H42 M22 42 Q32 54 42 42"
    return "M18 18 H46 V46 H18 Z"


def _band_rects(pattern: str, tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    if pattern == "vertical_stripes":
        width = 64 / len(tokens)
        return [
            f'<rect data-token="{html.escape(token)}" x="{idx * width:g}" y="0" width="{width:g}" height="64" fill="var(--{token})"/>'
            for idx, token in enumerate(tokens)
        ]
    if pattern in {"horizontal_bands", "ordered_sequence"}:
        height = 64 / len(tokens)
        return [
            f'<rect data-token="{html.escape(token)}" x="0" y="{idx * height:g}" width="64" height="{height:g}" fill="var(--{token})"/>'
            for idx, token in enumerate(tokens)
        ]
    if pattern == "squared":
        cells = []
        size = 32
        for y in range(2):
            for x in range(2):
                token = tokens[(x + y) % len(tokens)]
                cells.append(
                    f'<rect data-token="{html.escape(token)}" x="{x * size}" y="{y * size}" width="{size}" height="{size}" fill="var(--{token})"/>'
                )
        return cells
    return [f'<rect data-token="{html.escape(tokens[0])}" x="0" y="0" width="64" height="64" fill="var(--{tokens[0]})"/>']


def render_recipe_svg(recipe: dict[str, Any], palette: str = "day") -> str:
    if recipe.get("status") != "recipe_ready":
        raise ValueError(f"cannot render unresolved recipe: {recipe.get('status')}")
    shape_family = str(recipe["shape_family"])
    pattern = str(recipe["pattern_token"])
    tokens = [str(token) for token in recipe["color_tokens"]]
    if palette not in style_contract.OPENBRIDGE_NAV_PALETTES:
        raise KeyError(f"unknown palette {palette}")

    orientation = (PATTERN_DEFINITIONS.get(pattern) or {}).get("orientation") or "solid"
    body_id = f"body-{shape_family}"
    body_path = _body_shape(shape_family)
    fills = "\n      ".join(_band_rects(pattern, tokens))
    color_order = ",".join(tokens)
    stroke = recipe["render_defaults"]["stroke_width"]
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"',
        f'     data-recipe-version="{RECIPE_VERSION}" data-palette="{html.escape(palette)}"',
        f'     data-style-version="{STYLE_VERSION}" data-optical-center="32,32">',
        "  <defs>",
        f'    <clipPath id="{body_id}"><path d="{body_path}"/></clipPath>',
        "  </defs>",
        f'  <g data-shape-family="{shape_family}" data-pattern-token="{pattern}"',
        f'     data-band-orientation="{orientation}" data-color-order="{html.escape(color_order)}">',
        f'    <g clip-path="url(#{body_id})">',
        f"      {fills}",
        "    </g>",
        f'    <path d="{body_path}" fill="none" stroke="var(--ink)" stroke-width="{stroke:g}" stroke-linecap="round" stroke-linejoin="round"/>',
        "  </g>",
        "</svg>",
    ])


def build() -> dict[str, Any]:
    from . import semantic_evidence_db

    semantic = semantic_evidence_db.build()
    rows = []
    for row in semantic["rows"]:
        rows.append({
            "helm_catalog_id": row["helm_catalog_id"],
            "symbol_id": row["symbol_id"],
            "name": row["name"],
            "s52_instruction": row.get("s52_instruction"),
            "s57_attribute_tuple": row.get("s57_attribute_tuple"),
            "s101_crosswalk_class": row.get("s101_crosswalk_class"),
            "helm_symbol_recipe": row["helm_symbol_recipe"],
            "helm_symbol_recipe_status": row["helm_symbol_recipe_status"],
            "runtime_gate_summary": row["runtime_gate_summary"],
        })

    status_counts = Counter(row["helm_symbol_recipe_status"] for row in rows)
    shape_counts = Counter(
        row["helm_symbol_recipe"].get("shape_family") or "missing"
        for row in rows
    )
    pattern_counts = Counter(
        row["helm_symbol_recipe"].get("pattern_token") or "missing"
        for row in rows
    )
    colour_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    for row in rows:
        recipe = row["helm_symbol_recipe"]
        colour_counts.update(recipe.get("color_tokens") or [])
        reason_counts.update(recipe.get("reason_codes") or [])

    return {
        "schema": "helm.forge.symbol-recipe-contract.v1",
        "status": "provisional_symbol_recipe_contract_ready",
        "source": {
            "semantic_evidence_db": "catalog/semantic_evidence_db.json",
            "style_contract": "forge/style_contract.py",
        },
        "versions": {
            "recipe": RECIPE_VERSION,
            "palette": PALETTE_VERSION,
            "pattern": PATTERN_VERSION,
            "shape_family": SHAPE_FAMILY_VERSION,
            "style": STYLE_VERSION,
        },
        "global_defaults": {
            "palettes": style_contract.OPENBRIDGE_NAV_PALETTES,
            "supported_color_tokens": sorted(SUPPORTED_COLOUR_TOKENS),
            "patterns": PATTERN_DEFINITIONS,
            "shape_families": SHAPE_FAMILY_DEFINITIONS,
            "style": STYLE_DEFAULTS,
        },
        "consumer_contract": {
            "backend_db_source_of_truth": True,
            "browser_business_logic_allowed": False,
            "hidden_fallbacks_allowed": False,
            "runtime_export_allowed": False,
            "runtime_export_gate_owner": "FORGE-31",
        },
        "coverage": {
            "rows": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "shape_family_counts": dict(sorted(shape_counts.items())),
            "pattern_counts": dict(sorted(pattern_counts.items())),
            "color_token_counts": dict(sorted(colour_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Helm Symbol Recipe Contract",
        "",
        f"Status: `{result['status']}`",
        "",
        "This FORGE-28 artifact defines the backend-owned recipe vocabulary that",
        "connects semantic evidence rows to Helm-flavored symbol rendering. It",
        "does not approve runtime export.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- versions: `{result['versions']}`",
        f"- status_counts: `{coverage['status_counts']}`",
        f"- shape_family_counts: `{coverage['shape_family_counts']}`",
        f"- pattern_counts: `{coverage['pattern_counts']}`",
        f"- color_token_counts: `{coverage['color_token_counts']}`",
        "",
        "Consumer rule: the backend resolves shape family, color tokens, pattern",
        "tokens, style version, and palette version. Browser and proof UI code may",
        "display these fields and images, but must not derive colors, patterns, or",
        "fallback recipes from filenames or JavaScript heuristics.",
        "",
        "Known unresolved recipe states stay visible as `manual_exception_required`,",
        "`shape_family_missing`, or `recipe_missing` and remain blocked for runtime",
        "promotion until later gates approve them.",
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
    print(f"Helm symbol recipe contract -> {args.out}")
    print(f"Helm symbol recipe contract summary -> {args.md}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
