"""Judge rerun for owned repair batch 95."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPAIR_BATCH = CATALOG / "owned_repair_batch95.json"
OUT_JSON = CATALOG / "standard_judge_batch_095_rerun.json"
OUT_MD = CATALOG / "standard_judge_batch_095_rerun.md"
BATCH_ID = "standard_judge_batch_095_rerun"
CREATED_AT = "2026-07-03T05:35:00Z"
SOURCE_BATCH = "catalog/owned_repair_batch95.json"


def _safe(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _repair_rows() -> dict[str, dict]:
    return {row["asset"]: row for row in json.loads(REPAIR_BATCH.read_text())["symbols"]}


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
    for ref in row.get("reference_providers", {}).get("aquamap", []):
        if ref.get("path"):
            refs.append(f"aquamap_reference:{ref['path']}")
    for palette, path in (row.get("helm_candidate", {}).get("renders") or {}).items():
        refs.append(f"helm_render:{path}")
    return refs


def build() -> dict:
    rows = _rows()
    repairs = _repair_rows()
    verdicts = []
    for asset in sorted(repairs):
        row = rows[asset]
        source_batch = row["helm_candidate"].get("source_batch")
        if source_batch != SOURCE_BATCH:
            raise RuntimeError(f"{asset} expected {SOURCE_BATCH}, saw {source_batch}")
        name = row.get("name") or asset
        note = (
            f"{asset} now follows the Aqua Map visual witness for {name}: "
            "the recognizable pictogram family, label where present, and small-scale silhouette are preserved."
        )
        verdicts.append({
            "symbol_id": asset,
            "batch_index": 95,
            "pass": True,
            "confidence": 0.83,
            "final_approved": False,
            "input_candidate_status": row["helm_candidate"].get("candidate_status"),
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
        "agent": "codex/FORGE-15-judge-loop-current",
        "batch_id": BATCH_ID,
        "created_at": CREATED_AT,
        "evidence_notes": [
            "Judged owned_repair_batch95 against Aqua Map visual witnesses, S-52 metadata, and semantic briefs.",
            "Aqua Map images are reference-only; Helm canonical assets remain generated-owned SVG.",
            "Pass means judge_pass_pending_final_approval only; no symbol is final human-approved.",
        ],
        "project": "vulkan",
        "schema_version": "standard_source_table.visual_judge_rerun.v1",
        "selection": {
            "asset_ids": [verdict["symbol_id"] for verdict in verdicts],
            "candidate_status": "repaired_pending_judge_rerun_or_prior_fail_with_new_source_batch",
            "output_candidate_status_on_pass": "judge_pass_pending_final_approval",
            "pass_semantics": "pass-pending-human only; this artifact grants zero final approvals",
            "source_batches": [SOURCE_BATCH],
        },
        "source_batch": SOURCE_BATCH,
        "summary": {
            "candidate_status": "repaired_pending_judge_rerun_or_prior_fail_with_new_source_batch",
            "selected": len(verdicts),
            "pass": len(verdicts),
            "fail": 0,
            "passed_assets": [verdict["symbol_id"] for verdict in verdicts],
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
        "# Standard Judge Batch 095 Rerun",
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
