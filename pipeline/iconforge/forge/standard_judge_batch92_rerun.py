"""Judge rerun for owned repair batch 92.

Run:
  python3 -m forge.standard_judge_batch92_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_092_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_092_rerun.md"
BATCH_ID = "standard_judge_batch_092_rerun"
CREATED_AT = "2026-07-03T04:00:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch92.json"

PASS_ASSETS = {
    "CLRLIN01": "orange clearing-line arrowhead now matches the simple triangular witness closely enough at chart scale.",
    "ERBLNA01": "electronic bearing dash line now preserves the thin orange dash witness.",
    "ERBLNB01": "electronic bearing dash-dot line now preserves the thin orange dash-dot witness.",
    "FOULAR01": "foul-area cross pattern now preserves the small grey cross repeat witness.",
}

FAIL_REPAIRS = {
    "CBLSUB06": "Add the small terminal slash/kink seen in the OpenCPN cable witness and tighten the wave cadence; current candidate is close but too generic.",
    "CROSSX02": "Replace the large grid with a tight small-dot/cross fill matching the dense OpenCPN witness; keep the marks tiny at chart scale.",
    "DIAMOND1": "Use the OpenCPN crossed-line witness for depth-less-than-safety-contour, not a four-diamond cluster.",
    "DQUALA11": "Recreate the triangular outlined survey-quality stamp with internal star/cross marks; do not use two free triangles plus a plus sign.",
    "DQUALA21": "Recreate the triangular outlined survey-quality stamp with internal star/cross marks and the lower bar cue from the witness.",
    "DQUALB01": "Use the triangular outlined survey-quality witness, not three horizontal bars.",
    "DQUALC01": "Use the rounded capsule witness with three internal star/cross marks; current free plus marks miss the enclosure.",
    "DQUALD01": "Use the rounded capsule witness with internal star/cross marks; current dashed triangle is the wrong family.",
    "DQUALU01": "Keep the rounded capsule and add the centered U glyph seen in the OpenCPN witness.",
    "DWLDEF01": "Align the magenta route line, angle-bracket cue, question mark, and DW label to match the OpenCPN witness; current line/label placement is too simplified.",
    "DWRTCL05": "Match the two-way deep-water route witness: thin magenta line, bracket/arrow cues, and DW label placement; current arrows are too large.",
    "DWRTCL06": "Match the fixed-mark two-way deep-water route witness with the correct line/arrow cadence and DW placement; current arrows are too large.",
    "DWRTCL07": "Match the one-way deep-water route witness with small right-arrow cue and DW label; current arrow/label scale is too large.",
    "DWRTCL08": "Match the fixed-mark one-way deep-water route witness with small right-arrow cue and DW label; current arrow/label scale is too large.",
    "FERYRT01": "Use the ferry-route witness: magenta dashed line with the small vessel/route cue, not an F text label.",
    "FERYRT02": "Use the cable-ferry witness: grey dashed line with compact boat/box cue centered on the line; current rectangle is close but too large and not integrated.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    shape = brief.get("required_shape") or "reference witness geometry"
    colours = brief.get("required_colours") or []
    colour_text = f"; required colours {', '.join(colours)}" if colours else "; colours reference-defined"
    return f"{row['asset']} must preserve {shape}{colour_text} and match the provider witness at chart scale."


def _refs(asset: str, row: dict) -> list[str]:
    safe = _safe(asset)
    helm = row.get("helm_candidate") or {}
    refs = [
        f"semantic_brief:{asset}",
        f"s57_conditions:{','.join(row.get('s57_structure', {}).get('conditions') or [])}",
        f"helm_candidate:pipeline/iconforge/assets/svg/triad_generated/{safe}.svg",
        f"source_svg:{helm.get('source_svg')}",
        f"repair_catalog:{SOURCE_BATCH}",
        "source_table:pipeline/iconforge/catalog/standard_source_table.json",
        f"candidate_render:out/triad_reference_candidate_pack/renders/{safe}__day.png",
    ]
    providers = row.get("reference_providers") or {}
    for item in providers.get("opencpn_render") or []:
        paths = item.get("paths") or {}
        for palette in ("day", "dusk", "night"):
            path = paths.get(palette) or item.get(palette)
            if path:
                refs.append(f"opencpn_render_{palette}:{path}")
    for item in providers.get("aquamap") or []:
        if item.get("path"):
            refs.append(f"aquamap_reference:{item['path']}")
    return [ref for ref in refs if not ref.endswith("None")]


def _verdict(asset: str, row: dict) -> dict:
    passed = asset in PASS_ASSETS
    note = PASS_ASSETS.get(asset) or FAIL_REPAIRS[asset]
    return {
        "batch_index": 92,
        "confidence": 0.88 if passed else 0.84,
        "expected": _expected(row),
        "final_approved": False,
        "input_candidate_status": "repaired_pending_judge_rerun",
        "input_source_batch": SOURCE_BATCH,
        "judge_comments": (
            f"Pass pending human: {note} No final approval is granted."
            if passed
            else f"FAIL. {note}"
        ),
        "observed": note,
        "output_candidate_status": "judge_pass_pending_final_approval" if passed else "judge_fail_repair_queue",
        "pass": passed,
        "repair_batch_catalog": SOURCE_BATCH,
        "required_change": (
            "No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact."
            if passed
            else note
        ),
        "safety_reason_codes": [] if passed else [
            "visual_parity_mismatch",
            "reference_witness_not_followed",
            "repairable_batch92_candidate",
        ],
        "source_crop_valid": True,
        "source_refs_used": _refs(asset, row),
        "source_table_id": row.get("source_table_id"),
        "symbol_id": asset,
    }


def build() -> dict:
    rows = _rows()
    verdicts = []
    for asset in sorted({*PASS_ASSETS, *FAIL_REPAIRS}):
        row = rows[asset]
        actual_batch = row["helm_candidate"]["source_batch"]
        if actual_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} source batch drifted: expected {SOURCE_BATCH}, got {actual_batch}")
        verdicts.append(_verdict(asset, row))
    passed = [row["symbol_id"] for row in verdicts if row["pass"]]
    failed = [row["symbol_id"] for row in verdicts if not row["pass"]]
    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged current repaired rows from owned_repair_batch92 against provider witnesses and semantic metadata.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Failures are strict visual-parity failures, not final row rejections.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "selection": {
            "asset_ids": [row["symbol_id"] for row in verdicts],
            "candidate_status": "repaired_pending_judge_rerun",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
            "output_candidate_status_on_fail": "judge_fail_repair_queue",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": [SOURCE_BATCH],
            "source_table": "pipeline/iconforge/catalog/standard_source_table.json",
        },
        "summary": {
            "candidate_status": "repaired_pending_judge_rerun",
            "selected": len(verdicts),
            "pass": len(passed),
            "fail": len(failed),
            "passed_assets": passed,
            "failed_assets": failed,
            "final_approved": 0,
            "source_batches": [SOURCE_BATCH],
        },
        "task_id": "FORGE-15",
        "verdicts": verdicts,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Judge Batch 092 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batch: `owned_repair_batch92`",
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
        "| Symbol | Verdict | Confidence | Required change | Safety reason codes |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for verdict in result["verdicts"]:
        codes = ", ".join(verdict["safety_reason_codes"]) or "-"
        state = "Pass pending human" if verdict["pass"] else "Fail to repair"
        lines.append(
            f"| `{verdict['symbol_id']}` | {state} | {verdict['confidence']:.2f} | "
            f"{verdict['required_change']} | {codes} |"
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
