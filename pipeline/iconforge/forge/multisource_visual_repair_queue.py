"""Build the FORGE-15 visual-model repair queue from linked source examples.

The queue starts with FORGE-14 exact-symbol crop failures, then carries the
generated render, Chart No.1 crop, local OpenCPN reference render, and other
mapped examples into a structured prompt payload. It does not approve artwork;
it prepares auditable jobs for a visual judge and repair generator.

Run:  python -m forge.multisource_visual_repair_queue --limit 50
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from . import exact_crop_gate
from . import multisource_svg_render
from . import opencpn_reference_render


ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "catalog" / "multisource_svg_draft_pack.json"
EXACT_GATE = ROOT / "out" / "forge14_exact_crop_gate" / "report.json"
RENDER_REPORT = ROOT / "out" / "multisource_svg_draft" / "render_report.json"
OPENCPN_REPORT = ROOT / "out" / "opencpn_s52_reference" / "report.json"
OUT_DIR = ROOT / "out" / "multisource_visual_repair"
QUEUE_JSON = OUT_DIR / "repair_queue.json"
README = OUT_DIR / "README.md"
S101_ROOT_CANDIDATES = [
    Path("/private/tmp/helm-s101-portrayal-audit"),
    Path("/private/tmp/s101-audit"),
]


PRIORITY_SHAPES = {
    "topmark": 0,
    "cardinal_mark": 1,
    "conical_buoy": 2,
    "can_buoy": 2,
    "spar_buoy": 2,
    "pillar_buoy": 2,
    "spherical_buoy": 2,
    "barrel_buoy": 2,
    "generic_buoy": 3,
    "beacon": 4,
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _ensure_inputs() -> tuple[dict, dict, dict, dict]:
    if not EXACT_GATE.exists():
        exact_crop_gate.build()
    if not OPENCPN_REPORT.exists():
        opencpn_reference_render.build()
    if not RENDER_REPORT.exists():
        multisource_svg_render.build()
    return (
        _read_json(PACK),
        _read_json(EXACT_GATE),
        _read_json(RENDER_REPORT),
        _read_json(OPENCPN_REPORT),
    )


def _by_asset(rows: list[dict]) -> dict[str, dict]:
    return {row["asset"]: row for row in rows}


def _renders_by_asset(report: dict, palette: str) -> dict[str, dict]:
    return {
        row["asset"]: row
        for row in report["rows"]
        if row["palette"] == palette and row["status"] == "rendered"
    }


def _example_paths(symbol: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for example in symbol.get("examples", []):
        grouped.setdefault(example["source"], []).append(example)
    return grouped


def _strict_invariants(gate_row: dict, symbol: dict) -> list[str]:
    invariants = list(gate_row.get("strict_invariants", []))
    shape = symbol.get("geometry", {}).get("shape")
    colors = symbol.get("geometry", {}).get("color_tokens", [])
    if shape:
        invariants.append(f"Candidate geometry shape is currently classified as {shape}.")
    if colors:
        invariants.append(f"Candidate colour tokens are currently {', '.join(colors)}.")
    return sorted(set(invariants))


def _repair_prompt(job: dict) -> str:
    visual_examples = "\n".join(
        f"- {example['source']} ({example['role']}): {example.get('path') or example.get('url')}"
        for example in job["visual_examples"]
    )
    return (
        "You are repairing a generated-owned nautical chart SVG.\n"
        "Compare the candidate render to the exact Chart No.1 crop first. Use every visual example "
        "listed below as supporting evidence according to its license/status. More examples should "
        "improve the repair, but the exact Chart No.1 crop wins conflicts.\n"
        "Do not trace GPL/OpenCPN raster artwork into the canonical SVG.\n"
        "Return JSON with source_crop_valid, overall_pass, observed, expected, repair_instruction, "
        "safety_reason_codes, confidence, and a corrected SVG candidate when repair is possible.\n\n"
        f"Asset: {job['asset']}\n"
        f"Name: {job['name']}\n"
        f"Chart No.1 class: {job['chart1_class']}\n"
        f"Candidate SVG: {job['candidate']['svg']}\n"
        f"Candidate render: {job['candidate']['render']}\n"
        f"Exact Chart No.1 crop: {job['references']['chart1_exact_crop']['path']}\n"
        f"OpenCPN local oracle render: {job['references']['opencpn_s52_reference_render'].get('path')}\n"
        f"S-101 reference: {job['references'].get('s101_reference')}\n"
        f"Commons references: {job['references'].get('commons_references')}\n"
        f"Visual examples:\n{visual_examples}\n"
        f"Invariants: {' | '.join(job['strict_invariants'])}\n"
        f"Current deterministic reasons: {', '.join(job['deterministic_reasons'])}\n"
    )


def _resolve_s101_path(path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    for root in S101_ROOT_CANDIDATES:
        resolved = root / path
        if resolved.exists():
            return str(resolved)
    return None


def _visual_examples(job: dict) -> list[dict]:
    refs = job["references"]
    examples = [
        {
            "source": "helm_generated_draft_svg",
            "role": "candidate_render_to_repair",
            "status": "generated_pending_visual_parity",
            "path": job["candidate"]["render"],
            "priority": 0,
        },
        {
            "source": "chart1_exact_crop",
            "role": "primary_public_domain_reference",
            "status": refs["chart1_exact_crop"]["status"],
            "path": refs["chart1_exact_crop"]["path"],
            "priority": 1,
        },
    ]
    opencpn = refs["opencpn_s52_reference_render"]
    if opencpn.get("path"):
        examples.append({
            "source": "opencpn_s52_reference_render",
            "role": "local_visual_oracle_not_canonical_artwork",
            "status": opencpn.get("status"),
            "path": opencpn["path"],
            "priority": 2,
        })
    for index, chart1_mapping in enumerate(refs.get("chart1_mappings_examples", []), start=1):
        if chart1_mapping.get("path"):
            examples.append({
                "source": "chart1_mappings_symbol_reference",
                "role": "official_chart1_reference_crop",
                "status": chart1_mapping.get("status"),
                "path": chart1_mapping["path"],
                "label": chart1_mapping.get("int1"),
                "priority": 10 + index,
            })
    for index, s101 in enumerate(refs.get("s101_reference", []), start=1):
        local_path = _resolve_s101_path(s101.get("path"))
        examples.append({
            "source": "s101_portrayal_catalogue_svg",
            "role": "license_pending_visual_reference",
            "status": s101.get("status"),
            "path": s101.get("path"),
            "local_path": local_path,
            "label": s101.get("symbol_id") or s101.get("title"),
            "priority": 30 + index,
        })
    for index, commons in enumerate(refs.get("commons_references", []), start=1):
        examples.append({
            "source": "wikimedia_commons_svg",
            "role": "public_domain_candidate_reference",
            "status": commons.get("status"),
            "url": commons.get("url"),
            "description_url": commons.get("description_url"),
            "label": commons.get("title"),
            "priority": 50 + index,
        })
    return sorted(examples, key=lambda item: item["priority"])


def _job(
    gate_row: dict,
    symbol: dict,
    render_row: dict,
    opencpn_row: dict | None,
    palette: str,
) -> dict:
    examples = _example_paths(symbol)
    chart1 = {
        "status": gate_row["reference_evidence_status"],
        "crop_id": gate_row["reference_crop_id"],
        "path": gate_row["reference_crop"],
        "crop_box_unit": gate_row.get("reference_crop_box_unit"),
        "pages": gate_row.get("reference_pages", []),
        "section": gate_row.get("reference_section"),
    }
    opencpn_path = None
    if opencpn_row and opencpn_row.get("palette_paths"):
        opencpn_path = opencpn_row["palette_paths"].get(palette)
    job = {
        "asset": gate_row["asset"],
        "name": symbol["name"],
        "kind": symbol["kind"],
        "family": symbol["family"],
        "palette": palette,
        "priority": PRIORITY_SHAPES.get(symbol["geometry"]["shape"], 9),
        "chart1_class": gate_row["chart1_class"],
        "candidate": {
            "svg": symbol["asset_file"],
            "render": render_row["render"],
            "geometry": symbol["geometry"],
            "qa": symbol["qa"],
        },
        "references": {
            "chart1_exact_crop": chart1,
            "opencpn_s52_reference_render": {
                "path": opencpn_path,
                "status": (opencpn_row or {}).get("status", "missing"),
                "license_boundary": "local_visual_oracle_not_canonical_artwork",
            },
            "chart1_mappings_examples": examples.get("chart1_mappings_symbol_reference", []),
            "s101_reference": examples.get("s101_portrayal_catalogue_svg", []),
            "commons_references": examples.get("wikimedia_commons_svg", []),
        },
        "strict_invariants": _strict_invariants(gate_row, symbol),
        "deterministic_reasons": gate_row.get("reason_codes", []),
        "expected_judge_schema": {
            "source_crop_valid": "boolean",
            "overall_pass": "boolean",
            "observed": "string",
            "expected": "string",
            "repair_instruction": "string",
            "safety_reason_codes": "string[]",
            "confidence": "number",
            "corrected_svg": "string|null",
        },
        "attempt_log": [],
        "status": "queued_for_visual_judge",
    }
    job["visual_examples"] = _visual_examples(job)
    job["visual_judge_prompt"] = _repair_prompt(job)
    return job


def build(limit: int | None = None, palette: str = "day") -> dict:
    pack, gate, render_report, opencpn_report = _ensure_inputs()
    symbols_by_asset = _by_asset(pack["symbols"])
    renders_by_asset = _renders_by_asset(render_report, palette)
    opencpn_by_asset = _by_asset(opencpn_report["rows"])

    exact_failures = [
        row for row in gate["rows"]
        if row["status"] == "exact_crop_failed_verifier"
        and row["reference_evidence_status"] == "exact_symbol_crop"
    ]
    hard_pile: list[dict] = []
    jobs: list[dict] = []
    for gate_row in exact_failures:
        symbol = symbols_by_asset.get(gate_row["asset"])
        render_row = renders_by_asset.get(gate_row["asset"])
        if not symbol or not symbol.get("asset_file"):
            hard_pile.append({
                "asset": gate_row["asset"],
                "reason": "missing_generated_svg_candidate",
                "reference_crop": gate_row.get("reference_crop"),
            })
            continue
        if not render_row:
            hard_pile.append({
                "asset": gate_row["asset"],
                "reason": f"missing_candidate_render_for_palette_{palette}",
                "candidate_svg": symbol.get("asset_file"),
            })
            continue
        jobs.append(_job(gate_row, symbol, render_row, opencpn_by_asset.get(gate_row["asset"]), palette))

    jobs = sorted(jobs, key=lambda job: (job["priority"], job["asset"]))
    selected = jobs[:limit] if limit else jobs
    shape_counts = Counter(job["candidate"]["geometry"]["shape"] for job in selected)
    reference_counts = Counter()
    visual_example_counts = Counter()
    for job in selected:
        for key, value in job["references"].items():
            if isinstance(value, list):
                if value:
                    reference_counts[key] += 1
            elif value.get("path"):
                reference_counts[key] += 1
        visual_example_counts.update(example["source"] for example in job["visual_examples"])

    result = {
        "schema_version": 1,
        "generator": "iconforge-multisource-visual-repair-queue",
        "status": "ready_explicit_subset" if limit else "ready",
        "source_reports": {
            "exact_crop_gate": "out/forge14_exact_crop_gate/report.json",
            "candidate_renders": "out/multisource_svg_draft/render_report.json",
            "opencpn_reference": "out/opencpn_s52_reference/report.json",
            "multisource_pack": "catalog/multisource_svg_draft_pack.json",
        },
        "selection": {
            "required_gate_status": "exact_crop_failed_verifier",
            "required_reference_evidence_status": "exact_symbol_crop",
            "palette": palette,
            "exact_failures_available": len(exact_failures),
            "queueable_jobs": len(jobs),
            "selected_jobs": len(selected),
            "hard_pile_entries": len(hard_pile),
            "excluded_non_exact_counts": gate["summary"]["evidence_counts"],
            "shape_counts": dict(sorted(shape_counts.items())),
            "reference_counts": dict(sorted(reference_counts.items())),
            "visual_example_counts": dict(sorted(visual_example_counts.items())),
        },
        "non_go_conditions": [
            "Do not queue class_panel_reference or multi_symbol_reference rows until they have exact per-symbol crops.",
            "Do not use OpenCPN/S-52 raster crops as canonical artwork sources.",
            "Do not mark repaired SVGs final-approved until deterministic checks and a visual judge both pass.",
        ],
        "jobs": selected,
        "hard_pile": hard_pile,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    selection = result["selection"]
    lines = [
        "# Multi-Source Visual Repair Queue",
        "",
        "FORGE-15 queue for exact Chart No.1 crop failures.",
        "",
        "## Selection",
        "",
        f"- Status: `{result['status']}`",
        f"- Exact failures available: {selection['exact_failures_available']}",
        f"- Queueable jobs: {selection['queueable_jobs']}",
        f"- Selected jobs: {selection['selected_jobs']}",
        f"- Hard-pile entries: {selection['hard_pile_entries']}",
        f"- Palette: `{selection['palette']}`",
        "",
        "## Shape Counts",
        "",
    ]
    for shape, count in selection["shape_counts"].items():
        lines.append(f"- `{shape}`: {count}")
    lines.extend([
        "",
        "Broad panels and multi-symbol crops are intentionally excluded.",
        "",
    ])
    README.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="explicit queue subset")
    parser.add_argument("--palette", default="day", choices=["day", "dusk", "night"])
    args = parser.parse_args(argv)
    result = build(limit=args.limit, palette=args.palette)
    selection = result["selection"]
    print(f"visual repair queue: {result['status']}")
    print(f"exact failures available: {selection['exact_failures_available']}")
    print(f"queueable jobs: {selection['queueable_jobs']}")
    print(f"selected jobs: {selection['selected_jobs']}")
    print(f"hard pile: {selection['hard_pile_entries']}")
    print(f"report: {QUEUE_JSON}")
    return 0 if selection["hard_pile_entries"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
