"""Generate source-backed buoy body SymbolSpecs for Q20-Q25.

This is the first FORGE-13 drawing slice. It does not claim visual parity.
It turns official-table rows for the basic buoy body shapes into draft,
owned SVG primitives that stay traceable to the Chart 1 Mappings INT 1 row and the
S-57 conditions that selected each Helm asset.

Run:  python -m forge.buoy_body_primitives
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OFFICIAL_TABLE = CATALOG / "official_symbol_table.json"
MASTER_LIST = CATALOG / "master_symbol_list.json"

OUT_JSON = CATALOG / "symbol_specs_q20_q25.json"
OUT_YAML = CATALOG / "symbol_specs_q20_q25.yaml"
OUT_MD = CATALOG / "symbol_specs_q20_q25.md"
OUT_SVG_DIR = ROOT / "assets" / "svg" / "official_q20_q25"

Q_BODY_ROWS = {
    "Q20": {
        "primitive": "conical_buoy",
        "boys_hp": "BOYSHP1",
        "shape_label": "conical/nun/ogival",
    },
    "Q21": {
        "primitive": "can_buoy",
        "boys_hp": "BOYSHP2",
        "shape_label": "can/cylindrical",
    },
    "Q22": {
        "primitive": "spherical_buoy",
        "boys_hp": "BOYSHP3",
        "shape_label": "spherical",
    },
    "Q23": {
        "primitive": "pillar_buoy",
        "boys_hp": "BOYSHP4",
        "shape_label": "pillar",
    },
    "Q24": {
        "primitive": "spar_buoy",
        "boys_hp": "BOYSHP5",
        "shape_label": "spar/spindle",
    },
    "Q25": {
        "primitive": "barrel_buoy",
        "boys_hp": "BOYSHP6",
        "shape_label": "barrel/tun",
    },
}

COLOUR_TOKENS = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "11": "orange",
}

SVG_BODY_BY_PRIMITIVE = {
    "conical_buoy": '<path d="M32 11 L49 49 Q32 56 15 49 Z"/>',
    "can_buoy": '<path d="M18 21 Q32 14 46 21 L46 48 Q32 55 18 48 Z"/>',
    "spherical_buoy": '<circle cx="32" cy="35" r="17"/>',
    "pillar_buoy": '<path d="M24 14 L40 14 L45 49 Q32 56 19 49 Z"/>',
    "spar_buoy": '<path d="M29 10 L35 10 L38 52 Q32 58 26 52 Z"/>',
    "barrel_buoy": '<path d="M19 24 Q32 12 45 24 L45 45 Q32 56 19 45 Z"/>',
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _condition_values(asset_row: dict, attr: str) -> list[str]:
    values: list[str] = []
    for condition in asset_row.get("s57_conditions", []):
        text = str(condition).upper()
        if not text.startswith(attr):
            continue
        suffix = text[len(attr):]
        values.extend(part for part in re.split(r"[,./]", suffix) if part)
    return values


def _colour_tokens(asset_row: dict) -> list[str]:
    values = _condition_values(asset_row, "COLOUR")
    tokens = [COLOUR_TOKENS.get(value, f"s57-colour-{value}") for value in values]
    return tokens or ["black"]


def _pattern(asset_row: dict, colour_tokens: list[str]) -> str:
    values = _condition_values(asset_row, "COLPAT")
    if values:
        return f"s57-colpat-{'.'.join(values)}"
    if len(colour_tokens) > 1:
        return "inferred_horizontal_bands"
    return "solid"


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if all(ch.isalnum() or ch in "_./:-" for ch in text):
        return text
    return json.dumps(text)


def _yaml_lines(value, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}[]"]
        lines: list[str] = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def _paint_lines(asset: str, primitive: str, colour_tokens: list[str], pattern: str) -> list[str]:
    clip_id = f"clip-{asset}"
    body = SVG_BODY_BY_PRIMITIVE[primitive]
    lines = [
        f'  <defs><clipPath id="{clip_id}">{body}</clipPath></defs>',
        f'  <g clip-path="url(#{clip_id})">',
    ]
    if len(colour_tokens) == 1:
        lines.append(f'    <rect x="0" y="0" width="64" height="64" fill="var(--{colour_tokens[0]})"/>')
    elif pattern == "s57-colpat-2":
        width = 64 / len(colour_tokens)
        for index, token in enumerate(colour_tokens):
            x = round(index * width, 2)
            lines.append(f'    <rect x="{x}" y="0" width="{round(width + 0.25, 2)}" height="64" fill="var(--{token})"/>')
    else:
        height = 48 / len(colour_tokens)
        for index, token in enumerate(colour_tokens):
            y = round(10 + index * height, 2)
            lines.append(f'    <rect x="0" y="{y}" width="64" height="{round(height + 0.25, 2)}" fill="var(--{token})"/>')
    lines.extend([
        "  </g>",
        f'  <g fill="none" stroke="var(--black)" stroke-width="2.2" stroke-linejoin="round">{body}</g>',
        '  <path d="M32 55 L32 61" fill="none" stroke="var(--black)" stroke-width="1.5" stroke-linecap="round"/>',
    ])
    return lines


def _svg(spec: dict) -> str:
    asset = spec["asset"]["canonical"].split("/")[-1].removesuffix(".svg")
    primitive = spec["geometry"]["primitive"]
    colour_tokens = spec["geometry"]["color_tokens"]
    pattern = spec["geometry"]["pattern"]
    title = f"{asset} {spec['source_refs'][0]['int1']} {spec['geometry']['shape_label']}"
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img"',
        f'     aria-label="{title}">',
        f"  <title>{title}</title>",
        f'  <g data-origin="generated-owned-artwork" data-int1="{spec["source_refs"][0]["int1"]}"',
        f'     data-s52-asset="{asset}" data-primitive="{primitive}">',
    ]
    lines.extend(_paint_lines(asset, primitive, colour_tokens, pattern))
    lines.extend([
        "  </g>",
        "</svg>",
        "",
    ])
    return "\n".join(lines)


def _spec(row: dict, asset: dict, master_row: dict) -> dict:
    row_meta = Q_BODY_ROWS[row["int1"]]
    colour_tokens = _colour_tokens(asset)
    svg_path = OUT_SVG_DIR / f"{asset['asset']}.svg"
    return {
        "id": f"{row['int1']}-{asset['asset']}",
        "name": f"{asset['asset']} - {row['official_name']}",
        "kind": "chart-symbol",
        "tier": "chart-artifact",
        "s52_asset": asset["asset"],
        "s57_object_class": asset["s57_object_class"],
        "s57_conditions": asset["s57_conditions"],
        "source_refs": [
            {
                "type": "chart1_reference_row",
                "source_id": row["source_boundary"]["source_id"],
                "int1": row["int1"],
                "official_name": row["official_name"],
                "source_page": row["source_page"],
                "s57_refs": row["s57_refs"],
                "symbol_reference_crop": row["symbol_reference"]["icon_reference_crop"],
                "row_reference_crop": row["row_reference"]["row_crop"],
                "status": "reference_only_not_canonical_artwork",
            },
            {
                "type": "s52_s57_catalog_metadata",
                "helm_catalog_id": asset["helm_catalog_id"],
                "s52_instruction": asset["s52_instruction"],
                "s57_object_class": asset["s57_object_class"],
                "s57_conditions": asset["s57_conditions"],
            },
        ],
        "geometry": {
            "primitive": row_meta["primitive"],
            "shape_label": row_meta["shape_label"],
            "required_condition": row_meta["boys_hp"],
            "color_tokens": colour_tokens,
            "pattern": _pattern(asset, colour_tokens),
            "anchor": [0.5, 0.88],
        },
        "asset": {
            "canonical": str(svg_path.relative_to(ROOT)),
            "status": "generated_owned_draft",
        },
        "qa": {
            "semantic_source_match": True,
            "visual_parity": "pending",
            "final_approved": False,
            "approval_blocker": "requires visual-model and human spot-check against exact Chart No.1 crop",
        },
        "provenance": {
            "origin": "generated-owned-artwork",
            "allowed_sources": [
                "official S-57/S-52 metadata lookup",
                "reference-only public Chart No.1 row identity",
                "local metadata lookup",
            ],
            "forbidden_sources": row["source_boundary"]["forbidden_use"],
        },
        "crosswalk": {
            "master_list_chart1_gate_status": master_row["chart1_gate_status"],
            "master_list_next_action": master_row["next_action"],
            "s101_coverage": master_row["s101_coverage"],
            "s101_symbol_id": master_row["s101_symbol_id"],
            "commons_pd_candidate_count": master_row["commons_pd_candidate_count"],
        },
    }


def build() -> dict:
    official = _read_json(OFFICIAL_TABLE)
    master = _read_json(MASTER_LIST)
    master_by_asset = {row["asset"]: row for row in master["rows"]}
    OUT_SVG_DIR.mkdir(parents=True, exist_ok=True)

    specs: list[dict] = []
    skipped: list[dict] = []
    for row in official["rows"]:
        if row["int1"] not in Q_BODY_ROWS:
            continue
        required = Q_BODY_ROWS[row["int1"]]["boys_hp"]
        for asset in row["attribute_matched_helm_assets"]:
            reasons = []
            if not asset["asset"].startswith("BOY"):
                reasons.append("non_buoy_asset_in_body_shape_row")
            if required not in asset["s57_conditions"]:
                reasons.append("missing_required_boyshp_condition")
            if reasons:
                skipped.append({
                    "int1": row["int1"],
                    "asset": asset["asset"],
                    "s57_conditions": asset["s57_conditions"],
                    "reasons": reasons,
                })
                continue
            spec = _spec(row, asset, master_by_asset[asset["asset"]])
            specs.append(spec)
            (ROOT / spec["asset"]["canonical"]).write_text(_svg(spec))

    shape_counts = Counter(spec["geometry"]["primitive"] for spec in specs)
    output = {
        "schema_version": 1,
        "scope": "FORGE-13-A official-table Q20-Q25 buoy body primitive draft",
        "summary": {
            "official_rows": len(Q_BODY_ROWS),
            "generated_specs": len(specs),
            "generated_svgs": len(specs),
            "skipped_assets": len(skipped),
            "shape_counts": dict(sorted(shape_counts.items())),
            "visual_approvals": 0,
            "limits": [
                "Draft primitives are generated-owned artwork but are not final visual approvals.",
                "Chart 1 Mappings crops remain reference-only evidence and are not copied or vectorized.",
                "Q24 non-buoy beacon rows are skipped instead of silently drawing them as buoys.",
            ],
        },
        "specs": specs,
        "skipped_assets": skipped,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    OUT_YAML.write_text("\n".join(_yaml_lines(output)) + "\n")
    _write_md(output)
    return output


def _write_md(output: dict) -> None:
    summary = output["summary"]
    lines = [
        "# Q20-Q25 Buoy Body Primitive Drafts",
        "",
        "FORGE-13-A source-backed drawing slice for the basic buoy body shapes.",
        "",
        "## Summary",
        "",
        f"- Official rows: {summary['official_rows']}",
        f"- Generated draft specs/SVGs: {summary['generated_specs']}",
        f"- Skipped assets: {summary['skipped_assets']}",
        f"- Visual approvals: {summary['visual_approvals']}",
        "",
        "## Shape Counts",
        "",
    ]
    for primitive, count in summary["shape_counts"].items():
        lines.append(f"- `{primitive}`: {count}")
    lines.extend([
        "",
        "These assets are generated-owned draft artwork. They are traceable to the official table and S-57 conditions, but visual parity remains pending.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines))


def main() -> int:
    output = build()
    summary = output["summary"]
    print("Q20-Q25 buoy body primitive drafts")
    print(f"generated specs: {summary['generated_specs']}")
    print(f"skipped assets: {summary['skipped_assets']}")
    print(f"json: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
