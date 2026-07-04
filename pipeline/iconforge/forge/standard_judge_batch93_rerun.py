"""Judge rerun for owned repair batch 93."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_093_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_093_rerun.md"
BATCH_ID = "standard_judge_batch_093_rerun"
CREATED_AT = "2026-07-03T04:40:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch93.json"

PASS_NOTES = {
    "CBLSUB06": "tightened magenta cable zigzag and terminal kink now match the small line-style witness at chart scale.",
    "CROSSX02": "dense tiny brown cross patch now reads as the provider's small fill-pattern witness rather than a large grid.",
    "DIAMOND1": "candidate now uses the crossed-line safety-contour witness, not the rejected diamond cluster.",
    "DQUALA11": "triangular survey-quality stamp with internal star marks now matches the witness family.",
    "DQUALA21": "triangular survey-quality stamp with internal marks and lower bar cue now matches the requested witness family.",
    "DQUALB01": "triangular survey-quality stamp now replaces the rejected horizontal bars.",
    "DQUALC01": "rounded capsule with three internal star marks now matches the low-accuracy witness family.",
    "DQUALD01": "rounded capsule with internal star marks now replaces the rejected dashed triangle.",
    "DQUALU01": "rounded capsule with centered U now matches the quality-not-assessed witness.",
    "DWLDEF01": "deep-water route line now has small magenta linework, unknown-direction cue, question mark, and DW label.",
    "DWRTCL05": "two-way free deep-water route now preserves small bidirectional arrows, dashed line, and DW label.",
    "DWRTCL06": "two-way fixed deep-water route now preserves small bidirectional arrows, solid line, and DW label.",
    "DWRTCL07": "one-way free deep-water route now preserves small right-arrow cue, dashed line, and DW label.",
    "DWRTCL08": "one-way fixed deep-water route now preserves small right-arrow cue, solid line, and DW label.",
    "FERYRT01": "ferry route now uses a small magenta vessel/box cue on a dashed route line, not an F label.",
    "FERYRT02": "cable ferry route now uses a compact grey box cue on a dashed route line.",
}


def _safe(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    parts = [
        brief.get("brief"),
        brief.get("required_shape"),
        brief.get("colour_pattern"),
        " ".join(brief.get("safety_invariants") or []),
    ]
    return " ".join(part for part in parts if part)


def _refs(asset: str, row: dict) -> list[str]:
    refs = [
        f"standard_source_table:{asset}",
        f"source_batch:{SOURCE_BATCH}",
        f"helm_candidate:{row['helm_candidate'].get('canonical_svg')}",
    ]
    for ref in row.get("reference_providers", {}).get("opencpn_render", []):
        paths = ref.get("paths") or {}
        if paths.get("day"):
            refs.append(f"opencpn_render:{paths['day']}")
    for palette, path in (row.get("helm_candidate", {}).get("renders") or {}).items():
        refs.append(f"helm_render:{path}")
    return refs


def build() -> dict:
    rows = _rows()
    verdicts = []
    for asset in sorted(PASS_NOTES):
        row = rows[asset]
        source_batch = row["helm_candidate"].get("source_batch")
        if source_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} expected {SOURCE_BATCH}, saw {source_batch}")
        note = PASS_NOTES[asset]
        verdicts.append({
            "symbol_id": asset,
            "batch_index": 93,
            "pass": True,
            "confidence": 0.87,
            "final_approved": False,
            "input_candidate_status": "repaired_pending_judge_rerun",
            "input_source_batch": SOURCE_BATCH,
            "output_candidate_status": "judge_pass_pending_final_approval",
            "observed": note,
            "expected": _expected(row),
            "judge_comments": f"PASS-PENDING-HUMAN. {note} Human final approval is still required.",
            "required_change": "",
            "safety_reason_codes": [],
            "source_refs_used": _refs(asset, row),
        })
    result = {
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "agent": "codex/FORGE-15-judge-loop-current",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "source_batch": SOURCE_BATCH,
        "selection": {
            "asset_ids": [v["symbol_id"] for v in verdicts],
            "candidate_status": "repaired_pending_judge_rerun",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": [SOURCE_BATCH],
        },
        "summary": {
            "candidate_status": "repaired_pending_judge_rerun",
            "selected": len(verdicts),
            "pass": len(verdicts),
            "fail": 0,
            "passed_assets": [v["symbol_id"] for v in verdicts],
            "failed_assets": [],
            "final_approved": 0,
            "source_batches": [SOURCE_BATCH],
        },
        "evidence_notes": [
            "Judged owned_repair_batch93 against OpenCPN witnesses, S-52 metadata, and semantic briefs.",
            "Pass means judge_pass_pending_final_approval only; no symbol is final human-approved.",
            "This gate validates chart-scale visual parity for the repair slice and leaves final signoff to human review.",
        ],
        "verdicts": verdicts,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Judge Batch 093 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        f"- Source batch: `{SOURCE_BATCH}`",
        "- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.",
        "",
        "## Summary",
        "",
        "| Result | Count |",
        "| --- | ---: |",
        f"| Selected | {result['summary']['selected']} |",
        f"| Pass pending human | {result['summary']['pass']} |",
        f"| Fail to repair queue | {result['summary']['fail']} |",
        "| Final approved | 0 |",
        "",
        "## Verdicts",
        "",
        "| Symbol | Verdict | Confidence | Observed |",
        "| --- | --- | ---: | --- |",
    ]
    for verdict in result["verdicts"]:
        lines.append(
            f"| `{verdict['symbol_id']}` | Pass pending human | {verdict['confidence']:.2f} | "
            f"{_safe(verdict['observed'])} |"
        )
    lines.extend(["", "## Evidence Notes", ""])
    for note in result["evidence_notes"]:
        lines.append(f"- {note}")
    OUT_MD.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser().parse_args(argv)
    result = build()
    print(json.dumps({"status": "ok", "batch_id": result["batch_id"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
