"""Generate owned candidates for the next no-candidate line/pattern rows.

Batch 89 continues the non-point-symbol lane started by batch 88. These are
first Helm-owned SVG candidates for line-style and pattern rows with real local
OpenCPN reference renders. They enter pending judge only.

Run:
  python3 -m forge.standard_generate_batch89 --render
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
OUT = ROOT / "out" / "standard_generate_batch89"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch89"
REPORT = CATALOG / "owned_repair_batch89.json"
SUMMARY = CATALOG / "owned_repair_batch89.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "FSHHAV02": "fish_haven_pattern",
    "HODATA01": "ho_data_boundary",
    "ICEARE04": "ice_area_pattern",
    "LOWACC41": "low_accuracy_danger_line",
    "MARSHES1": "marsh_pattern",
    "MARSYS51": "iala_boundary_line",
    "NAVARE51": "navigation_area_boundary",
    "NODATA03": "no_data_pattern",
    "OVERSC01": "overscale_pattern",
    "PIPARE51": "pipeline_area_dangerous_boundary",
    "PIPARE61": "pipeline_area_nondangerous_boundary",
    "PIPSOL05": "oil_gas_pipeline_line",
    "PIPSOL06": "water_pipeline_line",
    "PLNRTE03": "planned_route_line",
    "PRTSUR01": "incomplete_survey_pattern",
    "RCKLDG01": "rock_ledge_pattern",
    "RCRDEF01": "regulated_recommended_route_undefined",
    "RCRTCL11": "regulated_recommended_two_way_free",
    "RCRTCL12": "regulated_recommended_one_way_free",
    "RCRTCL13": "regulated_recommended_two_way_fixed",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-generate-batch89">'
        f"<title>{asset} line/pattern candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _line(colour: str = "black", width: float = 1.8, dash: str | None = None, arrows: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    parts = [
        f'<path d="M10 32 H54" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'
    ]
    if arrows in {"one", "two"}:
        parts.append(f'<path d="M46 24 L54 32 L46 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>')
    if arrows == "two":
        parts.append(f'<path d="M18 24 L10 32 L18 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>')
    return "".join(parts)


def _boundary(colour: str = "magenta", dash: str = "8 5", label: str | None = None) -> str:
    text = ""
    if label:
        text = (
            f'<text x="32" y="25" text-anchor="middle" font-size="7" '
            f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
            f'fill="{_colour(colour)}" stroke="none">{label}</text>'
        )
    return _line(colour, 1.8, dash) + text


def _fish_haven() -> str:
    fish = []
    for x, y in ((22, 24), (42, 25), (28, 42), (48, 43)):
        fish.append(
            f'<path d="M{x-5} {y} Q{x} {y-4} {x+6} {y} Q{x} {y+4} {x-5} {y} Z" '
            f'fill="none" stroke="{_colour("black")}" stroke-width="1.5"/>'
        )
        fish.append(f'<path d="M{x-5} {y} L{x-9} {y-4} M{x-5} {y} L{x-9} {y+4}" fill="none" stroke="{_colour("black")}" stroke-width="1.4"/>')
    return "".join(fish)


def _ice_area() -> str:
    return "".join(
        f'<path d="M{x-6} {y} H{x+6} M{x} {y-6} V{y+6} M{x-4} {y-4} L{x+4} {y+4} M{x+4} {y-4} L{x-4} {y+4}" '
        f'fill="none" stroke="{_colour("blue")}" stroke-width="1.2"/>'
        for x, y in ((22, 22), (42, 24), (30, 42))
    )


def _marsh() -> str:
    parts = []
    for x in (18, 28, 38, 48):
        parts.append(f'<path d="M{x} 45 V24 M{x} 32 L{x-5} 25 M{x} 34 L{x+5} 27" fill="none" stroke="{_colour("brown")}" stroke-width="1.6"/>')
    return "".join(parts)


def _no_data() -> str:
    return (
        f'<rect x="14" y="14" width="36" height="36" fill="none" stroke="{_colour("gray")}" stroke-width="1.5" stroke-dasharray="5 4"/>'
        f'<path d="M16 48 L48 16 M16 16 L48 48" fill="none" stroke="{_colour("gray")}" stroke-width="1.5"/>'
    )


def _overscale() -> str:
    return (
        f'<rect x="16" y="20" width="32" height="24" rx="3" fill="none" stroke="{_colour("magenta")}" stroke-width="1.7"/>'
        f'<text x="32" y="36" text-anchor="middle" font-size="12" font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="700" fill="{_colour("magenta")}" stroke="none">OS</text>'
    )


def _incomplete_survey() -> str:
    return (
        f'<path d="M15 44 H49" fill="none" stroke="{_colour("black")}" stroke-width="1.5" stroke-dasharray="4 5"/>'
        f'<path d="M20 24 H44 M24 32 H40" fill="none" stroke="{_colour("black")}" stroke-width="1.4" stroke-dasharray="2 5"/>'
        f'<text x="32" y="39" text-anchor="middle" font-size="9" font-family="Arial, Helvetica, sans-serif" fill="{_colour("black")}" stroke="none">?</text>'
    )


def _rock_ledge() -> str:
    return (
        f'<path d="M16 39 L24 25 L32 39 L40 24 L48 39" fill="none" stroke="{_colour("black")}" stroke-width="1.7"/>'
        f'<path d="M16 45 H48" fill="none" stroke="{_colour("black")}" stroke-width="1.4" stroke-dasharray="3 5"/>'
    )


def _pipeline(colour: str = "magenta", contents: str = "P") -> str:
    return (
        _line(colour, 1.9, "10 5")
        + f'<text x="32" y="27" text-anchor="middle" font-size="8" font-family="Arial, Helvetica, sans-serif" '
        + f'font-weight="700" fill="{_colour(colour)}" stroke="none">{contents}</text>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "fish_haven_pattern":
        return _fish_haven()
    if kind == "ho_data_boundary":
        return _boundary("magenta", "8 5", "HO")
    if kind == "ice_area_pattern":
        return _ice_area()
    if kind == "low_accuracy_danger_line":
        return _line("black", 1.8, "4 4") + '<path d="M28 24 L36 40 M36 24 L28 40" fill="none" stroke="var(--black)" stroke-width="1.5"/>'
    if kind == "marsh_pattern":
        return _marsh()
    if kind == "iala_boundary_line":
        return _boundary("magenta", "7 5", "A/B")
    if kind == "navigation_area_boundary":
        return _boundary("magenta", "8 4")
    if kind == "no_data_pattern":
        return _no_data()
    if kind == "overscale_pattern":
        return _overscale()
    if kind == "pipeline_area_dangerous_boundary":
        return _pipeline("magenta", "PD")
    if kind == "pipeline_area_nondangerous_boundary":
        return _pipeline("gray", "P")
    if kind == "oil_gas_pipeline_line":
        return _pipeline("magenta", "OG")
    if kind == "water_pipeline_line":
        return _pipeline("blue", "W")
    if kind == "planned_route_line":
        return _line("magenta", 1.8, "8 5", "one") + '<text x="31" y="25" text-anchor="middle" font-size="7" font-family="Arial, Helvetica, sans-serif" fill="var(--magenta)" stroke="none">RT</text>'
    if kind == "incomplete_survey_pattern":
        return _incomplete_survey()
    if kind == "rock_ledge_pattern":
        return _rock_ledge()
    if kind == "regulated_recommended_route_undefined":
        return _line("magenta", 1.8, "9 5") + '<text x="32" y="25" text-anchor="middle" font-size="7" font-family="Arial, Helvetica, sans-serif" fill="var(--magenta)" stroke="none">RR</text>'
    if kind == "regulated_recommended_two_way_free":
        return _line("magenta", 1.8, "8 5", "two")
    if kind == "regulated_recommended_one_way_free":
        return _line("magenta", 1.8, "8 5", "one")
    if kind == "regulated_recommended_two_way_fixed":
        return _line("magenta", 1.8, None, "two")
    raise KeyError(f"unsupported batch89 target: {asset}")


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


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in TARGETS:
        source_row = source_rows[asset]
        refs = source_row.get("reference_providers") or {}
        if not refs.get("opencpn_render"):
            raise RuntimeError(f"{asset} has no OpenCPN reference image; refusing batch89 generation")
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
            "queue_action": "no_helm_candidate_generated_for_judge",
            "risk_bucket": "line_pattern_no_candidate_batch89",
            "candidate_strategy": f"owned_{TARGETS[asset]}_redraw_from_opencpn_reference",
            "candidate_source": None,
            "before_svg": None,
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": "Generated first Helm-owned line/pattern candidate from S-52 metadata and local OpenCPN reference; must be judged before promotion.",
            "safety_reason_codes": ["new_candidate_pending_visual_judge"],
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": refs,
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": None,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "pending_llm_judge",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "no_helm_candidate line/pattern row with real OpenCPN reference image",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_generate_batch89",
                "reference_role": "OpenCPN line/pattern render is a local visual oracle; generated SVG remains Helm-owned candidate art",
            },
        })
    result = {
        "schema_version": 1,
        "status": "generated_batch_pending_judge",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {"generated": len(rows), "visual_parity": "pending_llm_judge", "final_approved": 0},
        "symbols": rows,
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Generate Batch 89 / Owned Repair Batch 89",
        "",
        "Second generated-owned candidate batch for no-candidate line-style and pattern rows.",
        "",
        f"- generated: `{result['summary']['generated']}`",
        "- visual_parity: `pending_llm_judge`",
        "- final_approved: `0`",
        "",
        "| Asset | Strategy |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | `{TARGETS[row['asset']]}` |")
    lines.extend(["", "Rows are candidates only; none are final-approved.", ""])
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
