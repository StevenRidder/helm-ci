"""Audit S-101 mapping and witness-display consistency.

This is a proof artifact, not a mapper. It verifies that every row is accounted
for, that resolved rows do not contradict their semantic colour tuple, and that
the human approval page labels raw S-101 SVGs as shape witnesses instead of
colour-resolved portrayal.

Run:
  python3 -m forge.s101_mapping_audit
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import human_review_page


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
RESOLVER = CATALOG / "standards_s101_resolver.json"
DEFAULT_OUT = CATALOG / "s101_mapping_audit.json"
DEFAULT_MD = CATALOG / "s101_mapping_audit.md"


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _colour_mismatches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = []
    for row in rows:
        if row.get("resolver_status") == "unresolved":
            continue
        attrs = (row.get("portrayal_evidence") or {}).get("attributes") or {}
        semantic = row.get("semantic_tuple") or {}
        attr_colours = attrs.get("colour") or []
        semantic_colours = semantic.get("colour_sequence") or []
        if attr_colours and semantic_colours and attr_colours != semantic_colours:
            mismatches.append({
                "symbol_id": row.get("s52_symbol_id"),
                "resolver_status": row.get("resolver_status"),
                "s101_mapping_type": row.get("s101_mapping_type"),
                "portrayal_colours": attr_colours,
                "semantic_colours": semantic_colours,
            })
    return mismatches


def _human_review_witness_gaps() -> dict[str, list[str]]:
    rows = human_review_page._read_json(human_review_page.TABLE)["rows"]
    missing_id = []
    missing_note = []
    for row in rows:
        refs = (row.get("reference_providers") or {}).get("s101") or []
        if not refs:
            continue
        payload = human_review_page._row_payload(row)
        if not payload["s101_symbol_id"]:
            missing_id.append(row["asset"])
        if "raw SVG is not color-resolved portrayal" not in payload["s101_witness_note"]:
            missing_note.append(row["asset"])
    return {
        "missing_symbol_id": missing_id,
        "missing_shape_witness_note": missing_note,
    }


def build() -> dict[str, Any]:
    resolver = _read(RESOLVER)
    rows = resolver["rows"]
    status_counts = Counter(row["resolver_status"] for row in rows)
    mapping_counts = Counter(row["s101_mapping_type"] for row in rows)
    class_counts = Counter(
        (row.get("s101_crosswalk_classification") or {}).get("class", "unknown")
        for row in rows
    )
    unresolved = [
        {
            "symbol_id": row["s52_symbol_id"],
            "object_class": row.get("object_class"),
            "tuple_status": row.get("tuple_status"),
            "unresolved_reasons": row.get("unresolved_reasons") or [],
        }
        for row in rows
        if row["resolver_status"] == "unresolved"
    ]
    feature_equivalent_statuses = {
        "resolved_direct",
        "resolved_rule",
        "resolved_rule_catalogue",
        "resolved_with_deviation",
    }
    s101_feature_equivalent = sum(
        count for status, count in status_counts.items()
        if status in feature_equivalent_statuses
    )
    non_s101_or_extension = len(rows) - s101_feature_equivalent - len(unresolved)
    witness_gaps = _human_review_witness_gaps()
    colour_mismatches = _colour_mismatches(rows)
    return {
        "schema": "helm.forge.s101-mapping-audit.v1",
        "status": "review_required" if unresolved else "pass",
        "coverage": {
            "rows": len(rows),
            "s101_feature_equivalent": s101_feature_equivalent,
            "non_s101_or_extension": non_s101_or_extension,
            "unresolved": len(unresolved),
            "resolver_status_counts": dict(sorted(status_counts.items())),
            "s101_mapping_type_counts": dict(sorted(mapping_counts.items())),
            "s101_crosswalk_class_counts": dict(sorted(class_counts.items())),
            "all_rows_accounted_for": len(rows) == 824,
            "all_rows_classified": len(unresolved) == 0 and "unknown" not in class_counts,
            "all_rows_s101_feature_equivalent": s101_feature_equivalent == len(rows),
        },
        "consistency_checks": {
            "resolved_colour_attribute_mismatches": colour_mismatches,
            "human_review_s101_missing_symbol_id": witness_gaps["missing_symbol_id"],
            "human_review_s101_missing_shape_witness_note": witness_gaps["missing_shape_witness_note"],
            "passed": not colour_mismatches
            and not witness_gaps["missing_symbol_id"]
            and not witness_gaps["missing_shape_witness_note"],
        },
        "unresolved_rows": unresolved,
        "interpretation": {
            "s101_feature_equivalent_rows": "S-101 mapping evidence exists as direct, rule-derived, catalogue-rule, or acceptable-deviation evidence.",
            "non_s101_or_extension_rows": "Runtime display constructs and extension/inland profile rows are classified explicitly; do not claim these are S-101 ENC features.",
            "unresolved_rows": "No row may remain in this bucket; add a standards mapping or an explicit non-S-101/profile classification.",
            "raw_s101_svg_warning": "Raw S-101 SVG witnesses are shape/reference evidence; colour semantics come from resolver attributes.",
        },
    }


def _md(result: dict[str, Any]) -> str:
    cov = result["coverage"]
    checks = result["consistency_checks"]
    return "\n".join([
        "# S-101 Mapping Audit",
        "",
        f"Status: `{result['status']}`",
        "",
        f"- rows: `{cov['rows']}`",
        f"- s101_feature_equivalent: `{cov['s101_feature_equivalent']}`",
        f"- non_s101_or_extension: `{cov['non_s101_or_extension']}`",
        f"- unresolved: `{cov['unresolved']}`",
        f"- resolver_status_counts: `{cov['resolver_status_counts']}`",
        f"- mapping_type_counts: `{cov['s101_mapping_type_counts']}`",
        f"- crosswalk_class_counts: `{cov['s101_crosswalk_class_counts']}`",
        f"- all_rows_accounted_for: `{cov['all_rows_accounted_for']}`",
        f"- all_rows_classified: `{cov['all_rows_classified']}`",
        f"- all_rows_s101_feature_equivalent: `{cov['all_rows_s101_feature_equivalent']}`",
        "",
        "## Consistency Checks",
        "",
        f"- colour_attribute_mismatches: `{len(checks['resolved_colour_attribute_mismatches'])}`",
        f"- human_review_missing_symbol_id: `{len(checks['human_review_s101_missing_symbol_id'])}`",
        f"- human_review_missing_shape_witness_note: `{len(checks['human_review_s101_missing_shape_witness_note'])}`",
        f"- passed: `{checks['passed']}`",
        "",
        "The audit separates S-101 ENC feature-equivalent rows from renderer",
        "runtime constructs and extension/inland profile rows. Do not claim",
        "extension/runtime rows are S-101 ENC features.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = build()
    _write_json(args.out, result)
    args.md.write_text(_md(result))
    print(json.dumps({
        "status": result["status"],
        "coverage": result["coverage"],
        "consistency_checks": {
            key: (len(value) if isinstance(value, list) else value)
            for key, value in result["consistency_checks"].items()
        },
        "outputs": {
            "json": str(args.out.relative_to(ROOT)),
            "md": str(args.md.relative_to(ROOT)),
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
