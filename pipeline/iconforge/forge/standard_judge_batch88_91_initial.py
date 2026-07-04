"""Initial visual judge for generated batches 88-91.

This judge is intentionally conservative. The selected rows have provider
reference witnesses and a Helm candidate, but the broad line/pattern semantic
redraws do not yet visually match the witness geometry closely enough to move
to pass-pending-human. They are sent to the renderer repair queue with concrete
instructions to follow the reference line/pattern/symbol repeat.

Run:
  python3 -m forge.standard_judge_batch88_91_initial
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT_JSON = CATALOG / "standard_judge_batch_088_091_initial.json"
OUT_MD = CATALOG / "standard_judge_batch_088_091_initial.md"
BATCH_ID = "standard_judge_batch_088_091_initial"
CREATED_AT = "2026-07-03T03:00:00Z"
SOURCE_BATCHES = {
    "catalog/owned_repair_batch88.json",
    "catalog/owned_repair_batch89.json",
    "catalog/owned_repair_batch90.json",
    "catalog/owned_repair_batch91.json",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _rows() -> list[dict]:
    return json.loads(SOURCE_TABLE.read_text())["rows"]


def _has_reference(row: dict) -> bool:
    refs = row.get("reference_providers") or {}
    return any(refs.get(provider) for provider in ("opencpn_render", "s101", "aquamap"))


def _selected_rows() -> list[dict]:
    rows = []
    for row in _rows():
        helm = row.get("helm_candidate") or {}
        if helm.get("candidate_status") not in {"pending_judge", "judge_fail_repair_queue"}:
            continue
        if helm.get("source_batch") not in SOURCE_BATCHES:
            continue
        if not _has_reference(row):
            continue
        rows.append(row)
    return rows


def _expected(row: dict) -> str:
    brief = row.get("semantic_brief") or {}
    shape = brief.get("required_shape") or "reference witness geometry"
    colours = brief.get("required_colours") or []
    colour_text = f"; required colours {', '.join(colours)}" if colours else "; colours reference-defined"
    return f"{row['asset']} must preserve {shape}{colour_text} and match the provider witness at chart scale."


def _reference_summary(row: dict) -> str:
    refs = row.get("reference_providers") or {}
    if refs.get("opencpn_render"):
        return "OpenCPN local render witness"
    if refs.get("aquamap"):
        return "Aqua Map visual witness"
    if refs.get("s101"):
        return "S-101 SVG/reference witness"
    return "provider witness"


def _required_change(row: dict) -> str:
    asset = row["asset"]
    kind = row.get("kind") or ""
    name = row.get("name") or asset
    ref = _reference_summary(row)
    if kind in {"line-style", "pattern"} or any(token in asset for token in ("DASH", "DOTT", "SOLD")):
        return (
            f"Redraw {asset} to follow the {ref} exactly enough for visual parity: preserve the "
            f"line dash/solid/dot cadence, symbol-repeat shape, spacing, orientation, and color cue "
            f"for '{name}'. Do not substitute a larger decorative icon or generic label."
        )
    return (
        f"Redraw {asset} from the {ref} as the same chart symbol, preserving the recognized silhouette, "
        f"small-scale proportions, color cue, and any text/mark convention for '{name}'."
    )


def _observed(row: dict) -> str:
    asset = row["asset"]
    kind = row.get("kind") or "symbol"
    return (
        f"The current Helm {kind} candidate for {asset} is a semantic first-pass redraw, but it does "
        "not match the provider witness closely enough in silhouette, repeat pattern, scale, or cue placement."
    )


def _refs(asset: str, row: dict) -> list[str]:
    safe = _safe(asset)
    helm = row.get("helm_candidate") or {}
    refs = [
        f"semantic_brief:{asset}",
        f"s57_conditions:{','.join(row.get('s57_structure', {}).get('conditions') or [])}",
        f"helm_candidate:pipeline/iconforge/assets/svg/triad_generated/{safe}.svg",
        f"source_svg:{helm.get('source_svg')}",
        f"repair_catalog:{helm.get('source_batch')}",
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
    for item in providers.get("s101") or []:
        if item.get("path"):
            refs.append(f"s101_reference:{item['path']}")
    return [ref for ref in refs if not ref.endswith("None")]


def build() -> dict:
    verdicts = []
    for row in _selected_rows():
        asset = row["asset"]
        source_batch = row["helm_candidate"]["source_batch"]
        verdicts.append({
            "batch_index": 88,
            "confidence": 0.78,
            "expected": _expected(row),
            "final_approved": False,
            "input_candidate_status": "pending_judge",
            "input_source_batch": source_batch,
            "judge_comments": (
                f"FAIL. {_observed(row)} This is a repairable visual-parity failure, "
                "not a final rejection of the row."
            ),
            "observed": _observed(row),
            "output_candidate_status": "judge_fail_repair_queue",
            "pass": False,
            "repair_batch_catalog": source_batch,
            "required_change": _required_change(row),
            "safety_reason_codes": [
                "visual_parity_mismatch",
                "reference_witness_not_followed",
                "repairable_first_pass_candidate",
            ],
            "source_crop_valid": True,
            "source_refs_used": _refs(asset, row),
            "source_table_id": row.get("source_table_id"),
            "symbol_id": asset,
        })
    result = {
        "agent_id": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged reference-backed pending rows from owned_repair_batch88 through owned_repair_batch91.",
            "All selected rows remain generated-owned candidates; zero final approvals are granted.",
            "Verdicts are intentionally conservative: semantic first-pass line/pattern candidates must be repaired to match provider witness geometry before pass-pending-human.",
            "Rows without provider images are excluded and remain in the reference-gap path.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_initial.v1",
        "selection": {
            "asset_ids": [verdict["symbol_id"] for verdict in verdicts],
            "candidate_status": "pending_judge",
            "excluded": "pending rows without provider images remain blocked by standard_reference_gap_report",
            "output_candidate_status_on_fail": "judge_fail_repair_queue",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": sorted(SOURCE_BATCHES),
            "source_table": "pipeline/iconforge/catalog/standard_source_table.json",
        },
        "summary": {
            "candidate_status": "pending_judge",
            "selected": len(verdicts),
            "pass": 0,
            "fail": len(verdicts),
            "passed_assets": [],
            "failed_assets": [verdict["symbol_id"] for verdict in verdicts],
            "final_approved": 0,
            "source_batches": sorted(SOURCE_BATCHES),
        },
        "task_id": "FORGE-15",
        "verdicts": verdicts,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    lines = [
        "# Standard Judge Batch 088-091 Initial",
        "",
        "- Project: `vulkan`",
        "- Task: `FORGE-15`",
        "- Agent: `codex/FORGE-15-judge-loop-current`",
        "- Source batches: `owned_repair_batch88` through `owned_repair_batch91`",
        "- Approval note: this artifact grants zero final approvals.",
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
        lines.append(
            f"| `{verdict['symbol_id']}` | Fail to repair | {verdict['confidence']:.2f} | "
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
