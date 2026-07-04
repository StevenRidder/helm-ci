"""Repair inspectable TOPSHP OpenCPN-reference rows into owned batch 70.

Run:
  python3 -m forge.standard_repair_batch62 --render
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
OUT = ROOT / "out" / "standard_repair_batch62"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch70"
REPORT = CATALOG / "owned_repair_batch70.json"
SUMMARY = CATALOG / "owned_repair_batch70.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "TOPSHP00": "octagon_plus",
    "TOPSHP01": "notched23_vertical",
    "TOPSHP02": "notched23_vertical",
    "TOPSHP03": "notched22_vertical",
    "TOPSHP04": "notched22_vertical",
    "TOPSHP08": "triangle_horizontal",
    "TOPSHP16": "triangle_inset",
    "TOPSHP17": "triangle_vertical",
    "TOPSHP18": "triangle_solid",
    "TOPSHP19": "triangle_inset",
    "TOPSHP20": "triangle_solid",
    "TOPSHP21": "square_solid",
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
        'data-repair-batch="standard-repair-batch62">'
        f"<title>{asset} top-shape parity repair candidate</title>"
        '<g stroke-linecap="square" stroke-linejoin="miter">'
        f"{body}</g></svg>\n"
    )


def _colours(row: dict) -> list[str]:
    colours = (row.get("semantic_brief") or {}).get("required_colours") or []
    return [("gray" if colour == "grey" else colour) for colour in colours] or ["black"]


def _poly_fill(asset: str, points: str, colours: list[str], orientation: str) -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if orientation == "vertical":
        width = 42 / len(colours)
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="{11 + index * width:.2f}" y="7" width="{width:.2f}" height="50" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-topshape-band"/>'
            )
    else:
        height = 50 / len(colours)
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="11" y="{7 + index * height:.2f}" width="42" height="{height:.2f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-topshape-band"/>'
            )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _notched(asset: str, colours: list[str], variant: str) -> str:
    if variant == "notched23_vertical":
        points = "18,11 48,11 48,36 44,36 44,52 24,52 24,36 18,36"
    else:
        points = "25,11 46,11 46,40 51,40 51,52 17,52 17,40 23,40"
    return _poly_fill(asset, points, colours, "vertical")


def _triangle(asset: str, colours: list[str], mode: str) -> str:
    points = "32,9 51,52 13,52"
    if mode == "triangle_vertical":
        return _poly_fill(asset, points, colours, "vertical") + f'<rect x="28" y="7" width="8" height="16" fill="{_colour("black")}"/>'
    if mode == "triangle_horizontal":
        return _poly_fill(asset, points, colours, "horizontal") + f'<path d="M13 55 H51" stroke="{_colour("black")}" stroke-width="3"/>'
    if mode == "triangle_inset" and len(colours) >= 2:
        outer, inner = colours[0], colours[-1]
        return (
            f'<polygon points="{points}" fill="{_colour(outer)}" stroke="{_colour("black")}" stroke-width="3"/>'
            f'<polygon points="32,24 43,48 21,48" fill="{_colour(inner)}" stroke="none"/>'
            f'<rect x="28" y="9" width="8" height="13" fill="{_colour(outer)}" stroke="none"/>'
        )
    fill = colours[0]
    return (
        f'<polygon points="{points}" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<rect x="28" y="9" width="8" height="13" fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M13 55 H51" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _octagon_plus() -> str:
    outer = "32,6 46,12 58,26 58,38 46,52 32,58 18,52 6,38 6,26 18,12"
    inner = "32,14 43,19 50,29 50,35 43,45 32,50 21,45 14,35 14,29 21,19"
    return (
        f'<polygon points="{outer}" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<polygon points="{inner}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 24 V40 M24 32 H40" stroke="{_colour("red")}" stroke-width="8" stroke-linecap="square"/>'
    )


def _square(colours: list[str]) -> str:
    return f'<rect x="18" y="14" width="28" height="36" fill="{_colour(colours[0])}" stroke="{_colour("black")}" stroke-width="3"/>'


def _body(asset: str, row: dict) -> str:
    kind = TARGETS[asset]
    colours = _colours(row)
    if kind == "octagon_plus":
        return _octagon_plus()
    if kind.startswith("notched"):
        return _notched(asset, colours, kind)
    if kind.startswith("triangle"):
        return _triangle(asset, colours, kind)
    if kind == "square_solid":
        return _square(colours)
    raise KeyError(f"unsupported TOPSHP target: {asset}")


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
            }
            for row in prior.get("symbols", [])
        ]
    return []


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no inspectable TOPSHP rows in standard repair queue")

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
            "queue_action": "standard_topshape_open_cpn_reference_consumed",
            "risk_bucket": "topshape_opencpn_reference_repair_batch70",
            "candidate_strategy": "owned_topshape_redraw_from_opencpn_reference_silhouette_and_s57_colours",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": f"catalog/{judge.get('batch')}.json" if judge.get("batch") else None,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue TOPSHP OpenCPN visual-reference blocker",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch62",
                "reference_role": "OpenCPN raster and S-57 colour metadata are visual witnesses; SVG is owned redraw",
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
        "blockers": [
            "Malformed TOPSHP09;TE('%s and TOPSHP15;TE('%s rows require S-52 token normalization before repair.",
            "TOPSHP33 lacks a local OpenCPN reference raster and remains queued.",
        ],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 62 / Owned Repair Batch 70",
        "",
        "OpenCPN-reference repair pass for inspectable `TOPSHP*` top-shape rows.",
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
