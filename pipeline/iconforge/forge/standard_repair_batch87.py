"""Repair queued TOPSHP judge failures into owned batch 87.

Run:
  python3 -m forge.standard_repair_batch87 --render
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
OUT = ROOT / "out" / "standard_repair_batch87"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch87"
REPORT = CATALOG / "owned_repair_batch87.json"
SUMMARY = CATALOG / "owned_repair_batch87.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "TOPSHP47": ("compact_red_square_board", "catalog/standard_judge_batch_049_rerun.json"),
    "TOPSHP48": ("compact_green_square_board", "catalog/standard_judge_batch_049_rerun.json"),
    "TOPSHPI3": ("white_red_x_cross", "catalog/standard_judge_batch_051_rerun.json"),
    "TOPSHPJ1": ("yellow_cup_topmark", "catalog/standard_judge_batch_051_rerun.json"),
    "TOPSHPJ3": ("white_cup_topmark", "catalog/standard_judge_batch_051_rerun.json"),
    "TOPSHPP2": ("yellow_plus_topmark", "catalog/standard_judge_batch_051_rerun.json"),
    "TOPSHPR1": ("black_trapezoid_topmark", "catalog/standard_judge_batch_051_rerun.json"),
    "TOPSHPS1": ("red_white_red_target_topmark", "catalog/standard_judge_batch_051_rerun.json"),
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch87">'
        f"<title>{asset} topmark repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _square(fill: str) -> str:
    return (
        f'<rect x="22" y="22" width="20" height="20" rx="0.8" '
        f'fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _cup(fill: str) -> str:
    return (
        f'<path d="M23 25 L23 37 Q32 43 41 37 L41 25 L35 29 L29 29 Z" '
        f'fill="{_colour(fill)}" stroke="{_colour("black")}" stroke-width="1.8"/>'
    )


def _body(asset: str) -> str:
    if asset == "TOPSHP47":
        return _square("red")
    if asset == "TOPSHP48":
        return _square("green")
    if asset == "TOPSHPI3":
        return (
            f'<path d="M23 23 L41 41 M41 23 L23 41" fill="none" '
            f'stroke="{_colour("white")}" stroke-width="6"/>'
            f'<path d="M23 23 L41 41 M41 23 L23 41" fill="none" '
            f'stroke="{_colour("red")}" stroke-width="3.2"/>'
        )
    if asset == "TOPSHPJ1":
        return _cup("yellow")
    if asset == "TOPSHPJ3":
        return _cup("white")
    if asset == "TOPSHPP2":
        return (
            f'<path d="M32 23 V41 M23 32 H41" fill="none" '
            f'stroke="{_colour("black")}" stroke-width="5.8"/>'
            f'<path d="M32 23 V41 M23 32 H41" fill="none" '
            f'stroke="{_colour("yellow")}" stroke-width="3.4"/>'
        )
    if asset == "TOPSHPR1":
        return f'<path d="M25 40 L28 25 H36 L39 40 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
    if asset == "TOPSHPS1":
        return (
            f'<circle cx="32" cy="32" r="11" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
            f'<circle cx="32" cy="32" r="7" fill="{_colour("white")}" stroke="none"/>'
            f'<circle cx="32" cy="32" r="3.6" fill="{_colour("red")}" stroke="none"/>'
        )
    raise KeyError(f"unsupported repair target: {asset}")


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
        raise RuntimeError("no TOPSHP rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        repair_kind, source_judge = TARGETS[asset]
        svg = _svg(asset, _body(asset))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_topshp_failure_consumed",
            "risk_bucket": "topshp_precise_repair_batch87",
            "candidate_strategy": f"owned_{repair_kind}_redraw_from_judge_feedback",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": source_judge,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": f"{source_judge} TOPSHP repair feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch87",
                "reference_role": "OpenCPN topmark witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 87 / Owned Repair Batch 87",
        "",
        "Targeted TOPSHP redraws for visual-judge failures.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Repair |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | `{TARGETS[row['asset']][0]}` |")
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
