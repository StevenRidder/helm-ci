"""Repair queued TOPMA1 topmark rows into owned batch 71.

Run:
  python3 -m forge.standard_repair_batch63 --render
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
OUT = ROOT / "out" / "standard_repair_batch63"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch71"
REPORT = CATALOG / "owned_repair_batch71.json"
SUMMARY = CATALOG / "owned_repair_batch71.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "TOPMA100": "cone_down",
    "TOPMA102": "cone_up",
    "TOPMA106": "square_horizontal",
    "TOPMA107": "red_border_square",
    "TOPMA109": "green_border_diamond",
    "TOPMA113": "andreas_cross",
    "TOPMA114": "small_square",
    "TOPMA115": "cone_up",
    "TOPMA116": "square_horizontal",
    "TOPMA117": "sphere_horizontal",
}


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
        'data-repair-batch="standard-repair-batch63">'
        f"<title>{asset} topmark parity repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _colours(row: dict) -> list[str]:
    colours = (row.get("semantic_brief") or {}).get("required_colours") or []
    return [("gray" if colour == "grey" else colour) for colour in colours] or ["black"]


def _cone(asset: str, colour: str, direction: str) -> str:
    points = "32,14 18,48 46,48" if direction == "up" else "18,16 46,16 32,50"
    return f'<polygon points="{points}" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="3"/>'


def _horizontal_rect(asset: str, colours: list[str], *, x: int = 20, y: int = 18, w: int = 24, h: int = 28) -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs>']
    band_h = h / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{x}" y="{y + index * band_h:.2f}" width="{w}" height="{band_h:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-topmark-band"/>'
        )
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _sphere(asset: str, colours: list[str]) -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><circle cx="32" cy="32" r="17"/></clipPath></defs>']
    band_h = 34 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="15" y="{15 + index * band_h:.2f}" width="34" height="{band_h:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-sphere-band"/>'
        )
    parts.append(f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _red_border_square() -> str:
    return f'<rect x="20" y="18" width="24" height="28" fill="{_colour("white")}" stroke="{_colour("red")}" stroke-width="4"/>'


def _green_diamond() -> str:
    return f'<polygon points="32,14 50,32 32,50 14,32" fill="{_colour("white")}" stroke="{_colour("green")}" stroke-width="4"/>'


def _andreas_cross() -> str:
    return (
        f'<path d="M20 18 L44 46 M44 18 L20 46" fill="none" stroke="{_colour("black")}" stroke-width="9"/>'
        f'<path d="M20 18 L44 46 M44 18 L20 46" fill="none" stroke="{_colour("yellow")}" stroke-width="5"/>'
    )


def _small_square(colour: str) -> str:
    return f'<rect x="27" y="24" width="10" height="16" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="2.4"/>'


def _body(asset: str, row: dict) -> str:
    kind = TARGETS[asset]
    colours = _colours(row)
    if kind == "cone_down":
        return _cone(asset, colours[0], "down")
    if kind == "cone_up":
        return _cone(asset, colours[0], "up")
    if kind == "square_horizontal":
        return _horizontal_rect(asset, colours)
    if kind == "red_border_square":
        return _red_border_square()
    if kind == "green_border_diamond":
        return _green_diamond()
    if kind == "andreas_cross":
        return _andreas_cross()
    if kind == "small_square":
        return _small_square(colours[0])
    if kind == "sphere_horizontal":
        return _sphere(asset, colours)
    raise KeyError(f"unsupported TOPMA1 target: {asset}")


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
    items = [row for row in queue.get("items", []) if row.get("asset") in TARGETS]
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
            }
            for row in prior.get("symbols", [])
        ]
    return []


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no TOPMA1 rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
        svg = _svg(asset, _body(asset, source_row))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_topma1_reference_consumed",
            "risk_bucket": "topma1_reference_repair_batch71",
            "candidate_strategy": "owned_topmark_redraw_from_opencpn_chart1_reference_and_s57_colours",
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
            "source_judge": f"catalog/{judge.get('batch')}.json" if judge.get("batch") else None,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue TOPMA1 topmark blocker",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch63",
                "reference_role": "OpenCPN/Chart No.1 witness and S-57 colour metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 63 / Owned Repair Batch 71",
        "",
        "Reference repair pass for queued `TOPMA1*` topmark rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Strategy | Colours |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(semantic.get("required_colours") or []) or "black"
        lines.append(f"| `{row['asset']}` | {TARGETS[row['asset']]} | {colours} |")
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
