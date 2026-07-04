"""Repair remaining OpenCPN-backed line/pattern failures into owned batch 94.

Run:
  python3 -m forge.standard_repair_batch94 --render
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
OUT = ROOT / "out" / "standard_repair_batch94"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch94"
REPORT = CATALOG / "owned_repair_batch94.json"
SUMMARY = CATALOG / "owned_repair_batch94.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
SOURCE_JUDGE = "catalog/standard_judge_batch_088_091_initial.json"

TARGETS = {
    "FSHFAC04": "fish_trap_small_tick_pattern",
    "FSHHAV02": "fish_haven_small_fish_pattern",
    "HODATA01": "ho_data_boundary_kink_line",
    "ICEARE04": "ice_area_sparse_slash_pattern",
    "LOWACC41": "low_accuracy_rectangle_boundary",
    "MARSHES1": "marsh_small_reed_pattern",
    "MARSYS51": "iala_boundary_a_b_line",
    "NAVARE51": "navigation_area_v_line",
    "NODATA03": "no_data_single_line",
    "OVERSC01": "overscale_single_vertical_line",
    "PASTRK01": "past_track_time_mark",
    "PIPARE51": "dangerous_pipeline_area_wave_line",
    "PIPARE61": "pipeline_area_grey_wave_line",
    "PIPSOL05": "pipeline_oil_circle_line",
    "PIPSOL06": "pipeline_water_circle_line",
    "PLNRTE03": "planned_route_red_ring",
    "PRTSUR01": "incompletely_surveyed_single_line",
    "RCKLDG01": "rock_ledge_small_chevron_pattern",
    "RCRDEF01": "regulated_recommended_route_unknown",
    "RCRTCL11": "regulated_two_way_free",
    "RCRTCL12": "regulated_one_way_free",
    "RCRTCL13": "regulated_two_way_fixed",
    "RCRTCL14": "regulated_one_way_fixed",
    "RECDEF02": "recommended_track_unknown",
    "RECTRC09": "recommended_two_way_free",
    "RECTRC10": "recommended_two_way_fixed",
    "RECTRC11": "recommended_one_way_free",
    "RECTRC12": "recommended_one_way_fixed",
    "RESARE51": "restricted_area_t_boundary",
    "SCLBDY51": "scale_boundary_double_line",
    "SNDWAV01": "sand_waves_small_wave_pattern",
    "TIDINF51": "tidal_information_tick_line",
    "TSSJCT02": "traffic_scheme_diagonal_line",
    "VEGATN03": "wooded_area_tree_pattern",
    "VEGATN04": "mangrove_round_tree_pattern",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch94">'
        f"<title>{asset} OpenCPN-backed line/pattern repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "gray", width: float = 1.0, fill: str = "none", dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'


def _line(x1: float, y1: float, x2: float, y2: float, colour: str = "gray", width: float = 1.0, dash: str | None = None) -> str:
    return _path(f"M{x1:g} {y1:g} L{x2:g} {y2:g}", colour, width, dash=dash)


def _text(text: str, x: float, y: float, colour: str = "gray", size: float = 5.0) -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" text-anchor="middle" font-size="{size:g}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="500" '
        f'fill="{_colour(colour)}" stroke="none">{text}</text>'
    )


def _chevron(cx: float, cy: float, colour: str = "gray", width: float = 0.9) -> str:
    return _path(f"M{cx-3:g} {cy-3:g} L{cx:g} {cy:g} L{cx+3:g} {cy-3:g}", colour, width)


def _wave(x1: float, y: float, x2: float, colour: str, width: float = 1.0) -> str:
    return _path(
        f"M{x1:g} {y:g} C{x1+4:g} {y-4:g} {x1+8:g} {y+4:g} {x1+12:g} {y:g} "
        f"C{x1+16:g} {y-4:g} {x1+20:g} {y+4:g} {x1+24:g} {y:g} "
        f"C{x1+28:g} {y-4:g} {x1+32:g} {y+4:g} {x2:g} {y:g}",
        colour,
        width,
    )


def _arrow(cx: float, cy: float, direction: str, colour: str = "magenta") -> str:
    if direction == "right":
        return _line(cx - 5, cy - 3, cx, cy, colour, 0.9) + _line(cx - 5, cy + 3, cx, cy, colour, 0.9)
    return _line(cx + 5, cy - 3, cx, cy, colour, 0.9) + _line(cx + 5, cy + 3, cx, cy, colour, 0.9)


def _route(colour: str, *, dash: str | None, one_way: bool = False, unknown: bool = False, label: str = "") -> str:
    body = _line(18, 33, 48, 33, colour, 1.0, dash)
    if unknown:
        body += _arrow(22, 33, "left", colour) + _text("?", 31, 35.5, colour, 5.0)
    elif one_way:
        body += _arrow(46, 33, "right", colour)
    else:
        body += _arrow(20, 33, "left", colour) + _arrow(46, 33, "right", colour)
    if label:
        body += _text(label, 56, 35.5, colour, 5.0)
    return body


def _body(asset: str) -> str:
    if asset == "FSHFAC04":
        return "".join(_line(x, 38, x + 5, 29, "gray", 0.9) + _line(x + 5, 29, x + 10, 38, "gray", 0.9) for x in (18, 31))
    if asset == "FSHHAV02":
        return _path("M22 33 C27 27 38 27 43 33 C38 39 27 39 22 33 Z M43 33 L49 29 M43 33 L49 37", "gray", 0.9)
    if asset == "HODATA01":
        return _line(16, 43, 32, 25, "gray", 1.0) + _line(32, 25, 50, 25, "gray", 1.0)
    if asset == "ICEARE04":
        return "".join(_line(x, y, x + 4, y + 7, "gray", 0.9) for x, y in ((20, 24), (33, 21), (44, 28), (25, 40), (39, 42)))
    if asset == "LOWACC41":
        return '<rect x="19" y="23" width="26" height="18" fill="none" stroke="var(--gray)" stroke-width="1"/>'
    if asset == "MARSHES1":
        return "".join(_line(x, 39, x, 29, "yellow", 1.0) + _line(x, 35, x - 4, 31, "yellow", 0.9) + _line(x, 35, x + 4, 31, "yellow", 0.9) for x in (25, 32, 39))
    if asset == "MARSYS51":
        return _line(16, 33, 48, 33, "gray", 0.9, "5 4") + _text("A", 24, 30, "gray", 4.6) + _text("B", 41, 30, "gray", 4.6)
    if asset == "NAVARE51":
        return _line(18, 29, 32, 39, "gray", 0.95) + _line(32, 39, 46, 29, "gray", 0.95)
    if asset == "NODATA03":
        return _line(18, 33, 46, 33, "gray", 1.0)
    if asset == "OVERSC01":
        return _line(32, 19, 32, 45, "gray", 1.0)
    if asset == "PASTRK01":
        return _line(32, 22, 32, 42, "gray", 0.9) + _line(24, 32, 40, 32, "gray", 0.9)
    if asset == "PIPARE51":
        return _wave(16, 33, 50, "magenta", 1.0)
    if asset == "PIPARE61":
        return _wave(16, 33, 50, "gray", 1.0)
    if asset == "PIPSOL05":
        return _line(15, 33, 28, 33, "magenta", 1.0) + '<circle cx="36" cy="33" r="6" fill="none" stroke="var(--magenta)" stroke-width="1"/>' + _line(42, 33, 50, 33, "magenta", 1.0)
    if asset == "PIPSOL06":
        return _line(15, 33, 28, 33, "gray", 1.0) + '<circle cx="36" cy="33" r="5" fill="none" stroke="var(--gray)" stroke-width="1"/>' + _line(41, 33, 50, 33, "gray", 1.0)
    if asset == "PLNRTE03":
        return '<circle cx="32" cy="32" r="13" fill="none" stroke="var(--red)" stroke-width="1"/>'
    if asset == "PRTSUR01":
        return _line(18, 33, 46, 33, "gray", 0.9)
    if asset == "RCKLDG01":
        return "".join(_chevron(x, y, "orange", 0.9) for x, y in ((23, 26), (35, 25), (45, 32), (28, 41), (40, 43)))
    if asset == "RCRDEF01":
        return _route("magenta", dash="5 4", unknown=True, label="R")
    if asset == "RCRTCL11":
        return _route("magenta", dash="5 4", label="R")
    if asset == "RCRTCL12":
        return _route("magenta", dash="5 4", one_way=True, label="R")
    if asset == "RCRTCL13":
        return _route("magenta", dash=None, label="R")
    if asset == "RCRTCL14":
        return _route("magenta", dash=None, one_way=True, label="R")
    if asset == "RECDEF02":
        return _route("gray", dash="5 4", unknown=True)
    if asset == "RECTRC09":
        return _route("gray", dash="5 4")
    if asset == "RECTRC10":
        return _route("gray", dash=None)
    if asset == "RECTRC11":
        return _route("gray", dash="5 4", one_way=True)
    if asset == "RECTRC12":
        return _route("gray", dash=None, one_way=True)
    if asset == "RESARE51":
        return _line(18, 28, 46, 28, "magenta", 1.0) + _line(32, 28, 32, 46, "magenta", 1.0)
    if asset == "SCLBDY51":
        return _line(18, 28, 48, 28, "blue", 0.9) + _line(18, 36, 48, 36, "blue", 0.9)
    if asset == "SNDWAV01":
        return _wave(18, 33, 48, "gray", 0.95)
    if asset == "TIDINF51":
        return _line(16, 31, 48, 31, "gray", 0.9, "5 4") + "".join(_line(x, 31, x + 3, 36, "gray", 0.75) for x in (21, 31, 41))
    if asset == "TSSJCT02":
        return _line(22, 42, 43, 21, "magenta", 1.0)
    if asset == "VEGATN03":
        return "".join(_line(x - 6, y, x + 6, y, "brown", 0.8) for x, y in ((32, 23), (32, 29), (32, 35), (32, 41))) + _line(32, 19, 32, 45, "brown", 0.8)
    if asset == "VEGATN04":
        return '<path d="M32 20 C23 26 22 40 32 45 C42 40 41 26 32 20 Z" fill="none" stroke="var(--brown)" stroke-width="0.9"/>' + _line(32, 25, 32, 45, "brown", 0.8)
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
        raise RuntimeError("no batch94 rows in standard repair queue")
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
            "queue_action": "standard_opencpn_line_pattern_failure_consumed",
            "risk_bucket": "opencpn_line_pattern_repair_batch94",
            "candidate_strategy": f"owned_{TARGETS[asset]}_literal_redraw_from_opencpn_witness",
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
                "source_priority_basis": "standard_repair_queue OpenCPN-backed line/pattern failures",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch94",
                "reference_role": "OpenCPN local line/pattern witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Owned Repair Batch 94",
        "",
        "- Source: OpenCPN-backed rows from `standard_repair_queue`",
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
