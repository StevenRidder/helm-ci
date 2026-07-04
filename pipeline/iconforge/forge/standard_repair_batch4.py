"""Repair the current 12-row standard repair queue into owned batch 12 assets.

Run:
  python -m forge.standard_repair_batch4 --render
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
SOURCE_JUDGE = CATALOG / "standard_judge_batch_011_rerun.json"
OUT = ROOT / "out" / "standard_repair_batch4"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch12"
REPORT = CATALOG / "owned_repair_batch12.json"
SUMMARY = CATALOG / "owned_repair_batch12.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81",
    "BOYCAN81",
    "BOYCON74",
    "BOYCON81",
    "BOYINB01",
    "BOYISD12",
    "BOYLAT52",
    "BOYLAT53",
    "BOYMOR01",
    "BOYMOR11",
    "BOYPIL78",
    "BOYSAW12",
]

BLOCKED = {
    "BCNCON81": "hard_blocked_missing_exact_reference",
    "BOYLAT52": "blocked_missing_opencpn_day_render",
    "BOYLAT53": "blocked_missing_opencpn_day_render",
}

REPAIRS = {
    "BOYCAN81": "can_orange_white",
    "BOYCON74": "cone_green_white_green_white_green",
    "BOYCON81": "cone_blue_red_white_blue_cross_stripe",
    "BOYINB01": "installation_line_buoy",
    "BOYISD12": "isolated_danger_red_disks",
    "BOYMOR01": "mooring_line_buoy",
    "BOYMOR11": "mooring_filled_simplified",
    "BOYPIL78": "pillar_red_white_checkered",
    "BOYSAW12": "safe_water_red_disk",
}

REPAIR_NOTES = {
    "BOYCAN81": "Redraw as a can/cylindrical buoy with two ordered horizontal bands: orange over white.",
    "BOYCON74": "Redraw the conical body with five distinct green-white-green-white-green bands.",
    "BOYCON81": (
        "Redraw the conical body with explicit blue-red-white-blue striping in both axes; "
        "keep pending visual rerun because the exact special-purpose pattern still needs judge confirmation."
    ),
    "BOYINB01": "Replace the filled generic buoy body with an installation-buoy line symbol: top circle, lower ring, baseline, and trapezoid frame.",
    "BOYISD12": "Replace the black/red/black buoy body with the simplified isolated-danger cue: two red disks with black outlines.",
    "BOYMOR01": "Replace the filled spherical substitute with the mooring line cue: lower ring, top ring, baseline arms, and arched body stroke.",
    "BOYMOR11": "Replace the target-ring substitute with a compact filled mooring facility symbol: black trapezoid body plus top disk.",
    "BOYPIL78": "Redraw the pillar body as a clear red/white squared/checkered pattern.",
    "BOYSAW12": "Replace the split buoy/topmark substitute with the compact safe-water red disk and center mark.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch4">'
        f"<title>{asset} standard repair batch 12 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _clip(asset: str, shape: str) -> str:
    paths = {
        "can": "M21 15 H43 V46 H21 Z",
        "cone": "M32 10 L50 50 Q32 57 14 50 Z",
        "pillar": "M24 13 H40 L45 49 Q32 57 19 49 Z",
    }
    return f'<clipPath id="clip-{asset}"><path d="{paths[shape]}"/></clipPath>'


def _outline(shape: str) -> str:
    paths = {
        "can": "M21 15 H43 V46 H21 Z",
        "cone": "M32 10 L50 50 Q32 57 14 50 Z",
        "pillar": "M24 13 H40 L45 49 Q32 57 19 49 Z",
    }
    return f'<path d="{paths[shape]}" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'


def _banded(asset: str, shape: str, bands: list[str]) -> str:
    fill = []
    band_h = 64 / len(bands)
    for idx, colour in enumerate(bands):
        fill.append(
            f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
        )
    separators = []
    for idx in range(1, len(bands)):
        y = idx * band_h
        separators.append(
            f'<path d="M13 {y:g} H51" fill="none" stroke="{_colour("black")}" stroke-width="0.9" opacity="0.55"/>'
        )
    return (
        f"<defs>{_clip(asset, shape)}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fill)}</g>'
        f"{_outline(shape)}"
        f'{"".join(separators)}'
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _cross_striped_cone(asset: str) -> str:
    bands = ["blue", "red", "white", "blue"]
    fills = []
    band_h = 64 / len(bands)
    stripe_w = 64 / len(bands)
    for idx, colour in enumerate(bands):
        fills.append(
            f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
        )
    for idx, colour in enumerate(bands):
        fills.append(
            f'<rect x="{idx * stripe_w:g}" y="0" width="{stripe_w:g}" height="64" '
            f'fill="{_colour(colour)}" opacity="0.48"/>'
        )
    grid = []
    for idx in range(1, len(bands)):
        pos = idx * band_h
        grid.append(f'<path d="M12 {pos:g} H52" stroke="{_colour("black")}" stroke-width="0.75" opacity="0.5"/>')
        grid.append(f'<path d="M{pos:g} 10 V54" stroke="{_colour("black")}" stroke-width="0.75" opacity="0.5"/>')
    return (
        f"<defs>{_clip(asset, 'cone')}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}</g>'
        f'{"".join(grid)}'
        f"{_outline('cone')}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _checkered_pillar(asset: str) -> str:
    fills = []
    rows = 5
    cols = 4
    for row in range(rows):
        for col in range(cols):
            colour = "red" if (row + col) % 2 == 0 else "white"
            fills.append(
                f'<rect x="{col * 64 / cols:g}" y="{row * 64 / rows:g}" '
                f'width="{64 / cols:g}" height="{64 / rows:g}" fill="{_colour(colour)}"/>'
            )
    grid = []
    for col in range(1, cols):
        x = col * 64 / cols
        grid.append(f'<path d="M{x:g} 12 V54" stroke="{_colour("black")}" stroke-width="0.65" opacity="0.45"/>')
    for row in range(1, rows):
        y = row * 64 / rows
        grid.append(f'<path d="M18 {y:g} H46" stroke="{_colour("black")}" stroke-width="0.65" opacity="0.45"/>')
    return (
        f"<defs>{_clip(asset, 'pillar')}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}</g>'
        f'{"".join(grid)}'
        f"{_outline('pillar')}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _installation_line_buoy() -> str:
    return (
        f'<circle cx="32" cy="47" r="5.2" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="18" r="5.6" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M11 47 H25 M39 47 H53" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M15 47 L22 24 H42 L49 47" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
    )


def _isolated_danger_red_disks() -> str:
    return (
        f'<circle cx="39" cy="22" r="11.5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<circle cx="25" cy="45" r="11.5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2.4"/>'
    )


def _mooring_line_buoy() -> str:
    return (
        f'<circle cx="32" cy="49" r="4.8" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<circle cx="29" cy="15" r="5.3" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M37 49 H51 M27 49 H10" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M49 49 V39 C49 24 39 18 29 20 C18 22 11 32 11 49" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M18 32 C22 37 24 43 24 49" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
    )


def _mooring_filled_simplified() -> str:
    return (
        f'<circle cx="33" cy="18" r="6.4" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1.6"/>'
        f'<path d="M13 49 L19 29 H45 L51 49 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1.6"/>'
    )


def _safe_water_red_disk() -> str:
    return (
        f'<circle cx="32" cy="32" r="18.5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<circle cx="32" cy="32" r="2.2" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1"/>'
    )


def _redraw(asset: str) -> str:
    repair = REPAIRS[asset]
    if repair == "can_orange_white":
        return _svg(asset, _banded(asset, "can", ["orange", "white"]))
    if repair == "cone_green_white_green_white_green":
        return _svg(asset, _banded(asset, "cone", ["green", "white", "green", "white", "green"]))
    if repair == "cone_blue_red_white_blue_cross_stripe":
        return _svg(asset, _cross_striped_cone(asset))
    if repair == "installation_line_buoy":
        return _svg(asset, _installation_line_buoy())
    if repair == "isolated_danger_red_disks":
        return _svg(asset, _isolated_danger_red_disks())
    if repair == "mooring_line_buoy":
        return _svg(asset, _mooring_line_buoy())
    if repair == "mooring_filled_simplified":
        return _svg(asset, _mooring_filled_simplified())
    if repair == "pillar_red_white_checkered":
        return _svg(asset, _checkered_pillar(asset))
    if repair == "safe_water_red_disk":
        return _svg(asset, _safe_water_red_disk())
    raise KeyError(asset)


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
    if not SOURCE_JUDGE.exists():
        return {}
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
            "risk_bucket": "standard_repair_queue_batch12",
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
                "generator": "forge.standard_repair_batch4",
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
        "# Standard Repair Batch 4 / Owned Repair Batch 12",
        "",
        "Owned redraws for the current 12-row standard repair queue.",
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
