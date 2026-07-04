"""Repair BOYCON81 mixed-stripe buoy into owned repair batch 55.

Run:
  python3 -m forge.standard_repair_batch47 --render
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
OUT = ROOT / "out" / "standard_repair_batch47"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch55"
REPORT = CATALOG / "owned_repair_batch55.json"
SUMMARY = CATALOG / "owned_repair_batch55.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
REPAIRS = ("BOYCON81",)


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _mixed_boycon81() -> str:
    points = "32,11 16,48 48,48"
    clip_id = "clip_BOYCON81"
    return (
        f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>'
        f'<rect x="16" y="11" width="32" height="37" fill="{_colour("white")}" clip-path="url(#{clip_id})"/>'
        f'<rect x="16" y="11" width="32" height="10" fill="{_colour("blue")}" clip-path="url(#{clip_id})"/>'
        f'<rect x="16" y="21" width="32" height="10" fill="{_colour("red")}" clip-path="url(#{clip_id})"/>'
        f'<rect x="16" y="31" width="12" height="17" fill="{_colour("blue")}" clip-path="url(#{clip_id})"/>'
        f'<rect x="36" y="31" width="12" height="17" fill="{_colour("blue")}" clip-path="url(#{clip_id})"/>'
        f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 48 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _svg(asset: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch47">'
        f"<title>{asset} repair batch 55 mixed stripe buoy candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{_mixed_boycon81()}</g></svg>\n"
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


def _render_svg(svg: str, asset: str, palette: str) -> str:
    _ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _source_rows() -> dict[str, dict]:
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
        svg = _svg(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "judge_failure_consumed",
            "risk_bucket": "buoy_mixed_pattern_repair_batch55",
            "candidate_strategy": "owned_targeted_mixed_colpat12_buoy_redraw",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": judge.get("required_change"),
            "safety_reason_codes": judge.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
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
                "source_priority_basis": "standard_judge_batch_053_rerun BOYCON81 failure",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch47",
                "reference_role": "S-57 COLPAT1,2 and OpenCPN witness require mixed horizontal/vertical stripe semantics",
            },
            "source_judge": f"catalog/{judge.get('batch')}.json" if judge.get("batch") else None,
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
    SUMMARY.write_text(
        "# Standard Repair Batch 47 / Owned Repair Batch 55\n\n"
        "- failed_repaired: `1`\n"
        "- visual_parity: `repaired_pending_judge_rerun`\n\n"
        "Rows remain pending judge rerun; none are final-approved.\n"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
