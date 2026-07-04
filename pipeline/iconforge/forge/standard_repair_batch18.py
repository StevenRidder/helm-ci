"""Apply the remaining human review feedback into owned repair batch 26.

Run:
  python3 -m forge.standard_repair_batch18 --render
"""
from __future__ import annotations

import argparse
import ctypes.util
import json
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
FEEDBACK = ROOT / "out" / "human_review" / "icon_review_feedback.json"
OUT = ROOT / "out" / "standard_repair_batch18"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch26"
REPORT = CATALOG / "owned_repair_batch26.json"
SUMMARY = CATALOG / "owned_repair_batch26.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS: dict[str, dict] = {
    "MORFAC03": {"kind": "mooring_dolphin_square"},
    "MORFAC04": {"kind": "deviation_mooring_dolphin"},
    "MSTCON04": {"kind": "mast_triangular", "colour": "brown"},
    "MSTCON14": {"kind": "mast_triangular", "colour": "black"},
    "POSGEN04": {"kind": "position_ring"},
}

REPAIR_NOTES = {
    "MORFAC03": "Human review: redraw as the simple S-101/OpenCPN mooring-dolphin square witness; remove pile/ladder substitution.",
    "MORFAC04": "Human review: redraw as the trapezoid-and-center-pole deviation mooring-dolphin witness.",
    "MSTCON04": "Human review: redraw as the tall triangular mast witness with base circle, not a single line.",
    "MSTCON14": "Human review: redraw as the black conspicuous tall triangular mast witness with base circle.",
    "POSGEN04": "Human review: redraw as a single plain position ring; remove inner rings, dots, and triangles.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch18">'
        f"<title>{asset} human feedback repair batch 26 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _mooring_dolphin_square() -> str:
    c = _colour("black")
    land = _colour("brown")
    return (
        f'<rect x="19" y="19" width="26" height="26" rx="1.5" fill="{land}" '
        f'stroke="{c}" stroke-width="4.6"/>'
    )


def _deviation_mooring_dolphin() -> str:
    c = _colour("black")
    return (
        f'<path d="M17 50 H47" fill="none" stroke="{c}" stroke-width="3.4"/>'
        f'<path d="M22 50 L27 23 H37 L42 50" fill="none" stroke="{c}" stroke-width="3.2"/>'
        f'<path d="M32 50 V13" fill="none" stroke="{c}" stroke-width="3.4"/>'
    )


def _mast_triangular(colour: str) -> str:
    c = _colour(colour)
    return (
        f'<path d="M18 50 H27 M37 50 H46" fill="none" stroke="{c}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="50" r="5.3" fill="var(--white)" stroke="{c}" stroke-width="3.2"/>'
        f'<path d="M27 50 L32 12 L37 50" fill="none" stroke="{c}" stroke-width="3.5"/>'
    )


def _position_ring() -> str:
    c = _colour("black")
    return f'<circle cx="32" cy="32" r="15" fill="none" stroke="{c}" stroke-width="4"/>'


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "mooring_dolphin_square":
        return _svg(asset, _mooring_dolphin_square())
    if kind == "deviation_mooring_dolphin":
        return _svg(asset, _deviation_mooring_dolphin())
    if kind == "mast_triangular":
        return _svg(asset, _mast_triangular(spec["colour"]))
    if kind == "position_ring":
        return _svg(asset, _position_ring())
    raise KeyError(f"unsupported repair kind: {kind}")


def _ensure_cairo_library() -> None:
    if ctypes.util.find_library("cairo") or not HOMEBREW_CAIRO.exists():
        return
    original_find_library = ctypes.util.find_library

    def find_library(name: str) -> str | None:
        if name in {"cairo", "cairo-2", "libcairo-2"}:
            return str(HOMEBREW_CAIRO)
        return original_find_library(name)

    ctypes.util.find_library = find_library


def _render_svg(svg: str, asset: str, palette: str) -> str:
    _ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _feedback_rows() -> dict[str, dict]:
    data = json.loads(FEEDBACK.read_text())
    rows = data.get("checked_rows") or []
    return {row["asset"]: row for row in rows if row.get("asset") in REPAIRS}


def _source_rows() -> dict[str, dict]:
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


def build(*, render_outputs: bool = False) -> dict:
    feedback_rows = _feedback_rows()
    missing_feedback = sorted(set(REPAIRS) - set(feedback_rows))
    if missing_feedback:
        raise RuntimeError(f"human feedback missing repair target(s): {missing_feedback}")

    source_rows = _source_rows()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in sorted(REPAIRS):
        feedback = feedback_rows[asset]
        source_row = source_rows.get(asset, {})
        helm = source_row.get("helm_candidate") or {}
        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": feedback.get("name") or source_row.get("name"),
            "queue_action": "human_review_feedback_consumed",
            "risk_bucket": "human_review_targeted_repair_batch26",
            "candidate_strategy": "owned_redraw_from_human_review_feedback_and_s101_shape_witness",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "human_feedback": {
                "priority": feedback.get("priority"),
                "reason_codes": feedback.get("reason_codes"),
                "feedback": feedback.get("feedback"),
                "expected_change": feedback.get("expected_change"),
            },
            "required_change": feedback.get("expected_change") or feedback.get("feedback"),
            "safety_reason_codes": [
                code
                for code in str(feedback.get("reason_codes") or "").split(";")
                if code
            ],
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "human_review_feedback_plus_s101_reference",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch18",
                "reference_role": "S-101/OpenCPN/Aqua Map/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": (
                f"catalog/{source_row.get('judge', {}).get('latest', {}).get('batch')}.json"
                if source_row.get("judge", {}).get("latest", {}).get("batch")
                else None
            ),
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_feedback": str(FEEDBACK.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "human_feedback_rows": len(feedback_rows),
            "failed_repaired": len(rows),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 18 / Owned Repair Batch 26",
        "",
        "Owned redraws generated from the remaining submitted human review feedback.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
        feedback = row.get("human_feedback", {}).get("feedback")
        if feedback:
            lines.append(f"  - Human feedback: {feedback.strip()}")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved."])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
