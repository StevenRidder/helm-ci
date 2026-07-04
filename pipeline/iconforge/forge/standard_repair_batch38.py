"""Repair first topmark slice into owned repair batch 46.

Run:
  python3 -m forge.standard_repair_batch38 --render
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
OUT = ROOT / "out" / "standard_repair_batch38"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch46"
REPORT = CATALOG / "owned_repair_batch46.json"
SUMMARY = CATALOG / "owned_repair_batch46.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "TOPMA100": "cone_down_red",
    "TOPMA102": "cone_up_green",
    "TOPMA106": "square_wrw",
    "TOPMA107": "square_red_border",
    "TOPMA109": "diagonal_green_border",
    "TOPMA111": "upright_cross_yellow",
    "TOPMA113": "x_cross_yellow",
    "TOPMA114": "board_red",
    "TOPMA115": "board_green",
    "TOPMA116": "board_rwr",
    "TOPMA117": "sphere_red_green",
    "TOPMAR01": "sphere_red_green",
    "TOPMAR87": "besom_down_black",
    "TOPMAR88": "besom_up_black",
    "TOPMAR90": "pricken_down_black",
    "TOPMAR91": "board_red",
    "TOPMAR92": "board_green",
    "TOPMAR93": "pricken_up_black",
    "TOPMAR98": "diagonal_white_orange",
    "TOPMAR99": "diamond_yellow",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch38">'
        f"<title>{asset} repair batch 46 topmark candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 3.5) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _cone(direction: str, colour: str) -> str:
    points = "32,12 18,42 46,42" if direction == "up" else "18,22 46,22 32,52"
    return f'<polygon points="{points}" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="2.8"/>'


def _board(fill: str, *, border: str = "black") -> str:
    return f'<rect x="18" y="14" width="28" height="36" fill="{_colour(fill)}" stroke="{_colour(border)}" stroke-width="3.2"/>'


def _band_board(colours: list[str]) -> str:
    h = 36 / len(colours)
    parts = []
    for i, colour in enumerate(colours):
        parts.append(f'<rect x="18" y="{14 + i * h:.1f}" width="28" height="{h:.1f}" fill="{_colour(colour)}" stroke="none"/>')
    parts.append(f'<rect x="18" y="14" width="28" height="36" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>')
    return "".join(parts)


def _diagonal_board(first: str, second: str, border: str = "black") -> str:
    return (
        f'<polygon points="18,14 46,14 18,50" fill="{_colour(first)}" stroke="none"/>'
        f'<polygon points="46,14 46,50 18,50" fill="{_colour(second)}" stroke="none"/>'
        f'<rect x="18" y="14" width="28" height="36" fill="none" stroke="{_colour(border)}" stroke-width="3.2"/>'
    )


def _upright_cross() -> str:
    return _path("M32 13 V51 M18 32 H46", "yellow", 7)


def _x_cross() -> str:
    return _path("M19 19 L45 45 M45 19 L19 45", "yellow", 7)


def _sphere() -> str:
    return (
        f'<path d="M16 32 A16 16 0 0 1 48 32 H16 Z" fill="{_colour("red")}" stroke="none"/>'
        f'<path d="M16 32 A16 16 0 0 0 48 32 H16 Z" fill="{_colour("green")}" stroke="none"/>'
        f'<circle cx="32" cy="32" r="16" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
    )


def _besom(direction: str) -> str:
    if direction == "down":
        return _path("M32 13 V32 M20 29 L32 51 L44 29 M24 31 H40", "black", 4)
    return _path("M32 51 V32 M20 35 L32 13 L44 35 M24 33 H40", "black", 4)


def _pricken(direction: str) -> str:
    if direction == "down":
        return _path("M32 12 V50 M22 30 L32 50 L42 30", "black", 4)
    return _path("M32 52 V14 M22 34 L32 14 L42 34", "black", 4)


def _diamond(colour: str) -> str:
    return f'<polygon points="32,10 54,32 32,54 10,32" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="3"/>'


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "cone_down_red":
        return _svg(asset, _cone("down", "red"))
    if kind == "cone_up_green":
        return _svg(asset, _cone("up", "green"))
    if kind == "square_wrw":
        return _svg(asset, _band_board(["white", "red", "white"]))
    if kind == "square_red_border":
        return _svg(asset, _board("white", border="red"))
    if kind == "diagonal_green_border":
        return _svg(asset, _diagonal_board("white", "white", border="green"))
    if kind == "upright_cross_yellow":
        return _svg(asset, _upright_cross())
    if kind == "x_cross_yellow":
        return _svg(asset, _x_cross())
    if kind == "board_red":
        return _svg(asset, _board("red"))
    if kind == "board_green":
        return _svg(asset, _board("green"))
    if kind == "board_rwr":
        return _svg(asset, _band_board(["red", "white", "red"]))
    if kind == "sphere_red_green":
        return _svg(asset, _sphere())
    if kind == "besom_down_black":
        return _svg(asset, _besom("down"))
    if kind == "besom_up_black":
        return _svg(asset, _besom("up"))
    if kind == "pricken_down_black":
        return _svg(asset, _pricken("down"))
    if kind == "pricken_up_black":
        return _svg(asset, _pricken("up"))
    if kind == "diagonal_white_orange":
        return _svg(asset, _diagonal_board("white", "orange"))
    if kind == "diamond_yellow":
        return _svg(asset, _diamond("yellow"))
    raise KeyError(f"unsupported repair kind: {kind}")


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
    missing_source = sorted(set(REPAIRS) - set(source_rows))
    if missing_source:
        raise RuntimeError(f"source table missing repair target(s): {missing_source}")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
        svg = _redraw(asset)
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
            "risk_bucket": "topmark_repair_batch46",
            "candidate_strategy": "owned_topmark_redraw_from_semantic_brief_and_provider_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
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
                "source_priority_basis": "standard_repair_queue topmark slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch38",
                "reference_role": "provider refs and semantic_brief are shape witnesses; SVG is owned redraw",
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
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 38 / Owned Repair Batch 46",
        "",
        "Owned redraws for first topmark judge-failure slice.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {REPAIRS[row['asset']]}")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved."])
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
