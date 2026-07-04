"""Repair the standard repair queue into owned batch 11 assets.

Run:
  python -m forge.standard_repair_batch3 --render
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
OUT = ROOT / "out" / "standard_repair_batch3"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch11"
REPORT = CATALOG / "owned_repair_batch11.json"
SUMMARY = CATALOG / "owned_repair_batch11.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

BLOCKED = {
    "BCNCON81": "hard_blocked_missing_exact_reference",
}

SHAPE_RERUN_ASSETS = {"BOYBAR01", "BOYCAN62", "BOYCAN79", "BOYCON01"}

REPAIR_NOTES = {
    "BOYBAR01": (
        "Render the barrel buoy with red/black semantic colours from the current "
        "semantic_brief; keep pending rerun because the provider reference conflict "
        "still needs judge arbitration."
    ),
    "BOYCAN62": (
        "Render the can buoy with green/black semantic colours from the current "
        "semantic_brief; keep pending rerun because the generic-reference conflict "
        "still needs judge arbitration."
    ),
    "BOYCAN79": "Change BOYCAN79 body fill from yellow to orange while preserving the can body and black outline/stem.",
    "BOYCON01": (
        "Render the conical buoy with red/black semantic colours from the current "
        "semantic_brief; keep pending rerun because the provider reference conflict "
        "still needs judge arbitration."
    ),
}

REPAIRS: dict[str, dict] = {
    "BOYBAR01": {"shape": "barrel", "bands": ["red", "black"]},
    "BOYCAN62": {"shape": "can", "bands": ["green", "black"]},
    "BOYCAN79": {"shape": "can", "bands": ["orange"]},
    "BOYCON01": {"shape": "cone", "bands": ["red", "black"]},
    "BOYCON71": {"shape": "cone", "bands": ["black", "yellow", "black"]},
    "BOYCON72": {"shape": "cone", "bands": ["yellow", "black", "yellow"]},
    "BOYCON74": {"shape": "cone", "bands": ["green", "white", "green", "white", "green"]},
    "BOYCON78": {"shape": "cone", "bands": ["red", "white"], "pattern": "vertical"},
    "BOYCON79": {"shape": "stake", "bands": ["red", "green"]},
    "BOYCON80": {"shape": "cone", "bands": ["white", "orange", "white"]},
    "BOYCON81": {"shape": "cone", "bands": ["blue", "red", "white", "blue"], "pattern": "quad"},
    "BOYDEF03": {"shape": "default", "bands": ["black"]},
    "BOYGEN03": {"shape": "generic", "bands": ["black"]},
    "BOYINB01": {"shape": "installation", "bands": ["black"]},
    "BOYISD12": {"shape": "isolated_danger", "bands": ["black", "red", "black"]},
    "BOYLAT13": {"shape": "cone", "bands": ["green", "red", "green"]},
    "BOYLAT14": {"shape": "cone", "bands": ["red", "green", "red"]},
    "BOYLAT23": {"shape": "can", "bands": ["green", "red", "green"]},
    "BOYLAT24": {"shape": "can", "bands": ["red", "green", "red"]},
    "BOYLAT26": {"shape": "spar", "bands": ["white", "red"]},
    "BOYLAT27": {"shape": "spar", "bands": ["white", "green"]},
    "BOYLAT52": {"shape": "generic", "bands": ["red", "green", "red"]},
    "BOYLAT53": {"shape": "generic", "bands": ["green", "red", "green"]},
    "BOYMOR01": {"shape": "sphere", "bands": ["black"]},
    "BOYMOR11": {"shape": "mooring", "bands": ["black"]},
    "BOYPIL01": {"shape": "pillar", "bands": ["black"]},
    "BOYPIL66": {"shape": "pillar", "bands": ["red", "green", "red"]},
    "BOYPIL67": {"shape": "pillar", "bands": ["green", "red", "green"]},
    "BOYPIL70": {"shape": "pillar", "bands": ["black", "yellow", "black"]},
    "BOYPIL71": {"shape": "pillar", "bands": ["yellow", "black", "yellow"]},
    "BOYPIL72": {"shape": "pillar", "bands": ["black", "red", "black"]},
    "BOYPIL73": {"shape": "pillar", "bands": ["red", "white"], "pattern": "vertical"},
    "BOYPIL78": {"shape": "pillar", "bands": ["red", "white"], "pattern": "checkered"},
    "BOYSAW12": {"shape": "safe_water", "bands": ["red", "white"], "pattern": "vertical"},
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch3">'
        f"<title>{asset} standard repair batch 11 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _colour(name: str) -> str:
    return f"var(--{name})"


def _clip(asset: str, shape: str) -> str:
    paths = {
        "can": "M22 15 H42 V45 H22 Z",
        "barrel": "M20 19 Q20 14 32 14 Q44 14 44 19 V43 Q44 48 32 48 Q20 48 20 43 Z",
        "cone": "M32 11 L49 49 Q32 56 15 49 Z",
        "pillar": "M24 14 H40 L45 49 Q32 56 19 49 Z",
        "spar": "M27 12 H37 L40 49 Q32 55 24 49 Z",
        "generic": "M21 20 Q32 10 43 20 L48 45 Q32 57 16 45 Z",
        "sphere": "M32 15 C44 15 50 25 47 39 C44 51 32 56 20 49 C11 43 13 25 22 18 C25 16 28 15 32 15 Z",
    }
    return f'<clipPath id="clip-{asset}"><path d="{paths[shape]}"/></clipPath>'


def _outline(shape: str) -> str:
    paths = {
        "can": "M22 15 H42 V45 H22 Z",
        "barrel": "M20 19 Q20 14 32 14 Q44 14 44 19 V43 Q44 48 32 48 Q20 48 20 43 Z",
        "cone": "M32 11 L49 49 Q32 56 15 49 Z",
        "pillar": "M24 14 H40 L45 49 Q32 56 19 49 Z",
        "spar": "M27 12 H37 L40 49 Q32 55 24 49 Z",
        "generic": "M21 20 Q32 10 43 20 L48 45 Q32 57 16 45 Z",
        "sphere": "M32 15 C44 15 50 25 47 39 C44 51 32 56 20 49 C11 43 13 25 22 18 C25 16 28 15 32 15 Z",
    }
    return f'<path d="{paths[shape]}" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'


def _body(asset: str, shape: str, bands: list[str], pattern: str | None = None) -> str:
    if shape == "default":
        return (
            f"<defs>{_clip(asset, 'generic')}</defs>"
            f'<g clip-path="url(#clip-{asset})"><rect x="0" y="0" width="64" height="64" fill="{_colour("black")}"/></g>'
            f"{_outline('generic')}"
            f'<text x="32" y="39" text-anchor="middle" font-size="20" font-family="Arial, sans-serif" '
            f'font-weight="700" fill="{_colour("white")}" stroke="none">?</text>'
            f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
        )
    if shape == "installation":
        return (
            f"<defs>{_clip(asset, 'generic')}</defs>"
            f'<g clip-path="url(#clip-{asset})"><rect x="0" y="0" width="64" height="64" fill="{_colour("black")}"/></g>'
            f"{_outline('generic')}"
            f'<rect x="25" y="23" width="14" height="12" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="1.6"/>'
            f'<path d="M24 40 H40 M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
        )
    if shape == "isolated_danger":
        return (
            '<circle cx="32" cy="7" r="4.2" fill="var(--black)" stroke="var(--black)" stroke-width="1.6"/>'
            '<circle cx="32" cy="17" r="4.2" fill="var(--black)" stroke="var(--black)" stroke-width="1.6"/>'
            + _body(asset, "generic", bands)
        )
    if shape == "stake":
        h = 31 / len(bands)
        rects = "".join(
            f'<rect x="27" y="{15 + idx * h:g}" width="10" height="{h:g}" fill="{_colour(colour)}"/>'
            for idx, colour in enumerate(bands)
        )
        return (
            f"{rects}"
            f'<rect x="27" y="15" width="10" height="31" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
            f'<path d="M23 15 H41 M32 46 V58" fill="none" stroke="{_colour("black")}" stroke-width="2.1"/>'
        )
    if shape == "mooring":
        return (
            f'<circle cx="32" cy="31" r="15" fill="none" stroke="{_colour("black")}" stroke-width="5.2"/>'
            f'<circle cx="32" cy="31" r="5.5" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2"/>'
            f'<path d="M32 46 V58" fill="none" stroke="{_colour("black")}" stroke-width="2.1"/>'
        )
    if shape == "safe_water":
        return (
            '<circle cx="32" cy="11" r="5" fill="var(--red)" stroke="var(--black)" stroke-width="1.8"/>'
            + _body(asset, "generic", bands, pattern)
        )

    clip_shape = shape if shape in {"can", "barrel", "cone", "pillar", "spar", "sphere"} else "generic"
    fill = []
    if pattern == "vertical":
        w = 64 / len(bands)
        fill = [
            f'<rect x="{idx * w:g}" y="0" width="{w:g}" height="64" fill="{_colour(colour)}"/>'
            for idx, colour in enumerate(bands)
        ]
    elif pattern == "checkered":
        rows = 4
        cols = 3
        for row in range(rows):
            for col in range(cols):
                colour = bands[(row + col) % len(bands)]
                fill.append(
                    f'<rect x="{col * 64 / cols:g}" y="{row * 64 / rows:g}" '
                    f'width="{64 / cols:g}" height="{64 / rows:g}" fill="{_colour(colour)}"/>'
                )
    elif pattern == "quad":
        band_h = 64 / len(bands)
        for idx, colour in enumerate(bands):
            fill.append(
                f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
            )
        stripe_w = 64 / len(bands)
        for idx, colour in enumerate(bands):
            fill.append(
                f'<rect x="{idx * stripe_w:g}" y="0" width="{stripe_w:g}" height="64" '
                f'fill="{_colour(colour)}" opacity="0.42"/>'
            )
    else:
        band_h = 64 / len(bands)
        fill = [
            f'<rect x="0" y="{idx * band_h:g}" width="64" height="{band_h:g}" fill="{_colour(colour)}"/>'
            for idx, colour in enumerate(bands)
        ]
    return (
        f"<defs>{_clip(asset, clip_shape)}</defs>"
        f'<g clip-path="url(#clip-{asset})">{"".join(fill)}</g>'
        f"{_outline(clip_shape)}"
        f'<path d="M32 55 V61" fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    return _svg(asset, _body(asset, spec["shape"], spec["bands"], spec.get("pattern")))


def _render_svg(svg: str, asset: str, palette: str) -> str:
    _ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _ensure_cairo_library() -> None:
    if ctypes.util.find_library("cairo") or not HOMEBREW_CAIRO.exists():
        return
    original_find_library = ctypes.util.find_library

    def find_library(name: str) -> str | None:
        if name in {"cairo", "cairo-2", "libcairo-2"}:
            return str(HOMEBREW_CAIRO)
        return original_find_library(name)

    ctypes.util.find_library = find_library


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    existing = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    existing_rows = {row["asset"]: row for row in existing.get("symbols", [])}
    existing_blockers = {row["asset"]: row for row in existing.get("blockers", [])}
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in [*BLOCKED, *REPAIRS]:
        item = queue_items.get(asset, {})
        existing_row = existing_rows.get(asset, {})
        source_row = source_rows.get(asset, {})
        if asset in BLOCKED:
            blockers.append({
                "asset": asset,
                "status": BLOCKED[asset],
                "required_change": item.get("required_change") or existing_blockers.get(asset, {}).get("required_change"),
                "safety_reason_codes": item.get("safety_reason_codes")
                or existing_blockers.get(asset, {}).get("safety_reason_codes", []),
            })
            continue
        if asset in SHAPE_RERUN_ASSETS:
            source_judge = "catalog/standard_shape_judge_batch_004_rerun.json"
            visual_parity = "repaired_pending_shape_rerun"
        else:
            source_judge = "catalog/standard_judge_batch_005.json"
            visual_parity = "repaired_pending_judge_rerun"
        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": item.get("name") or existing_row.get("name") or source_row.get("name"),
            "queue_action": item.get("status") or "standard_repair_queue_consumed",
            "risk_bucket": "standard_repair_queue_batch11",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": existing_row.get("candidate_source")
            or item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": existing_row.get("before_svg")
            or item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES.get(asset)
            or item.get("required_change")
            or existing_row.get("repair_note")
            or "Batch11 owned repair generated from the archived 35-row standard repair queue.",
            "semantic_brief": item.get("semantic_brief")
            or existing_row.get("semantic_brief")
            or source_row.get("semantic_brief"),
            "visual_examples": item.get("reference_providers")
            or existing_row.get("visual_examples", {})
            or source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": visual_parity,
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch3",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": source_judge,
        })
    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_judge": "catalog/standard_judge_batch_005.json",
        "source_judges": [
            "catalog/standard_judge_batch_005.json",
            "catalog/standard_shape_judge_batch_004_rerun.json",
        ],
        "source_queue": str(SOURCE_QUEUE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_queue_rows": len(BLOCKED) + len(REPAIRS),
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
        "# Standard Repair Batch 3 / Owned Repair Batch 11",
        "",
        "Owned redraws for the 35-row standard repair queue.",
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
    lines.extend(["", "Rows remain pending shape/visual judge reruns; none are final-approved."])
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
