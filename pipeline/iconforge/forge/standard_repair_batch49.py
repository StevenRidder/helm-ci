"""Repair TOPSHP compact square-board failures into owned repair batch 57.

Run:
  python3 -m forge.standard_repair_batch49 --render
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
JUDGE_FILE = CATALOG / "standard_judge_batch_048_rerun.json"
OUT = ROOT / "out" / "standard_repair_batch49"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch57"
REPORT = CATALOG / "owned_repair_batch57.json"
SUMMARY = CATALOG / "owned_repair_batch57.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = (
    "TOPSHP22",
    "TOPSHP23",
    "TOPSHP24",
    "TOPSHP25",
    "TOPSHP28",
    "TOPSHP29",
    "TOPSHP30",
    "TOPSHP31",
    "TOPSHP32",
    "TOPSHP33",
    "TOPSHP34",
    "TOPSHP35",
    "TOPSHP36",
    "TOPSHP37",
    "TOPSHP38",
    "TOPSHP40",
    "TOPSHP41",
    "TOPSHP42",
    "TOPSHP43",
    "TOPSHP44",
)

BOARD = {"x": 19, "y": 17, "w": 26, "h": 26}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _defs(asset: str) -> tuple[str, str]:
    clip_id = f"clip_{_safe(asset)}"
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    return clip_id, f'<defs><clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs>'


def _frame() -> str:
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M32 {y + h} V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _solid(asset: str, colour: str) -> str:
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{_colour(colour)}" '
        f'data-pattern="solid-square-board"/>'
        + _frame()
    )


def _vertical(asset: str, colours: list[str]) -> str:
    clip_id, defs = _defs(asset)
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    stripe_w = w / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{x + index * stripe_w:.1f}" y="{y}" width="{stripe_w:.1f}" height="{h}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-square-board"/>'
        )
    parts.append(_frame())
    return "".join(parts)


def _horizontal(asset: str, colours: list[str]) -> str:
    clip_id, defs = _defs(asset)
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    stripe_h = h / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{x}" y="{y + index * stripe_h:.1f}" width="{w}" height="{stripe_h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="horizontal-square-board"/>'
        )
    parts.append(_frame())
    return "".join(parts)


def _checker(asset: str, colours: list[str]) -> str:
    clip_id, defs = _defs(asset)
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    cols = 4
    rows = 4
    cell_w = w / cols
    cell_h = h / rows
    parts = [defs]
    for row in range(rows):
        for col in range(cols):
            colour = colours[(row + col) % len(colours)]
            parts.append(
                f'<rect x="{x + col * cell_w:.1f}" y="{y + row * cell_h:.1f}" '
                f'width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{_colour(colour)}" '
                f'clip-path="url(#{clip_id})" data-pattern="s57-colpat6-square-board"/>'
            )
    parts.append(_frame())
    return "".join(parts)


PATTERNS: dict[str, tuple[str, list[str]]] = {
    "TOPSHP22": ("solid", ["red"]),
    "TOPSHP23": ("solid", ["black"]),
    "TOPSHP24": ("solid", ["green"]),
    "TOPSHP25": ("checker", ["white", "orange"]),
    "TOPSHP28": ("vertical", ["green", "white", "black"]),
    "TOPSHP29": ("checker", ["red", "green", "red"]),
    "TOPSHP30": ("checker", ["green", "green", "yellow"]),
    "TOPSHP31": ("checker", ["orange", "white"]),
    "TOPSHP32": ("vertical", ["red", "white"]),
    "TOPSHP33": ("checker", ["green", "red", "green"]),
    "TOPSHP34": ("vertical", ["white", "orange", "white"]),
    "TOPSHP35": ("solid", ["yellow"]),
    "TOPSHP36": ("solid", ["orange"]),
    "TOPSHP37": ("checker", ["black", "black"]),
    "TOPSHP38": ("checker", ["orange", "white"]),
    "TOPSHP40": ("checker", ["white", "black"]),
    "TOPSHP41": ("horizontal", ["orange", "orange"]),
    "TOPSHP42": ("horizontal", ["red", "white"]),
    "TOPSHP43": ("horizontal", ["green", "red", "green"]),
    "TOPSHP44": ("checker", ["yellow", "yellow"]),
}


def _body(asset: str) -> str:
    pattern, colours = PATTERNS[asset]
    if pattern == "solid":
        return _solid(asset, colours[0])
    if pattern == "vertical":
        return _vertical(asset, colours)
    if pattern == "horizontal":
        return _horizontal(asset, colours)
    if pattern == "checker":
        return _checker(asset, colours)
    raise KeyError(pattern)


def _svg(asset: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch49">'
        f"<title>{asset} compact TOPSHP square board repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{_body(asset)}</g></svg>\n"
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


def _judge_rows() -> dict[str, dict]:
    data = json.loads(JUDGE_FILE.read_text())
    return {row["asset"]: row for row in data.get("verdicts", [])}


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    judge_rows = _judge_rows()
    missing_source = sorted(set(REPAIRS) - set(source_rows))
    missing_judge = sorted(set(REPAIRS) - set(judge_rows))
    if missing_source or missing_judge:
        raise RuntimeError(f"missing repair inputs: source={missing_source}, judge={missing_judge}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = judge_rows[asset]
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
            "queue_action": "standard_judge_batch_048_failure_consumed",
            "risk_bucket": "topshp_compact_square_board_repair_batch57",
            "candidate_strategy": "judge48_compact_square_board_owned_redraw",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
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
                "source_priority_basis": "standard_judge_batch_048_rerun failed compact-square-board feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch49",
                "reference_role": "judge48 required_change and TOPSHP19 square-board metadata drive repair semantics",
            },
            "source_judge": "catalog/standard_judge_batch_048_rerun.json",
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
        "# Standard Repair Batch 49 / Owned Repair Batch 57",
        "",
        "Targeted compact square-board redraws for the TOPSHP failures from `standard_judge_batch_048_rerun`.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Required change | Pattern |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        pattern, colours = PATTERNS[row["asset"]]
        change = (row.get("required_change") or "").replace("|", "\\|")
        lines.append(f"| `{row['asset']}` | {change} | `{pattern}` `{','.join(colours)}` |")
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
