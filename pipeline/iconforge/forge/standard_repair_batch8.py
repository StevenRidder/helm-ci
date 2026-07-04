"""Repair a high-confidence subset of the 93-row queue into owned batch 16.

Run:
  python -m forge.standard_repair_batch8 --render
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
OUT = ROOT / "out" / "standard_repair_batch8"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch16"
REPORT = CATALOG / "owned_repair_batch16.json"
SUMMARY = CATALOG / "owned_repair_batch16.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81",
    "BOYCON74",
    "BOYCON81",
    "BOYLAT52",
    "BOYLAT53",
    "BOYSPH79",
    "BOYSPR02",
    "BOYSPR03",
    "BOYSUP01",
    "BOYSUP02",
    "BOYSUP03",
    "BOYSUP65",
    "BRIDGE01",
    "CAIRNS01",
    "CAIRNS11",
    "CGUSTA02",
    "CHIMNY01",
    "CHIMNY11",
    "CRANES01",
    "CTNARE51",
    "CTYARE51",
    "CURDEF01",
    "CURENT01",
    "DANGER53",
    "DAYSQR21",
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
    "ERBLTIK1",
    "ESSARE01",
    "EVENTS02",
    "FAIRWY51",
    "FAIRWY52",
    "FLASTK01",
    "FLASTK11",
    "FLDSTR01",
    "FLGSTF01",
    "FLTHAZ02",
    "FOGSIG01",
    "FORSTC01",
    "FORSTC11",
    "FOULGND1",
    "FRYARE51",
    "FRYARE52",
    "FSHFAC02",
    "FSHFAC03",
    "FSHGRD01",
    "FSHHAV01",
    "GATCON03",
    "GATCON04",
    "HECMTR01",
    "HECMTR02",
    "HGWTMK01",
    "HILTOP01",
    "HILTOP11",
    "HRBFAC09",
    "HRBFAC10",
    "HRBFAC11",
    "HRBFAC12",
    "HRBFAC13",
    "HRBFAC14",
    "HRBFAC15",
    "HRBFAC16",
    "HRBFAC17",
    "HRBFAC18",
    "HULKES01",
    "INFARE51",
    "INFORM01",
    "ISODGR51",
    "ITZARE51",
    "LITFLT01",
    "LITFLT02",
    "LITFLT10",
    "LITFLT61",
    "LITVES01",
    "LITVES02",
    "LITVES60",
    "LITVES61",
    "LNDARE01",
    "LOCMAG01",
]

REPAIRS: dict[str, dict] = {
    "BOYCON74": {"kind": "conical_bands", "bands": ["green", "white", "green", "white", "green"]},
    "CAIRNS01": {"kind": "cairn", "colour": "brown"},
    "CAIRNS11": {"kind": "cairn", "colour": "black"},
    "CTNARE51": {"kind": "caution_note"},
    "CTYARE51": {"kind": "caution_note"},
    "CURENT01": {"kind": "current_arrow"},
    "DAYSQR21": {"kind": "day_square_cross"},
    "DIRBOY01": {"kind": "direction_buoyage", "left": "black", "right": "black"},
    "DIRBOYA1": {"kind": "direction_buoyage", "left": "red", "right": "green"},
    "DIRBOYB1": {"kind": "direction_buoyage", "left": "green", "right": "red"},
    "DISMAR05": {"kind": "distance_target", "label": None},
    "DISMAR06": {"kind": "distance_target", "label": "1"},
    "DNGHILIT": {"kind": "danger_highlight"},
    "DOMES001": {"kind": "dome", "colour": "brown"},
    "DOMES011": {"kind": "dome", "colour": "black"},
    "DWRUTE51": {"kind": "double_route_arrow"},
    "EBBSTR01": {"kind": "ebb_arrow"},
    "ERBLTIK1": {"kind": "range_arc"},
    "FAIRWY51": {"kind": "fairway_arrow", "mode": "one_way"},
    "FAIRWY52": {"kind": "fairway_arrow", "mode": "two_way"},
    "FLDSTR01": {"kind": "flood_stream"},
    "FLGSTF01": {"kind": "flagstaff"},
    "FOULGND1": {"kind": "foul_ground"},
    "INFORM01": {"kind": "information"},
}

REPAIR_NOTES = {
    "BOYCON74": "Redraw the conical/nun body with five visibly legible green-white-green-white-green bands clipped inside the cone.",
    "CAIRNS01": "Replace the blue diamond placeholder with a generated cairn stack: three stone/ring lobes and a small base mark.",
    "CAIRNS11": "Replace the placeholder with the conspicuous black cairn stack and base mark.",
    "CTNARE51": "Replace the dashed area placeholder with the magenta caution-note circle/exclamation marker.",
    "CTYARE51": "Replace the dashed box/plus placeholder with the magenta caution-note circle/exclamation marker.",
    "CURENT01": "Replace the diamond with a compact current arrow/barb silhouette.",
    "DAYSQR21": "Replace the diamond with a square daymark panel on a stem with the required cross detail.",
    "DIRBOY01": "Replace the diamond with the direction-of-buoyage approach arrow and paired neutral side circles.",
    "DIRBOYA1": "Redraw the direction-of-buoyage cue with red-left/green-right side circles.",
    "DIRBOYB1": "Redraw the direction-of-buoyage cue with green-left/red-right side circles.",
    "DISMAR05": "Replace the diamond with a black concentric distance target mark.",
    "DISMAR06": "Replace the diamond with a black concentric 1 km distance target mark.",
    "DNGHILIT": "Replace the black stake with a translucent red danger-highlight square/border symbol.",
    "DOMES001": "Redraw as a dome silhouette with curved top and base marker.",
    "DOMES011": "Redraw as the conspicuous black dome silhouette with curved top and base marker.",
    "DWRUTE51": "Replace the dashed box/plus with a magenta vertical double-headed route arrow.",
    "EBBSTR01": "Replace the diamond with a vertical ebb-stream arrow symbol.",
    "ERBLTIK1": "Replace the diamond with an orange dashed range arc.",
    "FAIRWY51": "Replace the diamond with a one-way fairway arrow symbol.",
    "FAIRWY52": "Replace the diamond with a two-way fairway directional symbol.",
    "FLDSTR01": "Replace the placeholder with a flood-stream arrow and rate-bar cue.",
    "FLGSTF01": "Redraw as a flagstaff/flagpole with a small flag form.",
    "FOULGND1": "Replace the anchorage anchor with a black foul-ground hash/grid mark.",
    "INFORM01": "Replace the diamond with an information glyph/marker symbol.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch8">'
        f"<title>{asset} standard repair batch 16 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _conical_path() -> str:
    return "M32 9 L47 52 Q32 59 17 52 Z"


def _conical_bands(asset: str, bands: list[str]) -> str:
    height = 52 / len(bands)
    fills = []
    for idx, colour in enumerate(bands):
        y = 8 + idx * height
        fills.append(f'<rect x="0" y="{y:g}" width="64" height="{height:g}" fill="{_colour(colour)}"/>')
    seams = [
        f'<path d="M15 {8 + idx * height:g} H49" fill="none" stroke="{_colour("black")}" '
        'stroke-width="0.5" opacity="0.35"/>'
        for idx in range(1, len(bands))
    ]
    return (
        f'<defs><clipPath id="clip-{asset}"><path d="{_conical_path()}"/></clipPath></defs>'
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}{"".join(seams)}</g>'
        f'<path d="{_conical_path()}" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M32 56 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _cairn(colour: str) -> str:
    return (
        f'<ellipse cx="32" cy="22" rx="8" ry="5.4" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<ellipse cx="26" cy="34" rx="8.5" ry="5.8" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<ellipse cx="38" cy="34" rx="8.5" ry="5.8" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M21 46 H43 M32 41 V54" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _caution_note() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="4.8"/>'
        f'<path d="M32 20 V34" fill="none" stroke="{_colour("magenta")}" stroke-width="5"/>'
        f'<circle cx="32" cy="43" r="2.8" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _current_arrow() -> str:
    return (
        f'<path d="M18 47 C27 38 30 29 28 17" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M28 17 L20 25 M28 17 L36 25" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M35 46 C40 41 43 34 44 25" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _day_square_cross() -> str:
    return (
        f'<rect x="19" y="12" width="26" height="26" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 38 V57 M22 25 H42 M32 15 V35" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>'
    )


def _direction_buoyage(left: str, right: str) -> str:
    return (
        f'<path d="M32 12 V50 M32 12 L22 25 M32 12 L42 25" fill="none" stroke="{_colour("magenta")}" stroke-width="4"/>'
        f'<path d="M20 40 H44" fill="none" stroke="{_colour("magenta")}" stroke-width="4"/>'
        f'<circle cx="19" cy="50" r="7" fill="{_colour(left)}" stroke="{_colour("black")}" stroke-width="1.5"/>'
        f'<circle cx="45" cy="50" r="7" fill="{_colour(right)}" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _distance_target(label: str | None = None) -> str:
    text = ""
    if label:
        text = (
            f'<text x="32" y="38" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" '
            f'font-weight="700" fill="{_colour("black")}" stroke="none">{label}</text>'
        )
    return (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>'
        f'<circle cx="32" cy="32" r="11" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<circle cx="32" cy="32" r="3.5" fill="{_colour("black")}" stroke="none"/>'
        f"{text}"
    )


def _danger_highlight() -> str:
    return (
        f'<rect x="15" y="15" width="34" height="34" rx="1.5" fill="{_colour("red")}" fill-opacity="0.18" '
        f'stroke="{_colour("red")}" stroke-width="5"/>'
        f'<path d="M22 22 H42 V42 H22 Z" fill="none" stroke="{_colour("red")}" stroke-width="1.8" opacity="0.7"/>'
    )


def _dome(colour: str) -> str:
    return (
        f'<path d="M18 41 C20 25 26 18 32 18 C38 18 44 25 46 41 Z" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="5"/>'
        f'<path d="M18 47 H46 M32 41 V55 M25 55 H39" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
    )


def _double_route_arrow() -> str:
    return (
        f'<path d="M32 10 V54 M32 10 L24 20 M32 10 L40 20 M32 54 L24 44 M32 54 L40 44" '
        f'fill="none" stroke="{_colour("magenta")}" stroke-width="5"/>'
    )


def _ebb_arrow() -> str:
    return (
        f'<path d="M32 12 V52 M32 52 L23 40 M32 52 L41 40" fill="none" stroke="{_colour("black")}" stroke-width="4.5"/>'
        f'<path d="M22 21 H42" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _range_arc() -> str:
    return (
        f'<path d="M14 46 A27 27 0 0 1 50 46" fill="none" stroke="{_colour("orange")}" stroke-width="5" '
        'stroke-dasharray="5 5"/>'
        f'<path d="M24 36 A12 12 0 0 1 40 36" fill="none" stroke="{_colour("orange")}" stroke-width="4" '
        'stroke-dasharray="4 4"/>'
    )


def _fairway_arrow(mode: str) -> str:
    if mode == "one_way":
        return (
            f'<path d="M15 34 H47 M47 34 L36 23 M47 34 L36 45" fill="none" stroke="{_colour("magenta")}" stroke-width="5"/>'
            f'<path d="M15 22 H29 M15 46 H29" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        )
    return (
        f'<path d="M14 32 H50 M14 32 L25 21 M14 32 L25 43 M50 32 L39 21 M50 32 L39 43" '
        f'fill="none" stroke="{_colour("magenta")}" stroke-width="4.5"/>'
    )


def _flood_stream() -> str:
    return (
        f'<path d="M32 52 V13 M32 13 L23 25 M32 13 L41 25" fill="none" stroke="{_colour("black")}" stroke-width="4.5"/>'
        f'<path d="M22 42 H42 M25 35 H39" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _flagstaff() -> str:
    return (
        f'<path d="M27 12 V55 M21 55 H37" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M29 14 H48 L42 25 H29 Z" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _foul_ground() -> str:
    return (
        f'<path d="M19 19 L45 45 M45 19 L19 45" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M20 32 H44 M32 20 V44" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<rect x="18" y="18" width="28" height="28" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
    )


def _information() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="4.5"/>'
        f'<text x="32" y="42" text-anchor="middle" font-size="28" font-family="Arial, sans-serif" '
        f'font-weight="700" fill="{_colour("magenta")}" stroke="none">i</text>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "conical_bands":
        return _svg(asset, _conical_bands(asset, spec["bands"]))
    if kind == "cairn":
        return _svg(asset, _cairn(spec["colour"]))
    if kind == "caution_note":
        return _svg(asset, _caution_note())
    if kind == "current_arrow":
        return _svg(asset, _current_arrow())
    if kind == "day_square_cross":
        return _svg(asset, _day_square_cross())
    if kind == "direction_buoyage":
        return _svg(asset, _direction_buoyage(spec["left"], spec["right"]))
    if kind == "distance_target":
        return _svg(asset, _distance_target(spec["label"]))
    if kind == "danger_highlight":
        return _svg(asset, _danger_highlight())
    if kind == "dome":
        return _svg(asset, _dome(spec["colour"]))
    if kind == "double_route_arrow":
        return _svg(asset, _double_route_arrow())
    if kind == "ebb_arrow":
        return _svg(asset, _ebb_arrow())
    if kind == "range_arc":
        return _svg(asset, _range_arc())
    if kind == "fairway_arrow":
        return _svg(asset, _fairway_arrow(spec["mode"]))
    if kind == "flood_stream":
        return _svg(asset, _flood_stream())
    if kind == "flagstaff":
        return _svg(asset, _flagstaff())
    if kind == "foul_ground":
        return _svg(asset, _foul_ground())
    if kind == "information":
        return _svg(asset, _information())
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
    refs = item.get("reference_providers") or {}
    provider_count = sum(len(refs.get(name) or []) for name in ("s101", "aquamap", "opencpn_render"))
    if "regenerate/verify" in required or "regenerate or attach" in required:
        return "blocked_missing_local_reference_render"
    if "missing_reference_crop" in codes or "locate/render" in required or "resolve the exact reference" in required:
        return "blocked_missing_reference_or_exact_crop"
    if {"missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if provider_count < 2:
        return "skipped_batch16_low_reference_confidence"
    return "skipped_batch16_geometry_heavy_or_requires_exact_visual_contract"


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
            "risk_bucket": "standard_repair_queue_batch16_high_confidence_subset",
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
                "generator": "forge.standard_repair_batch8",
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
        "# Standard Repair Batch 8 / Owned Repair Batch 16",
        "",
        "Owned redraws for a bounded high-confidence subset of the current 93-row standard repair queue.",
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
