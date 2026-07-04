"""Judge rerun for owned repair batch 79 mixed symbol slice.

Run:
  python3 -m forge.standard_judge_batch79_rerun
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_079_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_079_rerun.md"
BATCH_ID = "standard_judge_batch_079_rerun"
CREATED_AT = "2026-07-03T00:00:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch79.json"

PASS_ASSETS = {
    "SILBUI01": "brown silo point mark preserves the circular silo witness.",
    "SILBUI11": "black conspicuous silo point mark preserves the circular witness.",
    "TMBYRD01": "timber-yard mark preserves the crossed-stack/hash witness.",
    "TNKFRM01": "tank-farm mark preserves the circle-with-four-tanks witness.",
    "TNKFRM11": "conspicuous tank-farm mark preserves the black circle-with-four-tanks witness.",
    "TREPNT04": "tree mark is a recognizable Helm-style tree matching the symbol family.",
    "TREPNT05": "mangrove mark preserves the low arch/root witness family.",
    "TRNBSN01": "turning-basin mark preserves the magenta circular-turn cue.",
    "WAYPNT01": "planned-route waypoint preserves the red open-circle cue.",
    "WAYPNT03": "alternate planned-route waypoint preserves the orange open-circle cue.",
    "WAYPNT11": "next planned-route waypoint preserves the concentric red target cue.",
    "WEDKLP03": "weed/kelp mark is a recognizable branch/kelp silhouette matching the witness family.",
    "WTLVGG01": "water-level gauge sign preserves the WL board-on-post cue.",
    "WTLVGG02": "recording water-level gauge preserves the vertical gauge/tick cue.",
}

FAILS = {
    "WATTUR02": {
        "confidence": 0.87,
        "observed": "The repaired SVG renders as two large grey waves, but the OpenCPN/Chart 1 witness for overfalls, eddies and breakers is a compact three-wave turbulence mark.",
        "required_change": "Redraw WATTUR02 as the three-wave overfalls/eddies/breakers mark from the witness; keep the compact grey water-turbulence silhouette and do not collapse it to two generic waves.",
        "codes": ["wrong_wave_count", "oversimplified_symbol", "reference_mismatch"],
    },
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
                "batch_index": 79,
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
            "batch_index": 79,
            "confidence": 0.85,
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
            "Judged current repaired rows from owned_repair_batch79.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Rows that lost a witness-level symbol detail were failed back to repair.",
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
        "# Standard Judge Batch 079 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batch: `owned_repair_batch79`",
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
