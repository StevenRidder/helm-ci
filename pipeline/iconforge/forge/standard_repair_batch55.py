"""Repair queued BOYCAN/BOYCON Chart No.1 parity rows into owned batch 63.

Run:
  python3 -m forge.standard_repair_batch55 --render
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
OUT = ROOT / "out" / "standard_repair_batch55"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch63"
REPORT = CATALOG / "owned_repair_batch63.json"
SUMMARY = CATALOG / "owned_repair_batch63.md"
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
        'data-repair-batch="standard-repair-batch55">'
        f"<title>{asset} can/cone buoy parity repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _shape_points(asset: str) -> str:
    if asset.startswith("BOYCON"):
        return "32,11 16,48 48,48"
    return "20,16 44,16 48,48 16,48"


def _pattern(row: dict) -> str:
    pattern = ((row.get("semantic_brief") or {}).get("colour_pattern") or "").lower()
    if "vertical" in pattern and "horizontal" in pattern:
        return "mixed"
    if "vertical" in pattern:
        return "vertical"
    return "horizontal"


def _colours(row: dict) -> list[str]:
    semantic = row.get("semantic_brief") or {}
    colours = semantic.get("required_colours") or []
    return [("gray" if colour == "grey" else colour) for colour in colours] or ["black"]


def _horizontal_bands(asset: str, points: str, colours: list[str]) -> list[str]:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    height = 40 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="12" y="{12 + index * height:.2f}" width="40" height="{height:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-buoy-band"/>'
        )
    return parts


def _vertical_bands(asset: str, points: str, colours: list[str]) -> list[str]:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    width = 40 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{12 + index * width:.2f}" y="10" width="{width:.2f}" height="42" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-buoy-band"/>'
        )
    return parts


def _mixed_bands(asset: str, points: str, colours: list[str]) -> list[str]:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    colours = colours or ["blue", "red", "white", "blue"]
    height = 40 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="12" y="{12 + index * height:.2f}" width="40" height="{height:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="mixed-horizontal-buoy-band"/>'
        )
    mid = colours[0]
    parts.append(
        f'<rect x="29" y="10" width="6" height="42" fill="{_colour(mid)}" '
        f'clip-path="url(#{clip_id})" data-pattern="mixed-vertical-buoy-band"/>'
    )
    return parts


def _banded_buoy(asset: str, row: dict) -> str:
    points = _shape_points(asset)
    colours = _colours(row)
    pattern = _pattern(row)
    if pattern == "vertical":
        parts = _vertical_bands(asset, points, colours)
    elif pattern == "mixed":
        parts = _mixed_bands(asset, points, colours)
    else:
        parts = _horizontal_bands(asset, points, colours)
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 48 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M24 56 H40" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


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
    items = [
        row for row in queue.get("items", [])
        if row.get("asset", "").startswith(("BOYCAN", "BOYCON"))
    ]
    if items:
        return items
    if REPORT.exists():
        prior = json.loads(REPORT.read_text())
        return [
            {
                "asset": row["asset"],
                "required_change": row.get("required_change"),
                "safety_reason_codes": row.get("safety_reason_codes", []),
                "chart1_parity_gate": row.get("chart1_parity_gate"),
                "status": "owned_repair_batch63_fallback_for_idempotent_rebuild",
            }
            for row in prior.get("symbols", [])
        ]
    return []


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no BOYCAN/BOYCON rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        svg = _svg(asset, _banded_buoy(asset, source_row))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_chart1_parity_buoy_can_cone_consumed",
            "risk_bucket": "chart1_buoy_can_cone_repair_batch63",
            "candidate_strategy": "owned_can_cone_redraw_from_s57_colour_order_and_chart1_parity_gate",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "chart1_parity_gate": item.get("chart1_parity_gate") or source_row.get("chart1_parity_gate"),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue Chart No.1 parity blocker for BOYCAN/BOYCON rows",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch55",
                "reference_role": "S-57 shape/colour metadata plus provider images drive a generated-owned can/cone redraw",
            },
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
        "# Standard Repair Batch 55 / Owned Repair Batch 63",
        "",
        "Chart No.1 parity repair pass for queued `BOYCAN*` and `BOYCON*` can/cone buoy rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Shape | Colours | Pattern |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["symbols"]:
        shape = "cone" if row["asset"].startswith("BOYCON") else "can"
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(semantic.get("required_colours") or []) or "black"
        pattern = semantic.get("colour_pattern") or "ordered horizontal/default"
        lines.append(f"| `{row['asset']}` | {shape} | {colours} | {pattern} |")
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
