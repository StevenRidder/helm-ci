"""Judge rerun for owned repair batches 83 and 84.

Run:
  python3 -m forge.standard_judge_batch83_84_rerun
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_083_084_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_083_084_rerun.md"
BATCH_ID = "standard_judge_batch_083_084_rerun"
CREATED_AT = "2026-07-02T00:00:00Z"

BATCH83 = "catalog/owned_repair_batch83.json"
BATCH84 = "catalog/owned_repair_batch84.json"

PASS_ASSETS = {
    "BCNGEN68": ("0.88", "beacon/daymark body preserves black-over-yellow semantics from the OpenCPN/Chart 1 witness."),
    "BCNGEN69": ("0.88", "beacon/daymark body preserves yellow-over-black semantics from the OpenCPN/Chart 1 witness."),
    "BCNGEN79": ("0.87", "solid orange beacon/daymark body matches the source-table colour requirement and witness family."),
    "BCNGEN80": ("0.87", "solid black beacon/daymark body matches the source-table colour requirement and witness family."),
    "BCNSPR62": ("0.86", "yellow spar/stake beacon body matches the required vertical spar family."),
    "BOYISD12": ("0.90", "two red isolated-danger dots match the simplified witness and required danger semantics."),
    "BOYMOR01": ("0.84", "mooring/spherical buoy cue and black outline match the provider witnesses closely enough for human review."),
    "BOYMOR03": ("0.82", "can/cylindrical mooring silhouette matches the OpenCPN/Chart 1 witness; colour is treated as reference-defined because the S-57 row has no explicit COLOUR condition."),
    "BOYMOR11": ("0.82", "black mooring-installation silhouette matches the simplified witness family closely enough for human review."),
    "BOYMOR31": ("0.84", "white can/cylindrical mooring silhouette matches the witness and explicit white colour condition."),
    "BOYSAW12": ("0.90", "red safe-water simplified target mark matches the provider witnesses."),
    "BOYSPP11": ("0.84", "yellow special-purpose simplified mark matches the OpenCPN/Chart 1 witness better than a generic diamond."),
    "BOYSPP15": ("0.86", "yellow conical/TSS starboard simplified triangle matches the witness family."),
    "BOYSPP25": ("0.86", "yellow can/TSS port simplified slanted can mark matches the witness family."),
    "TOPSHP09;TE('%s'": ("0.80", "upright triangle silhouette matches the exact crop and restores red/red/green source-table semantics with a text-bearing cue."),
    "TOPSHP15;TE('%s'": ("0.80", "upright triangle silhouette matches the exact crop and restores red/red/yellow source-table semantics with a text-bearing cue."),
    "TOPSHP33": ("0.91", "slanted hollow square topmark matches the exact Chart 1 crop silhouette."),
}

FAILS = {
    "BCNCON81": {
        "confidence": 0.72,
        "observed": "The repaired candidate is a blue/red/white/blue conical buoy body, but the available exact crop shows multiple local symbol components and does not validate that this simplified cone is the exact BCNCON81 beacon symbol.",
        "required_change": "Refine BCNCON81 against a true one-symbol crop or explicit SymbolSpec: preserve the required blue/red/white/blue pattern, but do not promote a conical substitute until the exact crop confirms body, stem, and any text/topmark cue.",
        "codes": ["exact_crop_ambiguous", "unverified_symbol_semantics", "unsafe_symbol_confusion"],
    },
    "TOWERS74|;TX(OBJNAM": {
        "confidence": 0.86,
        "observed": "The candidate is a reasonable thin tower pictogram with orange crossbars, but the available Chart 1 evidence is a broad page/table crop, not a one-symbol source crop for TOWERS74.",
        "required_change": "Create or attach a true TOWERS74 one-symbol crop/render witness, then rerun the judge; keep the tower silhouette direction, but do not promote from broad table evidence.",
        "codes": ["source_crop_not_symbol_tight", "insufficient_visual_evidence", "manual_review_required"],
    },
    "VEHTRF01": {
        "confidence": 0.88,
        "observed": "The candidate replaces the diamond placeholder with a traffic-signal pictogram, but the row lacks a tight VEHTRF01 reference crop and has only broad page evidence.",
        "required_change": "Attach a true VEHTRF01 one-symbol reference crop/render and redraw or confirm the vehicle-traffic geometry from that witness before promotion.",
        "codes": ["source_crop_not_symbol_tight", "insufficient_visual_evidence", "reference_mismatch_unproven"],
    },
    "boyspp50": {
        "confidence": 0.84,
        "observed": "The candidate is a yellow buoy-family pictogram instead of the old diamond, but the only visible Chart 1 evidence is a broad table crop and does not prove the correct boyspp50 body/topmark.",
        "required_change": "Generate or attach a tight boyspp50 OpenCPN/Chart 1 witness, then redraw the yellow buoy-family symbol to that exact body/topmark before promotion.",
        "codes": ["source_crop_not_symbol_tight", "insufficient_visual_evidence", "buoy_body_unverified"],
    },
}


def _safe(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> dict[str, dict]:
    data = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in data["rows"]}


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
        "chart1_parity_reference_crop_1.png",
        "opencpn_s52_reference_render_1.png",
        "chart1_mappings_symbol_reference_1.png",
    ):
        if not (variant / name).exists():
            continue
        rel = variant.relative_to(ROOT) / name
        if name == "chart1_parity_reference_crop_1.png":
            refs.append(f"chart1_crop:{rel}")
        elif name == "opencpn_s52_reference_render_1.png":
            refs.append(f"source_variant_opencpn:{rel}")
        else:
            refs.append(f"chart1_mapping_crop:{rel}")
    return [ref for ref in refs if not ref.endswith("None")]


def _pass_verdict(asset: str, row: dict, source_batch: str) -> dict:
    confidence_text, note = PASS_ASSETS[asset]
    return {
        "batch_index": 83 if source_batch == BATCH83 else 84,
        "confidence": float(confidence_text),
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
    }


def _fail_verdict(asset: str, row: dict, source_batch: str) -> dict:
    fail = FAILS[asset]
    return {
        "batch_index": 83 if source_batch == BATCH83 else 84,
        "confidence": fail["confidence"],
        "expected": _expected(row),
        "final_approved": False,
        "input_candidate_status": "repaired_pending_judge_rerun",
        "input_source_batch": source_batch,
        "judge_comments": f"FAIL. {fail['observed']}",
        "observed": fail["observed"],
        "output_candidate_status": "judge_fail_repair_queue",
        "pass": False,
        "repair_batch_catalog": source_batch,
        "required_change": fail["required_change"],
        "safety_reason_codes": fail["codes"],
        "source_crop_valid": False,
        "source_refs_used": _refs(asset, row, source_batch),
        "source_table_id": row.get("source_table_id"),
        "symbol_id": asset,
    }


def build() -> dict:
    rows = _rows()
    verdicts = []
    source_batches = {**{asset: BATCH83 for asset in list(PASS_ASSETS)[:14]}, **{asset: BATCH84 for asset in list(PASS_ASSETS)[14:]}, **{asset: BATCH84 for asset in FAILS}}
    for asset in sorted(source_batches):
        row = rows[asset]
        source_batch = row["helm_candidate"]["source_batch"]
        expected_batch = source_batches[asset]
        if source_batch != expected_batch:
            raise RuntimeError(f"{asset} source batch drifted: expected {expected_batch}, got {source_batch}")
        if asset in PASS_ASSETS:
            verdicts.append(_pass_verdict(asset, row, source_batch))
        else:
            verdicts.append(_fail_verdict(asset, row, source_batch))

    passed = [row["symbol_id"] for row in verdicts if row["pass"]]
    failed = [row["symbol_id"] for row in verdicts if not row["pass"]]
    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged only current repaired rows from owned_repair_batch83 and owned_repair_batch84.",
            "Pass means judge_pass_pending_final_approval only; this artifact grants zero final approvals.",
            "Rows backed only by broad page/table crops are failed back to the repair/evidence queue rather than promoted.",
            "Verdicts used standard_source_table semantic_brief, S-57 conditions, current generated SVGs/renders, and available Chart 1/OpenCPN/provider witnesses.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "selection": {
            "asset_ids": [row["symbol_id"] for row in verdicts],
            "candidate_status": "repaired_pending_judge_rerun",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": [BATCH83, BATCH84],
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
            "source_batches": [BATCH83, BATCH84],
        },
        "task_id": "FORGE-15",
        "verdicts": verdicts,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Judge Batch 083/084 Rerun",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batches: `owned_repair_batch83`, `owned_repair_batch84`",
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
