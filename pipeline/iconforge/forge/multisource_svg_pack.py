"""Generate a multi-source draft SVG pack from the master symbol list.

This is the practical pivot for FORGE-13: OpenCPN/S-52 tables are the local
reference oracle, while the emitted SVGs remain fresh Helm-owned draft artwork.
The generator also carries Chart No.1 mapping, S-101, and Commons mappings forward
from the master list so every row has one place to inspect source evidence.

Run:  python -m forge.multisource_svg_pack
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from .style_contract import OPENBRIDGE_NAV_PALETTES


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MASTER = CATALOG / "master_symbol_list.json"
OFFICIAL_TABLE = CATALOG / "official_symbol_table.json"
CHART1_PARITY_REPORT = ROOT / "out" / "chart1_parity" / "report.json"
S101_REGISTRY = CATALOG / "s101_reference_registry.json"
COMMONS_REGISTRY = CATALOG / "commons_nautical_chart_icons.json"
S52 = Path("/Users/steveridder/.helm/runtime/s57data/chartsymbols.xml")
OUT_DIR = ROOT / "assets" / "svg" / "multisource_draft"
OUT_JSON = CATALOG / "multisource_svg_draft_pack.json"
OUT_YAML = CATALOG / "multisource_svg_draft_pack.yaml"
OUT_MD = CATALOG / "multisource_svg_draft_pack.md"

PALETTES = OPENBRIDGE_NAV_PALETTES

COLOUR_TOKENS = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "11": "orange",
}

S52_COLOR_SUBSTRINGS = [
    ("CHRED", "red"),
    ("LITRD", "red"),
    ("CHGRN", "green"),
    ("LITGN", "green"),
    ("CHYLW", "yellow"),
    ("LITYW", "yellow"),
    ("CHBLK", "black"),
    ("OUTLW", "black"),
    ("CHWHT", "white"),
    ("CHMGD", "magenta"),
    ("CHMGF", "magenta"),
    ("CHBRN", "brown"),
    ("CHGRD", "gray"),
    ("CHGRF", "gray"),
    ("DEPMS", "blue"),
    ("DEPMD", "blue"),
    ("DEPDW", "blue"),
]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _safe_asset_filename(asset: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", asset).strip("_")
    return safe or "unnamed_asset"


def _text(node: ET.Element, child: str) -> str:
    return node.findtext(child) or ""


def _s52_registry() -> dict:
    root = ET.parse(S52).getroot()
    assets: dict[str, dict] = {}
    for kind, container, item in [
        ("symbol", "symbols", "symbol"),
        ("line-style", "line-styles", "line-style"),
        ("pattern", "patterns", "pattern"),
    ]:
        parent = root.find(container)
        if parent is None:
            continue
        for node in parent.findall(item):
            name = _text(node, "name")
            if not name:
                continue
            bitmap = node.find("bitmap")
            vector = node.find("vector")
            assets[name] = {
                "kind": kind,
                "rcid": node.get("RCID"),
                "name": name,
                "description": _text(node, "description"),
                "color_ref": _text(node, "color-ref"),
                "definition": _text(node, "definition"),
                "bitmap": dict(bitmap.attrib) if bitmap is not None else None,
                "vector": dict(vector.attrib) if vector is not None else None,
                "prefer_bitmap": _text(node, "prefer-bitmap") or None,
            }

    lookups_by_asset: dict[str, list[dict]] = {}
    for lookup in root.find("lookups").findall("lookup"):
        instruction = _text(lookup, "instruction")
        refs = []
        for pattern in [r"SY\(([^),]+)", r"AP\(([^),]+)", r"(?:LS|LC)\(([^),]+)", r"CS\(([^),]+)"]:
            refs.extend(re.findall(pattern, instruction))
        for asset in refs:
            lookups_by_asset.setdefault(asset, []).append({
                "lookup_id": lookup.get("id"),
                "rcid": lookup.get("RCID"),
                "object_class": lookup.get("name"),
                "conditions": [a.text or "" for a in lookup.findall("attrib-code")],
                "instruction": instruction,
            })
    return {"assets": assets, "lookups_by_asset": lookups_by_asset}


def _official_examples_by_int1() -> dict[str, dict]:
    if not OFFICIAL_TABLE.exists():
        return {}
    table = _read_json(OFFICIAL_TABLE)
    return {
        row["int1"]: {
            "official_name": row["official_name"],
            "symbol_reference_crop": row["symbol_reference"]["icon_reference_crop"],
            "row_reference_crop": row["row_reference"]["row_crop"],
            "status": row["symbol_reference"]["status"],
        }
        for row in table["rows"]
    }


def _chart1_parity_by_asset() -> dict[str, dict]:
    if not CHART1_PARITY_REPORT.exists():
        return {}
    report = _read_json(CHART1_PARITY_REPORT)
    return {
        row["asset"]: {
            "reference_crop": row.get("reference_crop"),
            "reference_crop_id": row.get("reference_crop_id"),
            "reference_evidence_status": row.get("reference_evidence_status"),
            "reference_pages": row.get("reference_pages"),
            "reference_section": row.get("reference_section"),
            "verdict": row.get("verdict"),
            "reason_codes": row.get("reason_codes", []),
        }
        for row in report["rows"]
    }


def _s101_by_id() -> dict[str, dict]:
    if not S101_REGISTRY.exists():
        return {}
    registry = _read_json(S101_REGISTRY)
    return {row["id"]: row for row in registry.get("svg_symbols", [])}


def _commons_by_asset() -> dict[str, list[dict]]:
    if not COMMONS_REGISTRY.exists():
        return {}
    registry = _read_json(COMMONS_REGISTRY)
    by_asset: dict[str, list[dict]] = {}
    for row in registry.get("files", []):
        if row.get("license_status") != "public_domain_or_cc0":
            continue
        for asset in row.get("mapping_candidates", {}).get("s52_assets", []):
            by_asset.setdefault(asset, []).append({
                "title": row["title"],
                "url": row["url"],
                "description_url": row["description_url"],
                "license_status": row["license_status"],
                "mapping_confidence": row.get("mapping_candidates", {}).get("mapping_confidence"),
            })
    return {key: sorted(rows, key=lambda item: item["title"]) for key, rows in by_asset.items()}


def _condition_values(row: dict, attr: str) -> list[str]:
    values: list[str] = []
    for condition in row.get("s57_conditions", []):
        text = str(condition).upper()
        if not text.startswith(attr):
            continue
        values.extend(part for part in re.split(r"[,./]", text[len(attr):]) if part)
    return values


def _colour_tokens(row: dict, s52: dict | None) -> list[str]:
    values = _condition_values(row, "COLOUR")
    tokens = [COLOUR_TOKENS.get(value, f"s57-colour-{value}") for value in values]
    if tokens:
        return list(dict.fromkeys(tokens))
    color_ref = (s52 or {}).get("color_ref") or ""
    for needle, token in S52_COLOR_SUBSTRINGS:
        if needle in color_ref:
            tokens.append(token)
    return list(dict.fromkeys(tokens)) or ["black"]


def _shape(row: dict, s52: dict | None) -> str:
    asset = row["asset"]
    text = f"{asset} {row.get('description') or ''} {(s52 or {}).get('description') or ''}".lower()
    if (
        asset.startswith(("TOPMAR", "TOPMA", "TOPSHP"))
        or row.get("s57_object_class") == "TOPMAR"
        or any(str(condition).upper().startswith("TOPSHP") for condition in row.get("s57_conditions", []))
    ):
        return "topmark"
    if asset.startswith(("BOYCAR", "BCNCAR")):
        return "cardinal_mark"
    if asset.startswith(("BOYCON", "BCNCON")) or "conical" in text:
        return "conical_buoy"
    if asset.startswith(("BOYCAN", "BCNCAN")) or "can buoy" in text or "cylindrical" in text:
        return "can_buoy"
    if asset.startswith("BOYSPH") or "spherical" in text:
        return "spherical_buoy"
    if asset.startswith("BOYPIL") or "pillar" in text:
        return "pillar_buoy"
    if asset.startswith(("BOYSPR", "BCNSTK")) or "spar" in text or "stake" in text:
        return "spar_buoy"
    if asset.startswith("BOYBAR") or "barrel" in text:
        return "barrel_buoy"
    if asset.startswith("BOY"):
        return "generic_buoy"
    if asset.startswith("BCN"):
        return "beacon"
    if asset.startswith("LIGHTS"):
        return "light_flare"
    if asset.startswith("WRECKS"):
        return "wreck"
    if asset.startswith("UWTROC"):
        return "rock"
    if asset.startswith("OBSTRN"):
        return "obstruction"
    if asset.startswith(("ACH", "ANC")) or "anchor" in text:
        return "anchor"
    if asset.startswith(("MORFAC", "BOYMOR")) or "mooring" in text:
        return "mooring"
    if asset.startswith(("HRBFAC", "SMCFAC")):
        return "harbor_service"
    if row.get("family") == "areas_patterns_lines":
        return "area_symbol"
    return "generic_symbol"


def _topmark_body(asset: str, color: str) -> list[str]:
    fill = f"var(--{color})"
    stroke = 'var(--black)'
    if asset in {"TOPMAR02", "TOPMAR05"}:
        return [f'<path d="M32 12 L45 34 H19 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
    if asset in {"TOPMAR04", "TOPMAR06"}:
        return [f'<path d="M19 26 H45 L32 48 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
    if asset == "TOPMAR07":
        return [
            f'<path d="M19 17 H45 L32 35 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
            f'<path d="M32 30 L45 48 H19 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
        ]
    if asset == "TOPMAR08":
        return [
            f'<path d="M32 14 L45 32 H19 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
            f'<path d="M19 32 H45 L32 50 Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
        ]
    if asset in {"TOPMAR10", "TOPMAR12"}:
        return [
            f'<circle cx="32" cy="25" r="9" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
            *([f'<circle cx="32" cy="43" r="9" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'] if asset == "TOPMAR12" else []),
        ]
    if asset == "TOPMAR13":
        return [f'<rect x="22" y="17" width="20" height="30" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']
    if asset in {"TOPMAR65", "TOPMAR86"}:
        return [
            f'<path d="M19 19 L45 45 M45 19 L19 45" fill="none" stroke="{stroke}" stroke-width="7" stroke-linecap="round"/>',
            f'<path d="M19 19 L45 45 M45 19 L19 45" fill="none" stroke="{fill}" stroke-width="4" stroke-linecap="round"/>',
        ]
    return [f'<circle cx="32" cy="32" r="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>']


def _body_shape(shape: str) -> str:
    return {
        "conical_buoy": '<path d="M32 11 L49 49 Q32 56 15 49 Z"/>',
        "can_buoy": '<path d="M18 21 Q32 14 46 21 L46 48 Q32 55 18 48 Z"/>',
        "spherical_buoy": '<circle cx="32" cy="35" r="17"/>',
        "pillar_buoy": '<path d="M24 14 L40 14 L45 49 Q32 56 19 49 Z"/>',
        "spar_buoy": '<path d="M29 10 L35 10 L38 52 Q32 58 26 52 Z"/>',
        "barrel_buoy": '<path d="M19 24 Q32 12 45 24 L45 45 Q32 56 19 45 Z"/>',
        "generic_buoy": '<path d="M21 20 Q32 10 43 20 L48 45 Q32 57 16 45 Z"/>',
        "beacon": '<path d="M26 11 H38 L43 51 H21 Z"/>',
        "cardinal_mark": '<path d="M23 31 Q32 20 41 31 L45 50 Q32 57 19 50 Z"/>',
    }.get(shape, '<rect x="18" y="18" width="28" height="28" rx="3"/>')


def _painted_body(asset: str, shape: str, colors: list[str]) -> list[str]:
    body = _body_shape(shape)
    clip_id = f"clip-{asset}"
    lines = [f'<defs><clipPath id="{clip_id}">{body}</clipPath></defs>', f'<g clip-path="url(#{clip_id})">']
    if len(colors) == 1:
        lines.append(f'<rect x="0" y="0" width="64" height="64" fill="var(--{colors[0]})"/>')
    else:
        height = 52 / len(colors)
        for index, color in enumerate(colors):
            lines.append(
                f'<rect x="0" y="{round(7 + index * height, 2)}" width="64" height="{round(height + 0.25, 2)}" fill="var(--{color})"/>'
            )
    lines.extend([
        "</g>",
        f'<g fill="none" stroke="var(--black)" stroke-width="2.1" stroke-linejoin="round">{body}</g>',
        '<path d="M32 55 L32 61" fill="none" stroke="var(--black)" stroke-width="1.4" stroke-linecap="round"/>',
    ])
    return lines


def _svg_for(row: dict, s52: dict | None, shape: str, colors: list[str]) -> str:
    asset = row["asset"]
    title = f"{asset} {shape}"
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img"',
        f'     aria-label="{title}">',
        f"  <title>{title}</title>",
        f'  <g data-origin="generated-owned-artwork" data-reference-oracle="opencpn-s52"',
        f'     data-s52-asset="{asset}" data-shape="{shape}">',
    ]
    primary = colors[0]
    if shape == "topmark":
        lines.extend(f"  {line}" for line in _topmark_body(asset, primary))
    elif shape in {
        "conical_buoy",
        "can_buoy",
        "spherical_buoy",
        "pillar_buoy",
        "spar_buoy",
        "barrel_buoy",
        "generic_buoy",
        "beacon",
        "cardinal_mark",
    }:
        lines.extend(f"  {line}" for line in _painted_body(asset, shape, colors))
        if shape == "cardinal_mark":
            lines.append('  <path d="M24 15 H40 L32 26 Z" fill="var(--black)" stroke="var(--black)" stroke-width="1.4"/>')
            lines.append('  <path d="M24 12 H40 L32 2 Z" fill="var(--black)" stroke="var(--black)" stroke-width="1.4"/>')
    elif shape == "light_flare":
        lines.extend([
            f'  <circle cx="32" cy="32" r="6" fill="var(--{primary})" stroke="var(--black)" stroke-width="1.5"/>',
            f'  <path d="M32 10 V21 M32 43 V54 M10 32 H21 M43 32 H54 M16 16 L24 24 M48 16 L40 24 M16 48 L24 40 M48 48 L40 40" stroke="var(--{primary})" stroke-width="3" stroke-linecap="round"/>',
        ])
    elif shape == "wreck":
        lines.extend([
            '<path d="M12 43 Q32 53 52 43" fill="none" stroke="var(--black)" stroke-width="2.2"/>',
            '<path d="M20 40 L29 25 L38 40" fill="none" stroke="var(--black)" stroke-width="2.1" stroke-linejoin="round"/>',
            '<path d="M18 45 L46 45" stroke="var(--black)" stroke-width="2.1" stroke-linecap="round"/>',
        ])
    elif shape == "rock":
        lines.extend([
            '<path d="M14 43 L25 23 L34 36 L42 20 L51 43 Z" fill="none" stroke="var(--black)" stroke-width="2.1" stroke-linejoin="round"/>',
            '<path d="M17 48 H48" stroke="var(--black)" stroke-width="2" stroke-linecap="round"/>',
        ])
    elif shape == "obstruction":
        lines.extend([
            '<circle cx="32" cy="32" r="18" fill="none" stroke="var(--black)" stroke-width="2" stroke-dasharray="3 3"/>',
            '<path d="M22 42 L42 22 M22 22 L42 42" stroke="var(--black)" stroke-width="2.2" stroke-linecap="round"/>',
        ])
    elif shape == "anchor":
        lines.extend([
            '<circle cx="32" cy="13" r="4" fill="none" stroke="var(--black)" stroke-width="2"/>',
            '<path d="M32 17 V47 M21 29 H43 M18 42 Q32 55 46 42" fill="none" stroke="var(--black)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
            '<path d="M18 42 L16 34 M46 42 L48 34" fill="none" stroke="var(--black)" stroke-width="2.2" stroke-linecap="round"/>',
        ])
    elif shape == "mooring":
        lines.extend([
            f'<circle cx="32" cy="32" r="15" fill="var(--{primary})" stroke="var(--black)" stroke-width="2"/>',
            '<circle cx="32" cy="32" r="6" fill="var(--white)" stroke="var(--black)" stroke-width="1.5"/>',
        ])
    elif shape == "harbor_service":
        lines.extend([
            '<rect x="18" y="18" width="28" height="28" rx="3" fill="var(--white)" stroke="var(--black)" stroke-width="2"/>',
            '<path d="M24 40 V24 H32 Q39 24 39 31 Q39 38 32 38 H24" fill="none" stroke="var(--black)" stroke-width="2.3" stroke-linejoin="round"/>',
        ])
    elif shape == "area_symbol":
        lines.extend([
            f'<rect x="13" y="13" width="38" height="38" fill="var(--{primary})" opacity="0.22" stroke="var(--black)" stroke-width="1.8" stroke-dasharray="5 3"/>',
            '<path d="M18 46 L46 18" stroke="var(--black)" stroke-width="1.6" stroke-dasharray="3 4"/>',
        ])
    else:
        lines.extend([
            f'<path d="M32 12 L52 32 L32 52 L12 32 Z" fill="var(--{primary})" stroke="var(--black)" stroke-width="2"/>',
            '<circle cx="32" cy="32" r="5" fill="var(--white)" stroke="var(--black)" stroke-width="1.5"/>',
        ])
    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def _source_refs(row: dict, s52: dict | None, lookups: list[dict]) -> dict:
    return {
        "opencpn_s52": {
            "role": "reference_oracle_not_canonical_artwork",
            "chartsymbols_xml": str(S52),
            "asset_definition": s52,
            "lookup_refs": lookups[:8],
            "allowed_use": [
                "master list validation",
                "symbol dimensions/pivot/color metadata",
                "sibling discovery",
                "visual reference render",
                "semantic QA oracle",
            ],
            "forbidden_use": ["copy_or_trace_gpl_artwork_into_owned_pack"],
        },
        "chart1_mappings": {
            "int1_refs": row.get("chart1_mappings_int1_refs", []),
            "evidence_status": row.get("chart1_evidence_status"),
            "gate_status": row.get("chart1_gate_status"),
            "crop_id": row.get("chart1_crop_id"),
            "allowed_use": ["name mapping", "semantic QA", "human reference"],
        },
        "s101": {
            "coverage": row.get("s101_coverage"),
            "symbol_id": row.get("s101_symbol_id"),
            "symbol_file": row.get("s101_symbol_file"),
            "license_status": row.get("s101_license_status"),
            "allowed_use": ["mapping", "sibling discovery", "visual reference pending license"],
        },
        "commons": {
            "pd_candidate_count": row.get("commons_pd_candidate_count"),
            "candidate_titles": row.get("commons_candidate_titles", []),
            "allowed_use": ["public-domain candidate intake after per-file review"],
        },
    }


def _palette_targets(asset_file: str | None) -> list[dict]:
    if not asset_file:
        return []
    return [
        {
            "palette": name,
            "render_status": "pending_render",
            "source_svg": asset_file,
            "css_variables": colors,
            "planned_render": f"out/multisource_svg_draft/renders/{Path(asset_file).stem}__{name}.png",
        }
        for name, colors in PALETTES.items()
    ]


def _examples(
    row: dict,
    s52: dict | None,
    manifest_asset_file: str | None,
    official_by_int1: dict[str, dict],
    chart1_by_asset: dict[str, dict],
    s101_by_id: dict[str, dict],
    commons_by_asset: dict[str, list[dict]],
) -> list[dict]:
    asset = row["asset"]
    examples: list[dict] = []
    if manifest_asset_file:
        examples.append({
            "source": "helm_generated_draft_svg",
            "role": "candidate_to_repair",
            "status": "generated_pending_visual_parity",
            "path": manifest_asset_file,
        })
    examples.append({
        "source": "opencpn_s52_reference_render",
        "role": "local_visual_oracle",
        "status": "pending_render",
        "paths": {
            "day": f"out/opencpn_s52_reference/{_safe_asset_filename(asset)}__day.png",
            "dusk": f"out/opencpn_s52_reference/{_safe_asset_filename(asset)}__dusk.png",
            "night": f"out/opencpn_s52_reference/{_safe_asset_filename(asset)}__night.png",
        },
        "metadata_available": bool(s52),
        "asset_description": (s52 or {}).get("description") or row.get("description"),
    })
    parity = chart1_by_asset.get(asset)
    if parity and parity.get("reference_crop"):
        examples.append({
            "source": "chart1_parity_reference_crop",
            "role": "chart_no_1_visual_reference",
            "status": parity.get("reference_evidence_status"),
            "path": parity["reference_crop"],
            "crop_id": parity.get("reference_crop_id"),
            "pages": parity.get("reference_pages"),
            "verdict": parity.get("verdict"),
            "reason_codes": parity.get("reason_codes", []),
        })
    for int1 in row.get("chart1_mappings_int1_refs", [])[:4]:
        official = official_by_int1.get(int1)
        if official and official.get("symbol_reference_crop"):
            examples.append({
                "source": "chart1_mappings_symbol_reference",
                "role": "official_name_and_symbol_reference",
                "status": official["status"],
                "int1": int1,
                "official_name": official["official_name"],
                "path": official["symbol_reference_crop"],
                "row_crop": official["row_reference_crop"],
            })
    s101_id = row.get("s101_symbol_id")
    if s101_id and s101_id in s101_by_id:
        s101 = s101_by_id[s101_id]
        examples.append({
            "source": "s101_portrayal_catalogue_svg",
            "role": "license_pending_visual_reference",
            "status": s101["license_status"],
            "symbol_id": s101_id,
            "path": s101["file"],
            "title": s101.get("title"),
            "viewBox": s101.get("viewBox"),
        })
    for commons in commons_by_asset.get(asset, [])[:3]:
        examples.append({
            "source": "wikimedia_commons_svg",
            "role": "public_domain_candidate_reference",
            "status": commons["license_status"],
            "title": commons["title"],
            "url": commons["url"],
            "description_url": commons["description_url"],
            "mapping_confidence": commons["mapping_confidence"],
        })
    return examples


def _manifest_row(
    row: dict,
    s52: dict | None,
    lookups: list[dict],
    generated: bool,
    official_by_int1: dict[str, dict],
    chart1_by_asset: dict[str, dict],
    s101_by_id: dict[str, dict],
    commons_by_asset: dict[str, list[dict]],
) -> dict:
    shape = _shape(row, s52)
    colors = _colour_tokens(row, s52)
    asset_path = OUT_DIR / f"{_safe_asset_filename(row['asset'])}.svg"
    asset_file = str(asset_path.relative_to(ROOT)) if generated else None
    return {
        "id": row["helm_catalog_id"],
        "asset": row["asset"],
        "name": row.get("description") or (s52 or {}).get("description") or row["asset"],
        "kind": row["s52_asset_kind"],
        "family": row["family"],
        "tier": "chart-artifact",
        "source_refs": _source_refs(row, s52, lookups),
        "geometry": {
            "shape": shape,
            "color_tokens": colors,
            "style": "helm-owned-draft",
            "basis": "fresh SVG drawn from semantic metadata and multi-source reference rows",
        },
        "asset_file": asset_file,
        "examples": _examples(
            row,
            s52,
            asset_file,
            official_by_int1,
            chart1_by_asset,
            s101_by_id,
            commons_by_asset,
        ),
        "palette_targets": _palette_targets(asset_file),
        "qa": {
            "semantic_pass": bool(s52 or lookups),
            "visual_parity": "pending",
            "final_approved": False,
            "review_status": "draft_generated" if generated else "renderer_not_yet_implemented",
        },
        "provenance": {
            "origin": "generated-owned-artwork" if generated else "not_generated_yet",
            "clean_ip_status": "pending_review",
            "reference_sources": ["opencpn_s52_tables", "chart1_mappings", "s101", "commons"],
            "forbidden_sources": row.get("forbidden_sources", []),
        },
    }


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
        lines = []
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
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def build() -> dict:
    master = _read_json(MASTER)
    s52 = _s52_registry()
    official_by_int1 = _official_examples_by_int1()
    chart1_by_asset = _chart1_parity_by_asset()
    s101_by_id = _s101_by_id()
    commons_by_asset = _commons_by_asset()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    generated = 0
    for row in master["rows"]:
        asset_def = s52["assets"].get(row["asset"])
        lookups = s52["lookups_by_asset"].get(row["asset"], [])
        can_generate = row["s52_asset_kind"] == "symbol" or row["asset"] == "TOPMAR01"
        manifest = _manifest_row(
            row,
            asset_def,
            lookups,
            can_generate,
            official_by_int1,
            chart1_by_asset,
            s101_by_id,
            commons_by_asset,
        )
        rows.append(manifest)
        if can_generate:
            svg = _svg_for(row, asset_def, manifest["geometry"]["shape"], manifest["geometry"]["color_tokens"])
            (ROOT / manifest["asset_file"]).write_text(svg)
            generated += 1

    kind_counts = Counter(row["kind"] for row in rows)
    shape_counts = Counter(row["geometry"]["shape"] for row in rows if row["asset_file"])
    source_counts = {
        "opencpn_asset_defs": sum(1 for row in rows if row["source_refs"]["opencpn_s52"]["asset_definition"]),
        "opencpn_lookup_refs": sum(1 for row in rows if row["source_refs"]["opencpn_s52"]["lookup_refs"]),
        "chart1_mappings_refs": sum(1 for row in rows if row["source_refs"]["chart1_mappings"]["int1_refs"]),
        "s101_exact": sum(1 for row in rows if row["source_refs"]["s101"]["coverage"] == "exact_symbol_match"),
        "commons_pd_candidates": sum(1 for row in rows if row["source_refs"]["commons"]["pd_candidate_count"]),
    }
    example_counts = Counter(len(row["examples"]) for row in rows)
    example_source_counts = Counter(example["source"] for row in rows for example in row["examples"])
    output = {
        "schema_version": 1,
        "scope": "multi-source draft SVG pack; OpenCPN/S-52 as reference oracle, generated-owned SVG output",
        "summary": {
            "master_rows": len(rows),
            "generated_symbol_svgs": generated,
            "manifest_only_rows": len(rows) - generated,
            "visual_approvals": 0,
            "kind_counts": dict(sorted(kind_counts.items())),
            "shape_counts": dict(sorted(shape_counts.items())),
            "source_counts": source_counts,
            "example_count_buckets": dict(sorted(example_counts.items())),
            "example_source_counts": dict(sorted(example_source_counts.items())),
            "palette_targets_per_generated_svg": len(PALETTES),
            "palette_target_count": generated * len(PALETTES),
            "limits": [
                "OpenCPN/S-52 tables and reference renders are used as an oracle, not copied/traced artwork.",
                "Line styles, patterns, and conditional procedures are manifest-only until dedicated renderers are added.",
                "Every generated SVG remains draft until visual-model and human parity review clears it.",
                "OpenCPN reference render paths are planned links until the renderer extraction task writes them.",
            ],
        },
        "symbols": rows,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    OUT_YAML.write_text("\n".join(_yaml_lines(output)) + "\n")
    _write_md(output)
    return output


def _write_md(output: dict) -> None:
    summary = output["summary"]
    lines = [
        "# Multi-Source SVG Draft Pack",
        "",
        "Draft Helm-owned SVG output generated from the master symbol list, using OpenCPN/S-52 tables as the local reference oracle plus Chart 1 Mappings, S-101, and Commons mapping fields.",
        "",
        "## Summary",
        "",
        f"- Master rows: {summary['master_rows']}",
        f"- Generated point-symbol SVGs: {summary['generated_symbol_svgs']}",
        f"- Manifest-only line/pattern/procedure rows: {summary['manifest_only_rows']}",
        f"- Visual approvals: {summary['visual_approvals']}",
        "",
        "## Source Counts",
        "",
    ]
    for key, value in summary["source_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Shape Counts", ""])
    for key, value in summary["shape_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Linked Examples", ""])
    for key, value in summary["example_source_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend([
        "",
        "## Palette Targets",
        "",
        f"- Palettes per generated SVG: {summary['palette_targets_per_generated_svg']}",
        f"- Planned day/dusk/night renders: {summary['palette_target_count']}",
    ])
    lines.extend([
        "",
        "These SVGs are generated-owned drafts. They are not copied from OpenCPN raster/vector artwork, and they are not visually approved yet.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines))


def main() -> int:
    output = build()
    summary = output["summary"]
    print("Multi-source SVG draft pack")
    print(f"master rows: {summary['master_rows']}")
    print(f"generated symbol SVGs: {summary['generated_symbol_svgs']}")
    print(f"manifest-only rows: {summary['manifest_only_rows']}")
    print(f"json: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
