"""Repair TOPSHP batch57 pattern failures into owned repair batch 58.

Run:
  python3 -m forge.standard_repair_batch50 --render
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import render, standard_repair_batch49
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
JUDGE_FILE = CATALOG / "standard_judge_batch_057_rerun.json"
OUT = ROOT / "out" / "standard_repair_batch50"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch58"
REPORT = CATALOG / "owned_repair_batch58.json"
SUMMARY = CATALOG / "owned_repair_batch58.md"
PALETTES = ("day", "dusk", "night")

REPAIRS = (
    "TOPSHP25",
    "TOPSHP29",
    "TOPSHP30",
    "TOPSHP31",
    "TOPSHP33",
    "TOPSHP37",
    "TOPSHP38",
    "TOPSHP40",
    "TOPSHP41",
    "TOPSHP43",
    "TOPSHP44",
)

BOARD = {"x": 19, "y": 17, "w": 26, "h": 26}


def _colour(name: str) -> str:
    return f"var(--{name})"


def _safe(text: str) -> str:
    return standard_repair_batch49._safe(text)


def _frame() -> str:
    return standard_repair_batch49._frame()


def _nested(asset: str, colours: list[str]) -> str:
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    outer = colours[0]
    mid = colours[1] if len(colours) > 1 else "white"
    inner = colours[2] if len(colours) > 2 else colours[1]
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{_colour(outer)}" data-pattern="nested-square-board"/>'
        f'<rect x="{x + 6}" y="{y + 6}" width="{w - 12}" height="{h - 12}" fill="{_colour(mid)}" data-pattern="nested-square-board"/>'
        f'<rect x="{x + 10}" y="{y + 10}" width="{w - 20}" height="{h - 20}" fill="{_colour(inner)}" data-pattern="nested-square-board"/>'
        + _frame()
    )


def _quadrant(asset: str, colours: list[str]) -> str:
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    a, b = colours
    half_w = w / 2
    half_h = h / 2
    return (
        f'<rect x="{x}" y="{y}" width="{half_w}" height="{half_h}" fill="{_colour(a)}" data-pattern="quadrant-square-board"/>'
        f'<rect x="{x + half_w}" y="{y}" width="{half_w}" height="{half_h}" fill="{_colour(b)}" data-pattern="quadrant-square-board"/>'
        f'<rect x="{x}" y="{y + half_h}" width="{half_w}" height="{half_h}" fill="{_colour(b)}" data-pattern="quadrant-square-board"/>'
        f'<rect x="{x + half_w}" y="{y + half_h}" width="{half_w}" height="{half_h}" fill="{_colour(a)}" data-pattern="quadrant-square-board"/>'
        + _frame()
    )


def _horizontal(asset: str, colours: list[str]) -> str:
    return standard_repair_batch49._horizontal(asset, colours)


def _compound_horizontal_nested(asset: str) -> str:
    x, y, w, h = BOARD["x"], BOARD["y"], BOARD["w"], BOARD["h"]
    band_h = h / 3
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{band_h:.1f}" fill="{_colour("green")}" data-pattern="compound-horizontal-square-board"/>'
        f'<rect x="{x}" y="{y + band_h:.1f}" width="{w}" height="{band_h:.1f}" fill="{_colour("red")}" data-pattern="compound-horizontal-square-board"/>'
        f'<rect x="{x}" y="{y + band_h * 2:.1f}" width="{w}" height="{band_h:.1f}" fill="{_colour("green")}" data-pattern="compound-horizontal-square-board"/>'
        f'<rect x="{x + 6}" y="{y + 6}" width="{w - 12}" height="{h - 12}" fill="{_colour("white")}" data-pattern="nested-square-board"/>'
        f'<rect x="{x + 10}" y="{y + 10}" width="{w - 20}" height="{h - 20}" fill="{_colour("green")}" data-pattern="nested-square-board"/>'
        + _frame()
    )


PATTERNS: dict[str, tuple[str, list[str]]] = {
    "TOPSHP25": ("nested", ["white", "orange"]),
    "TOPSHP29": ("nested", ["red", "green", "red"]),
    "TOPSHP30": ("nested", ["green", "white", "yellow"]),
    "TOPSHP31": ("nested", ["orange", "white"]),
    "TOPSHP33": ("nested", ["green", "red", "green"]),
    "TOPSHP37": ("nested", ["black", "white", "black"]),
    "TOPSHP38": ("quadrant", ["orange", "white"]),
    "TOPSHP40": ("nested", ["white", "black", "white"]),
    "TOPSHP41": ("horizontal", ["orange", "white", "orange"]),
    "TOPSHP43": ("compound", ["green", "red", "green"]),
    "TOPSHP44": ("nested", ["yellow", "white", "yellow"]),
}


def _body(asset: str) -> str:
    pattern, colours = PATTERNS[asset]
    if pattern == "nested":
        return _nested(asset, colours)
    if pattern == "quadrant":
        return _quadrant(asset, colours)
    if pattern == "horizontal":
        return _horizontal(asset, colours)
    if pattern == "compound":
        return _compound_horizontal_nested(asset)
    raise KeyError(pattern)


def _svg(asset: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch50">'
        f"<title>{asset} TOPSHP nested-pattern square board repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{_body(asset)}</g></svg>\n"
    )


def _render_svg(svg: str, asset: str, palette: str) -> str:
    standard_repair_batch49._ensure_cairo_library()
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _source_rows() -> dict[str, dict]:
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


def _judge_rows() -> dict[str, dict]:
    data = json.loads(JUDGE_FILE.read_text())
    return {row.get("asset") or row["symbol_id"]: row for row in data.get("verdicts", [])}


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
            "queue_action": "standard_judge_batch_057_failure_consumed",
            "risk_bucket": "topshp_nested_pattern_repair_batch58",
            "candidate_strategy": "judge57_nested_square_board_owned_redraw",
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
                "source_priority_basis": "standard_judge_batch_057_rerun nested-pattern feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch50",
                "reference_role": "judge57 required_change drives nested/bordered TOPSHP square-board repair semantics",
            },
            "source_judge": "catalog/standard_judge_batch_057_rerun.json",
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
        "# Standard Repair Batch 50 / Owned Repair Batch 58",
        "",
        "Targeted nested/bordered square-board redraws for the TOPSHP failures from `standard_judge_batch_057_rerun`.",
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
