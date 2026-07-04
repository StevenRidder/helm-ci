"""Repair queued BCNTOW/BCNSTK rows into owned repair batch 60.

Run:
  python3 -m forge.standard_repair_batch52 --render
"""
from __future__ import annotations

import argparse
import ctypes.util
import json
import re
from pathlib import Path

from . import render, standard_repair_batch51
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPAIR_QUEUE = CATALOG / "standard_repair_queue.json"
OUT = ROOT / "out" / "standard_repair_batch52"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch60"
REPORT = CATALOG / "owned_repair_batch60.json"
SUMMARY = CATALOG / "owned_repair_batch60.md"
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
        'data-repair-batch="standard-repair-batch52">'
        f"<title>{asset} beacon tower/stake repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _stake_clip(asset: str) -> tuple[str, str]:
    clip_id = f"clip_{_safe(asset)}"
    return clip_id, f'<defs><clipPath id="{clip_id}"><rect x="28" y="12" width="8" height="40"/></clipPath></defs>'


def _stake_frame() -> str:
    return (
        f'<rect x="28" y="12" width="8" height="40" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M18 52 H46" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M32 52 V57" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _stake(asset: str, colours: list[str], pattern: str | None) -> str:
    colours = colours or ["black"]
    clip_id, defs = _stake_clip(asset)
    pattern_l = (pattern or "").lower()
    if "vertical" in pattern_l:
        band_w = 8 / len(colours)
        parts = [defs]
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="{28 + index * band_w:.1f}" y="12" width="{band_w:.1f}" height="40" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-stake"/>'
            )
        return "".join(parts) + _stake_frame()
    if "horizontal" in pattern_l or len(colours) > 1:
        band_h = 40 / len(colours)
        parts = [defs]
        for index, colour in enumerate(colours):
            parts.append(
                f'<rect x="28" y="{12 + index * band_h:.1f}" width="8" height="{band_h:.1f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-stake"/>'
            )
        return "".join(parts) + _stake_frame()
    return (
        defs
        + f'<rect x="28" y="12" width="8" height="40" fill="{_colour(colours[0])}" clip-path="url(#{clip_id})" data-pattern="solid-stake"/>'
        + _stake_frame()
    )


def _body(asset: str, colours: list[str], pattern: str | None) -> str:
    if asset.startswith("BCNTOW"):
        return standard_repair_batch51._tower(asset, colours, pattern)
    return _stake(asset, colours, pattern)


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
    return [
        row for row in queue.get("items", [])
        if row.get("asset", "").startswith("BCNTOW") or row.get("asset", "").startswith("BCNSTK")
    ]


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no BCNTOW/BCNSTK rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        semantic = source_row.get("semantic_brief") or {}
        colours = semantic.get("required_colours") or []
        pattern = semantic.get("colour_pattern")
        svg = _svg(asset, _body(asset, colours, pattern))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_repair_queue_beacon_tower_stake_consumed",
            "risk_bucket": "beacon_tower_stake_repair_batch60",
            "candidate_strategy": "queued_bcntow_bcnstk_owned_silhouette_redraw",
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
                "source_priority_basis": "standard_repair_queue BCNTOW/BCNSTK exact-silhouette feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch52",
                "reference_role": "repair queue required_change plus semantic colour/pattern metadata drive tower/stake redraw",
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
        "# Standard Repair Batch 52 / Owned Repair Batch 60",
        "",
        "Data-driven beacon tower/stake redraws for queued `BCNTOW*` and `BCNSTK*` rows.",
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
