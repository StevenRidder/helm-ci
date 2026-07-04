"""Repair a high-confidence subset of the 252-row queue into owned batch 20.

Run:
  python3 -m forge.standard_repair_batch12 --render
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
OUT = ROOT / "out" / "standard_repair_batch12"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch20"
REPORT = CATALOG / "owned_repair_batch20.json"
SUMMARY = CATALOG / "owned_repair_batch20.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 252

REPAIRS: dict[str, dict] = {
    "SOUNDG02": {"kind": "sounding"},
    "SCALEB10": {"kind": "scale_vertical", "label": "1M"},
    "SCALEB11": {"kind": "scale_horizontal", "label": "10M"},
    "TNKCON02": {"kind": "tank_ring", "colour": "brown"},
    "TNKCON12": {"kind": "tank_ring", "colour": "black"},
    "TNKFRM01": {"kind": "tank_farm", "colour": "brown"},
    "TNKFRM11": {"kind": "tank_farm", "colour": "black"},
    "TMBYRD01": {"kind": "timber_yard", "colour": "brown"},
    "SWPARE51": {"kind": "swept_area"},
    "SNDWAV02": {"kind": "sand_waves"},
    "RDOCAL02": {"kind": "radio_call", "mode": "one_way"},
    "RDOCAL03": {"kind": "radio_call", "mode": "two_way"},
    "RDOSTA02": {"kind": "radio_station"},
    "RADRFL03": {"kind": "radar_reflector"},
    "RETRFL01": {"kind": "retro_reflector", "colour": "magenta"},
    "RETRFL02": {"kind": "retro_reflector", "colour": "black"},
    "REFPNT02": {"kind": "reference_point"},
    "RECTRC55": {"kind": "recommended_track", "mode": "two_way"},
    "RECTRC56": {"kind": "recommended_track", "mode": "fixed_two_way"},
    "RECTRC57": {"kind": "recommended_track", "mode": "one_way"},
    "RECTRC58": {"kind": "recommended_track", "mode": "fixed_one_way"},
    "RECDEF51": {"kind": "unknown_track"},
    "RCTLPT52": {"kind": "traffic_arrow"},
    "RSCSTA02": {"kind": "reference_star"},
    "RASCAN01": {"kind": "radar_scanner", "colour": "brown"},
    "RASCAN11": {"kind": "radar_scanner", "colour": "black"},
    "RACNSP01": {"kind": "radar_starburst"},
    "QUESMRK1": {"kind": "question_mark"},
    "QUARRY01": {"kind": "quarry"},
    "QUAPOS01": {"kind": "approx_position"},
}

REPAIR_NOTES = {
    "SOUNDG02": "Replace the dashed plus box with a compact black sounding-number glyph.",
    "SCALEB10": "Replace the diamond with a one-mile vertical segmented scalebar.",
    "SCALEB11": "Replace the diamond with a ten-mile horizontal segmented latitude scalebar.",
    "TNKCON02": "Replace the diamond marker with the brown tank circle/ring glyph.",
    "TNKCON12": "Replace the diamond marker with the black tank circle/ring glyph.",
    "TNKFRM01": "Replace the diamond marker with a brown tank-farm clustered-circle glyph.",
    "TNKFRM11": "Replace the dashed area tile with a black tank-farm clustered-circle glyph.",
    "TMBYRD01": "Replace the diamond marker with a brown timber-yard grid glyph.",
    "SWPARE51": "Replace the dashed area tile with a swept-area bracket symbol.",
    "SNDWAV02": "Replace the diamond with a wavy sand-wave line symbol.",
    "RDOCAL02": "Replace the diamond with a one-direction radio call-in point glyph.",
    "RDOCAL03": "Replace the diamond with a both-direction radio call-in point glyph.",
    "RDOSTA02": "Replace the diamond with a radio-station reference glyph.",
    "RADRFL03": "Replace the diamond with a radar-reflector mast and arc glyph.",
    "RETRFL01": "Replace the diamond with a magenta retro-reflector glyph.",
    "RETRFL02": "Replace the diamond with a simplified black retro-reflector glyph.",
    "REFPNT02": "Replace the diamond with an orange reference-point crosshair.",
    "RECTRC55": "Replace the diamond with a recommended two-way track annotation.",
    "RECTRC56": "Replace the diamond with a fixed-mark two-way track annotation.",
    "RECTRC57": "Replace the diamond with a recommended one-way track annotation.",
    "RECTRC58": "Replace the diamond with a fixed-mark one-way track annotation.",
    "RECDEF51": "Replace the diamond with a recommended-track line and unknown-direction cue.",
    "RCTLPT52": "Replace the diamond with a magenta dashed traffic-direction arrow.",
    "RSCSTA02": "Replace the diamond with the reference point/star mark.",
    "RASCAN01": "Replace the diamond with a brown radar-scanner glyph at reference scale.",
    "RASCAN11": "Replace the diamond with a black conspicuous radar-scanner glyph.",
    "RACNSP01": "Replace the diamond with a magenta radar-conspicuous starburst glyph.",
    "QUESMRK1": "Replace the dashed plus box with the magenta question-mark symbol.",
    "QUARRY01": "Replace the point diamond with the brown crossed quarry glyph.",
    "QUAPOS01": "Replace the dashed plus box with a black PA approximate-position label/cue.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _text(x: int, y: int, label: str, colour: str, size: int = 14, weight: int = 700) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="{weight}" fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch12">'
        f"<title>{asset} standard repair batch 20 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _sounding() -> str:
    return (
        f'{_text(27, 35, "12", "black", 22, 700)}'
        f'{_text(45, 40, "3", "black", 12, 700)}'
    )


def _scale_vertical(label: str) -> str:
    body = (
        f'<path d="M32 11 V53" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>'
        f'<path d="M22 11 H42 M24 25 H40 M24 39 H40 M22 53 H42" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3"/>'
    )
    return body + _text(48, 35, label, "black", 11, 700)


def _scale_horizontal(label: str) -> str:
    body = (
        f'<path d="M11 34 H53" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>'
        f'<path d="M11 25 V43 M25 27 V41 M39 27 V41 M53 25 V43" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3"/>'
    )
    return body + _text(32, 22, label, "black", 11, 700)


def _tank_ring(colour: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="15" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<ellipse cx="32" cy="32" rx="22" ry="11" fill="none" stroke="{_colour(colour)}" stroke-width="2.8"/>'
    )


def _tank_farm(colour: str) -> str:
    return (
        f'<circle cx="24" cy="27" r="9" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<circle cx="40" cy="27" r="9" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="42" r="9" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<path d="M25 36 H39" fill="none" stroke="{_colour(colour)}" stroke-width="2.6"/>'
    )


def _timber_yard(colour: str) -> str:
    return (
        f'<rect x="17" y="18" width="30" height="28" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'
        f'<path d="M17 27 H47 M17 37 H47 M27 18 V46 M37 18 V46" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.6"/>'
    )


def _swept_area() -> str:
    return (
        f'<path d="M18 16 H46 M18 48 H46" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<path d="M21 16 C12 25 12 39 21 48 M43 16 C52 25 52 39 43 48" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<path d="M25 32 H39" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8" stroke-dasharray="5 4"/>'
    )


def _sand_waves() -> str:
    return (
        f'<path d="M12 28 C18 20 25 36 32 28 S46 20 52 28" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3.2"/>'
        f'<path d="M12 40 C18 32 25 48 32 40 S46 32 52 40" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3.2"/>'
    )


def _radio_call(mode: str) -> str:
    arrows = (
        f'<path d="M19 32 H45 M36 24 L45 32 L36 40" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )
    if mode == "two_way":
        arrows += f'<path d="M28 24 L19 32 L28 40" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'{arrows}{_text(32, 22, "R", "magenta", 12, 700)}'
    )


def _radio_station() -> str:
    return (
        f'<path d="M32 19 V48" fill="none" stroke="{_colour("magenta")}" stroke-width="3.4"/>'
        f'<path d="M22 48 H42 M25 25 C20 30 20 38 25 43 M39 25 C44 30 44 38 39 43" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<circle cx="32" cy="17" r="4" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    )


def _radar_reflector() -> str:
    return (
        f'<path d="M32 17 V49 M23 49 H41" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>'
        f'<path d="M24 24 L40 32 L24 40 Z" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M42 22 C49 27 49 37 42 42" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
    )


def _retro_reflector(colour: str) -> str:
    return (
        f'<path d="M20 20 L44 32 L20 44 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'
        f'<path d="M26 24 L42 32 L26 40" fill="none" stroke="{_colour(colour)}" stroke-width="2.8"/>'
    )


def _reference_point() -> str:
    return (
        f'<circle cx="32" cy="32" r="15" fill="none" stroke="{_colour("orange")}" stroke-width="3.2"/>'
        f'<path d="M32 13 V51 M13 32 H51" fill="none" stroke="{_colour("orange")}" stroke-width="3"/>'
        f'<circle cx="32" cy="32" r="3.5" fill="{_colour("orange")}" stroke="none"/>'
    )


def _track(mode: str) -> str:
    fixed = "fixed" in mode
    two_way = "two_way" in mode
    body = (
        f'<path d="M13 32 H51" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2" '
        'stroke-dasharray="7 5"/>'
    )
    if two_way:
        body += (
            f'<path d="M22 24 L13 32 L22 40 M42 24 L51 32 L42 40" fill="none" '
            f'stroke="{_colour("magenta")}" stroke-width="3"/>'
        )
    else:
        body += f'<path d="M42 24 L51 32 L42 40" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    if fixed:
        body += f'<circle cx="32" cy="32" r="4" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    return body


def _unknown_track() -> str:
    return _track("one_way") + _text(32, 22, "?", "magenta", 15, 700)


def _traffic_arrow() -> str:
    return (
        f'<path d="M16 43 C28 28 39 24 50 20" fill="none" stroke="{_colour("magenta")}" '
        'stroke-width="3.2" stroke-dasharray="7 5"/>'
        f'<path d="M42 16 L50 20 L45 28" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
    )


def _reference_star() -> str:
    return (
        f'<circle cx="32" cy="32" r="3.5" fill="{_colour("black")}" stroke="none"/>'
        f'<path d="M32 13 V25 M32 39 V51 M13 32 H25 M39 32 H51 M20 20 L28 28 '
        f'M44 20 L36 28 M20 44 L28 36 M44 44 L36 36" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3.2"/>'
    )


def _radar_scanner(colour: str) -> str:
    return (
        f'<path d="M32 18 V48 M22 48 H42" fill="none" stroke="{_colour(colour)}" stroke-width="3.3"/>'
        f'<circle cx="32" cy="18" r="5" fill="none" stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<path d="M20 28 C27 22 37 22 44 28 M17 37 C26 30 38 30 47 37" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.8"/>'
    )


def _radar_starburst() -> str:
    return (
        f'<circle cx="32" cy="32" r="4" fill="{_colour("magenta")}" stroke="none"/>'
        f'<path d="M32 10 V24 M32 40 V54 M10 32 H24 M40 32 H54 M17 17 L27 27 '
        f'M47 17 L37 27 M17 47 L27 37 M47 47 L37 37" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="3.3"/>'
    )


def _question_mark() -> str:
    return (
        f'{_text(32, 42, "?", "magenta", 34, 700)}'
        f'<path d="M16 51 H48" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6" stroke-dasharray="5 4"/>'
    )


def _quarry() -> str:
    return (
        f'<path d="M20 44 L44 20 M20 20 L44 44" fill="none" stroke="{_colour("brown")}" stroke-width="4"/>'
        f'<path d="M17 47 H47 M17 17 H47" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
    )


def _approx_position() -> str:
    return (
        f'{_text(32, 34, "PA", "black", 18, 700)}'
        f'<path d="M17 44 H47" fill="none" stroke="{_colour("black")}" stroke-width="2.8" stroke-dasharray="5 4"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "sounding":
        return _svg(asset, _sounding())
    if kind == "scale_vertical":
        return _svg(asset, _scale_vertical(spec["label"]))
    if kind == "scale_horizontal":
        return _svg(asset, _scale_horizontal(spec["label"]))
    if kind == "tank_ring":
        return _svg(asset, _tank_ring(spec["colour"]))
    if kind == "tank_farm":
        return _svg(asset, _tank_farm(spec["colour"]))
    if kind == "timber_yard":
        return _svg(asset, _timber_yard(spec["colour"]))
    if kind == "swept_area":
        return _svg(asset, _swept_area())
    if kind == "sand_waves":
        return _svg(asset, _sand_waves())
    if kind == "radio_call":
        return _svg(asset, _radio_call(spec["mode"]))
    if kind == "radio_station":
        return _svg(asset, _radio_station())
    if kind == "radar_reflector":
        return _svg(asset, _radar_reflector())
    if kind == "retro_reflector":
        return _svg(asset, _retro_reflector(spec["colour"]))
    if kind == "reference_point":
        return _svg(asset, _reference_point())
    if kind == "recommended_track":
        return _svg(asset, _track(spec["mode"]))
    if kind == "unknown_track":
        return _svg(asset, _unknown_track())
    if kind == "traffic_arrow":
        return _svg(asset, _traffic_arrow())
    if kind == "reference_star":
        return _svg(asset, _reference_star())
    if kind == "radar_scanner":
        return _svg(asset, _radar_scanner(spec["colour"]))
    if kind == "radar_starburst":
        return _svg(asset, _radar_starburst())
    if kind == "question_mark":
        return _svg(asset, _question_mark())
    if kind == "quarry":
        return _svg(asset, _quarry())
    if kind == "approx_position":
        return _svg(asset, _approx_position())
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


def _required_change(item: dict) -> str | None:
    return item.get("required_change") or item.get("judge", {}).get("required_change")


def _safety_codes(item: dict) -> list[str]:
    return item.get("safety_reason_codes") or item.get("judge", {}).get("safety_reason_codes") or []


def _skip_status(item: dict) -> str:
    asset = item.get("asset", "")
    codes = set(_safety_codes(item))
    required = (_required_change(item) or "").lower()
    if "regenerate" in required or "attach the exact" in required or "before passing" in required:
        return "blocked_missing_or_unverified_reference_render"
    if "locate/render" in required or "resolve the exact" in required or "needs an exact" in required:
        return "blocked_missing_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch20_notice_board_family_dedicated_pass"
    if asset.startswith(("TOP", "LIGHTS")):
        return "skipped_batch20_topmark_light_dedicated_pass"
    if asset.startswith(("TID", "CUR")):
        return "skipped_batch20_tide_current_dedicated_pass"
    if asset.startswith(("BCN", "BOY", "DAY", "HRBFAC", "MORFAC", "PRICKE")):
        return "skipped_batch20_geometry_heavy_navigation_aid_contract"
    if asset.startswith(("TNK", "ROLROL", "TRN")) and asset not in REPAIRS:
        return "skipped_batch20_terminal_tank_contract_unclear"
    if _provider_count(item) < 2:
        return "skipped_batch20_low_reference_confidence"
    return "skipped_batch20_outside_bounded_high_confidence_subset"


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    actual_queue = [item["asset"] for item in queue.get("items", [])]
    if len(actual_queue) != EXPECTED_QUEUE_ROWS:
        raise RuntimeError(f"expected {EXPECTED_QUEUE_ROWS} repair queue rows, got {len(actual_queue)}")

    missing = sorted(set(REPAIRS) - set(queue_items))
    if missing:
        raise RuntimeError(f"repair target(s) missing from queue: {missing}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in actual_queue:
        item = queue_items.get(asset, {})
        source_row = source_rows.get(asset, {})
        if asset not in REPAIRS:
            blockers.append({
                "asset": asset,
                "status": _skip_status(item),
                "required_change": _required_change(item),
                "safety_reason_codes": _safety_codes(item),
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
            "risk_bucket": "standard_repair_queue_batch20_high_confidence_subset",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "required_change": _required_change(item),
            "safety_reason_codes": _safety_codes(item),
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
                "generator": "forge.standard_repair_batch12",
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
            "expected_queue_rows": EXPECTED_QUEUE_ROWS,
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
        "# Standard Repair Batch 12 / Owned Repair Batch 20",
        "",
        "Owned redraws for a bounded high-confidence subset of the current 252-row standard repair queue.",
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
