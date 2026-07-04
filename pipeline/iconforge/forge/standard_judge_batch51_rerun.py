"""Judge rerun for owned repair batch 51 TOPSHP slice.

Run:
  python3 -m forge.standard_judge_batch51_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_051_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_051_rerun.md"
BATCH_ID = "standard_judge_batch_051_rerun"
CREATED_AT = "2026-07-03T00:00:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch51.json"

PASS_ASSETS = {
    "TOPSHPA4": "red/white compact slanted-board topmark matches the witness family.",
    "TOPSHPA5": "white/black/white compact slanted-board topmark matches the witness family.",
    "TOPSHPA6": "solid red compact slanted-board topmark matches the witness family.",
    "TOPSHPA7": "green/red/green compact slanted-board topmark matches the witness family.",
    "TOPSHPA8": "green/black compact slanted-board topmark matches the witness family.",
    "TOPSHPA9": "white/red compact board topmark matches the row colour semantics.",
    "TOPSHPB0": "red/white compact board topmark matches the row colour semantics.",
    "TOPSHPD1": "orange circular topmark matches the OpenCPN/Chart 1 witness family.",
    "TOPSHPD2": "green circular topmark matches the OpenCPN witness and row colour semantics.",
    "TOPSHPD3": "red circular topmark matches the OpenCPN witness and row colour semantics.",
    "TOPSHPD5": "red/white/black circular partition preserves the row colour semantics closely enough for human review.",
    "TOPSHPI1": "yellow cross topmark matches the OpenCPN/Chart 1 cross witness family.",
    "TOPSHPI2": "black cross topmark matches the OpenCPN/Chart 1 cross witness family.",
    "TOPSHPT1": "red compact slanted-board topmark preserves the red row semantics and is close enough for human review.",
}

FAILS = {
    "TOPSHPI3": {
        "confidence": 0.90,
        "observed": "The repaired SVG renders as a plain black X and loses the white/red semantics visible in the OpenCPN witness and S-57 colour metadata.",
        "required_change": "Redraw TOPSHPI3 as a cross/X topmark that preserves the white/red colour cue; do not collapse it to a plain black X.",
        "codes": ["missing_colour_pattern", "colour_semantics_lost", "reference_mismatch"],
    },
    "TOPSHPJ1": {
        "confidence": 0.92,
        "observed": "The repaired SVG renders as a simple yellow slash, but the OpenCPN witness is a yellow cup/bucket-like TOPSHP17 topmark.",
        "required_change": "Redraw TOPSHPJ1 as the yellow TOPSHP17 cup/bucket-like topmark from the OpenCPN witness, not a diagonal slash.",
        "codes": ["wrong_topmark_silhouette", "wrong_symbol_family", "reference_mismatch"],
    },
    "TOPSHPJ3": {
        "confidence": 0.92,
        "observed": "The repaired SVG is effectively blank/too faint in the current render while the OpenCPN witness is a white cup/bucket-like TOPSHP17 topmark.",
        "required_change": "Redraw TOPSHPJ3 as the white TOPSHP17 cup/bucket-like topmark with visible black outline; do not emit a missing or slash-only candidate.",
        "codes": ["no_visible_art", "wrong_topmark_silhouette", "reference_mismatch"],
    },
    "TOPSHPP2": {
        "confidence": 0.90,
        "observed": "The repaired SVG renders as a yellow diagonal slash, but the OpenCPN witness is a yellow plus/cross topmark.",
        "required_change": "Redraw TOPSHPP2 as a yellow plus/cross topmark, not a diagonal slash.",
        "codes": ["wrong_topmark_silhouette", "wrong_symbol_family", "reference_mismatch"],
    },
    "TOPSHPR1": {
        "confidence": 0.90,
        "observed": "The repaired SVG renders as a black diagonal slash, but the OpenCPN witness is a black trapezoid/conical topmark.",
        "required_change": "Redraw TOPSHPR1 as the black trapezoid/conical topmark from the OpenCPN witness, not a diagonal slash.",
        "codes": ["wrong_topmark_silhouette", "wrong_symbol_family", "reference_mismatch"],
    },
    "TOPSHPS1": {
        "confidence": 0.91,
        "observed": "The repaired SVG renders as a black diagonal slash, but the OpenCPN witness is a target/ring topmark with red-white-red semantics.",
        "required_change": "Redraw TOPSHPS1 as the red/white/red target/ring topmark; do not collapse it to a black slash.",
        "codes": ["wrong_topmark_silhouette", "missing_colour_pattern", "reference_mismatch"],
    },
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    shape = brief.get("required_shape") or "exact topmark silhouette"
    colours = brief.get("required_colours") or []
    colour_text = f"; required colours {', '.join(colours)}" if colours else "; colours reference-defined"
    return f"{row['asset']} must preserve {shape}{colour_text}."


def _refs(asset: str, row: dict) -> list[str]:
    safe = _safe(asset)
    refs = [
        f"semantic_brief:{asset}",
        f"s57_conditions:{','.join(row.get('s57_structure', {}).get('conditions') or [])}",
        f"helm_candidate:pipeline/iconforge/assets/svg/triad_generated/{safe}.svg",
        f"source_svg:{row.get('helm_candidate', {}).get('source_svg')}",
        f"repair_catalog:{SOURCE_BATCH}",
        "source_table:pipeline/iconforge/catalog/standard_source_table.json",
        f"candidate_render:out/triad_reference_candidate_pack/renders/{safe}__day.png",
    ]
    variant = ROOT / "out" / "source_variant_matrix" / "renders" / asset
    for name in ("opencpn_s52_reference_render_1.png", "chart1_parity_reference_crop_1.png"):
        if not (variant / name).exists():
            continue
        rel = variant.relative_to(ROOT) / name
        refs.append(("source_variant_opencpn:" if name.startswith("opencpn") else "chart1_crop:") + str(rel))
    return [ref for ref in refs if not ref.endswith("None")]


def build() -> dict:
    rows = _rows()
    assets = list(PASS_ASSETS) + list(FAILS)
    verdicts = []
    for asset in assets:
        row = rows[asset]
        actual_batch = row["helm_candidate"]["source_batch"]
        if actual_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} source batch drifted: expected {SOURCE_BATCH}, got {actual_batch}")
        if asset in FAILS:
            fail = FAILS[asset]
            verdicts.append({
                "batch_index": 51,
                "confidence": fail["confidence"],
                "expected": _expected(row),
                "final_approved": False,
                "input_candidate_status": "repaired_pending_judge_rerun",
                "input_source_batch": SOURCE_BATCH,
                "judge_comments": f"FAIL. {fail['observed']}",
                "observed": fail["observed"],
                "output_candidate_status": "judge_fail_repair_queue",
                "pass": False,
                "repair_batch_catalog": SOURCE_BATCH,
                "required_change": fail["required_change"],
                "safety_reason_codes": fail["codes"],
                "source_crop_valid": True,
                "source_refs_used": _refs(asset, row),
                "source_table_id": row.get("source_table_id"),
                "symbol_id": asset,
            })
            continue
        note = PASS_ASSETS[asset]
        verdicts.append({
            "batch_index": 51,
            "confidence": 0.86,
            "expected": _expected(row),
            "final_approved": False,
            "input_candidate_status": "repaired_pending_judge_rerun",
            "input_source_batch": SOURCE_BATCH,
            "judge_comments": f"Pass pending human: {note} No final approval is granted.",
            "observed": f"After SVG/render shows {note}",
            "output_candidate_status": "judge_pass_pending_final_approval",
            "pass": True,
            "repair_batch_catalog": SOURCE_BATCH,
            "required_change": "No repair required for this visual/semantic rerun; candidate may move only to judge_pass_pending_final_approval and must not be final-approved by this artifact.",
            "safety_reason_codes": [],
            "source_crop_valid": True,
            "source_refs_used": _refs(asset, row),
            "source_table_id": row.get("source_table_id"),
            "symbol_id": asset,
        })

    passed = [row["symbol_id"] for row in verdicts if row["pass"]]
    failed = [row["symbol_id"] for row in verdicts if not row["pass"]]
    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged current repaired rows from owned_repair_batch51.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Rows that collapsed to slash-only or lost load-bearing colour cues were failed back to repair.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "selection": {
            "asset_ids": [row["symbol_id"] for row in verdicts],
            "candidate_status": "repaired_pending_judge_rerun",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
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
        "# Standard Judge Batch 051 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batch: `owned_repair_batch51`",
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
        "| Symbol | Verdict | Confidence | Required change | Safety reason codes | Notes |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for verdict in result["verdicts"]:
        status = "Pass pending human" if verdict["pass"] else "Fail"
        codes = ", ".join(verdict["safety_reason_codes"]) or "-"
        lines.append(
            f"| `{verdict['symbol_id']}` | {status} | {verdict['confidence']:.2f} | "
            f"{verdict['required_change']} | {codes} | {verdict['judge_comments']} |"
        )
    lines.extend(["", "## Failed Symbols", ""])
    for asset in result["summary"]["failed_assets"]:
        verdict = next(row for row in result["verdicts"] if row["symbol_id"] == asset)
        lines.append(f"- `{asset}`: {verdict['required_change']}")
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
