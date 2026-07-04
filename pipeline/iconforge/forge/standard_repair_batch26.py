"""Repair BCNGEN64 four-band beacon into owned repair batch 34.

Run:
  python3 -m forge.standard_repair_batch26 --render
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
OUT = ROOT / "out" / "standard_repair_batch26"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch34"
REPORT = CATALOG / "owned_repair_batch34.json"
SUMMARY = CATALOG / "owned_repair_batch34.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
ASSET = "BCNGEN64"


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg() -> str:
    red = _colour("red")
    white = _colour("white")
    black = _colour("black")
    body = (
        f'<rect x="25" y="10" width="14" height="39" rx="1.8" fill="{white}" stroke="{black}" stroke-width="4"/>'
        f'<path d="M32 49 V59" fill="none" stroke="{black}" stroke-width="4"/>'
        f'<rect x="27" y="12" width="10" height="8.75" fill="{red}" stroke="none"/>'
        f'<rect x="27" y="20.75" width="10" height="8.75" fill="{white}" stroke="none"/>'
        f'<rect x="27" y="29.5" width="10" height="8.75" fill="{red}" stroke="none"/>'
        f'<rect x="27" y="38.25" width="10" height="8.75" fill="{white}" stroke="none"/>'
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch26">'
        "<title>BCNGEN64 repair batch 34 candidate</title>"
        f'<g stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>\n'
    )


def _ensure_cairo_library() -> None:
    if ctypes.util.find_library("cairo") or not HOMEBREW_CAIRO.exists():
        return
    original_find_library = ctypes.util.find_library

    def find_library(name: str) -> str | None:
        if name in {"cairo", "cairo-2", "libcairo-2"}:
            return str(HOMEBREW_CAIRO)
        return original_find_library(name)

    ctypes.util.find_library = find_library


def _render_svg(svg: str, palette: str) -> str:
    _ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(ASSET)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _source_row() -> dict:
    table = json.loads(SOURCE_TABLE.read_text())
    for row in table.get("rows", []):
        if row["asset"] == ASSET:
            return row
    raise RuntimeError(f"source table missing repair target: {ASSET}")


def build(*, render_outputs: bool = False) -> dict:
    source_row = _source_row()
    helm = source_row.get("helm_candidate") or {}
    judge = (source_row.get("judge") or {}).get("latest") or {}
    svg = _svg()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    svg_path = SVG_OUT / f"{ASSET}.svg"
    svg_path.write_text(svg)
    renders = {}
    if render_outputs:
        for palette in PALETTES:
            renders[palette] = _render_svg(svg, palette)
    row = {
        "asset": ASSET,
        "name": source_row.get("name"),
        "queue_action": "judge_failure_consumed",
        "risk_bucket": "single_band_order_repair_batch34",
        "candidate_strategy": "owned_redraw_preserving_compact_beacon_with_four_bands",
        "candidate_source": helm.get("canonical_svg"),
        "before_svg": helm.get("canonical_svg"),
        "after_svg": str(svg_path.relative_to(ROOT)),
        "after_renders": renders,
        "repair_note": "Judge repair: split beacon body into four ordered bands red/white/red/white for COLOUR3,1,3,1.",
        "required_change": judge.get("required_change"),
        "safety_reason_codes": judge.get("safety_reason_codes", []),
        "semantic_brief": source_row.get("semantic_brief"),
        "visual_examples": source_row.get("reference_providers", {}),
        "qa": {
            "semantic_pass": False,
            "structural_pass": True,
            "visual_parity": "repaired_pending_judge_rerun",
            "final_approved": False,
        },
        "provenance": {
            "origin": "generated-owned-artwork",
            "source_priority_basis": "standard_judge_batch_007_009_beacon_rerun_feedback",
            "style_contract_id": OPENBRIDGE_STYLE_ID,
            "generator": "forge.standard_repair_batch26",
            "reference_role": "judge feedback and OpenCPN/Chart1 refs are shape witnesses; SVG is owned redraw",
        },
        "source_judge": "catalog/standard_judge_batch_007_009_beacon_rerun.json",
    }
    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {"failed_repaired": 1, "visual_parity": "repaired_pending_judge_rerun"},
        "symbols": [row],
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    row = result["symbols"][0]
    lines = [
        "# Standard Repair Batch 26 / Owned Repair Batch 34",
        "",
        "Owned redraw for the single BCNGEN64 band-order failure.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        f"- visual_parity: `{result['summary']['visual_parity']}`",
        "",
        "## Repaired",
        "",
        f"- `{row['asset']}`: {row['repair_note']}",
        "",
        "Rows remain pending judge rerun; none are final-approved.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
