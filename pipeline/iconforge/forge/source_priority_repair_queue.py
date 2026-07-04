"""Build the FORGE-15 Helm-style redraw/repair queue.

This queue starts where FORGE-14 now leaves us: the source-priority pack is a
staging pack, not the final icon set. Exact S-101 rows are shape references
that still need a Helm-style redraw unless license-cleared and intentionally
adopted. Helm-style fallback SVGs need repair against known reference witnesses.

Run:
  python -m forge.source_priority_repair_queue --limit 100 --render
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "catalog" / "source_priority_icon_pack.json"
OUT = ROOT / "out" / "source_priority_repair"
QUEUE_JSON = OUT / "repair_queue.json"
README = OUT / "README.md"

SAFETY_PREFIXES = (
    "BOY", "BCN", "TOP", "LIGHTS", "LIT", "WRECKS", "UWTROC", "OBSTRN",
    "MORFAC", "FOGSIG", "RAD", "RDOCAL", "RDOSTA",
)

PRIORITY_RULES = [
    (0, "navigation_hazard", ("BOYCAR", "BCNCAR", "TOPMAR", "WRECKS", "UWTROC", "OBSTRN")),
    (1, "aids_to_navigation", ("BOY", "BCN", "LIGHTS", "LIT", "FOGSIG")),
    (2, "moorings_and_radio", ("MORFAC", "BOYMOR", "RAD", "RDOCAL", "RDOSTA")),
    (3, "harbor_services", ("HRBFAC", "SMCFAC", "PIL", "ACH", "MARCUL")),
    (4, "traffic_and_regulatory", ("TSS", "RCTL", "RECTRC", "PRCARE", "RESARE")),
]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _risk(asset: str, family: str | None, name: str | None) -> tuple[int, str]:
    for priority, label, prefixes in PRIORITY_RULES:
        if asset.startswith(prefixes):
            return priority, label
    text = f"{family or ''} {name or ''}".lower()
    if any(word in text for word in ["buoy", "beacon", "wreck", "rock", "obstruction", "light"]):
        return 1, "aids_to_navigation"
    if any(word in text for word in ["harbour", "harbor", "marina", "pilot", "mooring"]):
        return 3, "harbor_services"
    return 9, "lower_risk_or_cosmetic"


def _examples_by_source(row: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for example in row.get("examples", []):
        grouped.setdefault(example["source"], []).append(example)
    return grouped


def _source_refs(row: dict) -> dict:
    examples = _examples_by_source(row)
    return {
        "opencpn_s52": examples.get("opencpn_s52_reference_render", []),
        "chart1_parity": examples.get("chart1_parity_reference_crop", []),
        "chart1_mappings": examples.get("chart1_mappings_symbol_reference", []),
        "s101": examples.get("s101_portrayal_catalogue_svg", []),
        "commons": examples.get("wikimedia_commons_svg", []),
        "selected_pack_refs": row.get("source_refs", {}),
    }


def _queue_action(row: dict) -> str:
    basis = row["source_priority"]["selected_basis"]
    if basis == "s101_exact_svg":
        return "redraw_s101_reference_into_helm_style"
    if basis == "helm_multisource_draft_svg":
        return "repair_existing_helm_style_svg"
    return "manual_or_renderer_gap"


def _visual_examples(row: dict, render_candidate: bool) -> list[dict]:
    action = _queue_action(row)
    examples = [
        {
            "source": "selected_source_priority_svg",
            "role": "shape_reference_to_redraw" if action == "redraw_s101_reference_into_helm_style" else "current_candidate_to_repair",
            "status": row["qa"]["visual_parity"],
            "path": row["asset_file"],
            "priority": 0,
        }
    ]
    if render_candidate:
        from . import source_priority_review

        render_path = source_priority_review._rasterize(row)  # Reuses the local review renderer.
        examples.append({
            "source": "selected_source_priority_render",
            "role": "reference_render_to_redraw" if action == "redraw_s101_reference_into_helm_style" else "current_candidate_render_to_compare",
            "status": "rendered" if render_path else "missing",
            "path": str(render_path.relative_to(ROOT)) if render_path else None,
            "priority": 1,
        })
    for example in row.get("examples", []):
        if example["source"] == "helm_generated_draft_svg":
            continue
        examples.append({**example, "priority": 10 + len(examples)})
    return sorted(examples, key=lambda item: item["priority"])


def _repair_prompt(job: dict) -> str:
    refs = "\n".join(
        f"- {example['source']} ({example.get('role')}): {example.get('path') or example.get('url') or example.get('description_url')}"
        for example in job["visual_examples"]
    )
    return (
        "Produce a final Helm-style nautical chart SVG.\n"
        "If the queue action is redraw_s101_reference_into_helm_style, copy the semantic shape and safety-critical colors from the selected reference, but redraw it in the clean Helm visual language.\n"
        "If the queue action is repair_existing_helm_style_svg, preserve the clean Helm stroke/fill style when it is already good and repair only mismatches.\n"
        "Use the references as semantic and shape oracles, not as a style replacement.\n"
        "If S-101, Aqua Map, OpenCPN, Chart 1, or Commons disagree, preserve safety-critical semantics first: silhouette, topmark orientation/count, color order, and symbol class.\n"
        "Do not trace GPL/OpenCPN artwork into the owned SVG. S-101 art is license-pending reference unless separately cleared.\n"
        "Return JSON with: pass_before, source_refs_sufficient, observed_problem, required_change, safety_reason_codes, corrected_svg, confidence.\n\n"
        f"Asset: {job['asset']}\n"
        f"Name: {job['name']}\n"
        f"Queue action: {job['queue_action']}\n"
        f"Risk bucket: {job['risk_bucket']}\n"
        f"Selected source-priority SVG: {job['candidate']['svg']}\n"
        f"Selected source-priority render: {job['candidate'].get('render')}\n"
        f"References:\n{refs}\n"
    )


def _job(row: dict, render_candidate: bool) -> dict:
    priority, bucket = _risk(row["asset"], row.get("family"), row.get("name"))
    action = _queue_action(row)
    visual_examples = _visual_examples(row, render_candidate)
    render_example = next((example for example in visual_examples if example["source"] == "selected_source_priority_render"), {})
    job = {
        "asset": row["asset"],
        "name": row.get("name"),
        "kind": row.get("kind"),
        "family": row.get("family"),
        "source_priority_basis": row["source_priority"]["selected_basis"],
        "queue_action": action,
        "priority": priority,
        "risk_bucket": bucket,
        "candidate": {
            "svg": row["asset_file"],
            "render": render_example.get("path"),
            "provenance": row.get("provenance", {}),
            "qa": row.get("qa", {}),
        },
        "references": _source_refs(row),
        "visual_examples": visual_examples,
        "style_policy": {
            "target": "helm_owned_visual_style",
            "reference_role": "semantic_shape_oracle",
            "preserve_helm_style": True,
            "copy_reference_art_directly": False,
        },
        "expected_output_schema": {
            "pass_before": "boolean",
            "source_refs_sufficient": "boolean",
            "observed_problem": "string",
            "required_change": "string",
            "safety_reason_codes": "string[]",
            "corrected_svg": "string|null",
            "confidence": "number",
        },
        "attempt_log": [],
        "status": "queued_for_style_preserving_repair",
    }
    job["repair_prompt"] = _repair_prompt(job)
    return job


def build(limit: int | None = 100, *, offset: int = 0, render_candidate: bool = False, include_s101_redraw: bool = True) -> dict:
    pack = _read_json(PACK)
    selected_rows = [
        row for row in pack["symbols"]
        if row["source_priority"]["selected_basis"] in {"helm_multisource_draft_svg", "s101_exact_svg"}
    ]
    if not include_s101_redraw:
        selected_rows = [
            row for row in selected_rows
            if row["source_priority"]["selected_basis"] == "helm_multisource_draft_svg"
        ]
    queueable = [row for row in selected_rows if row.get("asset_file")]
    missing_svg = [row for row in selected_rows if not row.get("asset_file")]

    jobs = sorted(
        (_job(row, render_candidate) for row in queueable),
        key=lambda job: (job["priority"], 0 if job["queue_action"] == "repair_existing_helm_style_svg" else 1, job["asset"]),
    )
    selected = jobs[offset:] if limit is None else jobs[offset:offset + limit]
    risk_counts = Counter(job["risk_bucket"] for job in selected)
    family_counts = Counter(job["family"] for job in selected)
    action_counts = Counter(job["queue_action"] for job in selected)
    source_basis_counts = Counter(job["source_priority_basis"] for job in selected)
    reference_counts = Counter()
    for job in selected:
        reference_counts.update(example["source"] for example in job["visual_examples"])

    result = {
        "schema_version": 1,
        "generator": "iconforge-source-priority-repair-queue",
        "status": "ready_batch" if limit else "ready_full_queue",
        "source_pack": "catalog/source_priority_icon_pack.json",
        "selection": {
            "selected_basis": "s101_exact_svg + helm_multisource_draft_svg",
            "source_priority_rows_available": len(selected_rows),
            "queueable_jobs": len(jobs),
            "selected_jobs": len(selected),
            "limit": limit,
            "offset": offset,
            "skipped_jobs": offset,
            "include_s101_redraw": include_s101_redraw,
            "render_candidate": render_candidate,
            "missing_svg_rows": len(missing_svg),
            "action_counts": dict(sorted(action_counts.items())),
            "source_basis_counts": dict(sorted(source_basis_counts.items())),
            "risk_counts": dict(sorted(risk_counts.items())),
            "family_counts": dict(sorted(family_counts.items())),
            "visual_example_counts": dict(sorted(reference_counts.items())),
        },
        "style_policy": [
            "The source-priority pack is a staging/reference pack, not the final canonical Helm icon set.",
            "The final target is Helm-owned visual style, not a wholesale S-101/OpenCPN/AquaMap look.",
            "S-101 exact rows should be redrawn into Helm style unless license-cleared exact reference art is intentionally adopted.",
            "Reference witnesses lock semantics, shapes, colors, and safety invariants.",
            "Repair rows only when the current Helm SVG disagrees with references or safety semantics.",
            "Do not final-approve without rendered before/after, structured critique, deterministic checks, and visual review.",
        ],
        "jobs": selected,
        "hard_pile": [
            {"asset": row["asset"], "reason": "fallback_row_missing_svg", "name": row.get("name")}
            for row in missing_svg
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    QUEUE_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    selection = result["selection"]
    lines = [
        "# Source-Priority Helm-Style Redraw/Repair Queue",
        "",
        "FORGE-15 queue that turns source-priority selections into final Helm-style SVGs.",
        "",
        "## Selection",
        "",
        f"- Source-priority rows available: {selection['source_priority_rows_available']}",
        f"- Queueable jobs: {selection['queueable_jobs']}",
        f"- Selected jobs: {selection['selected_jobs']}",
        f"- Include S-101 redraw rows: {selection['include_s101_redraw']}",
        f"- Candidate renders included: {selection['render_candidate']}",
        "",
        "## Action Counts",
        "",
    ]
    for action, count in selection["action_counts"].items():
        lines.append(f"- `{action}`: {count}")
    lines.extend([
        "",
        "## Risk Buckets",
        "",
    ])
    for bucket, count in selection["risk_counts"].items():
        lines.append(f"- `{bucket}`: {count}")
    lines.extend(["", "## Style Policy", ""])
    for line in result["style_policy"]:
        lines.append(f"- {line}")
    lines.append("")
    README.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="repair batch size; pass 0 for full queue")
    parser.add_argument("--offset", type=int, default=0, help="skip this many sorted queue jobs before selecting the batch")
    parser.add_argument("--render", action="store_true", help="render current candidate PNGs for visual-model input")
    parser.add_argument("--fallback-only", action="store_true", help="exclude S-101 exact rows and queue only existing Helm-style fallback SVGs")
    args = parser.parse_args(argv)
    limit = None if args.limit == 0 else args.limit
    result = build(limit=limit, offset=args.offset, render_candidate=args.render, include_s101_redraw=not args.fallback_only)
    selection = result["selection"]
    print(f"source-priority repair queue: {result['status']}")
    print(f"source-priority rows available: {selection['source_priority_rows_available']}")
    print(f"queueable jobs: {selection['queueable_jobs']}")
    print(f"selected jobs: {selection['selected_jobs']}")
    print(f"action counts: {selection['action_counts']}")
    print(f"risk counts: {selection['risk_counts']}")
    print(f"report: {QUEUE_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
