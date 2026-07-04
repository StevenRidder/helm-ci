"""Repair the current 9-row standard repair queue into owned batch 14 assets.

Run:
  python -m forge.standard_repair_batch6 --render
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
OUT = ROOT / "out" / "standard_repair_batch6"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch14"
REPORT = CATALOG / "owned_repair_batch14.json"
SUMMARY = CATALOG / "owned_repair_batch14.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

EXPECTED_QUEUE = [
    "BCNCON81",
    "BOYCON74",
    "BOYCON81",
    "BOYLAT52",
    "BOYLAT53",
    "BOYPIL78",
    "BOYSPH79",
    "BOYSPR02",
    "BOYSPR03",
]

BLOCKED = {
    "BCNCON81": "hard_blocked_missing_exact_reference",
    "BOYLAT52": "blocked_missing_opencpn_day_render",
    "BOYLAT53": "blocked_missing_opencpn_day_render",
    "BOYSPR02": "blocked_missing_opencpn_or_s101_reference",
    "BOYSPR03": "blocked_missing_opencpn_or_s101_reference",
}

REPAIRS: dict[str, dict] = {
    "BOYCON74": {"shape": "cone", "bands": ["green", "white", "green", "white", "green"]},
    "BOYCON81": {"shape": "cone", "bands": ["blue", "red", "white", "blue"], "pattern": "cross"},
    "BOYPIL78": {"shape": "pillar", "pattern": "checker", "colours": ["red", "white"]},
    "BOYSPH79": {"shape": "cone", "bands": ["red", "green"]},
}

REPAIR_NOTES = {
    "BOYCON74": (
        "Redraw the green-white-green-white-green conical body with all band boundaries clipped "
        "inside the cone; no separator bars protrude outside the silhouette."
    ),
    "BOYCON81": (
        "Use the local OpenCPN witness plus semantic brief to keep the blue-red-white-blue "
        "special-purpose conical cross-stripe cue while clipping all grid marks inside the cone."
    ),
    "BOYPIL78": (
        "Redraw the red-white checkered pillar with the checker grid clipped inside the pillar body."
    ),
    "BOYSPH79": (
        "Replace the wrong spherical body with a semantic conical/nun buoy body using red over green; "
        "keeps missing-reference reason codes pending visual rerun."
    ),
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch6">'
        f"<title>{asset} standard repair batch 14 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _shape_path(shape: str) -> str:
    paths = {
        "cone": "M32 10 L50 50 Q32 57 14 50 Z",
        "pillar": "M24 13 H40 L45 49 Q32 57 19 49 Z",
    }
    return paths[shape]


def _clip(asset: str, shape: str) -> str:
    return f'<clipPath id="clip-{asset}"><path d="{_shape_path(shape)}"/></clipPath>'


def _outline(shape: str) -> str:
    return f'<path d="{_shape_path(shape)}" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'


def _horizontal_bands(asset: str, shape: str, bands: list[str], *, show_internal_rules: bool = False) -> str:
    band_h = 64 / len(bands)
    fill = [
        f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
        for idx, colour in enumerate(bands)
    ]
    rules = []
    if show_internal_rules:
        for idx in range(1, len(bands)):
            y = idx * band_h
            rules.append(
                f'<path d="M0 {y:g} H64" fill="none" stroke="{_colour("black")}" '
                'stroke-width="0.75" opacity="0.5"/>'
            )
    return (
        f"<defs>{_clip(asset, shape)}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fill)}{"".join(rules)}</g>'
        f"{_outline(shape)}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _cross_striped_cone(asset: str, bands: list[str]) -> str:
    band_h = 64 / len(bands)
    stripe_w = 64 / len(bands)
    fills = []
    for idx, colour in enumerate(bands):
        fills.append(
            f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
        )
    for idx, colour in enumerate(bands):
        fills.append(
            f'<rect x="{idx * stripe_w:g}" y="0" width="{stripe_w:g}" height="64" '
            f'fill="{_colour(colour)}" opacity="0.46"/>'
        )
    grid = []
    for idx in range(1, len(bands)):
        pos = idx * band_h
        grid.append(
            f'<path d="M0 {pos:g} H64" fill="none" stroke="{_colour("black")}" '
            'stroke-width="0.65" opacity="0.45"/>'
        )
        grid.append(
            f'<path d="M{pos:g} 0 V64" fill="none" stroke="{_colour("black")}" '
            'stroke-width="0.65" opacity="0.45"/>'
        )
    return (
        f"<defs>{_clip(asset, 'cone')}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}{"".join(grid)}</g>'
        f"{_outline('cone')}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _checkered_pillar(asset: str) -> str:
    rows = 5
    cols = 4
    fills = []
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
        grid.append(
            f'<path d="M{x:g} 0 V64" fill="none" stroke="{_colour("black")}" '
            'stroke-width="0.6" opacity="0.42"/>'
        )
    for row in range(1, rows):
        y = row * 64 / rows
        grid.append(
            f'<path d="M0 {y:g} H64" fill="none" stroke="{_colour("black")}" '
            'stroke-width="0.6" opacity="0.42"/>'
        )
    return (
        f"<defs>{_clip(asset, 'pillar')}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fills)}{"".join(grid)}</g>'
        f"{_outline('pillar')}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    if spec.get("pattern") == "cross":
        return _svg(asset, _cross_striped_cone(asset, spec["bands"]))
    if spec.get("pattern") == "checker":
        return _svg(asset, _checkered_pillar(asset))
    return _svg(asset, _horizontal_bands(asset, spec["shape"], spec["bands"]))


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


def _source_judge_for(item: dict, asset: str) -> str | None:
    batch = item.get("judge", {}).get("batch")
    if batch:
        return f"catalog/{batch}.json"
    return None


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
        if asset in BLOCKED:
            blockers.append({
                "asset": asset,
                "status": BLOCKED[asset],
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
            "risk_bucket": "standard_repair_queue_batch14",
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
                "generator": "forge.standard_repair_batch6",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": _source_judge_for(item, asset),
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
        "# Standard Repair Batch 6 / Owned Repair Batch 14",
        "",
        "Owned redraws for the current 9-row standard repair queue.",
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
