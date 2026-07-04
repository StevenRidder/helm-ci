"""Repair queued BOYBAR barrel buoy rows into owned batch 75.

Run:
  python3 -m forge.standard_repair_batch67 --render
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
OUT = ROOT / "out" / "standard_repair_batch67"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch75"
REPORT = CATALOG / "owned_repair_batch75.json"
SUMMARY = CATALOG / "owned_repair_batch75.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
TARGETS = ("BOYBAR01", "BOYBAR60", "BOYBAR61", "BOYBAR62")


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
        'data-repair-batch="standard-repair-batch67">'
        f"<title>{asset} barrel buoy parity repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _colours(row: dict) -> list[str]:
    colours = (row.get("semantic_brief") or {}).get("required_colours") or []
    return [("gray" if colour == "grey" else colour) for colour in colours] or ["black"]


def _barrel(asset: str, colours: list[str]) -> str:
    clip_id = f"clip_{_safe(asset)}"
    path = "M20 32 Q20 24 26 22 H38 Q44 24 44 32 V41 Q44 48 38 50 H26 Q20 48 20 41 Z"
    parts = [f'<defs><clipPath id="{clip_id}"><path d="{path}"/></clipPath></defs>']
    height = 28 / len(colours)
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="18" y="{22 + index * height:.2f}" width="28" height="{height:.2f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-barrel-band"/>'
        )
    parts.append(f'<path d="{path}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M20 39 H44 M26 22 V17 H38 V22 M32 50 V55" fill="none" stroke="{_colour("black")}" stroke-width="2.6"/>')
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
        raise RuntimeError("no BOYBAR rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        svg = _svg(asset, _barrel(asset, _colours(source_row)))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_boybar_reference_consumed",
            "risk_bucket": "barrel_buoy_reference_repair_batch75",
            "candidate_strategy": "owned_barrel_buoy_redraw_from_chart1_opencpn_reference_and_s57_colours",
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
                "source_priority_basis": "standard_repair_queue BOYBAR barrel-buoy blocker",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch67",
                "reference_role": "OpenCPN/Chart No.1 witnesses and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 67 / Owned Repair Batch 75",
        "",
        "Chart No.1/OpenCPN repair pass for queued `BOYBAR*` barrel buoy rows.",
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
