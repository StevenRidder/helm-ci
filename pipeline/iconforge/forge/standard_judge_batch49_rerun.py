"""Judge rerun for owned repair batch 49 TOPSHP slice.

Run:
  python3 -m forge.standard_judge_batch49_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_049_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_049_rerun.md"
BATCH_ID = "standard_judge_batch_049_rerun"
CREATED_AT = "2026-07-03T00:00:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch49.json"

FAILS = {
    "TOPSHP47": {
        "confidence": 0.93,
        "observed": "The repaired SVG renders as a tall upright rectangle, while the OpenCPN/Chart 1 witnesses show a compact square/slanted-board topmark.",
        "required_change": "Redraw TOPSHP47 as a compact square/slanted-board topmark, preserving the red/red colour semantics; do not use a tall rectangle body.",
        "codes": ["wrong_topmark_silhouette", "wrong_aspect_ratio", "reference_mismatch"],
    },
    "TOPSHP48": {
        "confidence": 0.93,
        "observed": "The repaired SVG renders as a tall upright rectangle, while the OpenCPN/Chart 1 witnesses show a compact square/slanted-board topmark.",
        "required_change": "Redraw TOPSHP48 as a compact square/slanted-board topmark, preserving the green/green colour semantics; do not use a tall rectangle body.",
        "codes": ["wrong_topmark_silhouette", "wrong_aspect_ratio", "reference_mismatch"],
    },
}

PASS_NOTES = {
    "TOPSHP51": "diamond/topmark silhouette and white-black-white partition match the witness family.",
    "TOPSHP52": "solid black diamond/topmark silhouette matches the witness family.",
    "TOPSHP53": "solid yellow diamond/topmark silhouette matches the witness family.",
    "TOPSHP54": "solid red diamond/topmark silhouette matches the witness family.",
    "TOPSHP55": "solid orange diamond/topmark silhouette matches the witness family.",
    "TOPSHP58": "red/white diamond partition matches the witness family.",
    "TOPSHP61": "orange/white diamond partition matches the witness family.",
    "TOPSHP62": "white/orange diamond partition matches the witness family.",
    "TOPSHP63": "white/red/white diamond partition matches the witness family.",
    "TOPSHP64": "white/green/white diamond partition matches the witness family.",
    "TOPSHP65": "white/red diamond partition matches the witness family.",
    "TOPSHP67": "orange/white diamond partition matches the witness family.",
    "TOPSHP69": "white/red diamond partition matches the witness family.",
    "TOPSHP70": "yellow diamond/topmark silhouette matches the witness family.",
    "TOPSHP71": "white/orange diamond partition matches the witness family.",
    "TOPSHP72": "white/red/white diamond partition matches the witness family.",
    "TOPSHP73;TE('%s'": "white/black/white diamond partition and text-bearing cue match the S-52 row well enough for human review.",
    "TOPSHP74": "red/white/white/red diamond partition matches the witness family.",
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
    assets = list(FAILS) + list(PASS_NOTES)
    verdicts = []
    for asset in assets:
        row = rows[asset]
        actual_batch = row["helm_candidate"]["source_batch"]
        if actual_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} source batch drifted: expected {SOURCE_BATCH}, got {actual_batch}")
        if asset in FAILS:
            fail = FAILS[asset]
            verdicts.append({
                "batch_index": 49,
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
        note = PASS_NOTES[asset]
        verdicts.append({
            "batch_index": 49,
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
            "Judged current repaired rows from owned_repair_batch49.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "TOPSHP47 and TOPSHP48 fail because the generated candidate is a tall rectangle instead of the compact square/slanted-board witness shape.",
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
        "# Standard Judge Batch 049 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batch: `owned_repair_batch49`",
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
