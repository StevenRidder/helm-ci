"""Build owned canonical SVGs from exact Chart No.1 crop rows.

This is the conservative FORGE-15 asset lane: only rows with
reference_evidence_status=exact_symbol_crop are admitted. Each accepted row
gets one canonical SVG and one symbols.yaml entry. Broad class-panel and
multi-symbol references stay out of this artifact pack.

Run:  python -m forge.exact_symbol_assets
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import chart1_parity


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "svg" / "canonical"
SYMBOLS = ROOT / "symbols.yaml"
REPORT = ROOT / "out" / "chart1_parity" / "report.json"
CATALOG = ROOT / "pilots" / "full_catalog.json"
PROVENANCE = ROOT / "out" / "chart1_parity" / "reference_provenance.json"
S101_REPO = "https://github.com/iho-ohi/S-101_Portrayal-Catalogue"
ESRI_REPO = "https://github.com/Esri/nautical-chart-symbols"
WIKIMEDIA_CATEGORY = "https://commons.wikimedia.org/wiki/Category:SVG_Nautical_Chart_icons"
CHART1_MAPPINGS_URL = "file:///Users/steveridder/Downloads/Chart%201%20Mappings.pdf"
CHART1_MAPPINGS_TITLE = "Chart 1 Mappings - Symbols Abbreviations Terms and S-57 Objects"
CHART1_MAPPINGS_SHA256 = "6768d3935f312310686d94dc78683fa29f1e5c00901cd9cf0978481cfd54af64"


def _ensure_report() -> dict:
    if not REPORT.exists():
        rc = chart1_parity.main([])
        if rc != 0:
            raise RuntimeError("chart1 parity report generation failed")
    return json.loads(REPORT.read_text())


def _catalog_by_asset() -> dict[str, dict]:
    catalog = json.loads(CATALOG.read_text())
    return {entry["asset"]: entry for entry in catalog["entries"]}


def _reference_provenance() -> dict:
    return json.loads(PROVENANCE.read_text())


def _shape(row: dict) -> str:
    crop = row["reference_crop_id"]
    chart_class = row["chart1_class"].lower()
    if crop == "topmark_cone_up":
        return '<polygon points="32,22 25,42 39,42" fill="var(--black)"/>'
    if crop == "topmark_cone_down":
        return '<polygon points="25,22 39,22 32,42" fill="var(--black)"/>'
    if crop == "topmark_sphere":
        return '<circle cx="32" cy="32" r="7" fill="var(--black)"/>'
    if crop == "topmark_x_shape":
        return '<path d="M25 25l14 14M39 25L25 39" fill="none" stroke="var(--black)" stroke-width="5" stroke-linecap="round"/>'
    if crop == "topmark_t_shape":
        return '<path d="M24 24h16M32 24v20" fill="none" stroke="var(--black)" stroke-width="5" stroke-linecap="round"/>'
    if crop == "topmark_cross_circle":
        return '<circle cx="32" cy="38" r="6" fill="none" stroke="var(--black)" stroke-width="3"/><path d="M32 17v16M25 25h14" fill="none" stroke="var(--black)" stroke-width="4" stroke-linecap="round"/>'
    if crop == "topmark_flag_other":
        return '<polygon points="31,22 37,21 33,43 27,44" fill="var(--black)"/>'
    if crop == "topmark_horizontal_board":
        return '<polygon points="22,28 42,26 42,36 22,38" fill="var(--white)" stroke="var(--black)" stroke-width="3"/>'
    if crop == "topmark_vertical_rectangle":
        return '<polygon points="29,23 37,23 35,42 27,42" fill="var(--white)" stroke="var(--black)" stroke-width="3"/>'
    if crop == "topmark_cube_point_up" or "rhombus" in chart_class or "cube" in chart_class:
        return '<polygon points="32,23 40,32 32,41 24,32" fill="var(--white)" stroke="var(--black)" stroke-width="3"/>'
    raise ValueError(f"unhandled exact crop {crop!r} for {row['asset']}")


def _svg(row: dict) -> str:
    body = _shape(row)
    title = _escape(row["chart1_class"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
        f'role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<g data-forge-source="chart1-exact-crop" data-chart1-crop="{row["reference_crop_id"]}" '
        f'data-s52-asset="{row["asset"]}">{body}</g>'
        "</svg>\n"
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _yaml_string(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", value):
        return value
    return json.dumps(value)


def _yaml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return _yaml_string(str(value))


def _yaml_list(values: list) -> str:
    return "[" + ", ".join(_yaml_value(v) for v in values) + "]"


def _symbol_entry(symbol_id: str, row: dict, catalog_entry: dict, provenance: dict) -> list[str]:
    path = f"assets/svg/canonical/{symbol_id}.svg"
    crop = provenance["crops"][row["reference_crop_id"]]
    lines = [
        f"  - id: {symbol_id}",
        f"    name: {_yaml_string(row['chart1_class'])}",
        "    kind: chart-symbol",
        "    tier: chart-artifact",
        "    source_refs:",
        "      chart1:",
        "        status: exact_symbol_crop",
        f"        pdf_url: {_yaml_string(provenance['pdf_url'])}",
        f"        record_url: {_yaml_string(provenance['record_url'])}",
        f"        pdf_sha256: {_yaml_string(provenance['pdf_sha256'])}",
        f"        page: {crop['page']}",
        f"        crop_id: {_yaml_string(row['reference_crop_id'])}",
        f"        crop_box_unit: {_yaml_list(crop['box_unit'])}",
        f"        crop_sha256: {_yaml_string(crop['sha256'])}",
        f"        chart1_class: {_yaml_string(row['chart1_class'])}",
        "      s52:",
        f"        object_class: {_yaml_string(catalog_entry.get('object_class') or row['asset'])}",
        f"        asset: {_yaml_string(row['asset'])}",
        f"        lookup_id: {_yaml_string(str(catalog_entry.get('lookup_id') or ''))}",
        f"        rcid: {_yaml_string(str(catalog_entry.get('rcid') or ''))}",
        f"        conditions: {_yaml_list(catalog_entry.get('conditions') or [])}",
        "      s101:",
        f"        repository: {_yaml_string(S101_REPO)}",
        "        status: reference_catalog_candidate",
        "        mapping_status: pending_crosswalk",
        "        license_status: review_required_before_artwork_use",
        "      esri:",
        f"        repository: {_yaml_string(ESRI_REPO)}",
        "        status: reference_catalog_candidate",
        "        mapping_status: pending_crosswalk",
        "        license_status: apache-2.0-reference-candidate",
        "      wikimedia:",
        f"        category: {_yaml_string(WIKIMEDIA_CATEGORY)}",
        "        status: reference_catalog_candidate",
        "        mapping_status: pending_per_file_match",
        "        license_status: per-file-license-review-required",
        "      chart1_mappings:",
        f"        url: {_yaml_string(CHART1_MAPPINGS_URL)}",
        f"        title: {_yaml_string(CHART1_MAPPINGS_TITLE)}",
        f"        pdf_sha256: {_yaml_string(CHART1_MAPPINGS_SHA256)}",
        "        status: reference_only",
        "        mapping_status: pending_int1_s57_crosswalk",
        "        license_status: permission_required_before_artwork_use",
        "        allowed_use:",
        "          - name_mapping",
        "          - s57_object_crosswalk",
        "          - int1_section_cross_check",
        "          - semantic_qa",
        "        forbidden_use:",
        "          - crop_extract_svg",
        "          - direct_artwork_derivation",
        "    asset:",
        f"      canonical: {path}",
        "    qa:",
        "      semantic_pass: true",
        "      visual_parity: pending",
        "      source_license_checked: false",
        "    license_status:",
        "      canonical_asset: generated-owned-artwork",
        "      chart1: allowed-public-domain-reference",
        "      s52: local-metadata-lookup",
        "      s101: reference-only-license-review-required",
        "      esri: apache-2.0-reference-candidate",
        "      wikimedia: per-file-license-review-required",
        "      chart1_mappings: reference-only-permission-required",
        "    provenance:",
        "      origin: generated-owned-artwork",
        "      allowed_sources:",
        "        - public-domain Chart No.1 reference",
        "        - local metadata lookup",
        "      reference_only_sources:",
        "        - IHO S-101 Portrayal Catalogue",
        "        - Esri nautical-chart-symbols",
        "        - Wikimedia Commons per-file SVG references",
        "        - Chart 1 Mappings S-57 Objects reference",
        "      forbidden_sources:",
        "        - OpenCPN GPL rastersymbol sprites",
        "        - Chart 1 Mappings cropped/extracted artwork without permission",
    ]
    return lines


def build() -> dict:
    report = _ensure_report()
    catalog = _catalog_by_asset()
    provenance = _reference_provenance()
    rows = [
        row for row in report["rows"]
        if row["reference_evidence_status"] == "exact_symbol_crop"
    ]
    rows = sorted(rows, key=lambda row: (row["asset"], row["reference_crop_id"]))

    OUT.mkdir(parents=True, exist_ok=True)
    yaml_lines = [
        "symbols:",
    ]
    entries = []
    for i, row in enumerate(rows, start=1):
        symbol_id = f"N{i:04d}"
        svg_path = OUT / f"{symbol_id}.svg"
        svg_path.write_text(_svg(row))
        entry = catalog[row["asset"]]
        yaml_lines.extend(_symbol_entry(symbol_id, row, entry, provenance))
        entries.append({
            "id": symbol_id,
            "asset": row["asset"],
            "chart1_crop": row["reference_crop_id"],
            "svg": svg_path.relative_to(ROOT).as_posix(),
        })

    SYMBOLS.write_text("\n".join(yaml_lines) + "\n")
    result = {
        "status": "pass",
        "selected_exact_symbol_crops": len(rows),
        "symbols_yaml": SYMBOLS.relative_to(ROOT).as_posix(),
        "canonical_svg_dir": OUT.relative_to(ROOT).as_posix(),
        "entries": entries,
    }
    return result


def main() -> int:
    result = build()
    print(f"exact symbol assets: {result['status'].upper()}")
    print(f"exact rows: {result['selected_exact_symbol_crops']}")
    print(f"manifest: {result['symbols_yaml']}")
    print(f"canonical SVGs: {result['canonical_svg_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
