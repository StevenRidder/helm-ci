"""Build the full-catalog S-101 resolver ledger from standards tuples.

This is the FORGE-23 production-shaped successor to the earlier scale125
resolver scaffold. It does not vendor IHO catalogue files or OpenCPN artwork;
it records standards/reference evidence and resolver decisions derived from
the clean-room standards tuple ledger.

Run:  python -m forge.standards_s101_resolver
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TUPLE_LEDGER = ROOT / "catalog" / "standards_tuple_alignment.json"
DEFAULT_OUT = ROOT / "catalog" / "standards_s101_resolver.json"
DEFAULT_MD = ROOT / "catalog" / "standards_s101_resolver.md"


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _instruction_kind(geometry: str | None) -> str:
    if geometry == "line":
        return "LineInstruction"
    if geometry == "area":
        return "AreaInstruction"
    if geometry == "conditional":
        return "ConditionalInstruction"
    return "PointInstruction"


def _display_profile(tuple_: dict[str, Any], mapping_type: str) -> dict[str, Any]:
    mode = tuple_.get("display_mode") or "unspecified"
    geometry = tuple_.get("geometry")
    if mode == "simplified":
        profile = "simplified-symbol"
    elif mode == "full-chart":
        profile = "paper-chart-full-symbol"
    elif geometry == "line":
        profile = "line-style"
    elif geometry == "area":
        profile = "area-pattern"
    elif geometry == "conditional":
        profile = "conditional-portrayal"
    else:
        profile = "standard-symbol"
    return {
        "profile": profile,
        "source_display_mode": mode,
        "geometry": geometry,
        "palette_behavior": "tokenized-by-renderer",
        "requires_visual_gate": mapping_type != "direct_asset_match",
    }


def _unresolved_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    tuple_ = row["semantic_tuple"]
    s101 = row.get("s101") or {}
    if not s101.get("feature_type"):
        reasons.append("missing_s101_feature_or_rule")
    if row.get("tuple_status") != "complete":
        reasons.extend([f"tuple_missing_{reason}" for reason in row.get("missing_data_reasons", [])])
    if tuple_.get("geometry") == "conditional":
        reasons.append("conditional_portrayal_requires_rule_output_resolution")
    if not s101.get("symbol_id") and row.get("s101_mapping_type") == "unresolved":
        reasons.append("no_direct_s101_symbol_and_no_rule_equivalence")
    return sorted(set(reasons or ["resolver_review_required"]))


def _has_catalogue_rule_evidence(row: dict[str, Any]) -> bool:
    s101 = row.get("s101") or {}
    return bool(s101.get("feature_type") and s101.get("feature_rule_file"))


def _crosswalk_classification(row: dict[str, Any]) -> dict[str, Any]:
    """Classify every row without inventing S-101 equivalence.

    Exact S-101 SVG names are only one proof path. The S-101 portrayal model
    also resolves many S-57 rows through feature rules plus attributes, so
    missing same-name SVGs must not be treated as missing mappings.
    """
    tuple_ = row["semantic_tuple"]
    s101 = row.get("s101") or {}
    object_class = str(tuple_.get("object_class") or "")
    symbol_id = str(tuple_.get("s52_symbol_id") or "")
    mapping_type = row.get("s101_mapping_type")
    rule_refs = s101.get("rule_instruction_refs") or []

    if mapping_type == "direct_asset_match":
        return {
            "class": "s101_feature_equivalent",
            "basis": "direct_s101_symbol_reference",
            "runtime_scope": "chart_portrayal",
            "requires_manual_crosswalk": False,
        }
    if mapping_type == "rule_derived_equivalent":
        return {
            "class": "s101_feature_equivalent",
            "basis": "s101_feature_rule_and_attributes",
            "runtime_scope": "chart_portrayal",
            "requires_manual_crosswalk": False,
        }
    if mapping_type == "acceptable_deviation":
        return {
            "class": "s101_feature_equivalent_with_documented_deviation",
            "basis": "s52_s101_portrayal_difference",
            "runtime_scope": "chart_portrayal",
            "requires_manual_crosswalk": False,
        }
    if object_class.startswith("$"):
        return {
            "class": "non_s101_runtime_construct",
            "basis": "s52_display_construct_not_s57_feature",
            "runtime_scope": "renderer_overlay_or_ui",
            "requires_manual_crosswalk": False,
        }
    if object_class in {"ownshp", "vessel", "pastrk", "plnpos", "ebline"} or symbol_id.startswith(("AIS", "ARP", "OWN", "PLN", "VRM")):
        return {
            "class": "non_s101_runtime_construct",
            "basis": "navigation_runtime_overlay_not_enc_feature",
            "runtime_scope": "ownship_ais_arpa_route_overlay",
            "requires_manual_crosswalk": False,
        }
    if object_class.islower() or object_class.startswith("_"):
        return {
            "class": "non_s101_or_inland_extension",
            "basis": "lowercase_or_extension_object_class_without_s101_catalogue_evidence",
            "runtime_scope": "extension_profile_or_manual_mapping",
            "requires_manual_crosswalk": True,
        }
    if _has_catalogue_rule_evidence(row):
        return {
            "class": "s101_feature_equivalent",
            "basis": "s101_catalogue_rule_reference",
            "runtime_scope": "chart_portrayal",
            "requires_manual_crosswalk": False,
        }
    if rule_refs:
        return {
            "class": "manual_s101_crosswalk_required",
            "basis": "s101_rule_reference_without_feature_binding",
            "runtime_scope": "manual_review",
            "requires_manual_crosswalk": True,
        }
    return {
        "class": "manual_s101_crosswalk_required",
        "basis": "no_s101_feature_rule_or_runtime_construct_classification",
        "runtime_scope": "manual_review",
        "requires_manual_crosswalk": True,
    }


def _portrayal_basis(row: dict[str, Any]) -> dict[str, Any]:
    tuple_ = row["semantic_tuple"]
    s101 = row.get("s101") or {}
    mapping_type = row.get("s101_mapping_type")
    exact = mapping_type == "direct_asset_match"
    instruction_kind = _instruction_kind(tuple_.get("geometry"))
    rule_refs = s101.get("rule_instruction_refs") or []

    if exact and s101.get("symbol_id"):
        instructions = [{
            "kind": instruction_kind,
            "basis": "direct_s101_symbol_reference",
            "symbol_id": s101.get("symbol_id"),
            "symbol_file": s101.get("symbol_file"),
            "rule_file": s101.get("feature_rule_file"),
        }]
    elif s101.get("feature_type") and mapping_type in {"rule_derived_equivalent", "acceptable_deviation"}:
        instructions = [{
            "kind": instruction_kind,
            "basis": mapping_type,
            "feature_type": s101.get("feature_type"),
            "rule_file": s101.get("feature_rule_file"),
            "attributes": s101.get("attributes") or {},
            "symbol_id": s101.get("symbol_id"),
            "symbol_file": s101.get("symbol_file"),
        }]
    elif rule_refs:
        instructions = [{
            "kind": ref.get("kind") or instruction_kind,
            "basis": "catalog_rule_reference",
            "feature_type": s101.get("feature_type"),
            "rule": ref.get("rule"),
            "rule_file": ref.get("file") or s101.get("feature_rule_file"),
        } for ref in rule_refs]
    else:
        instructions = []

    return {
        "feature_type": s101.get("feature_type"),
        "feature_rule_file": s101.get("feature_rule_file"),
        "attributes": s101.get("attributes") or {},
        "direct_symbol": {
            "matched": exact,
            "symbol_id": s101.get("symbol_id"),
            "symbol_file": s101.get("symbol_file"),
        },
        "instruction_basis": instructions,
        "rule_instruction_refs": rule_refs,
        "license_status": s101.get("license_status", "reference_only_not_bundled"),
    }


def resolve_row(row: dict[str, Any]) -> dict[str, Any]:
    tuple_ = row["semantic_tuple"]
    mapping_type = row["s101_mapping_type"]
    s101 = row.get("s101") or {}
    direct_symbol = s101.get("symbol_id")
    exact_filename_match = bool(mapping_type == "direct_asset_match" and direct_symbol)
    false_filename_gap = bool(not direct_symbol and mapping_type in {"rule_derived_equivalent", "acceptable_deviation"})
    classification = _crosswalk_classification(row)
    if mapping_type == "direct_asset_match":
        resolver_status = "resolved_direct"
        reasons: list[str] = []
    elif mapping_type == "rule_derived_equivalent":
        resolver_status = "resolved_rule"
        reasons = []
    elif mapping_type == "acceptable_deviation":
        resolver_status = "resolved_with_deviation"
        reasons = ["acceptable_s52_s101_portrayal_difference"]
    elif classification["basis"] in {"s101_catalogue_rule_reference", "s101_rule_instruction_reference"}:
        resolver_status = "resolved_rule_catalogue"
        reasons = ["no_direct_s101_symbol_file", classification["basis"]]
    elif classification["class"] == "non_s101_runtime_construct":
        resolver_status = "classified_non_s101_runtime"
        reasons = [classification["basis"]]
    elif classification["class"] == "non_s101_or_inland_extension":
        resolver_status = "classified_extension_requires_profile"
        reasons = [classification["basis"]]
    elif classification["class"] == "manual_s101_crosswalk_required":
        resolver_status = "manual_crosswalk_required"
        reasons = _unresolved_reasons(row)
    else:
        resolver_status = "unresolved"
        reasons = _unresolved_reasons(row)

    return {
        "helm_catalog_id": row["helm_catalog_id"],
        "source_table_id": row.get("source_table_id"),
        "s52_symbol_id": tuple_.get("s52_symbol_id"),
        "object_class": tuple_.get("object_class"),
        "semantic_tuple": tuple_,
        "tuple_status": row.get("tuple_status"),
        "s101_mapping_type": mapping_type,
        "resolver_status": resolver_status,
        "s101_crosswalk_classification": classification,
        "exact_filename_match": exact_filename_match,
        "false_filename_gap": false_filename_gap,
        "display_profile": _display_profile(tuple_, mapping_type),
        "portrayal_evidence": _portrayal_basis(row),
        "unresolved_reasons": reasons,
        "source_refs": {
            "standards_tuple_alignment": "catalog/standards_tuple_alignment.json",
            "standard_source_table": row.get("source_refs", {}).get("standard_source_table"),
            "s52_s57_s101_crosswalk": row.get("source_refs", {}).get("s52_s57_s101_crosswalk"),
        },
    }


def build() -> dict[str, Any]:
    source = _read(TUPLE_LEDGER)
    rows = [resolve_row(row) for row in source["rows"]]
    mapping_counts = Counter(row["s101_mapping_type"] for row in rows)
    status_counts = Counter(row["resolver_status"] for row in rows)
    false_gap_count = sum(1 for row in rows if row["false_filename_gap"])
    return {
        "schema": "helm.forge.standards-s101-resolver.v1",
        "status": "provisional_s101_resolver_ready",
        "source": {
            "standards_tuple_alignment": "catalog/standards_tuple_alignment.json",
            "source_head": "ac276390f2bee11b63744a3aab4ef3a7e3ae557e",
            "source_pr": "https://github.com/StevenRidder/Helm/pull/243",
        },
        "clean_room_boundary": {
            "bundled_iho_catalog_files": False,
            "bundled_iho_svg_artwork": False,
            "bundled_opencpn_artwork": False,
            "reference_only_inputs": [
                "S-52/S-57/S-101 vocabulary and feature/rule names",
                "S-101 rule/file identifiers as standards evidence",
                "OpenCPN render outputs as comparison targets only",
                "Chart No.1 crops as public reference evidence only",
            ],
        },
        "coverage": {
            "rows": len(rows),
            "s101_mapping_type_counts": dict(sorted(mapping_counts.items())),
            "resolver_status_counts": dict(sorted(status_counts.items())),
            "false_filename_gap_count": false_gap_count,
        },
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    return "\n".join([
        "# Standards S-101 Resolver",
        "",
        f"Status: `{result['status']}`",
        "",
        "Full-catalog S-101 resolver artifact built from",
        "`catalog/standards_tuple_alignment.json`.",
        "",
        f"- rows: `{coverage['rows']}`",
        f"- s101_mapping_type_counts: `{coverage['s101_mapping_type_counts']}`",
        f"- resolver_status_counts: `{coverage['resolver_status_counts']}`",
        f"- false_filename_gap_count: `{coverage['false_filename_gap_count']}`",
        "",
        "Direct filename matches, rule-derived equivalents, acceptable deviations,",
        "and unresolved rows are separated so missing S-101 filenames do not",
        "masquerade as missing S-101 portrayal coverage.",
        "",
        "OpenCPN/IHO/Chart No.1 materials remain reference/comparison evidence,",
        "not source artwork or bundled catalogue material.",
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
    print(f"standards S-101 resolver -> {args.out}")
    print(f"standards S-101 summary -> {args.md}")
    print(f"coverage: {result['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
