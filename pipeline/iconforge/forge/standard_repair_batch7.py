"""Repair a high-confidence subset of the 75-row queue into owned batch 15.

Run:
  python -m forge.standard_repair_batch7 --render
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
OUT = ROOT / "out" / "standard_repair_batch7"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch15"
REPORT = CATALOG / "owned_repair_batch15.json"
SUMMARY = CATALOG / "owned_repair_batch15.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81",
    "BOYLAT52",
    "BOYLAT53",
    "BOYSPR01",
    "BOYSPR02",
    "BOYSPR03",
    "BOYSPR70",
    "BOYSPR71",
    "BOYSPR72",
    "BOYSUP01",
    "BOYSUP02",
    "BOYSUP03",
    "BOYSUP65",
    "BRIDGE01",
    "BRTHNO01",
    "BUAARE02",
    "BUIREL01",
    "BUIREL04",
    "BUIREL05",
    "BUIREL13",
    "BUIREL14",
    "BUIREL15",
    "BUISGL01",
    "BUISGL11",
    "BUNSTA02",
    "BUNSTA03",
    "CAIRNS01",
    "CAIRNS11",
    "CBLARE51",
    "CGUSTA02",
    "CHCRDEL1",
    "CHCRID01",
    "CHIMNY01",
    "CHIMNY11",
    "CHINFO06",
    "CHINFO07",
    "CHINFO08",
    "CHINFO09",
    "CHINFO10",
    "CHINFO11",
    "CHKSYM01",
    "CRANES01",
    "CTNARE51",
    "CTYARE51",
    "CURDEF01",
    "CURENT01",
    "CURSRA01",
    "CURSRB01",
    "CUSTOM01",
    "DANGER51",
    "DANGER52",
    "DANGER53",
    "DAYSQR01",
    "DAYSQR21",
    "DAYTRI01",
    "DAYTRI05",
    "DGPS01DRFSTA01",
    "DIRBOY01",
    "DIRBOYA1",
    "DIRBOYB1",
    "DISMAR03",
    "DISMAR04",
    "DISMAR05",
    "DISMAR06",
    "DNGHILIT",
    "DOMES001",
    "DOMES011",
    "DSHAER01",
    "DSHAER11",
    "DWRTPT51",
    "DWRUTE51",
    "EBBSTR01",
    "EBLVRM11",
    "ERBLTIK1",
    "ESSARE01",
]

REPAIRS: dict[str, dict] = {
    "BOYSPR01": {"kind": "spar", "bands": ["white", "black"]},
    "BOYSPR70": {"kind": "spar", "bands": ["black", "yellow", "black"]},
    "BOYSPR71": {"kind": "spar", "bands": ["yellow", "black", "yellow"]},
    "BOYSPR72": {"kind": "spar", "bands": ["black", "red", "black"]},
    "BRTHNO01": {"kind": "berth_number"},
    "BUAARE02": {"kind": "built_up_area"},
    "BUIREL01": {"kind": "christian_religious", "colour": "brown"},
    "BUIREL04": {"kind": "non_christian_religious", "colour": "brown"},
    "BUIREL05": {"kind": "mosque_religious", "colour": "brown"},
    "BUIREL13": {"kind": "christian_religious", "colour": "black"},
    "BUIREL14": {"kind": "non_christian_religious", "colour": "black"},
    "BUIREL15": {"kind": "mosque_religious", "colour": "black"},
    "BUISGL01": {"kind": "single_building", "colour": "brown"},
    "BUISGL11": {"kind": "single_building", "colour": "black"},
    "BUNSTA02": {"kind": "water_bunker"},
    "BUNSTA03": {"kind": "ballast_bunker"},
    "CBLARE51": {"kind": "cable_zigzag"},
    "CHCRDEL1": {"kind": "manual_delete"},
    "CHCRID01": {"kind": "manual_update"},
    "CHINFO06": {"kind": "info_note", "shape": "circle", "glyph": "!", "colour": "magenta"},
    "CHINFO07": {"kind": "info_note", "shape": "square", "glyph": "i", "colour": "magenta"},
    "CHINFO08": {"kind": "info_note", "shape": "square", "glyph": "i", "colour": "orange"},
    "CHINFO09": {"kind": "info_note", "shape": "circle", "glyph": "!", "colour": "orange"},
    "CHINFO10": {"kind": "info_note", "shape": "square", "glyph": "i", "colour": "brown"},
    "CHINFO11": {"kind": "info_note", "shape": "circle", "glyph": "!", "colour": "brown"},
    "CHKSYM01": {"kind": "solid_square"},
    "CURSRA01": {"kind": "cursor_plus"},
    "CURSRB01": {"kind": "cursor_open"},
    "CUSTOM01": {"kind": "customs"},
    "DANGER51": {"kind": "danger_dots", "variant": "defined_depth"},
    "DANGER52": {"kind": "danger_dots", "variant": "less_than_safety_contour"},
    "DAYSQR01": {"kind": "day_square", "variant": "simple"},
    "DAYTRI01": {"kind": "day_triangle", "orientation": "up"},
    "DAYTRI05": {"kind": "day_triangle", "orientation": "down"},
    "EBLVRM11": {"kind": "orange_origin"},
}

REPAIR_NOTES = {
    "BOYSPR01": "Clip the white-over-black spar banding inside the spar silhouette; no external separator strokes.",
    "BOYSPR70": "Clip the black-yellow-black spar banding inside the spar silhouette; no external separator strokes.",
    "BOYSPR71": "Clip the yellow-black-yellow spar banding inside the spar silhouette; no external separator strokes.",
    "BOYSPR72": "Clip the black-red-black spar banding inside the spar silhouette; no external separator strokes.",
    "BRTHNO01": "Redraw as a magenta berth-number circular cue and remove the invented baked text.",
    "BUAARE02": "Redraw as a brown filled built-up-area dot/cluster cue without a square frame or pictorial blocks.",
    "BUIREL01": "Redraw to a brown Christian cross/church schematic cue rather than a filled building silhouette.",
    "BUIREL04": "Redraw to a brown non-Christian religious-building schematic cue.",
    "BUIREL05": "Redraw to a brown mosque/minaret crescent cue and avoid a generic building silhouette.",
    "BUIREL13": "Redraw to the conspicuous black Christian cross/church schematic cue.",
    "BUIREL14": "Redraw to the conspicuous black non-Christian religious-building schematic cue.",
    "BUIREL15": "Redraw to the conspicuous black mosque/minaret crescent cue.",
    "BUISGL01": "Redraw as a compact brown square/building reference silhouette with no roof/door pictogram.",
    "BUISGL11": "Redraw as a compact black square/building reference silhouette with no roof/door pictogram.",
    "BUNSTA02": "Redraw to a water bunker-station bucket/tap cue rather than a generic droplet pictogram.",
    "BUNSTA03": "Redraw to a black ballast-station cube/box service symbol rather than a diamond.",
    "CBLARE51": "Replace the area placeholder with a magenta submarine-cable zig-zag line symbol.",
    "CHCRDEL1": "Replace the diamond placeholder with an orange diagonal manual-delete line symbol.",
    "CHCRID01": "Replace the diamond placeholder with an orange vertical update marker and ring base.",
    "CHINFO06": "Replace the diamond with a circular magenta exclamation-note symbol.",
    "CHINFO07": "Replace the area placeholder with a square magenta information-note symbol and i glyph.",
    "CHINFO08": "Replace the diamond with a square orange information-note symbol and i glyph.",
    "CHINFO09": "Replace the diamond with a circular orange exclamation-note symbol.",
    "CHINFO10": "Replace the diamond with a square olive/brown information-note symbol and i glyph.",
    "CHINFO11": "Replace the diamond with a circular olive/brown exclamation-note symbol.",
    "CHKSYM01": "Replace the diamond with a solid black square size-check symbol.",
    "CURSRA01": "Replace the diamond with an orange plus-shaped cursor.",
    "CURSRB01": "Replace the diamond with a segmented open-centre orange cursor.",
    "CUSTOM01": "Redraw as a circular red/white customs mark rather than a buoy-like diamond.",
    "DANGER51": "Replace the diamond with a dotted black danger boundary symbol.",
    "DANGER52": "Replace the diamond with a dotted black danger boundary symbol with a stronger central hazard dot.",
    "DAYSQR01": "Redraw as a square/rectangular daymark panel with the stem/attachment.",
    "DAYTRI01": "Redraw as an upright triangular daymark with a stem; preserve point-up orientation.",
    "DAYTRI05": "Redraw as an inverted triangular daymark with a stem; preserve point-down orientation.",
    "EBLVRM11": "Replace the diamond with the filled orange circular EBL/VRM origin marker.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch7">'
        f"<title>{asset} standard repair batch 15 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _spar_path() -> str:
    return "M28 10 H36 L39 51 Q32 57 25 51 Z"


def _spar(asset: str, bands: list[str]) -> str:
    band_h = 64 / len(bands)
    fills = [
        f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
        for idx, colour in enumerate(bands)
    ]
    rules = [
        f'<path d="M0 {idx * band_h:g} H64" fill="none" stroke="{_colour("black")}" '
        'stroke-width="0.65" opacity="0.48"/>'
        for idx in range(1, len(bands))
    ]
    return (
        f'<defs><clipPath id="clip-{asset}"><path d="{_spar_path()}"/></clipPath></defs>'
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}{"".join(rules)}</g>'
        f'<path d="{_spar_path()}" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _berth_number() -> str:
    return (
        f'<circle cx="32" cy="32" r="19" fill="none" stroke="{_colour("magenta")}" stroke-width="5"/>'
        f'<circle cx="32" cy="32" r="4.2" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _built_up_area() -> str:
    return (
        f'<circle cx="24" cy="25" r="5.5" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<circle cx="39" cy="24" r="6.2" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<circle cx="31" cy="39" r="6.8" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<path d="M19 49 H45" fill="none" stroke="{_colour("brown")}" stroke-width="4.5"/>'
    )


def _christian(colour: str) -> str:
    return (
        f'<path d="M32 13 V49 M21 25 H43" fill="none" stroke="{_colour(colour)}" stroke-width="6"/>'
        f'<path d="M24 49 H40" fill="none" stroke="{_colour(colour)}" stroke-width="5"/>'
    )


def _non_christian(colour: str) -> str:
    return (
        f'<path d="M18 43 C20 31 25 24 32 24 C39 24 44 31 46 43 Z" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="5"/>'
        f'<path d="M18 48 H46 M24 18 H40 M32 14 V23" fill="none" stroke="{_colour(colour)}" stroke-width="4.4"/>'
    )


def _mosque(colour: str) -> str:
    return (
        f'<path d="M25 43 C26 31 31 25 38 22 C34 29 34 37 42 45 C34 43 29 43 25 43 Z" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="4.4"/>'
        f'<path d="M18 49 V23 M15 26 H21 M18 19 V16 M43 49 V28 M40 31 H46" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _single_building(colour: str) -> str:
    return f'<rect x="22" y="22" width="20" height="20" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="1.6"/>'


def _water_bunker() -> str:
    return (
        f'<path d="M22 28 H45 V34 H38 V49 H25 V34 H22 Z" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M30 21 H45 Q50 21 50 27 V31" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M44 39 C39 45 39 50 44 52 C49 50 49 45 44 39 Z" fill="{_colour("blue")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _ballast_bunker() -> str:
    return (
        f'<path d="M20 26 L32 18 L45 26 L33 34 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<path d="M20 26 V41 L33 49 V34 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<path d="M45 26 V41 L33 49 V34 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _cable_zigzag() -> str:
    return f'<path d="M24 9 L40 17 L24 25 L40 33 L24 41 L40 49 L24 57" fill="none" stroke="{_colour("magenta")}" stroke-width="5"/>'


def _manual_delete() -> str:
    return f'<path d="M16 48 L48 16" fill="none" stroke="{_colour("orange")}" stroke-width="6"/>'


def _manual_update() -> str:
    return (
        f'<path d="M32 12 V45" fill="none" stroke="{_colour("orange")}" stroke-width="6"/>'
        f'<circle cx="32" cy="51" r="7" fill="none" stroke="{_colour("orange")}" stroke-width="4"/>'
    )


def _info_note(shape: str, glyph: str, colour: str) -> str:
    if shape == "circle":
        marker = f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour(colour)}" stroke-width="4.5"/>'
    else:
        marker = f'<rect x="17" y="17" width="30" height="30" fill="none" stroke="{_colour(colour)}" stroke-width="4.5"/>'
    return (
        marker
        + f'<text x="32" y="40" text-anchor="middle" font-size="24" font-family="Arial, sans-serif" '
        f'font-weight="700" fill="{_colour(colour)}" stroke="none">{glyph}</text>'
    )


def _solid_square() -> str:
    return f'<rect x="20" y="20" width="24" height="24" fill="{_colour("black")}" stroke="none"/>'


def _cursor_plus() -> str:
    return (
        f'<path d="M32 10 V54 M10 32 H54" fill="none" stroke="{_colour("orange")}" stroke-width="5"/>'
        f'<circle cx="32" cy="32" r="4" fill="{_colour("orange")}" stroke="none"/>'
    )


def _cursor_open() -> str:
    return (
        f'<path d="M32 9 V22 M32 42 V55 M9 32 H22 M42 32 H55" fill="none" '
        f'stroke="{_colour("orange")}" stroke-width="5"/>'
        f'<circle cx="32" cy="32" r="10" fill="none" stroke="{_colour("orange")}" stroke-width="3.2"/>'
    )


def _customs() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="{_colour("white")}" stroke="{_colour("red")}" stroke-width="5"/>'
        f'<path d="M24 22 A14 14 0 1 0 24 42" fill="none" stroke="{_colour("red")}" stroke-width="5"/>'
    )


def _danger_dots(stronger_center: bool = False) -> str:
    dots = []
    for x, y in [(32, 13), (45, 18), (51, 32), (45, 46), (32, 51), (19, 46), (13, 32), (19, 18)]:
        dots.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{_colour("black")}" stroke="none"/>')
    if stronger_center:
        dots.append(f'<circle cx="32" cy="32" r="5" fill="{_colour("black")}" stroke="none"/>')
    return "".join(dots)


def _day_square() -> str:
    return (
        f'<rect x="20" y="13" width="24" height="24" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 37 V56" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M23 25 H41" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _day_triangle(orientation: str) -> str:
    points = "32,12 48,40 16,40" if orientation == "up" else "16,16 48,16 32,44"
    stem_start = 40 if orientation == "up" else 44
    return (
        f'<polygon points="{points}" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 {stem_start} V57" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _orange_origin() -> str:
    return f'<circle cx="32" cy="32" r="15" fill="{_colour("orange")}" stroke="{_colour("black")}" stroke-width="2"/>'


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "spar":
        return _svg(asset, _spar(asset, spec["bands"]))
    if kind == "berth_number":
        return _svg(asset, _berth_number())
    if kind == "built_up_area":
        return _svg(asset, _built_up_area())
    if kind == "christian_religious":
        return _svg(asset, _christian(spec["colour"]))
    if kind == "non_christian_religious":
        return _svg(asset, _non_christian(spec["colour"]))
    if kind == "mosque_religious":
        return _svg(asset, _mosque(spec["colour"]))
    if kind == "single_building":
        return _svg(asset, _single_building(spec["colour"]))
    if kind == "water_bunker":
        return _svg(asset, _water_bunker())
    if kind == "ballast_bunker":
        return _svg(asset, _ballast_bunker())
    if kind == "cable_zigzag":
        return _svg(asset, _cable_zigzag())
    if kind == "manual_delete":
        return _svg(asset, _manual_delete())
    if kind == "manual_update":
        return _svg(asset, _manual_update())
    if kind == "info_note":
        return _svg(asset, _info_note(spec["shape"], spec["glyph"], spec["colour"]))
    if kind == "solid_square":
        return _svg(asset, _solid_square())
    if kind == "cursor_plus":
        return _svg(asset, _cursor_plus())
    if kind == "cursor_open":
        return _svg(asset, _cursor_open())
    if kind == "customs":
        return _svg(asset, _customs())
    if kind == "danger_dots":
        return _svg(asset, _danger_dots(spec["variant"] == "less_than_safety_contour"))
    if kind == "day_square":
        return _svg(asset, _day_square())
    if kind == "day_triangle":
        return _svg(asset, _day_triangle(spec["orientation"]))
    if kind == "orange_origin":
        return _svg(asset, _orange_origin())
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


def _skip_status(item: dict) -> str:
    codes = set(item.get("safety_reason_codes") or [])
    required = (item.get("required_change") or "").lower()
    if "regenerate/verify" in required or "regenerate or attach" in required:
        return "blocked_missing_local_reference_render"
    if "missing_reference_crop" in codes or "locate/render" in required or "resolve the exact reference" in required:
        return "blocked_missing_reference_or_exact_crop"
    if {"missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    return "skipped_batch15_lower_confidence_or_geometry_heavy"


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
            "risk_bucket": "standard_repair_queue_batch15_high_confidence_subset",
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
                "generator": "forge.standard_repair_batch7",
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
        "# Standard Repair Batch 7 / Owned Repair Batch 15",
        "",
        "Owned redraws for a high-confidence subset of the current 75-row standard repair queue.",
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
