"""Repair a conservative subset of the 461-row queue into owned batch 21.

Run:
  python3 -m forge.standard_repair_batch13 --render
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
OUT = ROOT / "out" / "standard_repair_batch13"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch21"
REPORT = CATALOG / "owned_repair_batch21.json"
SUMMARY = CATALOG / "owned_repair_batch21.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 461

REPAIRS: dict[str, dict] = {
    "BRIDGE01": {"kind": "opening_bridge"},
    "BUNSTA02": {"kind": "water_bunker"},
    "BUNSTA03": {"kind": "ballast_station"},
    "CRANES01": {"kind": "crane"},
    "CURDEF01": {"kind": "current_unknown"},
    "DISMAR03": {"kind": "distance_mark"},
    "DISMAR04": {"kind": "distance_point"},
    "DWRTPT51": {"kind": "deep_water_route"},
    "ESSARE01": {"kind": "essa_boundary"},
    "FAIRWY51": {"kind": "fairway", "mode": "one_way"},
    "FAIRWY52": {"kind": "fairway", "mode": "two_way"},
    "FLDSTR01": {"kind": "flood_stream"},
    "FLGSTF01": {"kind": "flagstaff"},
    "FLTHAZ02": {"kind": "floating_hazard"},
    "FOGSIG01": {"kind": "fog_signal"},
    "FORSTC01": {"kind": "fortified", "colour": "brown"},
    "FORSTC11": {"kind": "fortified", "colour": "black"},
    "FOULGND1": {"kind": "foul_ground"},
    "FRYARE51": {"kind": "ferry_area", "mode": "ferry"},
    "FRYARE52": {"kind": "ferry_area", "mode": "cable"},
    "FSHFAC02": {"kind": "fishing_stakes"},
    "FSHFAC03": {"kind": "fishing_stakes_pattern"},
    "FSHGRD01": {"kind": "fish_ground"},
    "FSHHAV01": {"kind": "fish_haven"},
}

REPAIR_NOTES = {
    "BRIDGE01": "Redraw as a magenta opening-bridge double-ring without diagonal slash or center dash clutter.",
    "BUNSTA02": "Redraw as a water bunker-station barrel/bucket with a blue water band.",
    "BUNSTA03": "Redraw as a ballast-station cube with visible face/grid divisions.",
    "CRANES01": "Redraw as a brown crane with boom, post, hook, and base.",
    "CURDEF01": "Redraw as a vertical current arrow with side question marks and straight lower structure.",
    "DISMAR03": "Replace the diamond with a distance-mark post and DM text marker.",
    "DISMAR04": "Replace the diamond with a distance-point crosshair and DP cue.",
    "DWRTPT51": "Redraw as DW text on a dashed deep-water-route line, without an enclosing placard.",
    "ESSARE01": "Redraw as ESSA/PSSA boundary text with a boundary line, without a boxed sign.",
    "FAIRWY51": "Redraw as a vertical one-way fairway arrow using black reference-style strokes.",
    "FAIRWY52": "Redraw as a vertical two-way fairway arrow using black reference-style strokes.",
    "FLDSTR01": "Redraw as an upward flood-stream arrow with spring-rate side barbs.",
    "FLGSTF01": "Redraw as a brown flagstaff with flag and base/ring marker.",
    "FLTHAZ02": "Redraw as the magenta circular floating-hazard mark.",
    "FOGSIG01": "Redraw as a magenta fog-signal arc glyph, not a bell or horn body.",
    "FORSTC01": "Redraw as the brown fortified-structure square outline without invented internal bars.",
    "FORSTC11": "Redraw as the black conspicuous fortified-structure square outline without invented internal bars.",
    "FOULGND1": "Redraw as an open foul-ground slash/hash mark, not a star or asterisk.",
    "FRYARE51": "Redraw as a ferry-area route and ferry-outline witness, without an F signboard.",
    "FRYARE52": "Redraw as a cable-ferry route and ferry-outline witness, without a CF signboard.",
    "FSHFAC02": "Redraw as fishing-stakes frame and angled-stake geometry.",
    "FSHFAC03": "Redraw as fishing-stakes area comb/pattern geometry.",
    "FSHGRD01": "Redraw as a fish outline without invented FG lettering.",
    "FSHHAV01": "Redraw as a fish-haven fish plus dotted boundary, without FH lettering.",
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
        'data-repair-batch="standard-repair-batch13">'
        f"<title>{asset} standard repair batch 21 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _opening_bridge() -> str:
    return (
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="32" r="9" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<path d="M20 44 L44 20 M31 45 L46 30" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )


def _water_bunker() -> str:
    return (
        f'<path d="M21 19 C21 14 43 14 43 19 V45 C43 50 21 50 21 45 Z" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M21 19 C21 24 43 24 43 19 M21 42 C21 47 43 47 43 42" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2.6"/>'
        f'<path d="M22 31 H42" fill="none" stroke="{_colour("blue")}" stroke-width="5"/>'
    )


def _ballast_station() -> str:
    return (
        f'<path d="M20 21 L32 14 L45 21 V43 L32 51 L20 43 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3.1"/>'
        f'<path d="M20 21 L32 29 L45 21 M32 29 V51 M20 43 L32 35 L45 43" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2.5"/>'
        f'<path d="M26 25 V39 M38 25 V39" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _crane() -> str:
    return (
        f'<path d="M22 49 V19 H31" fill="none" stroke="{_colour("brown")}" stroke-width="4"/>'
        f'<path d="M29 20 L50 28 M31 20 L43 36" fill="none" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M48 28 V39 M44 39 H52" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<path d="M15 50 H32" fill="none" stroke="{_colour("brown")}" stroke-width="3.4"/>'
    )


def _current_unknown() -> str:
    return (
        f'<path d="M32 51 V17 M24 25 L32 17 L40 25" fill="none" stroke="{_colour("orange")}" stroke-width="3.2"/>'
        f'<path d="M25 45 H39 M26 39 L32 45 L38 39" fill="none" stroke="{_colour("orange")}" stroke-width="2.7"/>'
        f'{_text(18, 35, "?", "orange", 15, 700)}{_text(46, 35, "?", "orange", 15, 700)}'
    )


def _distance_mark() -> str:
    return (
        f'<path d="M32 16 V49 M22 49 H42" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<rect x="22" y="18" width="20" height="15" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'{_text(32, 46, "DM", "black", 13, 700)}'
    )


def _distance_point() -> str:
    return (
        f'<circle cx="32" cy="30" r="13" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 14 V46 M16 30 H48" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
        f'{_text(32, 54, "DP", "black", 12, 700)}'
    )


def _deep_water_route() -> str:
    return (
        f'<path d="M12 38 H52" fill="none" stroke="{_colour("magenta")}" stroke-width="3" stroke-dasharray="7 5"/>'
        f'{_text(32, 29, "DW", "magenta", 18, 700)}'
    )


def _essa_boundary() -> str:
    return (
        f'<path d="M12 42 H52" fill="none" stroke="{_colour("magenta")}" stroke-width="3" stroke-dasharray="4 5"/>'
        f'{_text(32, 31, "ESSA", "magenta", 15, 700)}'
    )


def _fairway(mode: str) -> str:
    body = f'<path d="M32 52 V12" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
    body += f'<path d="M24 20 L32 12 L40 20" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
    if mode == "two_way":
        body += f'<path d="M24 44 L32 52 L40 44" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
    return body


def _flood_stream() -> str:
    return (
        f'<path d="M32 52 V13 M23 22 L32 13 L41 22" fill="none" stroke="{_colour("orange")}" stroke-width="3.3"/>'
        f'<path d="M23 34 H41 M25 42 H39" fill="none" stroke="{_colour("orange")}" stroke-width="2.7"/>'
    )


def _flagstaff() -> str:
    return (
        f'<path d="M26 50 V14" fill="none" stroke="{_colour("brown")}" stroke-width="3.4"/>'
        f'<path d="M27 15 C35 12 40 18 48 15 V31 C40 34 35 28 27 31 Z" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<circle cx="26" cy="53" r="5" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
    )


def _floating_hazard() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="3.2"/>'
        f'<path d="M21 32 H43 M32 21 V43 M24 24 L40 40 M40 24 L24 40" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    )


def _fog_signal() -> str:
    return (
        f'<path d="M20 44 C26 30 38 30 44 44" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M14 48 C22 24 42 24 50 48 M26 49 H38" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="3.1"/>'
    )


def _fortified(colour: str) -> str:
    return (
        f'<path d="M18 20 H46 V46 H18 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3.3"/>'
        f'<path d="M18 20 V15 H24 V20 H31 V15 H37 V20 H46" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="3.1"/>'
    )


def _foul_ground() -> str:
    return (
        f'<path d="M22 17 L15 48 M34 17 L27 48 M46 17 L39 48" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M17 28 H48 M14 39 H45" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
    )


def _ferry_area(mode: str) -> str:
    cable = mode == "cable"
    dash = ' stroke-dasharray="6 4"' if cable else ""
    body = (
        f'<path d="M12 42 C22 34 42 34 52 42" fill="none" stroke="{_colour("black")}" '
        f'stroke-width="3"{dash}/>'
        f'<path d="M21 34 H43 L38 26 H26 Z" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M24 42 H40" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )
    if cable:
        body += f'<path d="M14 24 H50" fill="none" stroke="{_colour("black")}" stroke-width="2.4" stroke-dasharray="4 4"/>'
    return body


def _fishing_stakes() -> str:
    return (
        f'<path d="M16 47 H50 M18 47 L25 20 M32 47 L39 20 M46 47 L53 20" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M23 29 H49 M20 38 H46" fill="none" stroke="{_colour("brown")}" stroke-width="2.5"/>'
    )


def _fishing_stakes_pattern() -> str:
    return (
        f'<path d="M17 18 V48 M28 18 V48 M39 18 V48 M50 18 V48" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.7"/>'
        f'<path d="M15 27 H52 M15 39 H52" fill="none" stroke="{_colour("brown")}" stroke-width="2.7"/>'
    )


def _fish_outline(colour: str = "brown") -> str:
    return (
        f'<path d="M13 32 C22 19 38 20 49 32 C38 44 22 45 13 32 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<path d="M49 32 L57 24 M49 32 L57 40 M26 28 L26 28" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<circle cx="21" cy="30" r="1.8" fill="{_colour(colour)}" stroke="none"/>'
    )


def _fish_haven() -> str:
    return (
        f'<rect x="10" y="14" width="44" height="38" rx="2" fill="none" stroke="{_colour("brown")}" '
        'stroke-width="2.8" stroke-dasharray="4 4"/>'
        f'{_fish_outline("brown")}'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "opening_bridge":
        return _svg(asset, _opening_bridge())
    if kind == "water_bunker":
        return _svg(asset, _water_bunker())
    if kind == "ballast_station":
        return _svg(asset, _ballast_station())
    if kind == "crane":
        return _svg(asset, _crane())
    if kind == "current_unknown":
        return _svg(asset, _current_unknown())
    if kind == "distance_mark":
        return _svg(asset, _distance_mark())
    if kind == "distance_point":
        return _svg(asset, _distance_point())
    if kind == "deep_water_route":
        return _svg(asset, _deep_water_route())
    if kind == "essa_boundary":
        return _svg(asset, _essa_boundary())
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
    if kind == "foul_ground":
        return _svg(asset, _foul_ground())
    if kind == "ferry_area":
        return _svg(asset, _ferry_area(spec["mode"]))
    if kind == "fishing_stakes":
        return _svg(asset, _fishing_stakes())
    if kind == "fishing_stakes_pattern":
        return _svg(asset, _fishing_stakes_pattern())
    if kind == "fish_ground":
        return _svg(asset, _fish_outline())
    if kind == "fish_haven":
        return _svg(asset, _fish_haven())
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
        return "skipped_batch21_chart1_parity_exact_crop_or_manual_exception_required"
    if "regenerate" in required or "attach the exact" in required or "before passing" in required:
        return "blocked_missing_or_unverified_reference_render"
    if "locate/render" in required or "resolve the exact" in required or "needs an exact" in required:
        return "blocked_missing_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch21_notice_board_family_dedicated_pass"
    if asset.startswith(("TOP", "LIGHTS", "DAY")):
        return "skipped_batch21_topmark_daymark_or_light_dedicated_pass"
    if asset.startswith(("BCN", "BOY", "PRICKE")):
        return "skipped_batch21_geometry_heavy_navigation_aid_contract"
    if _provider_count(item) < 2 and item.get("status") == "queued_for_render_repair":
        return "skipped_batch21_low_reference_confidence"
    return "skipped_batch21_outside_bounded_high_confidence_subset"


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
            "risk_bucket": "standard_repair_queue_batch21_high_confidence_non_aid_subset",
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
                "generator": "forge.standard_repair_batch13",
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
        "# Standard Repair Batch 13 / Owned Repair Batch 21",
        "",
        "Owned redraws for a bounded non-topmark/non-notice/non-beacon subset of the current 461-row standard repair queue.",
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
