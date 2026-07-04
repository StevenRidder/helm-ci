"""Repair queued TOWERS rows into owned repair batch 59.

Run:
  python3 -m forge.standard_repair_batch51 --render
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
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPAIR_QUEUE = CATALOG / "standard_repair_queue.json"
OUT = ROOT / "out" / "standard_repair_batch51"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch59"
REPORT = CATALOG / "owned_repair_batch59.json"
SUMMARY = CATALOG / "owned_repair_batch59.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    if name == "grey":
        name = "gray"
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch51">'
        f"<title>{asset} tower silhouette repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _tower_clip(asset: str) -> tuple[str, str]:
    clip_id = f"clip_{_safe(asset)}"
    outline = "25,12 39,12 49,52 15,52"
    return clip_id, f'<defs><clipPath id="{clip_id}"><polygon points="{outline}"/></clipPath></defs>'


def _tower_frame() -> str:
    return (
        f'<polygon points="25,12 39,12 49,52 15,52" fill="none" stroke="{_colour("black")}" stroke-width="3.6"/>'
        f'<path d="M13 52 H51" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M22 52 L40 12 M42 52 L24 12 M20 40 H44 M23 28 H41" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="2" opacity="0.42"/>'
        f'<circle cx="32" cy="54" r="4.5" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
    )


def _solid(asset: str, colours: list[str]) -> str:
    clip_id, defs = _tower_clip(asset)
    colour = colours[0] if colours else "black"
    return (
        defs
        + f'<rect x="13" y="10" width="38" height="44" fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="solid-tower"/>'
        + _tower_frame()
    )


def _horizontal(asset: str, colours: list[str]) -> str:
    clip_id, defs = _tower_clip(asset)
    colours = colours or ["black"]
    band_h = 42 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="13" y="{11 + index * band_h:.1f}" width="38" height="{band_h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-tower"/>'
        )
    parts.append(_tower_frame())
    return "".join(parts)


def _vertical(asset: str, colours: list[str]) -> str:
    clip_id, defs = _tower_clip(asset)
    colours = colours or ["black"]
    band_w = 38 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{13 + index * band_w:.1f}" y="10" width="{band_w:.1f}" height="44" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-tower"/>'
        )
    parts.append(_tower_frame())
    return "".join(parts)


def _diagonal(asset: str, colours: list[str]) -> str:
    clip_id, defs = _tower_clip(asset)
    colours = colours or ["black", "white"]
    a = colours[0]
    b = colours[1] if len(colours) > 1 else "white"
    parts = [defs, f'<rect x="13" y="10" width="38" height="44" fill="{_colour(a)}" clip-path="url(#{clip_id})"/>']
    for offset in range(-36, 58, 18):
        parts.append(
            f'<rect x="{offset}" y="8" width="10" height="70" transform="rotate(35 {offset} 8)" '
            f'fill="{_colour(b)}" clip-path="url(#{clip_id})" data-pattern="diagonal-tower"/>'
        )
    parts.append(_tower_frame())
    return "".join(parts)


def _checker(asset: str, colours: list[str]) -> str:
    clip_id, defs = _tower_clip(asset)
    colours = colours or ["black", "white"]
    cols = 4
    rows = 4
    cell_w = 38 / cols
    cell_h = 42 / rows
    parts = [defs]
    for row in range(rows):
        for col in range(cols):
            colour = colours[(row + col) % len(colours)]
            parts.append(
                f'<rect x="{13 + col * cell_w:.1f}" y="{11 + row * cell_h:.1f}" '
                f'width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{_colour(colour)}" '
                f'clip-path="url(#{clip_id})" data-pattern="checker-tower"/>'
            )
    parts.append(_tower_frame())
    return "".join(parts)


def _tower(asset: str, colours: list[str], pattern: str | None) -> str:
    if not colours:
        colours = ["black"]
    pattern_l = (pattern or "").lower()
    if pattern == "vertical-tower":
        return _vertical(asset, colours)
    if "vertical" in pattern_l:
        return _vertical(asset, colours)
    if "diagonal" in pattern_l:
        return _diagonal(asset, colours)
    if "squared" in pattern_l or "checkered" in pattern_l:
        return _checker(asset, colours)
    if "horizontal" in pattern_l or len(colours) > 1:
        return _horizontal(asset, colours)
    return _solid(asset, colours)


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


def _source_rows() -> dict[str, dict]:
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


def _repair_items() -> list[dict]:
    queue = json.loads(REPAIR_QUEUE.read_text())
    return [row for row in queue.get("items", []) if row.get("asset", "").startswith("TOWERS")]


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no TOWERS rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        semantic = source_row.get("semantic_brief") or {}
        colours = semantic.get("required_colours") or []
        pattern = semantic.get("colour_pattern")
        svg = _svg(asset, _tower(asset, colours, pattern))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_repair_queue_towers_consumed",
            "risk_bucket": "tower_silhouette_repair_batch59",
            "candidate_strategy": "queued_towers_owned_silhouette_redraw",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": semantic,
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue TOWERS missing tower silhouette feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch51",
                "reference_role": "repair queue required_change plus semantic_brief required colours/patterns drive tower silhouette redraw",
            },
            "source_judge": (item.get("judge") or {}).get("latest", {}).get("batch"),
        })
    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {"failed_repaired": len(rows), "visual_parity": "repaired_pending_judge_rerun"},
        "symbols": rows,
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 51 / Owned Repair Batch 59",
        "",
        "Data-driven tower silhouette redraws for queued `TOWERS*` rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Required colours | Colour pattern |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(f"`{c}`" for c in semantic.get("required_colours") or []) or "`black` default"
        pattern = semantic.get("colour_pattern") or "solid/default"
        lines.append(f"| `{row['asset']}` | {colours} | {pattern} |")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved.", ""])
    SUMMARY.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
