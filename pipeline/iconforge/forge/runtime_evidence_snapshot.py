"""Deterministic runtime-evidence snapshot for downstream consumers.

Run:
  python3 -m forge.runtime_evidence_snapshot
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import db_review_api, runtime_promotion_gate


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SNAPSHOT_JSON = CATALOG / "runtime_evidence_snapshot.json"
SNAPSHOT_MD = CATALOG / "runtime_evidence_snapshot.md"

SCHEMA = "helm.iconforge.runtime_evidence_snapshot.v1"


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(payload))


def _unique(values: list[str]) -> list[str]:
    return sorted({str(value) for value in values if value})


def _compact_classification(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "reason_code": item.get("reason_code") or "",
        "blocker_category": item.get("blocker_category") or "unclassified_authority_gap",
        "source_layer": item.get("source_layer") or "authority_trace",
        "runtime_effect": item.get("runtime_effect") or "blocks_runtime",
        "blocks_runtime": bool(item.get("blocks_runtime")),
        "remediation_hint": item.get("remediation_hint") or "",
        "evidence": item.get("evidence") or {},
    }


def _runtime_state(
    row: dict[str, Any],
    hard_pile: dict[int, dict[str, Any]],
    promoted: dict[int, dict[str, Any]],
) -> tuple[str, dict[str, Any], list[str]]:
    row_id = int(row["row_id"])
    if row_id in promoted:
        return "runtime_eligible", promoted[row_id], []
    if row_id in hard_pile:
        hard = hard_pile[row_id]
        return "runtime_blocked", hard, hard.get("reason_codes") or []
    return "snapshot_mismatch", {}, ["runtime_snapshot:row_missing_from_promotion_gate"]


def _snapshot_row(
    row: dict[str, Any],
    hard_pile: dict[int, dict[str, Any]],
    promoted: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    authority = row["qa"].get("authority_trace") or {}
    classifications = [
        _compact_classification(item)
        for item in authority.get("gap_classifications") or []
    ]
    state, runtime_record, runtime_reasons = _runtime_state(row, hard_pile, promoted)
    blocking_classifications = [item for item in classifications if item["blocks_runtime"]]
    warning_classifications = [item for item in classifications if not item["blocks_runtime"]]
    return {
        "row_id": row["row_id"],
        "row_key": row["row_key"],
        "symbol_id": row["symbol_id"],
        "helm_catalog_id": row["helm_catalog_id"],
        "runtime_state": state,
        "fail_closed": state != "runtime_eligible",
        "runtime_eligible_db": bool(row["qa"]["runtime_eligible"]),
        "runtime_gate_reason_codes": runtime_reasons,
        "candidate_status": row["status"],
        "s57": {
            "object_class": row["s57"]["object_class"],
            "geometry": row["s57"]["geometry"],
        },
        "s52": {
            "instruction": row["s52"]["instruction"],
            "ast_status": row["s52"]["ast_status"],
        },
        "s101": {
            "mapping_type": row["s101"]["mapping_type"],
            "crosswalk_class": row["s101"]["crosswalk_class"],
            "feature_type": row["s101"]["feature_type"],
            "rule_file": row["s101"]["rule_file"],
        },
        "authority_trace": {
            "gate_status": authority.get("gate_status") or "blocked",
            "authority_status": authority.get("authority_status") or "missing",
            "runtime_blocker": bool(authority.get("runtime_blocker")),
            "reason_codes": authority.get("reason_codes") or [],
            "blocker_summary": authority.get("blocker_summary") or {},
            "gap_classifications": classifications,
        },
        "blocker_categories": dict(sorted(Counter(item["blocker_category"] for item in classifications).items())),
        "source_layers": dict(sorted(Counter(item["source_layer"] for item in classifications).items())),
        "runtime_effects": dict(sorted(Counter(item["runtime_effect"] for item in classifications).items())),
        "remediation_hints": _unique([item["remediation_hint"] for item in classifications]),
        "authority_source_evidence": [
            {
                "reason_code": item["reason_code"],
                "blocker_category": item["blocker_category"],
                "source_layer": item["source_layer"],
                "evidence": item["evidence"],
            }
            for item in classifications
            if item.get("evidence")
        ],
        "review_gates": {
            "blocking": row["qa"]["blocking_gate_count"],
            "pending": row["qa"]["pending_gate_count"],
            "warning": row["qa"]["warning_gate_count"],
            "visual_human_approval_blocked": any(
                item["blocker_category"] == "visual_human_approval_blocker"
                for item in classifications
            ),
            "blocking_authority_gap_count": len(blocking_classifications),
            "warning_authority_gap_count": len(warning_classifications),
        },
        "runtime_record": {
            "present_in_runtime_export": state == "runtime_eligible",
            "present_in_hard_pile": state == "runtime_blocked",
            "reason_count": len(runtime_reasons),
            "authority_blocker_summary": runtime_record.get("authority_blocker_summary") or {},
        },
    }


def build_snapshot(*, limit: int = 10000, write_reports: bool = True) -> dict[str, Any]:
    review = db_review_api.build_review_payload(limit=limit)
    runtime = runtime_promotion_gate.build_runtime_export(limit=limit)
    hard_pile = {int(row["row_id"]): row for row in runtime["hard_pile"]}
    promoted = {int(row["row_id"]): row for row in runtime["rows"]}
    rows = [_snapshot_row(row, hard_pile, promoted) for row in review["rows"]]

    state_counts = Counter(row["runtime_state"] for row in rows)
    category_counts: Counter[str] = Counter()
    effect_counts: Counter[str] = Counter()
    for row in rows:
        category_counts.update(row["blocker_categories"])
        effect_counts.update(row["runtime_effects"])

    mismatch_rows = [
        row["row_id"]
        for row in rows
        if row["runtime_state"] == "snapshot_mismatch"
        or (row["runtime_state"] == "runtime_eligible") != bool(row["runtime_eligible_db"])
        and row["runtime_state"] != "runtime_blocked"
    ]
    warning_only_rows = sum(
        1
        for row in rows
        if row["runtime_effects"].get("warning_only", 0)
        and not row["runtime_effects"].get("blocks_runtime", 0)
    )

    payload = {
        "schema": SCHEMA,
        "status": "snapshot_ready" if not mismatch_rows else "snapshot_mismatch",
        "policy": {
            "source": "db_review_api + runtime_promotion_gate",
            "browser_business_logic_allowed": False,
            "visual_or_svg_inputs_used": False,
            "runtime_export_rule": "Rows must match runtime_promotion_gate behavior exactly.",
            "clean_room_boundary": "Generated metadata only; no source artwork or visual symbol edits.",
        },
        "source": {
            "review": review["source"],
            "runtime_export_schema": runtime["schema"],
            "runtime_export_status": runtime["status"],
        },
        "summary": {
            "review_rows": len(review["rows"]),
            "snapshot_rows": len(rows),
            "runtime_rows": runtime["summary"]["runtime_rows"],
            "hard_pile_rows": runtime["summary"]["hard_pile_rows"],
            "runtime_eligible_db_rows": runtime["summary"]["runtime_eligible_db_rows"],
            "runtime_portrayal_db_rows": runtime["summary"]["runtime_portrayal_db_rows"],
            "runtime_state_counts": dict(sorted(state_counts.items())),
            "blocker_category_counts": dict(sorted(category_counts.items())),
            "runtime_effect_counts": dict(sorted(effect_counts.items())),
            "warning_only_rows": warning_only_rows,
            "mismatch_rows": mismatch_rows,
            "matches_runtime_promotion_gate": not mismatch_rows
            and state_counts.get("runtime_eligible", 0) == runtime["summary"]["runtime_rows"]
            and state_counts.get("runtime_blocked", 0) == runtime["summary"]["hard_pile_rows"],
        },
        "rows": rows,
    }
    if write_reports:
        _write_reports(payload)
    return payload


def _write_reports(payload: dict[str, Any]) -> None:
    _write_json(SNAPSHOT_JSON, payload)
    summary = payload["summary"]
    lines = [
        "# Runtime Evidence Snapshot",
        "",
        "FORGE-37 downstream runtime-readiness snapshot generated from backend DB/proof data.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- snapshot_rows: `{summary['snapshot_rows']}`",
        f"- runtime_rows: `{summary['runtime_rows']}`",
        f"- hard_pile_rows: `{summary['hard_pile_rows']}`",
        f"- warning_only_rows: `{summary['warning_only_rows']}`",
        f"- matches_runtime_promotion_gate: `{summary['matches_runtime_promotion_gate']}`",
        "",
        "## Runtime States",
        "",
        "| State | Count |",
        "| --- | ---: |",
    ]
    for state, count in summary["runtime_state_counts"].items():
        lines.append(f"| `{state}` | {count} |")
    lines.extend([
        "",
        "## Top Blocker Categories",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ])
    for category, count in Counter(summary["blocker_category_counts"]).most_common(20):
        lines.append(f"| `{category}` | {count} |")
    SNAPSHOT_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--json", type=Path, default=SNAPSHOT_JSON)
    parser.add_argument("--markdown", type=Path, default=SNAPSHOT_MD)
    args = parser.parse_args(argv)
    payload = build_snapshot(limit=args.limit)
    if args.json != SNAPSHOT_JSON:
        _write_json(args.json, payload)
    if args.markdown != SNAPSHOT_MD:
        args.markdown.write_text(SNAPSHOT_MD.read_text())
    print(json.dumps({
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(args.json),
        "markdown": str(args.markdown),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
