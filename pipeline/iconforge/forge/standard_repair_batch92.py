"""Repair the first generated line/pattern judge failures into owned batch 92.

Run:
  python3 -m forge.standard_repair_batch92 --render
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
OUT = ROOT / "out" / "standard_repair_batch92"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch92"
REPORT = CATALOG / "owned_repair_batch92.json"
SUMMARY = CATALOG / "owned_repair_batch92.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "CBLSUB06": "submarine_cable_wavy_line",
    "CLRLIN01": "clearing_line_orange_arrowhead",
    "CROSSX02": "small_cross_grid_pattern",
    "DIAMOND1": "diamond_cluster_pattern",
    "DQUALA11": "survey_quality_a_triangle_pattern",
    "DQUALA21": "survey_quality_a2_triangle_pattern",
    "DQUALB01": "survey_quality_b_bar_pattern",
    "DQUALC01": "survey_quality_c_cross_pattern",
    "DQUALD01": "survey_quality_d_dashed_triangle",
    "DQUALU01": "survey_quality_unknown_capsule",
    "DWLDEF01": "deep_water_route_undefined",
    "DWRTCL05": "deep_water_route_two_way_free",
    "DWRTCL06": "deep_water_route_two_way_fixed",
    "DWRTCL07": "deep_water_route_one_way_free",
    "DWRTCL08": "deep_water_route_one_way_fixed",
    "ERBLNA01": "electronic_bearing_line_dash",
    "ERBLNB01": "electronic_bearing_line_dash_dot",
    "FERYRT01": "ferry_route_symbol_line",
    "FERYRT02": "cable_ferry_route_symbol_line",
    "FOULAR01": "foul_area_cross_pattern",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch92">'
        f"<title>{asset} line/pattern repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 1.8, fill: str = "none", dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'


def _line(y: int = 32, x1: int = 12, x2: int = 52, colour: str = "magenta", dash: str | None = None, width: float = 1.7) -> str:
    return _path(f"M{x1} {y} H{x2}", colour=colour, width=width, dash=dash)


def _arrow(x: int, y: int, direction: str, colour: str = "magenta") -> str:
    if direction == "right":
        return _path(f"M{x-6} {y-6} L{x} {y} L{x-6} {y+6}", colour=colour, width=1.7)
    return _path(f"M{x+6} {y-6} L{x} {y} L{x+6} {y+6}", colour=colour, width=1.7)


def _text(text: str, x: int, y: int, colour: str = "magenta", size: int = 6) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" fill="{_colour(colour)}" stroke="none">{text}</text>'
    )


def _diamond(cx: int, cy: int, r: int = 4, colour: str = "black", fill: str = "none") -> str:
    return f'<path d="M{cx} {cy-r} L{cx+r} {cy} L{cx} {cy+r} L{cx-r} {cy} Z" fill="{fill}" stroke="{_colour(colour)}" stroke-width="1.4"/>'


def _plus(cx: int, cy: int, colour: str = "grey", width: float = 1.25) -> str:
    return _path(f"M{cx-4} {cy} H{cx+4} M{cx} {cy-4} V{cy+4}", colour=colour, width=width)


def _triangle(cx: int, cy: int, colour: str = "grey", dash: str | None = None) -> str:
    return _path(f"M{cx} {cy-6} L{cx+7} {cy+6} L{cx-7} {cy+6} Z", colour=colour, width=1.35, dash=dash)


def _deep_water_route(label: str, arrows: str | None, fixed: bool) -> str:
    dash = None if fixed else "7 5"
    parts = [_line(32, 13, 51, "magenta", dash=dash, width=1.5)]
    if arrows in {"left", "two"}:
        parts.append(_arrow(18, 32, "left"))
    if arrows in {"right", "two"}:
        parts.append(_arrow(46, 32, "right"))
    if label:
        parts.append(_text(label, 32, 27, "magenta", 6))
    return "".join(parts)


def _body(asset: str) -> str:
    if asset == "CBLSUB06":
        return _path("M12 33 C17 27 22 39 27 33 C32 27 37 39 42 33 C47 27 52 39 57 33", "magenta", 1.55)
    if asset == "CLRLIN01":
        return '<path d="M32 17 L43 43 L21 43 Z" fill="var(--orange)" stroke="var(--orange)" stroke-width="1.2"/>'
    if asset == "CROSSX02":
        return "".join(_plus(x, y, "brown", 1.05) for y in (24, 32, 40) for x in (24, 32, 40))
    if asset == "DIAMOND1":
        return "".join(_diamond(x, y, 4) for x, y in ((25, 25), (39, 25), (25, 39), (39, 39)))
    if asset == "DQUALA11":
        return _triangle(24, 29, "grey") + _triangle(40, 29, "grey") + _plus(32, 42, "grey", 1.1)
    if asset == "DQUALA21":
        return _triangle(24, 28, "grey") + _triangle(40, 28, "grey") + _line(43, 24, 40, "grey", width=1.3)
    if asset == "DQUALB01":
        return "".join(_line(y, 22, 42, "black", width=1.35) for y in (26, 32, 38))
    if asset == "DQUALC01":
        return "".join(_plus(x, 32, "grey", 1.15) for x in (22, 32, 42))
    if asset == "DQUALD01":
        return _triangle(32, 32, "black", dash="3 3")
    if asset == "DQUALU01":
        return '<rect x="19" y="26" width="26" height="12" rx="6" fill="none" stroke="var(--gray)" stroke-width="1.35"/>'
    if asset == "DWLDEF01":
        return _deep_water_route("DW", None, False)
    if asset == "DWRTCL05":
        return _deep_water_route("DW", "two", False)
    if asset == "DWRTCL06":
        return _deep_water_route("DW", "two", True)
    if asset == "DWRTCL07":
        return _deep_water_route("DW", "right", False)
    if asset == "DWRTCL08":
        return _deep_water_route("DW", "right", True)
    if asset == "ERBLNA01":
        return _line(32, 13, 51, "orange", dash="12 6", width=1.5)
    if asset == "ERBLNB01":
        return _line(32, 13, 51, "orange", dash="12 5 2 5", width=1.5)
    if asset == "FERYRT01":
        return _line(32, 13, 51, "magenta", dash="10 6", width=1.45) + _text("F", 32, 29, "magenta", 7)
    if asset == "FERYRT02":
        return _line(32, 13, 51, "grey", dash="10 6", width=1.45) + '<rect x="26" y="27" width="12" height="8" fill="none" stroke="var(--gray)" stroke-width="1.4"/>'
    if asset == "FOULAR01":
        return "".join(_path(f"M{x-4} {y-4} L{x+4} {y+4} M{x+4} {y-4} L{x-4} {y+4}", "grey", 1.25) for x, y in ((24, 26), (40, 26), (32, 40)))
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
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


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
        raise RuntimeError("no batch92 rows in standard repair queue")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
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
            "queue_action": "standard_line_pattern_failure_consumed",
            "risk_bucket": "line_pattern_repair_batch92",
            "candidate_strategy": f"owned_{TARGETS[asset]}_redraw_from_provider_witness",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": "catalog/standard_judge_batch_088_091_initial.json",
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_judge_batch_088_091_initial repair feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch92",
                "reference_role": "OpenCPN/Aqua Map witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 92 / Owned Repair Batch 92",
        "",
        "First repair slice for generated line/pattern visual-judge failures.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Repair |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | `{TARGETS[row['asset']]}` |")
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
