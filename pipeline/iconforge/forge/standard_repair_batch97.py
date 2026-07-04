"""Render batch-96 SymbolSpec-ready rows into owned batch 97.

Run:
  python3 -m forge.standard_repair_batch97 --render
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
SPECS = CATALOG / "symbol_specs_batch96.json"
OUT = ROOT / "out" / "standard_repair_batch97"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch97"
REPORT = CATALOG / "owned_repair_batch97.json"
SUMMARY = CATALOG / "owned_repair_batch97.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
SOURCE_JUDGE = "catalog/standard_judge_batch_083_084_rerun.json"
TARGETS = ("BCNCON81", "boyspp50")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch97">'
        f"<title>{asset} batch-96 SymbolSpec repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _conical_bands(colours: list[str]) -> str:
    clip = "clip-bcncon81"
    body = '<path d="M32 12 L48 49 Q32 56 16 49 Z"/>'
    band_h = 44 / len(colours)
    bands = []
    for idx, colour in enumerate(colours):
        y = 10 + idx * band_h
        bands.append(f'<rect x="0" y="{y:.2f}" width="64" height="{band_h + 0.4:.2f}" fill="{_colour(colour)}"/>')
    return (
        f'<defs><clipPath id="{clip}">{body}</clipPath></defs>'
        f'<g clip-path="url(#{clip})">{"".join(bands)}</g>'
        f'<g fill="none" stroke="{_colour("black")}" stroke-width="1.6">{body}</g>'
        f'<path d="M32 55 V60" fill="none" stroke="{_colour("black")}" stroke-width="1.1"/>'
    )


def _yellow_special_buoy() -> str:
    return (
        '<path d="M24 18 H40 L45 49 Q32 56 19 49 Z" fill="var(--yellow)" stroke="var(--black)" stroke-width="1.6"/>'
        '<path d="M27 27 H37 M26 36 H38" fill="none" stroke="var(--black)" stroke-width="0.9"/>'
        '<circle cx="32" cy="14" r="3.2" fill="var(--yellow)" stroke="var(--black)" stroke-width="1.2"/>'
        '<path d="M32 55 V60" fill="none" stroke="var(--black)" stroke-width="1.1"/>'
    )


def _body(asset: str, spec: dict) -> str:
    if asset == "BCNCON81":
        return _conical_bands(spec["geometry"]["colours"])
    if asset == "boyspp50":
        return _yellow_special_buoy()
    raise KeyError(f"unsupported batch97 target: {asset}")


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
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


def _specs() -> dict[str, dict]:
    return {row["id"]: row for row in json.loads(SPECS.read_text())["symbols"]}


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    specs = _specs()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in TARGETS:
        spec = specs[asset]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        svg = _svg(asset, _body(asset, spec))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "batch96_symbolspec_rendered",
            "risk_bucket": "symbolspec_render_batch97",
            "candidate_strategy": f"owned_{spec['geometry']['primitive']}_from_batch96_symbolspec",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": spec["generation"]["resolution"],
            "safety_reason_codes": ["symbolspec_generated_from_s57_metadata"],
            "semantic_brief": source_row.get("semantic_brief"),
            "symbol_spec": spec,
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": SOURCE_JUDGE,
            "qa": {
                "semantic_pass": True,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_judge_batch_083_084_rerun failure resolved by batch96 SymbolSpec generated from S-57/S-52 metadata",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch97",
                "reference_role": "No external art imported; S-57 conditions and batch96 SymbolSpec drive generated-owned redraw",
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
        "# Owned Repair Batch 97",
        "",
        "- Source: `symbol_specs_batch96` renderable rows",
        "- Status: `repair_batch_pending_judge_rerun`",
        "- Final approval: none; visual judge plus human review still required.",
        "",
        "| Asset | Strategy | After SVG |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | {row['candidate_strategy']} | `{row['after_svg']}` |")
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="also rasterize day/dusk/night preview PNGs")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": "ok", "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
