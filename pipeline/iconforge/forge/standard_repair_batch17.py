"""Apply human review feedback into owned repair batch 25.

Run:
  python3 -m forge.standard_repair_batch17 --render
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
OUT = ROOT / "out" / "standard_repair_batch17"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch25"
REPORT = CATALOG / "owned_repair_batch25.json"
SUMMARY = CATALOG / "owned_repair_batch25.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS: dict[str, dict] = {
    "BUIREL01": {"kind": "jerusalem_cross", "colour": "brown"},
    "BUIREL13": {"kind": "jerusalem_cross", "colour": "black"},
    "GATCON03": {"kind": "gate_navigable"},
    "GATCON04": {"kind": "gate_non_navigable"},
    "HULKES01": {"kind": "hulk_top_down"},
    "INFORM01": {"kind": "information_marker_aligned"},
    "LNDARE01": {"kind": "land_point_bordered"},
    "LOCMAG01": {"kind": "magnetic_anomaly_sail"},
    "LOWACC01": {"kind": "low_accuracy_reversed"},
    "MAGVAR01": {"kind": "magnetic_variation_flag", "mode": "point"},
    "MAGVAR51": {"kind": "magnetic_variation_flag", "mode": "line"},
    "MARCUL02": {"kind": "marine_farm_cage"},
    "MONUMT02": {"kind": "striped_monument", "colour": "brown"},
    "MONUMT12": {"kind": "striped_monument", "colour": "black"},
}

REPAIR_NOTES = {
    "BUIREL01": "Human review: replace the religious-building/body substitute with a compact brown Jerusalem/potent cross witness.",
    "BUIREL13": "Human review: replace the religious-building/body substitute with a compact black Jerusalem/potent cross witness.",
    "GATCON03": "Human review: magenta circle, two horizontal bars, and two left-pointing gate triangles.",
    "GATCON04": "Human review: magenta circle, two horizontal bars, and a short central vertical closure bar.",
    "HULKES01": "Human review: redraw as a Helm-styled top-down boat/hulk silhouette, not mast/A-frame detail.",
    "INFORM01": "Human review: align the diagonal leader exactly to the square marker corner.",
    "LNDARE01": "Human review: keep the land point but add a Helm-style border.",
    "LOCMAG01": "Human review: redraw as the sail-like magnetic-anomaly wedge/line witness.",
    "LOWACC01": "Human review: reverse the diagonal line direction to match the references.",
    "MAGVAR01": "Human review: redraw as the filled magnetic-variation wedge/flag and vertical line.",
    "MAGVAR51": "Human review: redraw as the filled magnetic-variation wedge/flag and vertical line without dashed underline.",
    "MARCUL02": "Human review: redraw as a fish inside a rectangular cage/net with cage lines behind the fish.",
    "MONUMT02": "Human review: add striped monument lines and reference base/ring cue.",
    "MONUMT12": "Human review: add striped monument lines and reference base/ring cue.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch17">'
        f"<title>{asset} human feedback repair batch 25 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _jerusalem_cross(colour: str) -> str:
    c = _colour(colour)
    return (
        f'<path d="M32 13 V51 M13 32 H51" fill="none" stroke="{c}" stroke-width="4.4"/>'
        f'<path d="M25 13 H39 M25 51 H39 M13 25 V39 M51 25 V39" fill="none" stroke="{c}" stroke-width="3.4"/>'
        f'<path d="M20 20 V27 M16.5 23.5 H23.5 M44 20 V27 M40.5 23.5 H47.5 '
        f'M20 37 V44 M16.5 40.5 H23.5 M44 37 V44 M40.5 40.5 H47.5" '
        f'fill="none" stroke="{c}" stroke-width="2.4"/>'
    )


def _gate_navigable() -> str:
    c = _colour("magenta")
    return (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M18 28 H46 M18 36 H46" fill="none" stroke="{c}" stroke-width="2.9"/>'
        f'<path d="M29 22 L20 32 L29 42 Z M44 22 L35 32 L44 42 Z" fill="none" stroke="{c}" stroke-width="2.7"/>'
    )


def _gate_non_navigable() -> str:
    c = _colour("magenta")
    return (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M18 28 H46 M18 36 H46" fill="none" stroke="{c}" stroke-width="2.9"/>'
        f'<path d="M32 23 V41" fill="none" stroke="{c}" stroke-width="3.1"/>'
    )


def _hulk_top_down() -> str:
    c = _colour("brown")
    return (
        f'<path d="M32 12 C43 18 50 31 43 48 C36 54 28 54 21 48 C14 31 21 18 32 12 Z" '
        f'fill="none" stroke="{c}" stroke-width="3.1"/>'
        f'<path d="M24 42 C29 46 35 46 40 42 M23 30 C29 34 35 34 41 30 '
        f'M32 17 V48" fill="none" stroke="{c}" stroke-width="2.5"/>'
    )


def _information_marker_aligned() -> str:
    c = _colour("magenta")
    return (
        f'<circle cx="17" cy="48" r="4.5" fill="none" stroke="{c}" stroke-width="2.7"/>'
        f'<path d="M20.2 44.8 L38 31" fill="none" stroke="{c}" stroke-width="2.8"/>'
        f'<rect x="38" y="14" width="17" height="17" rx="1" fill="none" stroke="{c}" stroke-width="2.8"/>'
        '<text x="46.5" y="27.5" text-anchor="middle" font-size="16" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" fill="{c}" stroke="none">i</text>'
    )


def _land_point_bordered() -> str:
    c = _colour("brown")
    return (
        f'<circle cx="32" cy="32" r="8.5" fill="var(--white)" stroke="{c}" stroke-width="2.7"/>'
        f'<circle cx="32" cy="32" r="5.5" fill="{c}" stroke="none"/>'
    )


def _magnetic_anomaly_sail() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M25 49 L38 14 L48 49 Z" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M25 49 H50 M32 35 H43" fill="none" stroke="{c}" stroke-width="2.7"/>'
    )


def _low_accuracy_reversed() -> str:
    c = _colour("black")
    return (
        f'<path d="M18 20 L46 48" fill="none" stroke="{c}" stroke-width="3"/>'
        '<text x="25" y="42" text-anchor="middle" font-size="22" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" fill="{c}" stroke="none">?</text>'
    )


def _magnetic_variation_flag(mode: str) -> str:
    c = _colour("magenta")
    body = (
        f'<path d="M30 14 V50" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M31 16 L49 25 L31 34 Z" fill="{c}" stroke="{c}" stroke-width="2.4"/>'
    )
    if mode == "line":
        body += f'<path d="M20 50 H43" fill="none" stroke="{c}" stroke-width="2.5"/>'
    return body


def _marine_farm_cage() -> str:
    c = _colour("brown")
    return (
        f'<rect x="14" y="18" width="38" height="30" fill="none" stroke="{c}" stroke-width="2.8"/>'
        f'<path d="M21 20 V46 M32 20 V46 M43 20 V46 M16 27 H50 M16 39 H50" '
        f'fill="none" stroke="{c}" stroke-width="2"/>'
        f'<path d="M18 33 C25 25 38 25 47 33 C38 41 25 41 18 33 Z" '
        f'fill="var(--white)" stroke="{c}" stroke-width="2.7"/>'
        f'<path d="M40 29 L47 24 M40 37 L47 42 M24 33 H37" fill="none" stroke="{c}" stroke-width="2.2"/>'
        f'<circle cx="26" cy="31" r="1.4" fill="{c}" stroke="none"/>'
    )


def _striped_monument(colour: str) -> str:
    c = _colour(colour)
    return (
        f'<path d="M24 50 L29 17 H35 L40 50 Z" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M20 51 H44 M27 30 L36 24 M26 40 L39 31" fill="none" stroke="{c}" stroke-width="2.5"/>'
        f'<ellipse cx="32" cy="54" rx="7" ry="3.5" fill="none" stroke="{c}" stroke-width="2.4"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "jerusalem_cross":
        return _svg(asset, _jerusalem_cross(spec["colour"]))
    if kind == "gate_navigable":
        return _svg(asset, _gate_navigable())
    if kind == "gate_non_navigable":
        return _svg(asset, _gate_non_navigable())
    if kind == "hulk_top_down":
        return _svg(asset, _hulk_top_down())
    if kind == "information_marker_aligned":
        return _svg(asset, _information_marker_aligned())
    if kind == "land_point_bordered":
        return _svg(asset, _land_point_bordered())
    if kind == "magnetic_anomaly_sail":
        return _svg(asset, _magnetic_anomaly_sail())
    if kind == "low_accuracy_reversed":
        return _svg(asset, _low_accuracy_reversed())
    if kind == "magnetic_variation_flag":
        return _svg(asset, _magnetic_variation_flag(spec["mode"]))
    if kind == "marine_farm_cage":
        return _svg(asset, _marine_farm_cage())
    if kind == "striped_monument":
        return _svg(asset, _striped_monument(spec["colour"]))
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
            "risk_bucket": "human_review_targeted_repair_batch25",
            "candidate_strategy": "owned_redraw_from_human_review_feedback",
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
                "source_priority_basis": "human_review_feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch17",
                "reference_role": "human feedback plus provider refs are shape witnesses; SVG is owned redraw",
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
        "# Standard Repair Batch 17 / Owned Repair Batch 25",
        "",
        "Owned redraws generated from submitted human review feedback.",
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
