"""Generate owned candidates for no-candidate line/pattern rows.

This batch opens the next lane after the point-symbol repair loop: S-52
line-style and area-pattern assets that have real OpenCPN visual witnesses but
no Helm SVG candidate yet. Outputs are generated-owned SVGs pending judge, not
approved art.

Run:
  python3 -m forge.standard_generate_batch88 --render
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
OUT = ROOT / "out" / "standard_generate_batch88"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch88"
REPORT = CATALOG / "owned_repair_batch88.json"
SUMMARY = CATALOG / "owned_repair_batch88.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "CBLSUB06": "submarine_cable_dash",
    "CROSSX02": "small_dot_pattern",
    "DIAMOND1": "diamond_depth_pattern",
    "DQUALA11": "quality_five_metre_full",
    "DQUALA21": "quality_twenty_metre_full",
    "DQUALB01": "quality_fifty_metre_lines",
    "DQUALC01": "quality_low_incomplete",
    "DQUALD01": "quality_unreliable",
    "DQUALU01": "quality_unassessed",
    "DWLDEF01": "deep_water_undefined",
    "DWRTCL05": "deep_water_two_way_free",
    "DWRTCL06": "deep_water_two_way_fixed",
    "DWRTCL07": "deep_water_one_way_free",
    "DWRTCL08": "deep_water_one_way_fixed",
    "ERBLNA01": "bearing_line_dash",
    "ERBLNB01": "bearing_line_dash_dot",
    "FERYRT01": "ferry_route",
    "FERYRT02": "cable_ferry_route",
    "FOULAR01": "foul_area_pattern",
    "FSHFAC04": "fish_trap_pattern",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-generate-batch88">'
        f"<title>{asset} line/pattern candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _line(colour: str = "black", width: float = 2.0, dash: str | None = None, arrows: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    parts = [
        f'<path d="M10 32 H54" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'
    ]
    if arrows in {"one", "two"}:
        parts.append(
            f'<path d="M46 24 L54 32 L46 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>'
        )
    if arrows == "two":
        parts.append(
            f'<path d="M18 24 L10 32 L18 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>'
        )
    return "".join(parts)


def _dots(colour: str = "brown") -> str:
    return "".join(
        f'<circle cx="{x}" cy="{y}" r="2" fill="{_colour(colour)}" stroke="none"/>'
        for y in (18, 32, 46)
        for x in (18, 32, 46)
    )


def _diamonds(colour: str = "gray", stroke: str = "black") -> str:
    parts = []
    for x, y in ((20, 20), (44, 20), (20, 44), (44, 44), (32, 32)):
        parts.append(
            f'<path d="M{x} {y-5} L{x+5} {y} L{x} {y+5} L{x-5} {y} Z" '
            f'fill="{_colour(colour)}" stroke="{_colour(stroke)}" stroke-width="1.4"/>'
        )
    return "".join(parts)


def _quality_marks(kind: str) -> str:
    if kind == "quality_five_metre_full":
        return _dots("black") + _line("black", 1.4, "3 5")
    if kind == "quality_twenty_metre_full":
        return _dots("black") + _line("black", 1.4, "8 5")
    if kind == "quality_fifty_metre_lines":
        return _line("black", 1.5, "7 5") + '<path d="M16 20 H48 M16 44 H48" fill="none" stroke="var(--black)" stroke-width="1.3" stroke-dasharray="5 6"/>'
    if kind == "quality_low_incomplete":
        return _diamonds("white", "black") + _line("black", 1.2, "2 7")
    if kind == "quality_unreliable":
        return '<path d="M18 46 L32 18 L46 46 Z" fill="none" stroke="var(--black)" stroke-width="1.8" stroke-dasharray="4 4"/>'
    if kind == "quality_unassessed":
        return '<text x="32" y="39" text-anchor="middle" font-size="25" font-family="Arial, Helvetica, sans-serif" font-weight="700" fill="var(--black)" stroke="none">?</text>'
    raise KeyError(kind)


def _foul_pattern() -> str:
    return (
        '<path d="M17 42 L26 24 L35 42 Z" fill="none" stroke="var(--black)" stroke-width="1.8"/>'
        '<path d="M31 42 L40 24 L49 42 Z" fill="none" stroke="var(--black)" stroke-width="1.8"/>'
        '<path d="M18 47 H48" fill="none" stroke="var(--black)" stroke-width="1.4" stroke-dasharray="3 5"/>'
    )


def _fish_trap_pattern() -> str:
    return (
        '<path d="M14 22 H50 M14 42 H50" fill="none" stroke="var(--black)" stroke-width="1.6" stroke-dasharray="7 5"/>'
        '<path d="M22 18 V46 M42 18 V46" fill="none" stroke="var(--black)" stroke-width="1.4"/>'
        '<path d="M22 32 H42" fill="none" stroke="var(--black)" stroke-width="1.4"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "submarine_cable_dash":
        return _line("magenta", 2.0, "8 5") + '<circle cx="32" cy="32" r="3" fill="var(--magenta)" stroke="none"/>'
    if kind == "small_dot_pattern":
        return _dots("brown")
    if kind == "diamond_depth_pattern":
        return _diamonds("white", "black")
    if kind.startswith("quality_"):
        return _quality_marks(kind)
    if kind == "deep_water_undefined":
        return _line("magenta", 2.0, "8 6")
    if kind == "deep_water_two_way_free":
        return _line("magenta", 2.0, "8 5", "two")
    if kind == "deep_water_two_way_fixed":
        return _line("magenta", 2.0, None, "two")
    if kind == "deep_water_one_way_free":
        return _line("magenta", 2.0, "8 5", "one")
    if kind == "deep_water_one_way_fixed":
        return _line("magenta", 2.0, None, "one")
    if kind == "bearing_line_dash":
        return _line("black", 1.8, "8 6")
    if kind == "bearing_line_dash_dot":
        return _line("black", 1.8, "8 4 2 4")
    if kind == "ferry_route":
        return _line("black", 2.0, "10 6") + '<path d="M24 25 H40 L36 39 H28 Z" fill="none" stroke="var(--black)" stroke-width="1.7"/>'
    if kind == "cable_ferry_route":
        return _line("black", 2.0, "5 5") + '<path d="M23 25 H41 L36 39 H28 Z" fill="none" stroke="var(--black)" stroke-width="1.7"/>'
    if kind == "foul_area_pattern":
        return _foul_pattern()
    if kind == "fish_trap_pattern":
        return _fish_trap_pattern()
    raise KeyError(f"unsupported batch88 target: {asset}")


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
            raise RuntimeError(f"{asset} has no OpenCPN reference image; refusing batch88 generation")
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
            "risk_bucket": "line_pattern_no_candidate_batch88",
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
                "generator": "forge.standard_generate_batch88",
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
        "summary": {
            "generated": len(rows),
            "visual_parity": "pending_llm_judge",
            "final_approved": 0,
        },
        "symbols": rows,
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Generate Batch 88 / Owned Repair Batch 88",
        "",
        "First generated-owned candidates for no-candidate line-style and pattern rows.",
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
