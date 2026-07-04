"""Generate owned candidates for the final reference-backed line/pattern rows.

Batch 90 clears the remaining no-candidate line-style and pattern rows that
have real local OpenCPN reference renders. These candidates enter pending judge;
none are approved by this step.

Run:
  python3 -m forge.standard_generate_batch90 --render
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
OUT = ROOT / "out" / "standard_generate_batch90"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch90"
REPORT = CATALOG / "owned_repair_batch90.json"
SUMMARY = CATALOG / "owned_repair_batch90.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "RCRTCL14": "regulated_recommended_one_way_fixed",
    "RECDEF02": "recommended_track_undefined",
    "RECTRC09": "recommended_two_way_free",
    "RECTRC10": "recommended_two_way_fixed",
    "RECTRC11": "recommended_one_way_free",
    "RECTRC12": "recommended_one_way_fixed",
    "RESARE51": "restricted_area_boundary",
    "SCLBDY51": "scale_boundary_double_line",
    "SNDWAV01": "sand_waves_pattern",
    "TIDINF51": "tidal_information_boundary",
    "TSSJCT02": "tss_junction_pattern",
    "VEGATN03": "wooded_area_pattern",
    "VEGATN04": "mangrove_pattern",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-generate-batch90">'
        f"<title>{asset} line/pattern candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _line(colour: str = "black", width: float = 1.8, dash: str | None = None, arrows: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    parts = [f'<path d="M10 32 H54" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>']
    if arrows in {"one", "two"}:
        parts.append(f'<path d="M46 24 L54 32 L46 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>')
    if arrows == "two":
        parts.append(f'<path d="M18 24 L10 32 L18 40" fill="none" stroke="{_colour(colour)}" stroke-width="{width:g}"/>')
    return "".join(parts)


def _recommended(label: str, arrows: str | None, fixed: bool) -> str:
    dash = None if fixed else "8 5"
    return (
        _line("magenta", 1.8, dash, arrows)
        + f'<text x="32" y="25" text-anchor="middle" font-size="7" '
        + f'font-family="Arial, Helvetica, sans-serif" fill="{_colour("magenta")}" stroke="none">{label}</text>'
    )


def _restricted_area() -> str:
    return (
        _line("magenta", 1.8, "6 5")
        + f'<text x="32" y="25" text-anchor="middle" font-size="7" font-family="Arial, Helvetica, sans-serif" '
        + f'font-weight="700" fill="{_colour("magenta")}" stroke="none">R</text>'
    )


def _scale_boundary() -> str:
    return (
        f'<path d="M22 14 V50 M30 14 V50" fill="none" stroke="{_colour("magenta")}" stroke-width="1.6"/>'
        f'<path d="M38 14 V50" fill="none" stroke="{_colour("magenta")}" stroke-width="1.6" stroke-dasharray="5 5"/>'
    )


def _sand_waves() -> str:
    return "".join(
        f'<path d="M14 {y} C20 {y-7} 26 {y+7} 32 {y} C38 {y-7} 44 {y+7} 50 {y}" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="1.6"/>'
        for y in (22, 34, 46)
    )


def _tss_junction() -> str:
    return (
        f'<path d="M18 20 H46 M18 44 H46" fill="none" stroke="{_colour("magenta")}" stroke-width="1.7" stroke-dasharray="8 5"/>'
        f'<path d="M24 20 L40 44 M40 20 L24 44" fill="none" stroke="{_colour("magenta")}" stroke-width="1.7"/>'
        f'<circle cx="32" cy="32" r="5" fill="none" stroke="{_colour("magenta")}" stroke-width="1.5"/>'
    )


def _wooded() -> str:
    parts = []
    for x, y in ((20, 36), (32, 28), (44, 36)):
        parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="{_colour("green")}" stroke-width="1.6"/>')
        parts.append(f'<path d="M{x} {y+6} V48" fill="none" stroke="{_colour("brown")}" stroke-width="1.5"/>')
    return "".join(parts)


def _mangrove() -> str:
    parts = []
    for x in (19, 31, 43):
        parts.append(f'<path d="M{x} 47 V28 M{x} 37 L{x-6} 45 M{x} 37 L{x+6} 45" fill="none" stroke="{_colour("green")}" stroke-width="1.6"/>')
        parts.append(f'<path d="M{x-5} 30 Q{x} 22 {x+5} 30" fill="none" stroke="{_colour("green")}" stroke-width="1.6"/>')
    return "".join(parts)


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "regulated_recommended_one_way_fixed":
        return _recommended("RR", "one", True)
    if kind == "recommended_track_undefined":
        return _recommended("RT", None, False)
    if kind == "recommended_two_way_free":
        return _recommended("RT", "two", False)
    if kind == "recommended_two_way_fixed":
        return _recommended("RT", "two", True)
    if kind == "recommended_one_way_free":
        return _recommended("RT", "one", False)
    if kind == "recommended_one_way_fixed":
        return _recommended("RT", "one", True)
    if kind == "restricted_area_boundary":
        return _restricted_area()
    if kind == "scale_boundary_double_line":
        return _scale_boundary()
    if kind == "sand_waves_pattern":
        return _sand_waves()
    if kind == "tidal_information_boundary":
        return _recommended("T", None, False)
    if kind == "tss_junction_pattern":
        return _tss_junction()
    if kind == "wooded_area_pattern":
        return _wooded()
    if kind == "mangrove_pattern":
        return _mangrove()
    raise KeyError(f"unsupported batch90 target: {asset}")


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
            raise RuntimeError(f"{asset} has no OpenCPN reference image; refusing batch90 generation")
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
            "risk_bucket": "line_pattern_no_candidate_batch90",
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
                "generator": "forge.standard_generate_batch90",
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
        "# Standard Generate Batch 90 / Owned Repair Batch 90",
        "",
        "Final generated-owned candidate batch for reference-backed no-candidate line-style and pattern rows.",
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
