"""Repair strict batch-92 line/pattern failures into owned batch 93.

Run:
  python3 -m forge.standard_repair_batch93 --render
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
OUT = ROOT / "out" / "standard_repair_batch93"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch93"
REPORT = CATALOG / "owned_repair_batch93.json"
SUMMARY = CATALOG / "owned_repair_batch93.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
SOURCE_JUDGE = "catalog/standard_judge_batch_092_rerun.json"

TARGETS = {
    "CBLSUB06": "submarine_cable_tight_zigzag_with_terminal_kink",
    "CROSSX02": "tiny_dense_cross_pattern",
    "DIAMOND1": "crossed_safety_contour_pattern",
    "DQUALA11": "survey_quality_a_triangle_stamp",
    "DQUALA21": "survey_quality_a2_triangle_stamp_with_bar",
    "DQUALB01": "survey_quality_b_triangle_stamp",
    "DQUALC01": "survey_quality_c_capsule_stamp",
    "DQUALD01": "survey_quality_d_capsule_stamp",
    "DQUALU01": "survey_quality_u_capsule_stamp",
    "DWLDEF01": "deep_water_route_undefined_small_label",
    "DWRTCL05": "deep_water_route_two_way_free_small_label",
    "DWRTCL06": "deep_water_route_two_way_fixed_small_label",
    "DWRTCL07": "deep_water_route_one_way_free_small_label",
    "DWRTCL08": "deep_water_route_one_way_fixed_small_label",
    "FERYRT01": "ferry_route_small_vessel_dash",
    "FERYRT02": "cable_ferry_route_small_box_dash",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch93">'
        f"<title>{asset} strict line/pattern repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "gray", width: float = 1.1, fill: str = "none", dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'


def _line(x1: float, y1: float, x2: float, y2: float, colour: str = "magenta", width: float = 1.1, dash: str | None = None) -> str:
    return _path(f"M{x1:g} {y1:g} L{x2:g} {y2:g}", colour=colour, width=width, dash=dash)


def _text(text: str, x: float, y: float, colour: str = "magenta", size: float = 5.4) -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" text-anchor="middle" font-size="{size:g}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="500" '
        f'fill="{_colour(colour)}" stroke="none">{text}</text>'
    )


def _tiny_star(cx: float, cy: float, colour: str = "gray") -> str:
    return (
        _line(cx - 2.2, cy, cx + 2.2, cy, colour, 0.75)
        + _line(cx, cy - 2.2, cx, cy + 2.2, colour, 0.75)
        + _line(cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6, colour, 0.65)
        + _line(cx - 1.6, cy + 1.6, cx + 1.6, cy - 1.6, colour, 0.65)
    )


def _triangle_stamp(*, bar: bool = False) -> str:
    body = _path("M20 21 H44 L32 45 Z", "gray", 1.0)
    for x, y in ((25, 28), (32, 28), (39, 28), (28.5, 36), (35.5, 36)):
        body += _tiny_star(x, y)
    if bar:
        body += _line(28, 47, 36, 47, "gray", 1.0)
    return body


def _capsule(inner: str) -> str:
    return f'<rect x="19" y="28" width="26" height="9" rx="4.5" fill="none" stroke="{_colour("gray")}" stroke-width="1"/>' + inner


def _route_base(*, dash: str | None, one_way: bool = False, unknown: bool = False) -> str:
    body = _line(16, 33, 49, 33, "magenta", 1.05, dash)
    if unknown:
        body += _line(20, 29.5, 15, 33, "magenta", 1.0) + _line(20, 36.5, 15, 33, "magenta", 1.0)
        body += _text("?", 25, 35.5, "magenta", 6)
    elif one_way:
        body += _line(21, 29.5, 27, 33, "magenta", 1.0) + _line(21, 36.5, 27, 33, "magenta", 1.0)
    else:
        body += _line(21, 29.5, 15, 33, "magenta", 1.0) + _line(21, 36.5, 15, 33, "magenta", 1.0)
        body += _line(43, 29.5, 49, 33, "magenta", 1.0) + _line(43, 36.5, 49, 33, "magenta", 1.0)
    body += _text("DW", 55, 35.5, "magenta", 5.3)
    return body


def _ferry(colour: str, box_width: float, box_height: float) -> str:
    y = 33
    body = _line(14, y, 24, y, colour, 1.15, "6 5") + _line(40, y, 51, y, colour, 1.15, "6 5")
    body += f'<rect x="{32 - box_width / 2:g}" y="{y - box_height / 2:g}" width="{box_width:g}" height="{box_height:g}" rx="1" fill="none" stroke="{_colour(colour)}" stroke-width="1"/>'
    return body


def _body(asset: str) -> str:
    if asset == "CBLSUB06":
        return _path("M16 32 L20 29 L24 32 L28 29 L32 32 L36 29 L40 32 L44 29 L48 32 M49 29 L53 33", "magenta", 1.1)
    if asset == "CROSSX02":
        return "".join(_tiny_star(x, y, "brown") for y in (28, 31, 34, 37) for x in (28, 31, 34, 37))
    if asset == "DIAMOND1":
        return _line(23, 18, 41, 46, "gray", 1.05) + _line(41, 18, 23, 46, "gray", 1.05)
    if asset in {"DQUALA11", "DQUALB01"}:
        return _triangle_stamp()
    if asset == "DQUALA21":
        return _triangle_stamp(bar=True)
    if asset == "DQUALC01":
        return _capsule(_tiny_star(25, 32.5) + _tiny_star(32, 32.5) + _tiny_star(39, 32.5))
    if asset == "DQUALD01":
        return _capsule(_tiny_star(27.5, 32.5) + _tiny_star(36.5, 32.5))
    if asset == "DQUALU01":
        return _capsule(_text("U", 32, 35.2, "gray", 5.0))
    if asset == "DWLDEF01":
        return _route_base(dash="5 4", unknown=True)
    if asset == "DWRTCL05":
        return _route_base(dash="5 4")
    if asset == "DWRTCL06":
        return _route_base(dash=None)
    if asset == "DWRTCL07":
        return _route_base(dash="5 4", one_way=True)
    if asset == "DWRTCL08":
        return _route_base(dash=None, one_way=True)
    if asset == "FERYRT01":
        return _ferry("magenta", 8, 4)
    if asset == "FERYRT02":
        return _ferry("gray", 7, 6)
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
        raise RuntimeError("no batch93 rows in standard repair queue")
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
            "queue_action": "standard_line_pattern_strict_failure_consumed",
            "risk_bucket": "line_pattern_repair_batch93",
            "candidate_strategy": f"owned_{TARGETS[asset]}_literal_redraw_from_provider_witness",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": SOURCE_JUDGE,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_judge_batch_092_rerun strict repair feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch93",
                "reference_role": "OpenCPN line/pattern witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Owned Repair Batch 93",
        "",
        "- Source: `standard_judge_batch_092_rerun` strict failures",
        "- Status: `repair_batch_pending_judge_rerun`",
        "- Final approval: none; visual judge plus human review still required.",
        "",
        "| Asset | Strategy | After SVG | Required change |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(
            f"| `{row['asset']}` | {row['candidate_strategy']} | `{row['after_svg']}` | "
            f"{row.get('required_change') or ''} |"
        )
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
