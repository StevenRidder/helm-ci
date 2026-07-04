"""Repair a conservative subset of the 557-row queue into owned batch 23.

Run:
  python3 -m forge.standard_repair_batch15 --render
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
OUT = ROOT / "out" / "standard_repair_batch15"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch23"
REPORT = CATALOG / "owned_repair_batch23.json"
SUMMARY = CATALOG / "owned_repair_batch23.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 557

REPAIRS: dict[str, dict] = {
    "BRIDGE01": {"kind": "opening_bridge"},
    "CRANES01": {"kind": "gantry_crane"},
    "CURDEF01": {"kind": "current_unknown"},
    "DWRTPT51": {"kind": "deep_water_route"},
    "ESSARE01": {"kind": "essa"},
    "FAIRWY51": {"kind": "fairway", "mode": "one_way"},
    "FAIRWY52": {"kind": "fairway", "mode": "two_way"},
    "FLDSTR01": {"kind": "flood_stream"},
    "FLGSTF01": {"kind": "flagstaff"},
    "FLTHAZ02": {"kind": "floating_hazard"},
    "FOGSIG01": {"kind": "fog_signal"},
    "FORSTC01": {"kind": "fortified", "colour": "brown"},
    "FORSTC11": {"kind": "fortified", "colour": "black"},
    "FRYARE51": {"kind": "ferry_area", "mode": "ferry"},
    "FRYARE52": {"kind": "ferry_area", "mode": "cable"},
    "FSHFAC02": {"kind": "fishing_stakes_panel"},
    "FSHFAC03": {"kind": "fishing_stakes_pattern"},
    "FSHHAV01": {"kind": "fish_haven"},
    "HRBFAC09": {"kind": "fishing_harbour"},
    "OBSTRN03": {"kind": "obstruction_covers_uncovers"},
    "OFSPLF01": {"kind": "offshore_platform"},
    "PILBOP02": {"kind": "pilot_boarding"},
    "PILPNT02": {"kind": "pile_bollard"},
    "POSGEN01": {"kind": "position_point"},
}

REPAIR_NOTES = {
    "BRIDGE01": "Redraw as clean magenta concentric opening-bridge rings with no diagonal slash or centre clutter.",
    "CRANES01": "Redraw as a quay/gantry crane with twin vertical legs, top beam, trolley, hook, and base.",
    "CURDEF01": "Keep the current arrow and unknown-direction question cues, but use the reference gray/slate colour family.",
    "DWRTPT51": "Keep only the DW text cue at reference proportions; remove the dashed underline.",
    "ESSARE01": "Use the ESSA text witness only; remove the invented dashed boundary underline.",
    "FAIRWY51": "Redraw as a hollow one-way fairway arrow in the reference stroke colour.",
    "FAIRWY52": "Redraw as a hollow two-way fairway arrow in the reference stroke colour.",
    "FLDSTR01": "Redraw as a gray flood-stream arrow with one spring-rate crossbar, not stacked bars.",
    "FLGSTF01": "Redraw as a flagstaff with square flag and foot structure, not a circular base.",
    "FLTHAZ02": "Redraw as the circled-X floating-hazard mark with a lower hazard contour.",
    "FOGSIG01": "Redraw as three fog-signal sound arcs without a bell or arch placeholder.",
    "FORSTC01": "Redraw as the plain brown fortified-structure square outline without battlements.",
    "FORSTC11": "Redraw as the plain black conspicuous fortified-structure square outline without battlements.",
    "FRYARE51": "Redraw as a dashed ferry-area route with the ferry outline riding on the line.",
    "FRYARE52": "Redraw as a cable-ferry horizontal line witness with ferry outline and no wake arcs.",
    "FSHFAC02": "Redraw as a rectangular fishing-stake panel with one diagonal stake/line.",
    "FSHFAC03": "Redraw as a horizontal fishing-stakes pattern: baseline with several vertical posts.",
    "FSHHAV01": "Replace the dashed rectangle with a dotted oval fish-haven enclosure around the fish.",
    "HRBFAC09": "Redraw as a fishing-harbour facility mark using a fish/letter service convention.",
    "OBSTRN03": "Redraw with a filled/tinted obstruction circle and dotted perimeter.",
    "OFSPLF01": "Redraw as the square offshore-platform glyph with a central dot.",
    "PILBOP02": "Redraw as the magenta circle/diamond pilot-boarding witness without P text or stem.",
    "PILPNT02": "Redraw as the black pile/bollard point mark, not a signpost.",
    "POSGEN01": "Keep ring/dot position geometry but move to the brown reference colour family.",
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
        'data-repair-batch="standard-repair-batch15">'
        f"<title>{asset} standard repair batch 23 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _opening_bridge() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<circle cx="32" cy="32" r="9" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    )


def _gantry_crane() -> str:
    return (
        f'<path d="M18 50 V22 H48 V50" fill="none" stroke="{_colour("brown")}" stroke-width="3.3"/>'
        f'<path d="M14 50 H52 M18 32 H48" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M34 22 V39 M30 39 H38 M34 39 V45" fill="none" stroke="{_colour("brown")}" stroke-width="2.7"/>'
        f'<path d="M43 22 L50 16" fill="none" stroke="{_colour("brown")}" stroke-width="2.7"/>'
    )


def _current_unknown() -> str:
    return (
        f'<path d="M32 51 V16 M24 25 L32 16 L40 25" fill="none" stroke="{_colour("gray")}" stroke-width="3.2"/>'
        f'<path d="M26 43 L32 50 L38 43" fill="none" stroke="{_colour("gray")}" stroke-width="2.7"/>'
        f'{_text(18, 35, "?", "gray", 15, 700)}{_text(46, 35, "?", "gray", 15, 700)}'
    )


def _deep_water_route() -> str:
    return _text(32, 39, "DW", "magenta", 25, 700)


def _essa() -> str:
    return _text(32, 38, "ESSA", "magenta", 18, 700)


def _fairway(mode: str) -> str:
    body = (
        f'<path d="M26 50 H38 V25 H46 L32 11 L18 25 H26 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3.1"/>'
    )
    if mode == "two_way":
        body += (
            f'<path d="M26 14 H38 V39 H46 L32 53 L18 39 H26 Z" fill="none" '
            f'stroke="{_colour("black")}" stroke-width="3.1"/>'
        )
    return body


def _flood_stream() -> str:
    return (
        f'<path d="M32 52 V14 M23 23 L32 14 L41 23" fill="none" stroke="{_colour("gray")}" stroke-width="3.2"/>'
        f'<path d="M23 38 H41" fill="none" stroke="{_colour("gray")}" stroke-width="2.8"/>'
    )


def _flagstaff() -> str:
    return (
        f'<path d="M25 51 V14" fill="none" stroke="{_colour("brown")}" stroke-width="3.3"/>'
        f'<path d="M27 16 H48 V30 H27 Z" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<path d="M18 51 H34 M21 56 H31 M22 51 L18 56 M28 51 L33 56" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.7"/>'
    )


def _floating_hazard() -> str:
    return (
        f'<circle cx="32" cy="28" r="16" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M22 18 L42 38 M42 18 L22 38" fill="none" stroke="{_colour("magenta")}" stroke-width="2.9"/>'
        f'<path d="M19 47 C25 41 39 41 45 47 C38 51 26 51 19 47 Z" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    )


def _fog_signal() -> str:
    return (
        f'<path d="M18 46 C24 37 40 37 46 46" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<path d="M12 50 C21 30 43 30 52 50" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<path d="M24 42 C28 38 36 38 40 42" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )


def _fortified(colour: str) -> str:
    return f'<path d="M18 18 H46 V46 H18 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'


def _ferry_area(mode: str) -> str:
    line_dash = ' stroke-dasharray="7 5"' if mode == "ferry" else ""
    body = (
        f'<path d="M10 39 H54" fill="none" stroke="{_colour("black")}" stroke-width="3"{line_dash}/>'
        f'<path d="M21 37 H43 L38 27 H26 Z" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M24 39 H40" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )
    if mode == "cable":
        body += f'<path d="M12 23 H52" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
    return body


def _fishing_stakes_panel() -> str:
    return (
        f'<rect x="16" y="20" width="34" height="28" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<path d="M20 44 L46 24" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M22 20 V48 M44 20 V48" fill="none" stroke="{_colour("brown")}" stroke-width="2.3"/>'
    )


def _fishing_stakes_pattern() -> str:
    return (
        f'<path d="M12 43 H54" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M17 43 V21 M26 43 V18 M35 43 V21 M44 43 V18 M53 43 V24" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.8"/>'
    )


def _fish_outline(colour: str = "brown") -> str:
    return (
        f'<path d="M13 32 C22 20 39 20 50 32 C39 44 22 44 13 32 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.8"/>'
        f'<path d="M50 32 L57 25 M50 32 L57 39" fill="none" stroke="{_colour(colour)}" stroke-width="2.8"/>'
        f'<circle cx="22" cy="30" r="1.7" fill="{_colour(colour)}" stroke="none"/>'
    )


def _fish_haven() -> str:
    return (
        f'<ellipse cx="32" cy="32" rx="25" ry="17" fill="none" stroke="{_colour("brown")}" '
        'stroke-width="2.8" stroke-dasharray="1 5"/>'
        f'{_fish_outline("brown")}'
    )


def _fishing_harbour() -> str:
    return (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M18 33 C25 24 37 24 46 33 C37 42 25 42 18 33 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2.7"/>'
        f'<path d="M46 33 L53 27 M46 33 L53 39" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
        f'{_text(32, 53, "F", "black", 11, 700)}'
    )


def _obstruction_covers_uncovers() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="{_colour("black")}" fill-opacity="0.18" '
        f'stroke="{_colour("black")}" stroke-width="2.8" stroke-dasharray="1 5"/>'
        f'<circle cx="32" cy="32" r="8" fill="{_colour("black")}" fill-opacity="0.38" '
        f'stroke="{_colour("black")}" stroke-width="2.5"/>'
    )


def _offshore_platform() -> str:
    return (
        f'<rect x="19" y="19" width="26" height="26" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="32" r="4" fill="{_colour("black")}" stroke="none"/>'
    )


def _pilot_boarding() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M32 17 L47 32 L32 47 L17 32 Z" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )


def _pile_bollard() -> str:
    return (
        f'<path d="M25 46 H39 L36 20 H28 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2.6"/>'
        f'<ellipse cx="32" cy="20" rx="5" ry="3.5" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2.2"/>'
    )


def _position_point() -> str:
    return (
        f'<circle cx="32" cy="32" r="13" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<circle cx="32" cy="32" r="4" fill="{_colour("brown")}" stroke="none"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "opening_bridge":
        return _svg(asset, _opening_bridge())
    if kind == "gantry_crane":
        return _svg(asset, _gantry_crane())
    if kind == "current_unknown":
        return _svg(asset, _current_unknown())
    if kind == "deep_water_route":
        return _svg(asset, _deep_water_route())
    if kind == "essa":
        return _svg(asset, _essa())
    if kind == "fairway":
        return _svg(asset, _fairway(spec["mode"]))
    if kind == "flood_stream":
        return _svg(asset, _flood_stream())
    if kind == "flagstaff":
        return _svg(asset, _flagstaff())
    if kind == "floating_hazard":
        return _svg(asset, _floating_hazard())
    if kind == "fog_signal":
        return _svg(asset, _fog_signal())
    if kind == "fortified":
        return _svg(asset, _fortified(spec["colour"]))
    if kind == "ferry_area":
        return _svg(asset, _ferry_area(spec["mode"]))
    if kind == "fishing_stakes_panel":
        return _svg(asset, _fishing_stakes_panel())
    if kind == "fishing_stakes_pattern":
        return _svg(asset, _fishing_stakes_pattern())
    if kind == "fish_haven":
        return _svg(asset, _fish_haven())
    if kind == "fishing_harbour":
        return _svg(asset, _fishing_harbour())
    if kind == "obstruction_covers_uncovers":
        return _svg(asset, _obstruction_covers_uncovers())
    if kind == "offshore_platform":
        return _svg(asset, _offshore_platform())
    if kind == "pilot_boarding":
        return _svg(asset, _pilot_boarding())
    if kind == "pile_bollard":
        return _svg(asset, _pile_bollard())
    if kind == "position_point":
        return _svg(asset, _position_point())
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
    status = item.get("status", "")
    codes = set(_safety_codes(item))
    required = (_required_change(item) or "").lower()
    if status == "queued_for_chart1_parity_repair":
        return "skipped_batch23_chart1_parity_exact_crop_or_manual_exception_required"
    if (
        "regenerate" in required
        or "attach the exact" in required
        or "before passing" in required
        or "provide a valid reference" in required
        or "verify against" in required
    ):
        return "blocked_batch23_missing_or_unverified_reference_render"
    if "locate/render" in required or "resolve the exact" in required or "needs an exact" in required:
        return "blocked_batch23_missing_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_batch23_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch23_notice_board_family_dedicated_pass"
    if asset.startswith(("TOP", "LIGHTS", "LIT", "DAY")):
        return "skipped_batch23_topmark_daymark_or_light_dedicated_pass"
    if asset.startswith(("BCN", "BOY", "PRICKE")):
        return "skipped_batch23_geometry_heavy_navigation_aid_contract"
    if _provider_count(item) < 2 and item.get("status") == "queued_for_render_repair":
        return "skipped_batch23_low_reference_confidence"
    return "skipped_batch23_outside_bounded_high_confidence_subset"


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
            "risk_bucket": "standard_repair_queue_batch23_high_confidence_non_aid_subset",
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
                "generator": "forge.standard_repair_batch15",
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
        "# Standard Repair Batch 15 / Owned Repair Batch 23",
        "",
        "Owned redraws for a bounded non-aid/non-light/non-notice subset of the current 557-row standard repair queue.",
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
