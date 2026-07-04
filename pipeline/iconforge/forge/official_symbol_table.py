"""Build source-backed official symbol table artifacts.

This is the evidence layer for Icon Forge. It starts from the local Chart 1
Mappings PDF Q-section table, keeps that source reference-only, and records which
Helm/S-52 rows map to each official INT 1 row. It also links public-domain
Commons candidates and S-101 reference coverage where those exist.

Run:  python -m forge.official_symbol_table
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CHART1_MAPPING = CATALOG / "chart1_mappings_q_table.json"
CHART1_REPORT = ROOT / "out" / "chart1_mappings" / "chart1_mappings_q_table_report.json"
MASTER = CATALOG / "master_symbol_list.json"
COMMONS = CATALOG / "commons_nautical_chart_icons.json"

OUT_JSON = CATALOG / "official_symbol_table.json"
OUT_CSV = CATALOG / "official_symbol_table.csv"
OUT_YAML = CATALOG / "official_symbol_table.yaml"
OUT_MD = CATALOG / "official_symbol_table.md"

CSV_FIELDS = [
    "int1",
    "section",
    "official_name",
    "page",
    "s57_refs",
    "precise_s57_mappings",
    "symbol_reference",
    "row_reference",
    "precise_asset_count",
    "precise_assets",
    "attribute_match_count",
    "attribute_matched_assets",
    "broad_candidate_count",
    "broad_candidate_assets",
    "s101_exact_asset_count",
    "commons_candidate_count",
    "commons_candidate_titles",
    "evidence_status",
    "allowed_use",
    "forbidden_use",
]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _join(values: list | tuple | set) -> str:
    return "; ".join(str(value) for value in values if value not in {None, ""})


def _commons_by_int1(commons: dict) -> dict[str, list[dict]]:
    by_int1: dict[str, list[dict]] = {}
    for file_row in commons["files"]:
        candidates = file_row.get("mapping_candidates", {})
        if file_row.get("license_status") != "public_domain_or_cc0":
            continue
        for int1 in candidates.get("int1", []):
            by_int1.setdefault(int1, []).append({
                "title": file_row["title"],
                "url": file_row["url"],
                "description_url": file_row["description_url"],
                "license_status": file_row["license_status"],
                "mapping_confidence": candidates.get("mapping_confidence"),
            })
    return {key: sorted(rows, key=lambda row: row["title"]) for key, rows in sorted(by_int1.items())}


def _crop_by_int1(report: dict) -> dict[str, dict]:
    return {row["int1"]: row for row in report.get("entries", [])}


ATTR_ALIASES = {
    "TOPSH": "TOPSHP",
}


def _object_matches(token: str, asset_row: dict) -> bool:
    asset = asset_row["asset"].upper()
    object_class = (asset_row["s57_object_class"] or "").upper()
    token = token.upper()
    if token == "BOYXXX":
        return asset.startswith("BOY") or object_class.startswith("BOY")
    if token == "BCNXXX":
        return asset.startswith("BCN") or object_class.startswith("BCN")
    if token == "TOPMAR":
        return asset.startswith("TOP") or object_class == "TOPMAR"
    return token == object_class or asset.startswith(token)


def _condition_values(asset_row: dict, attr: str) -> list[str]:
    attr = ATTR_ALIASES.get(attr.upper(), attr.upper())
    values: list[str] = []
    for condition in asset_row.get("s57_conditions", []):
        text = str(condition).upper()
        if not text.startswith(attr):
            continue
        suffix = text[len(attr):]
        values.extend(part for part in suffix.replace("/", ",").split(",") if part)
    return values


def _attr_matches(attr_expr: str, asset_row: dict) -> bool:
    if "=" in attr_expr:
        attr, raw_values = attr_expr.split("=", 1)
        values = _condition_values(asset_row, attr)
        accepted = [value for value in raw_values.replace("/", ",").split(",") if value]
        return any(value in values for value in accepted)
    return bool(_condition_values(asset_row, attr_expr))


def _split_s57_ref(ref: str) -> tuple[str, list[str]]:
    parts = [part for part in ref.split(".") if part and not part.startswith("(X")]
    if not parts:
        return "", []
    return parts[0], parts[1:]


def _parsed_s57_mapping(ref: str) -> dict:
    object_token, attr_exprs = _split_s57_ref(ref)
    attrs = []
    for expr in attr_exprs:
        if "=" in expr:
            attr, values = expr.split("=", 1)
            attrs.append({
                "attribute": ATTR_ALIASES.get(attr.upper(), attr.upper()),
                "accepted_values": [value for value in values.replace("/", ",").split(",") if value],
                "match": "value_any",
            })
        else:
            attrs.append({
                "attribute": ATTR_ALIASES.get(expr.upper(), expr.upper()),
                "accepted_values": [],
                "match": "attribute_present",
            })
    return {
        "source_ref": ref,
        "object": object_token,
        "attributes": attrs,
        "precision": "object_and_attributes" if attrs else "object_only_broad",
    }


def _match_assets(mapping_row: dict, master_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    exact: dict[str, dict] = {}
    broad: dict[str, dict] = {}
    for ref in mapping_row.get("s57", []):
        object_token, attr_exprs = _split_s57_ref(ref)
        if not object_token:
            continue
        for asset_row in master_rows:
            if not _object_matches(object_token, asset_row):
                continue
            if attr_exprs and all(_attr_matches(expr, asset_row) for expr in attr_exprs):
                exact[asset_row["asset"]] = asset_row
            elif not attr_exprs:
                broad[asset_row["asset"]] = asset_row
    for asset in exact:
        broad.pop(asset, None)
    return (
        sorted(exact.values(), key=lambda row: row["asset"]),
        sorted(broad.values(), key=lambda row: row["asset"]),
    )


def _asset_payload(row: dict) -> dict:
    return {
        "asset": row["asset"],
        "helm_catalog_id": row["helm_catalog_id"],
        "s57_object_class": row["s57_object_class"],
        "s57_conditions": row["s57_conditions"],
        "s52_instruction": row["s52_instruction"],
        "art_state": row["art_state"],
        "visual_approval": row["visual_approval"],
        "s101_coverage": row["s101_coverage"],
        "commons_pd_candidate_count": row["commons_pd_candidate_count"],
    }


def _row(
    mapping_row: dict,
    crop_row: dict,
    exact_assets: list[dict],
    broad_assets: list[dict],
    commons_rows: list[dict],
    source: dict,
) -> dict:
    s101_exact = [row["asset"] for row in exact_assets if row["s101_coverage"] == "exact_symbol_match"]
    return {
        "int1": mapping_row["int1"],
        "section": mapping_row["section"],
        "official_name": mapping_row["name"],
        "source_page": mapping_row["page"],
        "s57_refs": mapping_row["s57"],
        "precise_s57_mappings": [_parsed_s57_mapping(ref) for ref in mapping_row["s57"]],
        "symbol_reference": {
            "status": "reference_only_not_canonical_artwork",
            "icon_reference_crop": crop_row.get("icon_reference_crop"),
            "icon_crop_box_pixels": crop_row.get("icon_crop_box_pixels"),
        },
        "row_reference": {
            "status": "reference_only_not_canonical_artwork",
            "row_crop": crop_row.get("row_crop"),
            "crop_box_pixels": crop_row.get("crop_box_pixels"),
        },
        "precise_helm_asset_matches": [_asset_payload(row) for row in exact_assets],
        "attribute_matched_helm_assets": [_asset_payload(row) for row in exact_assets],
        "broad_candidate_helm_assets": [_asset_payload(row) for row in broad_assets],
        "s101_exact_assets": s101_exact,
        "commons_public_domain_candidates": commons_rows,
        "evidence_status": _evidence_status(mapping_row, crop_row, exact_assets, broad_assets),
        "source_boundary": {
            "source_id": source["id"],
            "title": source["title"],
            "url": source["url"],
            "pdf_sha256": source["pdf_sha256"],
            "status": source["status"],
            "license_status": source["license_status"],
            "allowed_use": source["allowed_use"],
            "forbidden_use": source["forbidden_use"],
        },
    }


def _evidence_status(mapping_row: dict, crop_row: dict, exact_assets: list[dict], broad_assets: list[dict]) -> str:
    if not mapping_row.get("name") or not mapping_row.get("int1"):
        return "invalid_missing_official_name_or_id"
    if not crop_row:
        return "missing_reference_crop"
    if exact_assets:
        return "official_row_attribute_mapped"
    if broad_assets:
        return "official_row_broad_candidate_only"
    if not exact_assets:
        return "official_row_unmatched_to_helm_asset"
    return "official_row_unmatched_to_helm_asset"


def _csv_value(value) -> str:
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return _join(row.get("asset") or row.get("title") or json.dumps(row, sort_keys=True) for row in value)
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
            writer.writerow({
                "int1": row["int1"],
                "section": row["section"],
                "official_name": row["official_name"],
                "page": row["source_page"],
                "s57_refs": _csv_value(row["s57_refs"]),
                "precise_s57_mappings": _csv_value(row["precise_s57_mappings"]),
                "symbol_reference": row["symbol_reference"]["icon_reference_crop"],
                "row_reference": row["row_reference"]["row_crop"],
                "precise_asset_count": len(row["precise_helm_asset_matches"]),
                "precise_assets": _csv_value(row["precise_helm_asset_matches"]),
                "attribute_match_count": len(row["attribute_matched_helm_assets"]),
                "attribute_matched_assets": _csv_value(row["attribute_matched_helm_assets"]),
                "broad_candidate_count": len(row["broad_candidate_helm_assets"]),
                "broad_candidate_assets": _csv_value(row["broad_candidate_helm_assets"]),
                "s101_exact_asset_count": len(row["s101_exact_assets"]),
                "commons_candidate_count": len(row["commons_public_domain_candidates"]),
                "commons_candidate_titles": _csv_value(row["commons_public_domain_candidates"]),
                "evidence_status": row["evidence_status"],
                "allowed_use": _csv_value(row["source_boundary"]["allowed_use"]),
                "forbidden_use": _csv_value(row["source_boundary"]["forbidden_use"]),
            })


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
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def _write_yaml(output: dict) -> None:
    OUT_YAML.write_text("\n".join(_yaml_lines(output)) + "\n")


def _write_md(summary: dict) -> None:
    lines = [
        "# Official Symbol Table",
        "",
        "Source-backed official reference rows extracted from the local Chart 1 Mappings PDF Q-section table.",
        "",
        "## Summary",
        "",
        f"- Official source rows: {summary['official_rows']}",
        f"- Rows with local reference crops: {summary['rows_with_reference_crops']}",
        f"- Rows with attribute matches: {summary['rows_with_attribute_matches']}",
        f"- Attribute Helm asset links: {summary['attribute_helm_asset_links']}",
        f"- Rows with broad candidates only: {summary['rows_with_broad_candidates_only']}",
        f"- Commons public-domain candidate rows: {summary['rows_with_commons_candidates']}",
        f"- S-101 exact asset links through matched Helm rows: {summary['s101_exact_asset_links']}",
        "",
        "## Evidence Status",
        "",
    ]
    for status, count in summary["evidence_status_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Files",
        "",
        "- `catalog/official_symbol_table.yaml`",
        "- `catalog/official_symbol_table.json`",
        "- `catalog/official_symbol_table.csv`",
        "",
        "The Chart 1 Mappings crops are reference-only. They prove row identity/name/S-57 reference for QA, but they are not canonical artwork sources.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines))


def build() -> dict:
    mapping = _read_json(CHART1_MAPPING)
    if not CHART1_REPORT.exists():
        from . import chart1_mappings

        chart1_mappings.build_reference_crops()
    report = _read_json(CHART1_REPORT)
    master = _read_json(MASTER)
    commons = _read_json(COMMONS)
    master_rows = master["rows"]
    commons_by_int1 = _commons_by_int1(commons)
    crops = _crop_by_int1(report)

    rows = []
    for mapping_row in mapping["rows"]:
        exact_assets, broad_assets = _match_assets(mapping_row, master_rows)
        rows.append(
            _row(
                mapping_row,
                crops.get(mapping_row["int1"], {}),
                exact_assets,
                broad_assets,
                commons_by_int1.get(mapping_row["int1"], []),
                mapping["source"],
            )
        )
    evidence_counts = Counter(row["evidence_status"] for row in rows)
    summary = {
        "official_rows": len(rows),
        "rows_with_reference_crops": sum(1 for row in rows if row["symbol_reference"]["icon_reference_crop"]),
        "rows_with_attribute_matches": sum(1 for row in rows if row["attribute_matched_helm_assets"]),
        "attribute_helm_asset_links": sum(len(row["attribute_matched_helm_assets"]) for row in rows),
        "precise_helm_asset_links": sum(len(row["precise_helm_asset_matches"]) for row in rows),
        "rows_with_broad_candidates_only": sum(
            1 for row in rows if row["broad_candidate_helm_assets"] and not row["attribute_matched_helm_assets"]
        ),
        "broad_candidate_links": sum(len(row["broad_candidate_helm_assets"]) for row in rows),
        "rows_with_commons_candidates": sum(1 for row in rows if row["commons_public_domain_candidates"]),
        "commons_public_domain_candidate_links": sum(len(row["commons_public_domain_candidates"]) for row in rows),
        "s101_exact_asset_links": sum(len(row["s101_exact_assets"]) for row in rows),
        "evidence_status_counts": dict(sorted(evidence_counts.items())),
        "limits": [
            "This official table currently covers the local Chart 1 Mappings Q-section rows only.",
            "It validates row identity/name/reference symbol against the source table; it does not visually approve Helm-generated SVGs.",
            "Chart 1 Mappings crops are reference-only and cannot be converted into canonical SVG artwork without permission.",
        ],
    }
    output = {
        "schema_version": 1,
        "source": mapping["source"],
        "summary": summary,
        "formats": {
            "yaml": str(OUT_YAML.relative_to(ROOT)),
            "json": str(OUT_JSON.relative_to(ROOT)),
            "csv": str(OUT_CSV.relative_to(ROOT)),
        },
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    _write_csv(rows)
    _write_yaml(output)
    _write_md(summary)
    return output


def main() -> int:
    output = build()
    summary = output["summary"]
    print("Official symbol table")
    print(f"official rows: {summary['official_rows']}")
    print(f"rows with reference crops: {summary['rows_with_reference_crops']}")
    print(f"rows with attribute matches: {summary['rows_with_attribute_matches']}")
    print(f"attribute Helm asset links: {summary['attribute_helm_asset_links']}")
    print(f"yaml: {OUT_YAML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
