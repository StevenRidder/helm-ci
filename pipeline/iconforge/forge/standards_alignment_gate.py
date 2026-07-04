"""Roll up FORGE-14 standards-alignment evidence.

This gate connects the current Icon Forge evidence packs:

- Chart No.1 crop/parity evidence.
- S-52/S-57/S-101 crosswalk evidence.
- Standard source table routing/judge state.
- Topmark standards pass evidence.

It does not approve rows. It makes the standards state explicit so downstream
FORGE-22/23/24 work can distinguish implemented scaffolds from final visual
approval.

Run:  python -m forge.standards_alignment_gate
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_JSON = ROOT / "catalog" / "standards_alignment_gate.json"
DEFAULT_OUT_MD = ROOT / "catalog" / "standards_alignment_gate.md"

INPUTS = {
    "chart1_parity": ROOT / "out" / "chart1_parity" / "report.json",
    "chart1_hard_pile": ROOT / "out" / "chart1_parity" / "hard_pile.json",
    "chart1_crop_review": ROOT / "out" / "chart1_parity" / "crop_review.json",
    "standard_source_table": ROOT / "catalog" / "standard_source_table.json",
    "s52_s57_s101_crosswalk": ROOT / "catalog" / "s52_s57_s101_crosswalk.json",
    "topmark_standards_pass": ROOT / "catalog" / "topmark_standards_pass.json",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, body: Any) -> None:
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_inputs() -> dict[str, Any]:
    missing = [name for name, path in INPUTS.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing standards-alignment input(s): {', '.join(missing)}")
    return {name: _read_json(path) for name, path in INPUTS.items()}


def _review_state(chart1: dict[str, Any], topmark: dict[str, Any]) -> dict[str, Any]:
    chart_summary = chart1["summary"]
    topmark_summary = topmark["summary"]
    blockers = []
    if chart1["status"] != "pass":
        blockers.append("chart1_parity_status_not_pass")
    if chart_summary.get("final_approved", 0) == 0:
        blockers.append("no_final_approved_chart1_rows")
    if chart_summary.get("hard_pile_entries", 0):
        blockers.append("chart1_hard_pile_not_empty")
    if topmark_summary.get("ambiguous_or_unresolved_rows", 0):
        blockers.append("topmark_unresolved_rows_not_empty")
    state = "ready_for_downstream_unblock" if not blockers else "review_required"
    return {"state": state, "blockers": blockers}


def build() -> dict[str, Any]:
    data = _load_inputs()
    chart1 = data["chart1_parity"]
    source = data["standard_source_table"]
    crosswalk = data["s52_s57_s101_crosswalk"]
    topmark = data["topmark_standards_pass"]
    hard_pile = data["chart1_hard_pile"]
    crop_review = data["chart1_crop_review"]
    review = _review_state(chart1, topmark)

    result = {
        "schema": "helm.forge.standards-alignment-gate.v1",
        "status": review["state"],
        "task": "FORGE-14",
        "purpose": "Align Chart No.1, S-52/S-57, S-101, topmark, and judge evidence before unblocking FORGE-22/23/24.",
        "inputs": {name: _rel(path) for name, path in INPUTS.items()},
        "clean_room_boundary": {
            "allowed": [
                "Chart No.1 reference crop metadata and hashes",
                "S-52/S-57 object, lookup, and symbol vocabulary",
                "S-101 feature/rule references as standards evidence",
                "Helm-generated SVG candidates and judge results",
            ],
            "not_bundled_as_source_artwork": [
                "OpenCPN GPL raster sprites",
                "official IHO SVG artwork",
                "IHO Feature Catalogue XML",
                "IHO Portrayal Catalogue XML",
                "IHO Lua portrayal rule files",
                "private ENC, S-63, or oeSENC data",
            ],
        },
        "review_state": review,
        "chart1_parity": {
            "status": chart1["status"],
            "rows": chart1["summary"]["full_catalog_assets"],
            "gate_assets": chart1["summary"]["gate_assets"],
            "evidence_counts": chart1["summary"]["evidence_counts"],
            "verdict_counts": chart1["summary"]["verdict_counts"],
            "final_approved": chart1["summary"]["final_approved"],
            "hard_pile_entries": chart1["summary"]["hard_pile_entries"],
            "crop_count": crop_review["crop_count"],
            "pdf_url": crop_review["pdf_url"],
            "pdf_sha256": crop_review["pdf_sha256"],
        },
        "standard_source_table": {
            "status": source["status"],
            "summary": source["summary"],
        },
        "s52_s57_s101_crosswalk": {
            "counts": crosswalk["counts"],
        },
        "topmark_standards": {
            "status": topmark["status"],
            "summary": topmark["summary"],
        },
        "downstream_policy": {
            "FORGE-22": "may use semantic tuple scaffolds, but stays blocked until this gate is ready or a human explicitly accepts provisional unblock",
            "FORGE-23": "may use rule-derived equivalence scaffolds, but cannot claim final S-101 portrayal equivalence until this gate and official rule evidence are accepted",
            "FORGE-24": "may publish a proof scaffold, but final parity proof requires approved S-52/OpenCPN, S-101, and Helm render evidence per row",
        },
        "hard_pile_sample": [
            {
                "asset": row.get("asset"),
                "reason_codes": row.get("reason_codes", []),
                "reference_evidence_status": row.get("reference_evidence_status"),
                "final_approval": row.get("final_approval"),
            }
            for row in hard_pile[:20]
        ],
    }
    return result


def _md(gate: dict[str, Any]) -> str:
    chart = gate["chart1_parity"]
    source = gate["standard_source_table"]["summary"]
    crosswalk = gate["s52_s57_s101_crosswalk"]["counts"]
    topmark = gate["topmark_standards"]["summary"]
    blockers = gate["review_state"]["blockers"]
    lines = [
        "# FORGE-14 Standards Alignment Gate",
        "",
        f"Status: `{gate['status']}`",
        "",
        "This rollup aligns the standards evidence currently built for Icon Forge.",
        "It does not approve rows; it tells downstream tasks which evidence is safe",
        "to consume and why FORGE-22/23/24 remain provisional.",
        "",
        "## Blockers",
    ]
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Chart No.1 Parity",
        "",
        f"- rows: `{chart['rows']}`",
        f"- gate_assets: `{chart['gate_assets']}`",
        f"- final_approved: `{chart['final_approved']}`",
        f"- hard_pile_entries: `{chart['hard_pile_entries']}`",
        f"- crop_count: `{chart['crop_count']}`",
        f"- evidence_counts: `{chart['evidence_counts']}`",
        f"- verdict_counts: `{chart['verdict_counts']}`",
        "",
        "## Standard Source Table",
        "",
        f"- rows: `{source['rows']}`",
        f"- judge_queue_rows: `{source['judge_queue_rows']}`",
        f"- semantic_shape_judge_queue_rows: `{source['semantic_shape_judge_queue_rows']}`",
        f"- candidate_status_counts: `{source['candidate_status_counts']}`",
        "",
        "## S-52/S-57/S-101 Crosswalk",
        "",
        f"- rows: `{crosswalk['rows']}`",
        f"- s101_exact_symbol_matches: `{crosswalk['s101_exact_symbol_matches']}`",
        f"- s101_feature_rule_candidates: `{crosswalk['s101_feature_rule_candidates']}`",
        "",
        "## Topmark Standards",
        "",
        f"- topmark_rows_needing_special_pass: `{topmark['topmark_rows_needing_special_pass']}`",
        f"- resolved_exact_or_inferred_shape_rows: `{topmark['resolved_exact_or_inferred_shape_rows']}`",
        f"- ambiguous_or_unresolved_rows: `{topmark['ambiguous_or_unresolved_rows']}`",
        f"- candidate_status_counts: `{topmark['candidate_status_counts']}`",
        "",
        "## Clean-Room Boundary",
        "",
        "OpenCPN, IHO, S-101, and Chart No.1 references are standards/comparison",
        "evidence. They are not bundled source artwork for the generated Helm",
        "symbol package.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args(argv)
    gate = build()
    _write_json(args.json, gate)
    args.md.write_text(_md(gate))
    print(f"standards alignment gate -> {args.json}")
    print(f"standards alignment summary -> {args.md}")
    print(f"status: {gate['status']}")
    print(f"blockers: {gate['review_state']['blockers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
