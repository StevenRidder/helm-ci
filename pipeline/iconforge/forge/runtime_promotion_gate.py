"""Fail-closed runtime promotion export for Icon Forge symbols.

FORGE-31 does not approve symbols. It enforces the boundary between DB-backed
evidence and chartplotter/runtime consumption. Rows may enter the runtime export
only after semantic, recipe, interpretation, provenance, and human visual gates
all pass.

Run:
  python3 -m forge.runtime_promotion_gate
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import db_review_api


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "runtime"
EXPORT_JSON = OUT / "runtime_symbol_export.json"
HARD_PILE_JSON = OUT / "runtime_symbol_hard_pile.json"

SCHEMA = "helm.iconforge.runtime_symbol_export.v1"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _reason_codes(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not row["qa"]["runtime_eligible"]:
        reasons.append("runtime_eligible:false")
    if row["qa"]["blocking_gate_count"]:
        reasons.append(f"blocking_gates:{row['qa']['blocking_gate_count']}")
    if row["qa"]["pending_gate_count"]:
        reasons.append(f"pending_gates:{row['qa']['pending_gate_count']}")
    approval = row["approval"]["state"] or {}
    if not (approval.get("final_approved") or approval.get("final_decision") == "approve"):
        reasons.append("final_approved:false")
    if row["helm"]["interpretation_status"] != "helm_interpretation_ready":
        reasons.append(f"helm_interpretation:{row['helm']['interpretation_status']}")
    if row["helm"]["recipe_status"] != "recipe_ready":
        reasons.append(f"helm_recipe:{row['helm']['recipe_status']}")
    if row["qa"]["missing_evidence"]:
        reasons.extend(f"missing:{reason}" for reason in row["qa"]["missing_evidence"])
    style_contract = row["qa"].get("style_contract") or {}
    style_gate = style_contract.get("gate_status")
    if style_gate == "failed":
        reasons.append("style_contract_failed")
    elif style_gate == "pending":
        reasons.append("style_contract_pending")
    elif style_gate != "pass":
        reasons.append("style_contract_missing")
    reasons.extend(style_contract.get("reason_codes") or [])
    colour_authority = row["qa"].get("colour_authority") or {}
    colour_gate = colour_authority.get("gate_status")
    if colour_gate in {"failed", "blocked"}:
        reasons.append("colour_authority_failed")
    elif colour_gate == "pending":
        reasons.append("colour_authority_pending")
    elif not colour_gate:
        reasons.append("colour_authority_missing")
    if colour_authority.get("runtime_blocker"):
        reasons.append("colour_authority_blocked")
    if colour_gate not in {"pass", "warn"} or colour_authority.get("runtime_blocker"):
        reasons.extend(colour_authority.get("reason_codes") or [])
    for gate in row["qa"]["gates"]:
        if gate["status"] in {"blocked", "pending", "warn"}:
            reasons.append(f"gate:{gate['name']}:{gate['status']}")
    return sorted(set(str(reason) for reason in reasons if reason))


def _runtime_row(row: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    images = row["images"]["helm"]
    return {
        "row_id": row["row_id"],
        "row_key": row["row_key"],
        "symbol_id": row["symbol_id"],
        "helm_catalog_id": row["helm_catalog_id"],
        "s57": row["s57"],
        "s52": {
            "instruction": row["s52"]["instruction"],
            "ast_status": row["s52"]["ast_status"],
        },
        "s101": {
            "mapping_type": row["s101"]["mapping_type"],
            "crosswalk_class": row["s101"]["crosswalk_class"],
            "feature_type": row["s101"]["feature_type"],
            "rule_file": row["s101"]["rule_file"],
            "attributes": row["s101"]["attributes"],
        },
        "helm": {
            "recipe": row["helm"]["recipe"],
            "interpretation": row["helm"]["interpretation"],
            "canonical_svg": images.get("canonical_svg"),
            "palette_resolved_svg": images.get("palette_resolved_svg") or {},
            "style_contract": row["qa"].get("style_contract") or {},
            "colour_authority": row["qa"].get("colour_authority") or {},
        },
        "approval": row["approval"]["state"],
        "provenance": {
            "source_db": source["db"],
            "source_db_sha256": source["db_sha256"],
            "semantic_evidence": source["semantic_evidence"],
            "proof_manifest": source["proof_manifest"],
            "clean_room_boundary": "generated_helm_assets_only; comparison references are not source artwork",
        },
    }


def build_runtime_export(*, limit: int = 10000) -> dict[str, Any]:
    review = db_review_api.build_review_payload(limit=limit)
    promoted = []
    hard_pile = []
    reason_counts: Counter[str] = Counter()
    for row in review["rows"]:
        reasons = _reason_codes(row)
        if reasons:
            hard_pile.append({
                "row_id": row["row_id"],
                "row_key": row["row_key"],
                "symbol_id": row["symbol_id"],
                "helm_catalog_id": row["helm_catalog_id"],
                "candidate_status": row["status"],
                "reason_codes": reasons,
                "gate_summary": {
                    "blocking": row["qa"]["blocking_gate_count"],
                    "pending": row["qa"]["pending_gate_count"],
                    "warning": row["qa"]["warning_gate_count"],
                },
            })
            reason_counts.update(reasons)
            continue
        promoted.append(_runtime_row(row, review["source"]))

    payload = {
        "schema": SCHEMA,
        "status": "fail_closed" if not promoted else "contains_runtime_rows",
        "source": review["source"],
        "summary": {
            "review_rows": len(review["rows"]),
            "runtime_rows": len(promoted),
            "hard_pile_rows": len(hard_pile),
            "runtime_eligible_db_rows": review["summary"]["runtime_eligible"],
            "runtime_portrayal_db_rows": review["summary"]["runtime_portrayal_rows"],
            "reason_counts": dict(sorted(reason_counts.items())),
            "promotion_rule": (
                "Export only rows with DB runtime_eligible=true, no blocking/pending gates, "
                "recipe_ready, helm_interpretation_ready, style_contract pass, "
                "colour_authority pass or documented warn, "
                "final human approval, and no missing evidence."
            ),
        },
        "render_targets": [
            "OpenCPN/Vulkan",
            "Helm C++",
            "iOS/native",
            "WebGPU",
            "SVG",
            "atlas PNG",
        ],
        "rows": promoted,
        "hard_pile": hard_pile,
    }
    return payload


def write_runtime_export(
    *,
    export_path: Path = EXPORT_JSON,
    hard_pile_path: Path = HARD_PILE_JSON,
) -> dict[str, Any]:
    payload = build_runtime_export()
    hard_pile_payload = {
        "schema": "helm.iconforge.runtime_symbol_hard_pile.v1",
        "source": payload["source"],
        "summary": payload["summary"],
        "rows": payload["hard_pile"],
    }
    export_payload = {key: value for key, value in payload.items() if key != "hard_pile"}
    _write_json(export_path, export_payload)
    _write_json(hard_pile_path, hard_pile_payload)
    return {
        "status": "runtime_export_written",
        "export": _display_path(export_path),
        "hard_pile": _display_path(hard_pile_path),
        "summary": payload["summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", type=Path, default=EXPORT_JSON)
    parser.add_argument("--hard-pile", type=Path, default=HARD_PILE_JSON)
    args = parser.parse_args(argv)
    print(json.dumps(write_runtime_export(export_path=args.export, hard_pile_path=args.hard_pile), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
