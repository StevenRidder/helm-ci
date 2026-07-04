"""Repair queued BOYLAT Chart No.1 parity rows into owned batch 68.

Run:
  python3 -m forge.standard_repair_batch60 --render
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
OUT = ROOT / "out" / "standard_repair_batch60"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch68"
REPORT = CATALOG / "owned_repair_batch68.json"
SUMMARY = CATALOG / "owned_repair_batch68.md"
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
        'data-repair-batch="standard-repair-batch60">'
        f"<title>{asset} lateral buoy parity repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _colours(row: dict) -> list[str]:
    semantic = row.get("semantic_brief") or {}
    return [("gray" if colour == "grey" else colour) for colour in semantic.get("required_colours") or []] or ["black"]


def _shape(asset: str, row: dict) -> str:
    required = ((row.get("semantic_brief") or {}).get("required_shape") or "").lower()
    name = (row.get("name") or "").lower()
    if "conical" in required or "conical" in name or asset in {"BOYLAT13", "BOYLAT14", "BOYLAT51"}:
        return "cone"
    if "can/cylindrical" in required or "can shape" in name or asset in {"BOYLAT23", "BOYLAT24", "BOYLAT50"}:
        return "can"
    if asset in {"BOYLAT26", "BOYLAT27"}:
        return "spar"
    if asset == "BOYLAT25":
        return "sphere"
    return "can"


def _points(shape: str) -> str:
    if shape == "cone":
        return "32,11 16,48 48,48"
    if shape == "spar":
        return "28,10 36,10 40,52 24,52"
    return "20,16 44,16 48,48 16,48"


def _polygon_body(asset: str, shape: str, colours: list[str]) -> str:
    points = _points(shape)
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    height = 40 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="12" y="{12 + index * height:.2f}" width="40" height="{height:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-lateral-band"/>'
        )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 48 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _sphere(asset: str, colours: list[str]) -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><circle cx="32" cy="32" r="18"/></clipPath></defs>']
    height = 36 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="14" y="{14 + index * height:.2f}" width="36" height="{height:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-sphere-band"/>'
        )
    parts.append(f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 50 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _body(asset: str, row: dict) -> str:
    shape = _shape(asset, row)
    colours = _colours(row)
    if shape == "sphere":
        return _sphere(asset, colours)
    return _polygon_body(asset, shape, colours)


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
    items = [row for row in queue.get("items", []) if row.get("asset", "").startswith("BOYLAT")]
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
        raise RuntimeError("no BOYLAT rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
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
            "queue_action": "standard_chart1_parity_lateral_buoy_consumed",
            "risk_bucket": "chart1_lateral_buoy_repair_batch68",
            "candidate_strategy": "owned_lateral_buoy_redraw_from_s57_shape_colour_and_chart1_parity_gate",
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
                "source_priority_basis": "standard_repair_queue Chart No.1 parity blocker for BOYLAT rows",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch60",
                "reference_role": "S-57 lateral buoy metadata plus provider images drive generated-owned redraw",
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
        "# Standard Repair Batch 60 / Owned Repair Batch 68",
        "",
        "Chart No.1 parity repair pass for queued `BOYLAT*` lateral buoy rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Shape | Colours |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(semantic.get("required_colours") or []) or "black"
        shape = _shape(row["asset"], row)
        lines.append(f"| `{row['asset']}` | {shape} | {colours} |")
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
