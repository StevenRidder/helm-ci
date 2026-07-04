"""Judge rerun for owned repair batches 76 and 82.

Run:
  python3 -m forge.standard_judge_batch76_82_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_076_082_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_076_082_rerun.md"
BATCH_ID = "standard_judge_batch_076_082_rerun"
CREATED_AT = "2026-07-02T00:00:00Z"

BATCH76 = "catalog/owned_repair_batch76.json"
BATCH82 = "catalog/owned_repair_batch82.json"

PASS_ASSETS = {
    "BOYBAR01": (BATCH76, 0.88, "black/outline barrel body matches the approved sideways barrel-buoy family and avoids the earlier red half-fill error."),
    "BOYBAR60": (BATCH76, 0.90, "red sideways barrel body preserves the BOYSHP6 barrel silhouette and required red colour."),
    "BOYBAR61": (BATCH76, 0.90, "green sideways barrel body preserves the BOYSHP6 barrel silhouette and required green colour."),
    "BOYBAR62": (BATCH76, 0.90, "yellow sideways barrel body preserves the BOYSHP6 barrel silhouette and required yellow colour."),
    "BUNSTA02": (BATCH82, 0.84, "water bunker/bucket silhouette matches the OpenCPN witness and keeps the water cue."),
    "SSENTR01": (BATCH82, 0.84, "port-entry signal board silhouette and flag/entry cue match the OpenCPN witness family."),
    "SSLOCK01": (BATCH82, 0.84, "lock signal board silhouette and paired signal cue match the OpenCPN witness family."),
    "SSWARS01": (BATCH82, 0.84, "wahrschau signal board and triangular warning cue match the OpenCPN witness family."),
    "ZZZZZZ01": (BATCH82, 0.86, "small multicolour square topmark matches the OpenCPN witness and TOPSHP98 cue closely enough for human review."),
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    shape = brief.get("required_shape") or "reference-matched symbol geometry"
    colours = brief.get("required_colours") or []
    colour_text = f"; required colours {', '.join(colours)}" if colours else "; colours reference-defined"
    return f"{row['asset']} must preserve {shape}{colour_text}."


def _refs(asset: str, row: dict, source_batch: str) -> list[str]:
    safe = _safe(asset)
    refs = [
        f"semantic_brief:{asset}",
        f"s57_conditions:{','.join(row.get('s57_structure', {}).get('conditions') or [])}",
        f"helm_candidate:pipeline/iconforge/assets/svg/triad_generated/{safe}.svg",
        f"source_svg:{row.get('helm_candidate', {}).get('source_svg')}",
        f"repair_catalog:{source_batch}",
        "source_table:pipeline/iconforge/catalog/standard_source_table.json",
        f"candidate_render:out/triad_reference_candidate_pack/renders/{safe}__day.png",
    ]
    variant = ROOT / "out" / "source_variant_matrix" / "renders" / asset
    for name in (
        "opencpn_s52_reference_render_1.png",
        "chart1_parity_reference_crop_1.png",
        "chart1_mappings_symbol_reference_1.png",
    ):
        if not (variant / name).exists():
            continue
        rel = variant.relative_to(ROOT) / name
        if name == "opencpn_s52_reference_render_1.png":
            refs.append(f"source_variant_opencpn:{rel}")
        elif name == "chart1_parity_reference_crop_1.png":
            refs.append(f"chart1_crop:{rel}")
        else:
            refs.append(f"chart1_mapping_crop:{rel}")
    return [ref for ref in refs if not ref.endswith("None")]


def build() -> dict:
    rows = _rows()
    verdicts = []
    for asset, (source_batch, confidence, note) in PASS_ASSETS.items():
        row = rows[asset]
        actual_batch = row["helm_candidate"]["source_batch"]
        if actual_batch != source_batch:
            raise RuntimeError(f"{asset} source batch drifted: expected {source_batch}, got {actual_batch}")
        verdicts.append({
            "batch_index": 76 if source_batch == BATCH76 else 82,
            "confidence": confidence,
            "expected": _expected(row),
            "final_approved": False,
            "input_candidate_status": "repaired_pending_judge_rerun",
            "input_source_batch": source_batch,
            "judge_comments": f"Pass pending human: {note} No final approval is granted.",
            "observed": f"After SVG/render shows {note}",
            "output_candidate_status": "judge_pass_pending_final_approval",
            "pass": True,
            "repair_batch_catalog": source_batch,
            "required_change": "No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact.",
            "safety_reason_codes": [],
            "source_crop_valid": True,
            "source_refs_used": _refs(asset, row, source_batch),
            "source_table_id": row.get("source_table_id"),
            "symbol_id": asset,
        })

    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged current repaired rows from owned_repair_batch76 and owned_repair_batch82.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Each row has a tight OpenCPN/source-variant visual witness in addition to semantic_brief and S-57 conditions.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "selection": {
            "asset_ids": [row["symbol_id"] for row in verdicts],
            "candidate_status": "repaired_pending_judge_rerun",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": [BATCH76, BATCH82],
            "source_table": "pipeline/iconforge/catalog/standard_source_table.json",
        },
        "summary": {
            "candidate_status": "repaired_pending_judge_rerun",
            "selected": len(verdicts),
            "pass": len(verdicts),
            "fail": 0,
            "passed_assets": [row["symbol_id"] for row in verdicts],
            "failed_assets": [],
            "final_approved": 0,
            "source_batches": [BATCH76, BATCH82],
        },
        "task_id": "FORGE-15",
        "verdicts": verdicts,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Judge Batch 076/082 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batches: `owned_repair_batch76`, `owned_repair_batch82`",
        "- Approval note: pass means `judge_pass_pending_final_approval` only; no row is human-final-approved.",
        "",
        "## Summary",
        "",
        "| Result | Count |",
        "| --- | ---: |",
        f"| Selected | {result['summary']['selected']} |",
        f"| Pass pending human | {result['summary']['pass']} |",
        f"| Fail | {result['summary']['fail']} |",
        "| Final approved | 0 |",
        "",
        "## Verdicts",
        "",
        "| Symbol | Verdict | Confidence | Required change | Notes |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for verdict in result["verdicts"]:
        lines.append(
            f"| `{verdict['symbol_id']}` | Pass pending human | {verdict['confidence']:.2f} | "
            f"{verdict['required_change']} | {verdict['judge_comments']} |"
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
