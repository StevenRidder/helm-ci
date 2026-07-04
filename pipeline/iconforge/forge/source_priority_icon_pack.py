"""Build the source-priority icon pack for the full Helm symbol catalog.

This is the practical FORGE-14 pivot: prefer exact S-101 SVG geometry when the
master table has an exact match, fall back to Helm's multi-source generated
draft SVGs, and leave only true non-SVG/renderer gaps in the hard-pile.

Run:  python -m forge.source_priority_icon_pack
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MASTER = CATALOG / "master_symbol_list.json"
DRAFT_PACK = CATALOG / "multisource_svg_draft_pack.json"
OUT_JSON = CATALOG / "source_priority_icon_pack.json"
OUT_YAML = CATALOG / "source_priority_icon_pack.yaml"
OUT_MD = CATALOG / "source_priority_icon_pack.md"
S101_OUT = ROOT / "assets" / "svg" / "source_priority" / "s101_exact"
S101_ROOTS = [
    Path("/tmp/s101-audit"),
    ROOT / "reference_sources" / "s101_portrayal_catalogue",
]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _safe_asset_filename(asset: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", asset).strip("_")
    return safe or "unnamed_asset"


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


def _resolve_s101_source(symbol_file: str | None) -> Path | None:
    if not symbol_file:
        return None
    for root in S101_ROOTS:
        candidate = root / symbol_file
        if candidate.exists():
            return candidate
    return None


def _insert_svg_attrs(text: str, attrs: str) -> str:
    def repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        return tag[:-1] + attrs + ">"

    text, replacements = re.subn(r"(<svg\b[^>]*>)", repl, text, count=1)
    if replacements != 1:
        raise ValueError("could not find root svg element")
    return text


def _inline_s101_svg(asset: str, source: Path, target: Path) -> Path:
    css = source.parent / "daySvgStyle.css"
    if not css.exists():
        raise FileNotFoundError(f"S-101 CSS missing beside {source}")

    text = source.read_text()
    text = re.sub(r'<\?xml-stylesheet[^>]+\?>\s*', "", text)
    text = _insert_svg_attrs(
        text,
        f' data-s52-asset="{asset}"'
        ' data-helm-source-pack="source-priority"'
        ' data-origin="license-pending-s101-reference-art"',
    )
    style = "<style><![CDATA[\n.layout{display:none}\n" + css.read_text() + "\n]]></style>"
    text, replacements = re.subn(r"(<svg\b[^>]*>)", r"\1\n" + style, text, count=1)
    if replacements != 1:
        raise ValueError(f"could not inline S-101 CSS for {source}")

    text = "\n".join(line.rstrip() for line in text.strip().splitlines()) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    ET.fromstring(text)
    return target


def _s101_asset_file(row: dict) -> str | None:
    if row.get("s101_coverage") != "exact_symbol_match":
        return None
    asset = row["asset"]
    target = S101_OUT / f"{_safe_asset_filename(asset)}.svg"
    source = _resolve_s101_source(row.get("s101_symbol_file"))
    if source:
        _inline_s101_svg(asset, source, target)
    if target.exists():
        return str(target.relative_to(ROOT))
    return None


def _palette_targets(asset_file: str | None, basis: str) -> list[dict]:
    if not asset_file:
        return []
    if basis == "s101_exact_svg":
        return [
            {
                "palette": "day",
                "source_svg": asset_file,
                "render_status": "ready_with_embedded_s101_day_style",
            }
        ]
    return [
        {
            "palette": palette,
            "source_svg": asset_file,
            "render_status": "pending_render",
        }
        for palette in ["day", "dusk", "night"]
    ]


def _selected_row(row: dict, draft: dict) -> dict:
    s101_asset = _s101_asset_file(row)
    draft_asset = draft.get("asset_file")
    if s101_asset:
        basis = "s101_exact_svg"
        asset_file = s101_asset
        origin = "license_pending_reference_art"
        visual_parity = "reference_exact_pending_license"
        review_status = "selected_s101_exact_svg"
        clean_ip_status = "license_pending"
    elif draft_asset:
        basis = "helm_multisource_draft_svg"
        asset_file = draft_asset
        origin = "generated-owned-artwork"
        visual_parity = "pending_repair"
        review_status = "draft_fallback_selected"
        clean_ip_status = "pending_visual_review"
    else:
        basis = "no_svg_renderer_yet"
        asset_file = None
        origin = "not_generated_yet"
        visual_parity = "not_started"
        review_status = "hard_pile_renderer_or_manual_exception"
        clean_ip_status = "not_applicable"

    selected_example = {
        "source": basis,
        "role": "selected_canonical_candidate",
        "path": asset_file,
        "status": review_status,
    }
    examples = [selected_example]
    examples.extend(example for example in draft.get("examples", []) if example != selected_example)

    return {
        "id": row["helm_catalog_id"],
        "asset": row["asset"],
        "name": draft.get("name") or row.get("description") or row["asset"],
        "kind": row["s52_asset_kind"],
        "family": row["family"],
        "tier": "chart-artifact",
        "asset_file": asset_file,
        "source_priority": {
            "selected_basis": basis,
            "selected_asset_file": asset_file,
            "selected_origin": origin,
            "fallback_generated_asset_file": draft_asset,
            "selection_rules": [
                "Use exact S-101 SVG geometry first when the master row maps to an exact S-101 symbol.",
                "Use Helm generated-owned multi-source draft SVG where no exact S-101 symbol exists.",
                "Keep non-symbol renderers, patterns, line styles, and conditional procedures in a logged hard-pile until their renderer exists.",
            ],
        },
        "source_refs": draft.get("source_refs", {}),
        "examples": examples,
        "palette_targets": _palette_targets(asset_file, basis),
        "qa": {
            "semantic_pass": draft.get("qa", {}).get("semantic_pass", False),
            "visual_parity": visual_parity,
            "final_approved": False,
            "review_status": review_status,
        },
        "provenance": {
            "origin": origin,
            "clean_ip_status": clean_ip_status,
            "license_status": "pending_iho_clearance" if basis == "s101_exact_svg" else draft.get("provenance", {}).get("clean_ip_status"),
            "reference_sources": ["s101", "opencpn_s52_tables", "aquamap_map_symbols", "chart1_mappings", "commons", "openbridge", "openmoji"],
            "forbidden_sources": row.get("forbidden_sources", []),
        },
    }


def build() -> dict:
    master = _read_json(MASTER)
    draft_pack = _read_json(DRAFT_PACK)
    draft_by_asset = {row["asset"]: row for row in draft_pack["symbols"]}

    rows = []
    for row in master["rows"]:
        rows.append(_selected_row(row, draft_by_asset[row["asset"]]))

    basis_counts = Counter(row["source_priority"]["selected_basis"] for row in rows)
    kind_counts = Counter(row["kind"] for row in rows)
    provenance_counts = Counter(row["provenance"]["origin"] for row in rows)
    usable_rows = sum(1 for row in rows if row["asset_file"])
    output = {
        "schema_version": 1,
        "scope": "source-priority full catalog icon pack; exact S-101 first, Helm-owned drafts second, hard-pile only for true gaps",
        "summary": {
            "master_rows": len(rows),
            "usable_svg_rows": usable_rows,
            "coverage_percent": round(usable_rows / len(rows) * 100, 2),
            "selected_s101_exact_svgs": basis_counts["s101_exact_svg"],
            "selected_helm_draft_svgs": basis_counts["helm_multisource_draft_svg"],
            "hard_pile_rows": basis_counts["no_svg_renderer_yet"],
            "origin_counts": dict(sorted(provenance_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "basis_counts": dict(sorted(basis_counts.items())),
            "limits": [
                "S-101 exact SVG rows are selected as reference art pending license/counsel clearance, not declared clean-IP Helm-owned artwork.",
                "Generated-owned draft rows still require visual repair against Aqua Map, OpenCPN, S-101, Chart 1, Commons, OpenBridge, and OpenMoji references.",
                "Hard-pile rows are logged explicitly; there are no silent caps.",
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
        "# Source-Priority Icon Pack",
        "",
        "Full-catalog production handoff pack. The selected asset for each row is chosen by priority: exact S-101 SVG, then Helm multi-source generated draft SVG, then hard-pile.",
        "",
        "## Summary",
        "",
        f"- Master rows: {summary['master_rows']}",
        f"- Usable SVG rows now selected: {summary['usable_svg_rows']} ({summary['coverage_percent']}%)",
        f"- Exact S-101 SVG selections: {summary['selected_s101_exact_svgs']}",
        f"- Helm generated draft fallback selections: {summary['selected_helm_draft_svgs']}",
        f"- Hard-pile rows: {summary['hard_pile_rows']}",
        "",
        "## Basis Counts",
        "",
    ]
    for key, value in summary["basis_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Origin Counts", ""])
    for key, value in summary["origin_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Limits", ""])
    for line in summary["limits"]:
        lines.append(f"- {line}")
    lines.append("")
    OUT_MD.write_text("\n".join(lines))


def main() -> int:
    output = build()
    summary = output["summary"]
    print("Source-priority icon pack")
    print(f"master rows: {summary['master_rows']}")
    print(f"usable SVG rows: {summary['usable_svg_rows']} ({summary['coverage_percent']}%)")
    print(f"S-101 exact selections: {summary['selected_s101_exact_svgs']}")
    print(f"Helm draft fallback selections: {summary['selected_helm_draft_svgs']}")
    print(f"hard-pile rows: {summary['hard_pile_rows']}")
    print(f"json: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
