"""Repair the current 35-row standard repair queue into owned batch 13 assets.

Run:
  python -m forge.standard_repair_batch5 --render
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
SOURCE_JUDGE = CATALOG / "standard_judge_batch_006.json"
OUT = ROOT / "out" / "standard_repair_batch5"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch13"
REPORT = CATALOG / "owned_repair_batch13.json"
SUMMARY = CATALOG / "owned_repair_batch13.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81",
    "BOYLAT52",
    "BOYLAT53",
    "BOYSPH01",
    "BOYSPH65",
    "BOYSPH66",
    "BOYSPH70",
    "BOYSPH71",
    "BOYSPH79",
    "BOYSPP11",
    "BOYSPP15",
    "BOYSPP25",
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
    "BUNSTA01",
    "BUNSTA02",
]

BLOCKED = {
    "BCNCON81": "hard_blocked_missing_exact_reference",
    "BOYLAT52": "blocked_missing_opencpn_day_render",
    "BOYLAT53": "blocked_missing_opencpn_day_render",
    "BOYSPH79": "blocked_missing_opencpn_day_render",
    "BOYSPR02": "blocked_missing_opencpn_or_s101_reference",
    "BOYSPR03": "blocked_missing_opencpn_or_s101_reference",
}

REPAIRS: dict[str, dict] = {
    "BOYSPH01": {"shape": "sphere", "bands": ["red", "black"]},
    "BOYSPH65": {"shape": "sphere", "bands": ["red", "white"], "pattern": "vertical"},
    "BOYSPH66": {"shape": "sphere", "bands": ["red", "green", "red"]},
    "BOYSPH70": {"shape": "sphere", "bands": ["black", "yellow", "black"]},
    "BOYSPH71": {"shape": "sphere", "bands": ["yellow", "black", "yellow"]},
    "BOYSPP11": {"shape": "pillar", "bands": ["yellow"]},
    "BOYSPP15": {"shape": "cone", "bands": ["yellow"]},
    "BOYSPP25": {"shape": "can", "bands": ["yellow"]},
    "BOYSPR01": {"shape": "spar", "bands": ["white", "black"]},
    "BOYSPR70": {"shape": "spar", "bands": ["black", "yellow", "black"]},
    "BOYSPR71": {"shape": "spar", "bands": ["yellow", "black", "yellow"]},
    "BOYSPR72": {"shape": "spar", "bands": ["black", "red", "black"]},
    "BOYSUP01": {"shape": "super", "bands": ["red", "black"]},
    "BOYSUP02": {"shape": "super", "bands": ["black"]},
    "BOYSUP03": {"shape": "lanby", "bands": ["red", "black"]},
    "BOYSUP65": {"shape": "super", "bands": ["red", "white"], "pattern": "vertical"},
    "BRIDGE01": {"shape": "opening_bridge"},
    "BRTHNO01": {"shape": "berth_number"},
    "BUAARE02": {"shape": "built_up_area"},
    "BUIREL01": {"shape": "christian_building", "fill": "black", "conspicuous": False},
    "BUIREL04": {"shape": "non_christian_building", "fill": "black", "conspicuous": False},
    "BUIREL05": {"shape": "mosque_minaret", "fill": "black", "conspicuous": False},
    "BUIREL13": {"shape": "christian_building", "fill": "black", "conspicuous": True},
    "BUIREL14": {"shape": "non_christian_building", "fill": "black", "conspicuous": True},
    "BUIREL15": {"shape": "mosque_minaret", "fill": "black", "conspicuous": True},
    "BUISGL01": {"shape": "single_building", "fill": "brown", "conspicuous": False},
    "BUISGL11": {"shape": "single_building", "fill": "black", "conspicuous": True},
    "BUNSTA01": {"shape": "diesel_bunker"},
    "BUNSTA02": {"shape": "water_bunker"},
}

REPAIR_NOTES = {
    "BOYSPH01": "Remove invented blue/grey and redraw a spherical buoy with red-over-black semantic bands only.",
    "BOYSPH65": "Rotate the red/white spherical buoy body to vertical stripes.",
    "BOYSPH66": "Add the missing lower red band so the spherical buoy reads red-green-red.",
    "BOYSPH70": "Add the missing lower black band so the spherical buoy reads black-yellow-black.",
    "BOYSPH71": "Add the missing lower yellow band so the spherical buoy reads yellow-black-yellow.",
    "BOYSPP11": "Replace the generic black lower body with a simplified yellow pillar special-purpose buoy cue.",
    "BOYSPP15": "Replace the generic body with a simplified yellow conical TSS starboard buoy cue.",
    "BOYSPP25": "Replace the generic body with a simplified yellow can/cylindrical TSS port buoy cue.",
    "BOYSPR01": "Remove invented blue and redraw the spar using only white/black semantic colours.",
    "BOYSPR70": "Add the missing lower black band so the spar reads black-yellow-black.",
    "BOYSPR71": "Add the missing lower yellow band so the spar reads yellow-black-yellow.",
    "BOYSPR72": "Add the missing lower black band so the spar reads black-red-black.",
    "BOYSUP01": "Remove invented blue/grey and redraw the super-buoy with red/black semantic colours only.",
    "BOYSUP02": "Remove the blue/grey lower fill so the super-buoy is black only.",
    "BOYSUP03": "Add a LANBY/super-buoy top cue and remove the invented blue field.",
    "BOYSUP65": "Rotate the red/white super-buoy body to vertical stripes.",
    "BRIDGE01": "Replace the diamond placeholder with an opening-bridge ring/circular silhouette.",
    "BRTHNO01": "Replace the diamond placeholder with a berth-number circular reference cue.",
    "BUAARE02": "Replace the dashed square placeholder with a built-up-area block cluster cue.",
    "BUIREL01": "Replace the diamond placeholder with a Christian religious-building cross/church silhouette.",
    "BUIREL04": "Replace the diamond placeholder with a non-Christian religious-building temple/dome silhouette.",
    "BUIREL05": "Replace the diamond placeholder with a mosque/minaret silhouette.",
    "BUIREL13": "Use the conspicuous Christian religious-building silhouette in black.",
    "BUIREL14": "Use the conspicuous non-Christian religious-building silhouette in black.",
    "BUIREL15": "Use the conspicuous mosque/minaret silhouette in black.",
    "BUISGL01": "Replace the diamond placeholder with a brown single-building square/roof cue.",
    "BUISGL11": "Replace the diamond placeholder with a black conspicuous single-building square/roof cue.",
    "BUNSTA01": "Replace the diamond placeholder with a diesel bunker-station fuel-pump cue.",
    "BUNSTA02": "Replace the diamond placeholder with a water bunker-station tap/drop cue.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch5">'
        f"<title>{asset} standard repair batch 13 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _clip(asset: str, shape: str) -> str:
    paths = {
        "can": "M21 15 H43 V47 H21 Z",
        "cone": "M32 10 L50 50 Q32 57 14 50 Z",
        "pillar": "M24 12 H40 L44 50 Q32 57 20 50 Z",
        "spar": "M28 10 H36 L39 51 Q32 57 25 51 Z",
        "super": "M17 24 C17 15 25 10 32 10 C39 10 47 15 47 24 V43 C47 52 39 57 32 57 C25 57 17 52 17 43 Z",
        "sphere": "M32 15 C44 15 50 25 47 39 C44 51 32 56 20 49 C11 43 13 25 22 18 C25 16 28 15 32 15 Z",
    }
    return f'<clipPath id="clip-{asset}"><path d="{paths[shape]}"/></clipPath>'


def _outline(shape: str) -> str:
    paths = {
        "can": "M21 15 H43 V47 H21 Z",
        "cone": "M32 10 L50 50 Q32 57 14 50 Z",
        "pillar": "M24 12 H40 L44 50 Q32 57 20 50 Z",
        "spar": "M28 10 H36 L39 51 Q32 57 25 51 Z",
        "super": "M17 24 C17 15 25 10 32 10 C39 10 47 15 47 24 V43 C47 52 39 57 32 57 C25 57 17 52 17 43 Z",
        "sphere": "M32 15 C44 15 50 25 47 39 C44 51 32 56 20 49 C11 43 13 25 22 18 C25 16 28 15 32 15 Z",
    }
    return f'<path d="{paths[shape]}" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'


def _banded(asset: str, shape: str, bands: list[str], pattern: str | None = None) -> str:
    fill = []
    if pattern == "vertical":
        width = 64 / len(bands)
        for idx, colour in enumerate(bands):
            fill.append(
                f'<rect x="{idx * width:g}" y="0" width="{width:g}" height="64" fill="{_colour(colour)}"/>'
            )
    else:
        height = 64 / len(bands)
        for idx, colour in enumerate(bands):
            fill.append(
                f'<rect x="0" y="{idx * height:g}" width="64" height="{height:g}" fill="{_colour(colour)}"/>'
            )
    separators = []
    for idx in range(1, len(bands)):
        pos = idx * (64 / len(bands))
        if pattern == "vertical":
            separators.append(
                f'<path d="M{pos:g} 10 V55" fill="none" stroke="{_colour("black")}" stroke-width="0.8" opacity="0.55"/>'
            )
        else:
            separators.append(
                f'<path d="M13 {pos:g} H51" fill="none" stroke="{_colour("black")}" stroke-width="0.8" opacity="0.55"/>'
            )
    return (
        f"<defs>{_clip(asset, shape)}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fill)}</g>'
        f'{"".join(separators)}'
        f"{_outline(shape)}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _lanby(asset: str, bands: list[str]) -> str:
    return (
        f'<path d="M32 7 V15" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<path d="M27 7 H37 L34 13 H30 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
        + _banded(asset, "super", bands)
    )


def _opening_bridge() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("magenta")}" stroke-width="6"/>'
        f'<circle cx="32" cy="32" r="8" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<path d="M16 32 H48 M32 16 V48" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
    )


def _berth_number() -> str:
    return (
        f'<circle cx="32" cy="32" r="19" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'<text x="32" y="39" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" '
        f'font-weight="700" fill="{_colour("black")}" stroke="none">No</text>'
    )


def _built_up_area() -> str:
    return (
        f'<rect x="14" y="14" width="36" height="36" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<rect x="19" y="20" width="9" height="9" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<rect x="35" y="19" width="10" height="12" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<rect x="24" y="36" width="11" height="9" fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
        f'<path d="M16 48 L48 16" fill="none" stroke="{_colour("black")}" stroke-width="1.5" opacity="0.75"/>'
    )


def _christian_building(fill: str, conspicuous: bool) -> str:
    width = "3.2" if conspicuous else "2.4"
    return (
        f'<path d="M16 47 H48 L45 29 L32 18 L19 29 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M32 10 V30 M24 18 H40" fill="none" stroke="{_colour("white" if fill == "black" else "black")}" stroke-width="4"/>'
        f'<path d="M32 10 V30 M24 18 H40" fill="none" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _non_christian_building(fill: str, conspicuous: bool) -> str:
    width = "3.2" if conspicuous else "2.4"
    return (
        f'<path d="M14 48 H50 L46 31 H18 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M19 31 C24 18 40 18 45 31 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M23 48 V35 M32 48 V33 M41 48 V35" fill="none" stroke="{_colour("white" if fill == "black" else "black")}" stroke-width="2"/>'
    )


def _mosque_minaret(fill: str, conspicuous: bool) -> str:
    width = "3.2" if conspicuous else "2.4"
    return (
        f'<path d="M18 48 H42 V31 C42 23 36 19 30 19 C24 19 18 23 18 31 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M43 48 V16 H50 V48 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M42 16 Q46 8 51 16 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<path d="M26 19 Q30 11 35 19" fill="none" stroke="{_colour("white" if fill == "black" else "black")}" stroke-width="2"/>'
    )


def _single_building(fill: str, conspicuous: bool) -> str:
    width = "3" if conspicuous else "2.2"
    return (
        f'<path d="M17 48 H47 V28 L32 16 L17 28 Z" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="{width}"/>'
        f'<rect x="27" y="35" width="10" height="13" fill="{_colour("white" if fill == "black" else "black")}" stroke="{_colour("black")}" stroke-width="1.1"/>'
    )


def _diesel_bunker() -> str:
    return (
        f'<rect x="18" y="18" width="20" height="32" rx="2" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<rect x="23" y="23" width="10" height="8" fill="{_colour("white")}" stroke="{_colour("white")}" stroke-width="1"/>'
        f'<path d="M38 23 H45 Q49 23 49 27 V46 Q49 50 45 50 H43" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M41 25 L47 19" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
    )


def _water_bunker() -> str:
    return (
        f'<path d="M32 13 C43 27 48 35 48 43 C48 52 41 57 32 57 C23 57 16 52 16 43 C16 35 21 27 32 13 Z" '
        f'fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M25 42 C27 48 34 51 40 45" fill="none" stroke="{_colour("white")}" stroke-width="2.6"/>'
    )


def _body(asset: str, spec: dict) -> str:
    shape = spec["shape"]
    if shape in {"can", "cone", "pillar", "spar", "sphere", "super"}:
        return _banded(asset, shape, spec["bands"], spec.get("pattern"))
    if shape == "lanby":
        return _lanby(asset, spec["bands"])
    if shape == "opening_bridge":
        return _opening_bridge()
    if shape == "berth_number":
        return _berth_number()
    if shape == "built_up_area":
        return _built_up_area()
    if shape == "christian_building":
        return _christian_building(spec["fill"], spec["conspicuous"])
    if shape == "non_christian_building":
        return _non_christian_building(spec["fill"], spec["conspicuous"])
    if shape == "mosque_minaret":
        return _mosque_minaret(spec["fill"], spec["conspicuous"])
    if shape == "single_building":
        return _single_building(spec["fill"], spec["conspicuous"])
    if shape == "diesel_bunker":
        return _diesel_bunker()
    if shape == "water_bunker":
        return _water_bunker()
    raise KeyError(shape)


def _redraw(asset: str) -> str:
    return _svg(asset, _body(asset, REPAIRS[asset]))


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


def _verdicts() -> dict[str, dict]:
    judge = json.loads(SOURCE_JUDGE.read_text())
    return {row["symbol_id"]: row for row in judge.get("verdicts", [])}


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    verdicts = _verdicts()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in EXPECTED_QUEUE:
        item = queue_items.get(asset, {})
        source_row = source_rows.get(asset, {})
        verdict = verdicts.get(asset, {})
        if asset in BLOCKED:
            blockers.append({
                "asset": asset,
                "status": BLOCKED[asset],
                "required_change": item.get("required_change") or verdict.get("required_change"),
                "safety_reason_codes": item.get("safety_reason_codes") or verdict.get("safety_reason_codes", []),
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
            "risk_bucket": "standard_repair_queue_batch13",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "required_change": item.get("required_change") or verdict.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes") or verdict.get("safety_reason_codes", []),
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
                "generator": "forge.standard_repair_batch5",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": str(SOURCE_JUDGE.relative_to(ROOT)),
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_judge": str(SOURCE_JUDGE.relative_to(ROOT)),
        "source_queue": str(SOURCE_QUEUE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_queue_rows": len(EXPECTED_QUEUE),
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
        "# Standard Repair Batch 5 / Owned Repair Batch 13",
        "",
        "Owned redraws for the current 35-row standard repair queue.",
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
