"""Repair a high-confidence subset of the 133-row queue into owned batch 17.

Run:
  python -m forge.standard_repair_batch9 --render
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
SOURCE_QUEUE = CATALOG / "standard_repair_queue.json"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT = ROOT / "out" / "standard_repair_batch9"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch17"
REPORT = CATALOG / "owned_repair_batch17.json"
SUMMARY = CATALOG / "owned_repair_batch17.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81", "BOYCON81", "BOYLAT52", "BOYLAT53", "BOYSPH79", "BOYSPR02",
    "BOYSPR03", "BOYSUP01", "BOYSUP02", "BOYSUP03", "BOYSUP65", "BRIDGE01",
    "BUAARE02", "BUIREL01", "BUIREL04", "BUIREL05", "BUIREL13", "BUIREL14",
    "BUIREL15", "BUNSTA02", "BUNSTA03", "CGUSTA02", "CHIMNY01", "CHIMNY11",
    "CRANES01", "CURDEF01", "CURSRB01", "CUSTOM01", "DANGER53", "DAYSQR01",
    "DAYTRI01", "DAYTRI05", "DGPS01DRFSTA01", "DISMAR03", "DISMAR04",
    "DSHAER01", "DSHAER11", "DWRTPT51", "ESSARE01", "EVENTS02", "FLASTK01",
    "FLASTK11", "FLTHAZ02", "FOGSIG01", "FORSTC01", "FORSTC11", "FRYARE51",
    "FRYARE52", "FSHFAC02", "FSHFAC03", "FSHGRD01", "FSHHAV01", "GATCON03",
    "GATCON04", "HECMTR01", "HECMTR02", "HGWTMK01", "HILTOP01", "HILTOP11",
    "HRBFAC09", "HRBFAC10", "HRBFAC11", "HRBFAC12", "HRBFAC13", "HRBFAC14",
    "HRBFAC15", "HRBFAC16", "HRBFAC17", "HRBFAC18", "HULKES01", "INFARE51",
    "ISODGR51", "ITZARE51", "LITFLT01", "LITFLT02", "LITFLT10", "LITFLT61",
    "LITVES01", "LITVES02", "LITVES60", "LITVES61", "LNDARE01", "LOCMAG01",
    "LOCMAG51", "LOWACC01", "MAGVAR01", "MAGVAR51", "MARCUL02", "MONUMT02",
    "MONUMT12", "MORFAC03", "MORFAC04", "MSTCON04", "MSTCON14", "NEWOBJ 01",
    "NEWOBJ01", "NMKINF01", "NMKINF02", "NMKINF03", "NMKINF04", "NMKINF05",
    "NMKINF06", "NMKINF19", "NMKINF20", "NMKINF21", "NMKINF22", "NMKINF23",
    "NMKINF24", "NMKINF25", "NMKINF26", "NMKINF27", "NMKINF28", "NMKINF29",
    "NMKINF38", "NMKINF40", "NMKINF43", "NMKINF44", "NMKINF45", "NMKINF46",
    "NMKINF47", "NMKINF48", "NMKINF49", "NMKINF50", "NMKINF53", "NMKPRH02",
    "NMKPRH06", "NMKPRH07", "NMKPRH08", "NMKPRH10", "NMKPRH11", "NMKPRH12",
    "NMKPRH13", "NMKPRH14",
]

REPAIRS: dict[str, dict] = {
    "BUAARE02": {"kind": "built_up_dot"},
    "BUIREL01": {"kind": "christian_building", "colour": "brown"},
    "BUIREL04": {"kind": "hourglass_building", "colour": "brown"},
    "BUIREL05": {"kind": "crescent_minaret", "colour": "brown"},
    "BUIREL13": {"kind": "christian_building", "colour": "black"},
    "BUIREL14": {"kind": "hourglass_building", "colour": "black"},
    "BUIREL15": {"kind": "crescent_minaret", "colour": "black"},
    "CHIMNY01": {"kind": "chimney", "colour": "brown"},
    "CHIMNY11": {"kind": "chimney", "colour": "black"},
    "CURSRB01": {"kind": "cursor_open"},
    "DAYSQR01": {"kind": "day_square"},
    "DAYTRI01": {"kind": "day_triangle", "orientation": "up"},
    "DAYTRI05": {"kind": "day_triangle", "orientation": "down"},
    "DSHAER01": {"kind": "dish_aerial", "colour": "brown"},
    "DSHAER11": {"kind": "dish_aerial", "colour": "black"},
    "FLASTK01": {"kind": "flare_stack", "colour": "brown"},
    "FLASTK11": {"kind": "flare_stack", "colour": "black"},
    "FORSTC01": {"kind": "fortified", "colour": "brown"},
    "FORSTC11": {"kind": "fortified", "colour": "black"},
    "HILTOP01": {"kind": "hilltop", "colour": "brown"},
    "HILTOP11": {"kind": "hilltop", "colour": "black"},
    "LOCMAG01": {"kind": "magnetic_anomaly_point"},
    "LOCMAG51": {"kind": "magnetic_anomaly_area"},
    "LOWACC01": {"kind": "low_accuracy"},
    "MAGVAR01": {"kind": "magvar_point"},
    "MAGVAR51": {"kind": "magvar_area"},
}

REPAIR_NOTES = {
    "BUAARE02": "Redraw as a single compact brown built-up-area dot cue; remove the multi-circle cluster and baseline.",
    "BUIREL01": "Redraw as the brown Christian religious-building schematic with a church base and cross cue, not a plain cross.",
    "BUIREL04": "Redraw as the brown non-Christian rectangular/hourglass schematic and remove dome/cross-like features.",
    "BUIREL05": "Redraw as a brown crescent-over-minaret cue with circular base/dot and no extra side minarets.",
    "BUIREL13": "Redraw as the black Christian religious-building schematic with a church base and cross cue, not a plain cross.",
    "BUIREL14": "Redraw as the black non-Christian rectangular/hourglass schematic and remove dome/cross-like features.",
    "BUIREL15": "Redraw as a black crescent-over-minaret cue with circular base/dot and no extra side minarets.",
    "CHIMNY01": "Redraw as a chimney stack with base ring and smoke/top mark.",
    "CHIMNY11": "Redraw as a conspicuous black chimney stack with base ring and smoke/top mark.",
    "CURSRB01": "Remove the circular center ring and render four separated orange cursor arms with an open center gap.",
    "DAYSQR01": "Redraw as a square/rectangular daymark panel on a stem; remove the invented horizontal bar.",
    "DAYTRI01": "Redraw as an upright triangular daymark on a stem, preserving point-up orientation.",
    "DAYTRI05": "Redraw as an inverted triangular daymark on a stem, preserving point-down orientation.",
    "DSHAER01": "Redraw as a dish aerial with curved dish, support stand, and base marker.",
    "DSHAER11": "Redraw as a conspicuous black dish aerial with curved dish, support stand, and base marker.",
    "FLASTK01": "Redraw as a flare stack with vertical stack, base, and flame geometry.",
    "FLASTK11": "Redraw as a conspicuous black flare stack with vertical stack, base, and flame geometry.",
    "FORSTC01": "Redraw as a compact fortified-structure outline with crenellated top and base.",
    "FORSTC11": "Redraw as a conspicuous black fortified-structure outline with crenellated top and base.",
    "HILTOP01": "Redraw as the hill/mountain-top contour silhouette rather than a diamond placeholder.",
    "HILTOP11": "Redraw as the conspicuous black hill/mountain-top contour silhouette rather than a diamond placeholder.",
    "LOCMAG01": "Replace the diamond with a magnetic-anomaly point glyph using a compass needle and field ring.",
    "LOCMAG51": "Replace the diamond with a magenta magnetic-anomaly line/area cue.",
    "LOWACC01": "Replace the diamond with the low-accuracy contour/question-mark cue.",
    "MAGVAR01": "Replace the diamond with a magnetic-variation point glyph.",
    "MAGVAR51": "Replace the diamond with a magenta magnetic-variation line/area glyph.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch9">'
        f"<title>{asset} standard repair batch 17 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _built_up_dot() -> str:
    return (
        f'<circle cx="32" cy="32" r="8.5" fill="{_colour("brown")}" '
        f'stroke="{_colour("black")}" stroke-width="1.3"/>'
    )


def _christian_building(colour: str) -> str:
    return (
        f'<path d="M22 48 H42 V29 L32 20 L22 29 Z" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M32 13 V28 M25 20 H39 M18 53 H46" fill="none" stroke="{_colour(colour)}" stroke-width="4.2"/>'
    )


def _hourglass_building(colour: str) -> str:
    return (
        f'<path d="M23 17 H41 L31 32 L41 47 H23 L33 32 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="4.4"/>'
        f'<path d="M19 53 H45" fill="none" stroke="{_colour(colour)}" stroke-width="4.2"/>'
    )


def _crescent_minaret(colour: str) -> str:
    return (
        f'<path d="M34 13 C27 17 26 29 35 34 C29 35 23 31 22 24 C21 17 26 12 34 13 Z" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="3.8"/>'
        f'<path d="M32 34 V50 M24 50 H40" fill="none" stroke="{_colour(colour)}" stroke-width="4.4"/>'
        f'<circle cx="32" cy="56" r="3.4" fill="{_colour(colour)}" stroke="none"/>'
    )


def _chimney(colour: str) -> str:
    return (
        f'<path d="M27 18 H38 L40 49 H25 Z" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M22 53 H44 M25 43 H40 M31 14 C37 8 43 13 39 19" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="3.5"/>'
    )


def _cursor_open() -> str:
    return (
        f'<path d="M32 8 V23 M32 41 V56 M8 32 H23 M41 32 H56" fill="none" '
        f'stroke="{_colour("orange")}" stroke-width="5.5"/>'
        f'<circle cx="32" cy="32" r="2.5" fill="{_colour("orange")}" stroke="none"/>'
    )


def _day_square() -> str:
    return (
        f'<rect x="20" y="13" width="24" height="24" fill="{_colour("white")}" '
        f'stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M32 37 V57" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _day_triangle(orientation: str) -> str:
    points = "32,12 48,40 16,40" if orientation == "up" else "16,16 48,16 32,44"
    stem_start = 40 if orientation == "up" else 44
    return (
        f'<polygon points="{points}" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M32 {stem_start} V57" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _dish_aerial(colour: str) -> str:
    return (
        f'<path d="M17 25 C25 16 40 15 49 22 C43 35 29 39 18 33 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M31 35 V51 M23 54 H39 M31 44 L43 52" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _flare_stack(colour: str) -> str:
    flame = "orange" if colour == "brown" else "black"
    return (
        f'<path d="M28 23 H38 L40 52 H26 Z" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M23 56 H45 M32 23 V14" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M32 8 C25 16 30 22 36 20 C42 17 39 10 32 8 Z" fill="none" '
        f'stroke="{_colour(flame)}" stroke-width="3.2"/>'
    )


def _fortified(colour: str) -> str:
    return (
        f'<path d="M18 49 V24 H24 V18 H31 V24 H37 V18 H44 V49 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M18 54 H44" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _hilltop(colour: str) -> str:
    return (
        f'<path d="M14 45 C22 29 29 22 35 30 C40 20 48 28 54 45" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="4.5"/>'
        f'<path d="M21 51 H47" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _magnetic_anomaly_point() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<path d="M32 15 L39 34 L32 49 L25 34 Z" fill="none" stroke="{_colour("magenta")}" stroke-width="3.4"/>'
    )


def _magnetic_anomaly_area() -> str:
    return (
        f'<path d="M15 39 C23 22 41 22 49 39" fill="none" stroke="{_colour("magenta")}" '
        'stroke-width="4" stroke-dasharray="6 5"/>'
        f'<path d="M22 49 H42 M32 16 V49" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
    )


def _low_accuracy() -> str:
    return (
        f'<path d="M15 40 C24 28 39 28 49 40" fill="none" stroke="{_colour("black")}" '
        'stroke-width="4" stroke-dasharray="5 5"/>'
        f'<text x="32" y="28" text-anchor="middle" font-size="25" font-family="Arial, sans-serif" '
        f'font-weight="700" fill="{_colour("black")}" stroke="none">?</text>'
    )


def _magvar_point() -> str:
    return (
        f'<path d="M32 12 V52 M22 26 L32 12 L42 26" fill="none" stroke="{_colour("magenta")}" stroke-width="4"/>'
        f'<path d="M21 47 H43" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )


def _magvar_area() -> str:
    return (
        f'<path d="M16 46 C24 36 40 36 48 46" fill="none" stroke="{_colour("magenta")}" '
        'stroke-width="4" stroke-dasharray="5 5"/>'
        f'<path d="M32 14 V49 M24 25 L32 14 L40 25" fill="none" stroke="{_colour("magenta")}" stroke-width="3.5"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "built_up_dot":
        return _svg(asset, _built_up_dot())
    if kind == "christian_building":
        return _svg(asset, _christian_building(spec["colour"]))
    if kind == "hourglass_building":
        return _svg(asset, _hourglass_building(spec["colour"]))
    if kind == "crescent_minaret":
        return _svg(asset, _crescent_minaret(spec["colour"]))
    if kind == "chimney":
        return _svg(asset, _chimney(spec["colour"]))
    if kind == "cursor_open":
        return _svg(asset, _cursor_open())
    if kind == "day_square":
        return _svg(asset, _day_square())
    if kind == "day_triangle":
        return _svg(asset, _day_triangle(spec["orientation"]))
    if kind == "dish_aerial":
        return _svg(asset, _dish_aerial(spec["colour"]))
    if kind == "flare_stack":
        return _svg(asset, _flare_stack(spec["colour"]))
    if kind == "fortified":
        return _svg(asset, _fortified(spec["colour"]))
    if kind == "hilltop":
        return _svg(asset, _hilltop(spec["colour"]))
    if kind == "magnetic_anomaly_point":
        return _svg(asset, _magnetic_anomaly_point())
    if kind == "magnetic_anomaly_area":
        return _svg(asset, _magnetic_anomaly_area())
    if kind == "low_accuracy":
        return _svg(asset, _low_accuracy())
    if kind == "magvar_point":
        return _svg(asset, _magvar_point())
    if kind == "magvar_area":
        return _svg(asset, _magvar_area())
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


def _source_judge_for(item: dict) -> str | None:
    batch = item.get("judge", {}).get("batch")
    if batch:
        return f"catalog/{batch}.json"
    return None


def _provider_count(item: dict) -> int:
    refs = item.get("reference_providers") or {}
    return sum(len(refs.get(name) or []) for name in ("s101", "aquamap", "opencpn_render"))


def _skip_status(item: dict) -> str:
    asset = item.get("asset", "")
    codes = set(item.get("safety_reason_codes") or [])
    required = (item.get("required_change") or "").lower()
    if "regenerate/verify" in required or "regenerate or attach" in required:
        return "blocked_missing_local_reference_render"
    if "missing_reference_crop" in codes or "locate/render" in required or "resolve the exact reference" in required:
        return "blocked_missing_reference_or_exact_crop"
    if {"missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH")):
        return "skipped_batch17_notice_board_family_requires_dedicated_pass"
    if _provider_count(item) < 2:
        return "skipped_batch17_low_reference_confidence"
    if asset.startswith(("BOY", "BCN", "HRBFAC", "LIT", "MORFAC", "GATCON")):
        return "skipped_batch17_geometry_heavy_or_exact_contract"
    return "skipped_batch17_outside_bounded_high_confidence_subset"


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    actual_queue = [item["asset"] for item in queue.get("items", [])]
    if actual_queue != EXPECTED_QUEUE:
        raise RuntimeError(f"unexpected standard repair queue: {actual_queue}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in EXPECTED_QUEUE:
        item = queue_items.get(asset, {})
        source_row = source_rows.get(asset, {})
        if asset not in REPAIRS:
            blockers.append({
                "asset": asset,
                "status": _skip_status(item),
                "required_change": item.get("required_change"),
                "safety_reason_codes": item.get("safety_reason_codes", []),
                "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
                "reference_providers": item.get("reference_providers") or source_row.get("reference_providers", {}),
            })
            continue

        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": item.get("name") or source_row.get("name"),
            "queue_action": item.get("status") or "standard_repair_queue_consumed",
            "risk_bucket": "standard_repair_queue_batch17_high_confidence_subset",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
            "visual_examples": item.get("reference_providers") or source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch9",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": _source_judge_for(item),
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_queue": str(SOURCE_QUEUE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_queue_rows": len(actual_queue),
            "expected_queue_rows": len(EXPECTED_QUEUE),
            "failed_repaired": len(rows),
            "blocked_or_skipped": len(blockers),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
        "blockers": blockers,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 9 / Owned Repair Batch 17",
        "",
        "Owned redraws for a bounded high-confidence subset of the current 133-row standard repair queue.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
    lines.extend(["", "## Blocked / skipped", ""])
    for row in result["blockers"]:
        lines.append(f"- `{row['asset']}`: {row['status']} - {row.get('required_change')}")
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
