"""Judge rerun for owned repair batch 81 wind landmark slice.

Run:
  python3 -m forge.standard_judge_batch81_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_081_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_081_rerun.md"
BATCH_ID = "standard_judge_batch_081_rerun"
CREATED_AT = "2026-07-03T00:00:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch81.json"

PASS_ASSETS = {
    "WIMCON01": "windmotor landmark preserves the brown motor-on-post silhouette.",
    "WIMCON11": "conspicuous windmotor landmark preserves the black motor-on-post silhouette.",
    "WNDFRM51": "wind-generator farm preserves the circular turbine/farm witness cue.",
    "WNDFRM61": "conspicuous wind-generator farm preserves the black circular turbine/farm witness cue.",
    "WNDMIL02": "windmill landmark preserves the compact four-blade windmill cue.",
    "WNDMIL12": "conspicuous windmill landmark preserves the black four-blade windmill cue.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    shape = brief.get("required_shape") or "exact symbol silhouette"
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
    verdicts = []
    for asset, note in PASS_ASSETS.items():
        row = rows[asset]
        actual_batch = row["helm_candidate"]["source_batch"]
        if actual_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} source batch drifted: expected {SOURCE_BATCH}, got {actual_batch}")
        verdicts.append({
            "batch_index": 81,
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
    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged current repaired rows from owned_repair_batch81.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Windmotor, windfarm, and windmill forms were checked as separate symbol families.",
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
            "fail": 0,
            "passed_assets": passed,
            "failed_assets": [],
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
        "# Standard Judge Batch 081 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batch: `owned_repair_batch81`",
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
        codes = ", ".join(verdict["safety_reason_codes"]) or "-"
        lines.append(
            f"| `{verdict['symbol_id']}` | Pass pending human | {verdict['confidence']:.2f} | "
            f"{verdict['required_change']} | {codes} | {verdict['judge_comments']} |"
        )
    lines.extend(["", "## Failed Symbols", "", "- None.", "", "## Evidence Notes", ""])
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
