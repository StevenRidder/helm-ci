"""Validate Chart 1 Mappings semantic generation targets.

These rows cover precise S-57 mappings whose source-table symbol cell may be
blank. They are generator targets, not source-art approvals.

Run:  python -m forge.chart1_semantic_targets
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ROOT / "catalog" / "chart1_mappings_semantic_targets.json"
REPORT = ROOT / "out" / "chart1_mappings" / "chart1_mappings_semantic_targets_report.json"


def load_targets() -> dict:
    return json.loads(TARGETS.read_text())


def parse_s57_ref(ref: str) -> dict:
    parts = [part for part in ref.split(".") if part]
    if not parts:
        return {"source_ref": ref, "object": "", "attributes": []}
    attributes = []
    for expr in parts[1:]:
        if "=" in expr:
            attribute, values = expr.split("=", 1)
            attributes.append({
                "attribute": attribute,
                "accepted_values": [value for value in values.replace("/", ",").split(",") if value],
                "match": "value_any",
            })
        else:
            attributes.append({
                "attribute": expr,
                "accepted_values": [],
                "match": "attribute_present",
            })
    return {
        "source_ref": ref,
        "object": parts[0],
        "attributes": attributes,
    }


def validate_targets(data: dict) -> list[str]:
    errors: list[str] = []
    source = data.get("source", {})
    targets = data.get("targets", [])
    ids = [target.get("target_id") for target in targets]

    if source.get("status") != "reference_only":
        errors.append("source.status must be reference_only")
    if "canonical_asset_source" not in set(source.get("forbidden_use", [])):
        errors.append("canonical_asset_source must be forbidden")
    if "semantic_generation_target" not in set(source.get("allowed_use", [])):
        errors.append("semantic_generation_target must be allowed")
    if len(ids) != len(set(ids)):
        errors.append("duplicate target ids found")
    for target in targets:
        target_id = target.get("target_id", "")
        if not re.fullmatch(r"[A-Z0-9_]+", target_id):
            errors.append(f"invalid target_id: {target_id}")
        if not target.get("official_name"):
            errors.append(f"{target_id} missing official_name")
        if not target.get("s57_refs"):
            errors.append(f"{target_id} missing s57_refs")
        if not target.get("generation_target", {}).get("visual_brief"):
            errors.append(f"{target_id} missing visual_brief")
        status = target.get("source_table", {}).get("symbol_cell_status")
        if status not in {"source_symbol_present", "no_symbol_in_source_table"}:
            errors.append(f"{target_id} has invalid symbol_cell_status")
        if status == "no_symbol_in_source_table" and target.get("source_table", {}).get("source_crop_status") != "not_applicable":
            errors.append(f"{target_id} must not claim a crop")
        for ref in target.get("s57_refs", []):
            parsed = parse_s57_ref(ref)
            if not parsed["object"] or not parsed["attributes"]:
                errors.append(f"{target_id} has imprecise S-57 ref: {ref}")
    return errors


def build_report() -> dict:
    data = load_targets()
    errors = validate_targets(data)
    if errors:
        raise ValueError("; ".join(errors))

    rows = []
    for target in data["targets"]:
        rows.append({
            "target_id": target["target_id"],
            "official_name": target["official_name"],
            "s57_mappings": [parse_s57_ref(ref) for ref in target["s57_refs"]],
            "symbol_cell_status": target["source_table"]["symbol_cell_status"],
            "expected_symbol": target["generation_target"]["expected_symbol"],
            "origin": target["generation_target"]["origin"],
            "qa": target["qa"],
        })

    report = {
        "status": "pass",
        "source": data["source"],
        "target_count": len(rows),
        "counts": {
            "source_symbol_present": sum(1 for row in rows if row["symbol_cell_status"] == "source_symbol_present"),
            "semantic_only": sum(1 for row in rows if row["symbol_cell_status"] == "no_symbol_in_source_table"),
        },
        "rows": rows,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    report = build_report()
    print(json.dumps({
        "status": report["status"],
        "target_count": report["target_count"],
        "counts": report["counts"],
        "report": str(REPORT),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
