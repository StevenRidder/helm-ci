"""Repair queued BOYSUP super-buoy rows into owned batch 73.

Run:
  python3 -m forge.standard_repair_batch65 --render
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
OUT = ROOT / "out" / "standard_repair_batch65"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch73"
REPORT = CATALOG / "owned_repair_batch73.json"
SUMMARY = CATALOG / "owned_repair_batch73.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = ("BOYSUP01", "BOYSUP02", "BOYSUP03", "BOYSUP62", "BOYSUP65", "BOYSUP66")


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
        'data-repair-batch="standard-repair-batch65">'
        f"<title>{asset} super-buoy parity repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _colours(row: dict) -> list[str]:
    colours = (row.get("semantic_brief") or {}).get("required_colours") or []
    return [("gray" if colour == "grey" else colour) for colour in colours] or ["black"]


def _bands(asset: str, colours: list[str], pattern: str | None) -> str:
    points = "20,28 44,28 49,41 40,51 24,51 15,41"
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if pattern and "vertical" in pattern:
        width = 34 / len(colours)
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="{15 + index * width:.2f}" y="26" width="{width:.2f}" height="27" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-super-buoy-band"/>'
            )
    else:
        height = 25 / len(colours)
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="14" y="{27 + index * height:.2f}" width="36" height="{height:.2f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-super-buoy-band"/>'
            )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 51 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _top_detail(asset: str) -> str:
    if asset == "BOYSUP03":
        return (
            f'<path d="M32 23 V15 M27 18 L37 18 M28 14 L36 22 M36 14 L28 22" '
            f'fill="none" stroke="{_colour("black")}" stroke-width="2.3"/>'
        )
    if asset in {"BOYSUP01", "BOYSUP02", "BOYSUP62"}:
        return f'<path d="M28 28 V23 H36 V28" fill="none" stroke="{_colour("black")}" stroke-width="2.6"/>'
    return ""


def _body(asset: str, row: dict) -> str:
    colours = _colours(row)
    pattern = (row.get("semantic_brief") or {}).get("colour_pattern")
    return _top_detail(asset) + _bands(asset, colours, pattern)


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
        raise RuntimeError("no BOYSUP rows in standard repair queue")

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
            "queue_action": "standard_boysup_reference_consumed",
            "risk_bucket": "super_buoy_reference_repair_batch73",
            "candidate_strategy": "owned_super_buoy_redraw_from_s57_colour_and_chart1_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue BOYSUP super-buoy blocker",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch65",
                "reference_role": "OpenCPN/S-101/Chart No.1 witnesses and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 65 / Owned Repair Batch 73",
        "",
        "Chart No.1/OpenCPN repair pass for queued `BOYSUP*` super-buoy rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Colours |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(semantic.get("required_colours") or []) or "black/reference"
        lines.append(f"| `{row['asset']}` | {colours} |")
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
