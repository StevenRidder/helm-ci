"""Build the full Icon Forge master symbol list.

This is the human-usable inventory for the full S-52/S-57-derived catalog. It
does not stop at the exact-crop subset: every required catalog row is listed
with current art state, S-57/S-52 metadata, Chart No.1 evidence, S-101 coverage,
Commons candidates, and the next action needed before it can be trusted.

Run:  python -m forge.master_symbol_list
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT_JSON = CATALOG / "master_symbol_list.json"
OUT_CSV = CATALOG / "master_symbol_list.csv"
OUT_MD = CATALOG / "master_symbol_list.md"

EXHAUSTIVE = CATALOG / "exhaustive_symbol_inventory.json"
CHART1_REPORT = ROOT / "out" / "chart1_parity" / "report.json"
EXACT_GATE = ROOT / "out" / "forge14_exact_crop_gate" / "report.json"
SYMBOLS = ROOT / "symbols.yaml"

CSV_FIELDS = [
    "row",
    "asset",
    "helm_catalog_id",
    "family",
    "description",
    "s52_instruction",
    "s52_asset_kind",
    "s57_object_class",
    "s57_lookup_id",
    "s57_rcid",
    "s57_conditions",
    "art_state",
    "visual_approval",
    "chart1_evidence_status",
    "chart1_gate_status",
    "chart1_crop_id",
    "chart1_pages",
    "chart1_verdict",
    "chart1_reason_codes",
    "s101_coverage",
    "s101_symbol_id",
    "s101_symbol_file",
    "s101_feature_rule",
    "s101_license_status",
    "commons_pd_candidate_count",
    "commons_candidate_titles",
    "chart1_mappings_int1_refs",
    "canonical_symbol_ids",
    "canonical_paths",
    "next_action",
    "forbidden_sources",
]

ART_STATE_TEXT = {
    "visual_approved": "Exact Chart No.1 visual approval is recorded.",
    "generated_owned_needs_visual_repair": "Generated owned SVG exists, but visual parity is not approved.",
    "external_pd_candidate_needs_review": "Public-domain/CC0 Commons candidate exists; review license, mapping, and visual parity.",
    "license_blocked_reference_only": "External match exists, but art use is not cleared for canonical packaging.",
    "manual_exception": "Manual domain/counsel review is required before generation or promotion.",
    "generate_owned": "No approved art exists; generate owned SVG from allowed references and metadata.",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _join(values: list | tuple | set) -> str:
    return "; ".join(str(value) for value in values if value not in {None, ""})


def _symbol_manifest_assets() -> dict[str, dict]:
    """Return asset -> generated canonical manifest ids/paths.

    The manifest is YAML, but its generated shape is simple and stable. Avoid a
    PyYAML dependency so this report remains runnable in the lightweight test
    environment.
    """
    assets: dict[str, dict] = {}
    current_id: str | None = None
    current_path: str | None = None
    current_asset: str | None = None
    for line in SYMBOLS.read_text().splitlines():
        id_match = re.match(r"  - id: (N\d+)", line)
        if id_match:
            current_id = id_match.group(1)
            current_path = None
            current_asset = None
            continue
        path_match = re.match(r"      canonical: (.+)", line)
        if path_match:
            current_path = path_match.group(1).strip()
            if current_asset:
                entry = assets[current_asset]
                if current_path not in entry["paths"]:
                    entry["paths"].append(current_path)
            continue
        asset_match = re.match(r"        asset: (.+)", line)
        if asset_match and current_id:
            asset = asset_match.group(1).strip().strip('"')
            current_asset = asset
            entry = assets.setdefault(asset, {"ids": [], "paths": []})
            entry["ids"].append(current_id)
            if current_path:
                entry["paths"].append(current_path)
    return assets


def _chart1_rows() -> dict[str, dict]:
    if not CHART1_REPORT.exists():
        return {}
    return {row["asset"]: row for row in _read_json(CHART1_REPORT)["rows"]}


def _gate_rows() -> dict[str, dict]:
    if not EXACT_GATE.exists():
        return {}
    return {row["asset"]: row for row in _read_json(EXACT_GATE)["rows"]}


def _s101_coverage(s101: dict) -> str:
    if s101.get("exact_symbol_match"):
        return "exact_symbol_match"
    if s101.get("feature_rule") or s101.get("rule_instruction_refs"):
        return "feature_rule_candidate"
    return "none"


def _art_state(row: dict, chart1: dict, manifest: dict) -> str:
    if chart1.get("final_approval"):
        return "visual_approved"
    if manifest:
        return "generated_owned_needs_visual_repair"
    status = row["status"]
    if status == "external_pd_candidate":
        return "external_pd_candidate_needs_review"
    if status == "license_blocked":
        return "license_blocked_reference_only"
    if status == "manual_exception":
        return "manual_exception"
    return "generate_owned"


def _next_action(art_state: str, chart1: dict, gate: dict) -> str:
    if art_state == "visual_approved":
        return "Keep approved; preserve source hashes and verifier evidence."
    if art_state == "generated_owned_needs_visual_repair":
        crop = chart1.get("reference_crop_id") or "exact Chart No.1 crop"
        return f"Repair generated SVG against {crop}; rerun deterministic and visual parity gates."
    if art_state == "external_pd_candidate_needs_review":
        return "Review Commons candidate license and semantic mapping; promote only after visual QA."
    if art_state == "license_blocked_reference_only":
        return "Use S-101/external art as reference only; generate owned art or clear license before packaging."
    if art_state == "manual_exception":
        reason = _join(gate.get("reason_codes", [])) if gate else ""
        suffix = f" Current reason: {reason}." if reason else ""
        return f"Record human/counsel/domain decision, then generate or explicitly exempt.{suffix}"
    return "Generate owned SVG from allowed Chart No.1/public-domain references plus local S-57/S-52 metadata."


def _row(index: int, row: dict, chart1: dict, gate: dict, manifest: dict) -> dict:
    s52 = row["s52"]
    s57 = row["s57"]
    s101 = row.get("s101", {})
    commons = row.get("commons", {}).get("public_domain_candidates", [])
    chart1_mapping_refs = row.get("chart1_mappings_q_reference", [])
    art_state = _art_state(row, chart1, manifest)
    return {
        "row": index,
        "asset": s52["asset"],
        "helm_catalog_id": row["helm_catalog_id"],
        "family": s52.get("family"),
        "description": s52.get("description", ""),
        "s52_instruction": s52.get("instruction"),
        "s52_asset_kind": s52.get("asset_kind"),
        "s57_object_class": s57.get("object_class"),
        "s57_lookup_id": s57.get("lookup_id"),
        "s57_rcid": s57.get("rcid"),
        "s57_conditions": s57.get("conditions", []),
        "art_state": art_state,
        "art_state_description": ART_STATE_TEXT[art_state],
        "visual_approval": "approved" if chart1.get("final_approval") else "not_approved",
        "chart1_evidence_status": row.get("chart1_reference_evidence_status"),
        "chart1_gate_status": gate.get("status", "not_in_forge14_scope"),
        "chart1_crop_id": chart1.get("reference_crop_id"),
        "chart1_pages": chart1.get("reference_pages", []),
        "chart1_verdict": chart1.get("verdict"),
        "chart1_reason_codes": chart1.get("reason_codes", []),
        "s101_coverage": _s101_coverage(s101),
        "s101_symbol_id": s101.get("symbol_id"),
        "s101_symbol_file": s101.get("symbol_file"),
        "s101_feature_rule": s101.get("feature_rule"),
        "s101_license_status": s101.get("license_status", "license_pending_reference"),
        "commons_pd_candidate_count": len(commons),
        "commons_candidate_titles": [candidate["title"] for candidate in commons[:8]],
        "chart1_mappings_int1_refs": [ref.get("int1") for ref in chart1_mapping_refs],
        "canonical_symbol_ids": manifest.get("ids", []),
        "canonical_paths": manifest.get("paths", []),
        "next_action": _next_action(art_state, chart1, gate),
        "forbidden_sources": [
            "OpenCPN GPL rastersymbol sprites",
            "Chart 1 Mappings cropped/extracted artwork without permission",
            "S-101 SVG bodies unless license/permission is cleared for canonical use",
        ],
    }


def _csv_value(value) -> str:
    if isinstance(value, list):
        return _join(value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def _write_csv(rows: list[dict]) -> None:
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in CSV_FIELDS})


def _summary(rows: list[dict], manifest_assets: dict[str, dict]) -> dict:
    art_counts = Counter(row["art_state"] for row in rows)
    chart1_counts = Counter(row["chart1_evidence_status"] for row in rows)
    gate_counts = Counter(row["chart1_gate_status"] for row in rows)
    s101_counts = Counter(row["s101_coverage"] for row in rows)
    family_counts = Counter(row["family"] for row in rows)
    return {
        "total_required_symbols": len(rows),
        "visual_approved": art_counts.get("visual_approved", 0),
        "generated_manifest_entries": sum(len(entry["ids"]) for entry in manifest_assets.values()),
        "generated_unique_assets": len(manifest_assets),
        "art_state_counts": dict(sorted(art_counts.items())),
        "chart1_evidence_counts": dict(sorted(chart1_counts.items())),
        "chart1_gate_status_counts": dict(sorted(gate_counts.items())),
        "s101_coverage_counts": dict(sorted(s101_counts.items())),
        "commons_pd_candidate_rows": sum(1 for row in rows if row["commons_pd_candidate_count"] > 0),
        "chart1_mappings_reference_rows": sum(1 for row in rows if row["chart1_mappings_int1_refs"]),
        "family_counts": dict(sorted(family_counts.items())),
        "non_go_conditions": [
            "The master list has 824 required catalog rows; the 139 exact-crop rows are only one subset.",
            "Generated owned SVGs are not accepted until Chart No.1 visual parity passes.",
            "S-101 and Esri-style external catalogs are reference/mapping inputs unless license review explicitly clears artwork reuse.",
            "Commons candidates require per-file license, semantic mapping, and visual QA before promotion.",
            "OpenCPN GPL raster sprites are forbidden as canonical artwork sources.",
        ],
    }


def _write_md(summary: dict) -> None:
    lines = [
        "# Icon Forge Master Symbol List",
        "",
        "This is the full S-52/S-57-derived master list for the Icon Forge asset pack. It is not limited to exact Chart No.1 crops.",
        "",
        "## Summary",
        "",
        f"- Required catalog rows: {summary['total_required_symbols']}",
        f"- Chart No.1 visually approved rows: {summary['visual_approved']}",
        f"- Generated manifest entries: {summary['generated_manifest_entries']}",
        f"- Generated unique assets: {summary['generated_unique_assets']}",
        f"- Commons public-domain candidate rows: {summary['commons_pd_candidate_rows']}",
        f"- Chart 1 Mappings reference rows: {summary['chart1_mappings_reference_rows']}",
        "",
        "## Art State Counts",
        "",
    ]
    for status, count in summary["art_state_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Chart No.1 Evidence Counts", ""])
    for status, count in summary["chart1_evidence_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## S-101 Coverage Counts", ""])
    for status, count in summary["s101_coverage_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Non-Go Conditions", ""])
    for item in summary["non_go_conditions"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Files",
        "",
        "- `catalog/master_symbol_list.csv`: flat spreadsheet-ready master list.",
        "- `catalog/master_symbol_list.json`: structured master list with summary and rows.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines))


def build() -> dict:
    exhaustive = _read_json(EXHAUSTIVE)
    chart1_by_asset = _chart1_rows()
    gate_by_asset = _gate_rows()
    manifest_assets = _symbol_manifest_assets()

    rows = []
    for index, source_row in enumerate(exhaustive["rows"], start=1):
        asset = source_row["s52"]["asset"]
        rows.append(
            _row(
                index,
                source_row,
                chart1_by_asset.get(asset, {}),
                gate_by_asset.get(asset, {}),
                manifest_assets.get(asset, {}),
            )
        )

    summary = _summary(rows, manifest_assets)
    output = {
        "schema_version": 1,
        "summary": summary,
        "art_state_taxonomy": ART_STATE_TEXT,
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    _write_csv(rows)
    _write_md(summary)
    return output


def main() -> int:
    output = build()
    summary = output["summary"]
    print("Icon Forge master symbol list")
    print(f"required rows: {summary['total_required_symbols']}")
    print(f"visual approved: {summary['visual_approved']}")
    print(f"generated unique assets: {summary['generated_unique_assets']}")
    print(f"csv: {OUT_CSV}")
    print(f"json: {OUT_JSON}")
    print(f"summary: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
