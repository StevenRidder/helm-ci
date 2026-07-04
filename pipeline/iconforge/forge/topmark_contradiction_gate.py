"""Detect contradictions in the topmark standards witness pass.

This gate is intentionally conservative. The topmark standards pass may contain
useful S-101 witnesses, but a row is not safe for final approval when the row
name, expected TOPSHP shape, and S-101 witness description disagree.

Run:  python -m forge.topmark_contradiction_gate
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TOPMARK_PASS = ROOT / "catalog" / "topmark_standards_pass.json"
DEFAULT_OUT = ROOT / "catalog" / "topmark_contradiction_gate.json"
DEFAULT_MD = ROOT / "catalog" / "topmark_contradiction_gate.md"


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _shape_tokens(text: str | None) -> set[str]:
    t = _norm(text)
    tokens: set[str] = set()
    if "point up" in t or "point upward" in t or "points upward" in t:
        tokens.add("point_up")
    if "point down" in t or "point downward" in t or "points downward" in t:
        tokens.add("point_down")
    if "point to point" in t:
        tokens.add("point_to_point")
    if "base to base" in t:
        tokens.add("base_to_base")
    if "cone" in t or "conical" in t or "triangle" in t:
        tokens.add("triangular")
    if "sphere" in t or "circle" in t:
        tokens.add("round")
    if "two spheres" in t:
        tokens.add("two_round")
    if "cylinder" in t:
        tokens.add("cylinder")
    if "board" in t:
        tokens.add("board")
    if "square" in t:
        tokens.add("square")
    if "rectangle" in t:
        tokens.add("rectangle")
    if "rhombus" in t or "diamond" in t:
        tokens.add("rhombus")
    if "besom" in t:
        tokens.add("besom")
    if "trapezium" in t or "trapezoid" in t:
        tokens.add("trapezium")
    if "upright cross" in t or "cross" in t:
        tokens.add("cross")
    if "x shaped" in t or "x shape" in t or "x-shaped" in t:
        tokens.add("x_shape")
    if " t shape" in f" {t}" or "t shaped" in t or "t-shape" in t:
        tokens.add("t_shape")
    if "flag" in t:
        tokens.add("flag")
    if "cube" in t:
        tokens.add("cube")
    return tokens


def _contradicts(expected: set[str], observed: set[str]) -> bool:
    if not expected or not observed:
        return False
    mutually_exclusive = [
        {"point_up", "point_down"},
        {"square", "cylinder", "round", "rhombus", "trapezium", "triangular", "cross", "x_shape", "t_shape"},
        {"board", "cylinder", "round", "rhombus", "triangular", "cross", "x_shape", "t_shape"},
        {"rectangle", "cylinder", "round", "rhombus", "triangular", "cross", "x_shape", "t_shape"},
        {"besom", "cylinder", "round", "square", "board", "rectangle", "rhombus", "triangular", "cross", "x_shape", "t_shape"},
    ]
    for group in mutually_exclusive:
        if expected & group and observed & group and not (expected & observed & group):
            return True
    if ("point_up" in expected and "point_down" in observed) or ("point_down" in expected and "point_up" in observed):
        return True
    return False


def _primary_witness(row: dict[str, Any]) -> dict[str, Any] | None:
    witnesses = row.get("s101_witnesses") or []
    return witnesses[0] if witnesses else None


def check_row(row: dict[str, Any]) -> dict[str, Any]:
    expected = row.get("expected_shape") or {}
    expected_text = expected.get("shape_name")
    expected_tokens = _shape_tokens(expected_text)
    name_tokens = _shape_tokens(row.get("name"))
    primary = _primary_witness(row)
    primary_tokens = _shape_tokens((primary or {}).get("description"))
    same_asset_witnesses = [
        witness for witness in row.get("s101_witnesses") or []
        if "same_asset_id_if_s101_symbol_exists" in (witness.get("role") or "")
    ]

    findings: list[dict[str, str]] = []
    if expected.get("ambiguous") and "pass_pending" in (row.get("candidate_status") or ""):
        findings.append({
            "code": "unresolved_shape_is_pass_pending",
            "detail": "Ambiguous or unresolved topmark shape is still candidate pass-pending.",
        })
    if row.get("human_rejected") and "pass_pending" in (row.get("candidate_status") or ""):
        findings.append({
            "code": "human_rejected_is_pass_pending",
            "detail": "Human-rejected topmark row is still candidate pass-pending.",
        })
    if _contradicts(expected_tokens, name_tokens):
        findings.append({
            "code": "row_name_contradicts_expected_shape",
            "detail": f"row name tokens {sorted(name_tokens)} conflict with expected {sorted(expected_tokens)}",
        })
    if primary and _contradicts(expected_tokens, primary_tokens):
        findings.append({
            "code": "primary_s101_witness_contradicts_expected_shape",
            "detail": f"primary witness {primary.get('id')} tokens {sorted(primary_tokens)} conflict with expected {sorted(expected_tokens)}",
        })
    for witness in same_asset_witnesses:
        witness_tokens = _shape_tokens(witness.get("description"))
        if _contradicts(expected_tokens, witness_tokens):
            findings.append({
                "code": "same_asset_s101_witness_contradicts_expected_shape",
                "detail": f"same-asset witness {witness.get('id')} tokens {sorted(witness_tokens)} conflict with expected {sorted(expected_tokens)}",
            })

    gate_status = "manual_review_required" if findings else "no_contradiction_detected"
    return {
        "asset": row.get("asset"),
        "name": row.get("name"),
        "candidate_status": row.get("candidate_status"),
        "human_rejected": bool(row.get("human_rejected")),
        "expected_shape": expected,
        "primary_s101_witness": primary,
        "expected_tokens": sorted(expected_tokens),
        "row_name_tokens": sorted(name_tokens),
        "primary_s101_tokens": sorted(primary_tokens),
        "gate_status": gate_status,
        "findings": findings,
        "recommended_status": "manual_review" if findings else row.get("candidate_status"),
    }


def build() -> dict[str, Any]:
    source = _read(TOPMARK_PASS)
    rows = [check_row(row) for row in source.get("queue", [])]
    finding_counts = Counter(finding["code"] for row in rows for finding in row["findings"])
    status_counts = Counter(row["gate_status"] for row in rows)
    blocked = [row for row in rows if row["gate_status"] == "manual_review_required"]
    return {
        "schema": "helm.forge.topmark-contradiction-gate.v1",
        "status": "manual_review_required" if blocked else "pass",
        "source": {
            "topmark_standards_pass": "catalog/topmark_standards_pass.json",
            "source_pr": "https://github.com/StevenRidder/Helm/pull/243",
        },
        "policy": {
            "rule": "No topmark row may be promoted when row name, expected TOPSHP shape, and S-101 witness semantics contradict each other.",
            "manual_review_required_codes": [
                "unresolved_shape_is_pass_pending",
                "human_rejected_is_pass_pending",
                "row_name_contradicts_expected_shape",
                "primary_s101_witness_contradicts_expected_shape",
                "same_asset_s101_witness_contradicts_expected_shape",
            ],
        },
        "summary": {
            "rows": len(rows),
            "manual_review_required": len(blocked),
            "gate_status_counts": dict(sorted(status_counts.items())),
            "finding_counts": dict(sorted(finding_counts.items())),
        },
        "blocked_rows": blocked,
        "rows": rows,
    }


def _md(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Topmark Contradiction Gate",
        "",
        f"Status: `{result['status']}`",
        "",
        f"- rows: `{summary['rows']}`",
        f"- manual_review_required: `{summary['manual_review_required']}`",
        f"- gate_status_counts: `{summary['gate_status_counts']}`",
        f"- finding_counts: `{summary['finding_counts']}`",
        "",
        "Rows below must not be final-approved until the contradiction is resolved.",
        "",
    ]
    for row in result["blocked_rows"][:80]:
        codes = ", ".join(finding["code"] for finding in row["findings"])
        expected = row["expected_shape"].get("shape_id") or "unresolved"
        lines.append(f"- `{row['asset']}` -> `{expected}`: {codes}")
    if len(result["blocked_rows"]) > 80:
        lines.append(f"- ... {len(result['blocked_rows']) - 80} more rows")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    result = build()
    _write(args.out, result)
    args.md.write_text(_md(result))
    print(f"topmark contradiction gate -> {args.out}")
    print(f"topmark contradiction summary -> {args.md}")
    print(f"summary: {result['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
