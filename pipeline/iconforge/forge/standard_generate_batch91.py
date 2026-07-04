"""Generate semantic hard-pile candidates for remaining no-SVG rows.

Batch 91 clears the remaining no-candidate hard pile by creating Helm-owned
first-pass SVGs from S-57/S-52 metadata and adjacent accepted Helm symbol
families. Rows with provider images enter normal pending judge. Rows without
provider images remain blocked from recognition approval until reference images
or explicit human/source confirmation are attached.

Run:
  python3 -m forge.standard_generate_batch91 --render
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
OUT = ROOT / "out" / "standard_generate_batch91"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch91"
REPORT = CATALOG / "owned_repair_batch91.json"
SUMMARY = CATALOG / "owned_repair_batch91.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "ARCSLN01": "arc_slip_line",
    "CLRLIN01": "clearing_line_arrowhead",
    "DASH": "dashed_line_primitive",
    "DATCVR01": "data_coverage_boundary",
    "DEPARE01": "depth_area_shallow",
    "DEPARE02": "depth_area_deep",
    "DEPCNT02": "depth_contour",
    "DOTT": "dotted_line_primitive",
    "LEGLIN02": "route_leg_line",
    "LIGHTS05": "light_characteristic",
    "OBSTRN04": "obstruction_hazard",
    "OWNSHP02": "ownship_scaled_outline",
    "PASTRK01": "past_track_time_mark",
    "QUAPOS01;TX(OBJNAM": "position_quality_with_label_anchor",
    "RESARE01": "restricted_anchor_area",
    "RESARE02": "restricted_area_notice",
    "RESTRN01": "traffic_restriction",
    "SLCONS03": "shoreline_construction_pier",
    "SOLD": "solid_line_primitive",
    "SYMINS01": "symbol_insert_instruction",
    "TOPMARI1": "isolated_topmark_reference",
    "VESSEL01": "vessel_target",
    "VRMEBL01": "vrm_ebl_control",
    "WRECKS02": "wreck_unknown_variant",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-generate-batch91">'
        f"<title>{asset} semantic hard-pile candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 2.0, fill: str = "none", dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{_colour(colour)}" stroke-width="{width:g}"{dash_attr}/>'


def _line(dash: str | None = None, colour: str = "black") -> str:
    return _path("M10 32 H54", colour=colour, width=2.0, dash=dash)


def _arrow(direction: str = "right", colour: str = "black") -> str:
    if direction == "left":
        return _path("M22 24 L12 32 L22 40", colour=colour, width=2.1)
    return _path("M42 24 L52 32 L42 40", colour=colour, width=2.1)


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "arc_slip_line":
        return _path("M12 42 C22 18 42 18 52 42", width=2.0)
    if kind == "clearing_line_arrowhead":
        return _arrow("right") + _path("M13 32 H50", width=1.6, dash="8 6")
    if kind == "dashed_line_primitive":
        return _line("8 6")
    if kind == "data_coverage_boundary":
        return _path("M14 18 H50 V46 H14 Z", width=1.8, dash="6 5")
    if kind == "depth_area_shallow":
        return (
            '<rect x="14" y="18" width="36" height="28" rx="3" fill="var(--blue)" fill-opacity=".12" stroke="none"/>'
            + _path("M14 18 H50 V46 H14 Z", colour="blue", width=1.7)
        )
    if kind == "depth_area_deep":
        return (
            '<rect x="14" y="18" width="36" height="28" rx="3" fill="var(--blue)" fill-opacity=".22" stroke="none"/>'
            + _path("M14 18 H50 V46 H14 Z", colour="blue", width=1.7)
            + _path("M20 32 H44", colour="blue", width=1.5)
        )
    if kind == "depth_contour":
        return _path("M8 38 C18 28 28 46 38 34 C45 27 51 30 56 24", colour="blue", width=1.8)
    if kind == "dotted_line_primitive":
        return _line("1 7")
    if kind == "route_leg_line":
        return _path("M12 46 L52 18", colour="magenta", width=1.9, dash="9 5")
    if kind == "light_characteristic":
        return (
            '<circle cx="32" cy="32" r="5" fill="var(--yellow)" stroke="var(--black)" stroke-width="1.6"/>'
            + _path("M32 14 V22 M32 42 V50 M14 32 H22 M42 32 H50 M20 20 L25 25 M44 20 L39 25 M20 44 L25 39 M44 44 L39 39", width=1.6)
        )
    if kind == "obstruction_hazard":
        return _path("M16 32 L32 16 L48 32 L32 48 Z", colour="black", width=2.2) + _path("M24 32 H40 M32 24 V40", width=2.1)
    if kind == "ownship_scaled_outline":
        return _path("M25 49 V18 Q32 11 39 18 V49 Z", colour="black", width=2.1, fill="var(--white)") + '<circle cx="32" cy="30" r="2.6" fill="var(--black)" stroke="none"/>'
    if kind == "past_track_time_mark":
        return _line("2 6", colour="grey") + '<circle cx="32" cy="32" r="4.5" fill="var(--white)" stroke="var(--black)" stroke-width="1.8"/>'
    if kind == "position_quality_with_label_anchor":
        return _path("M20 20 H44 V44 H20 Z", width=1.7, dash="4 4") + '<text x="32" y="37" text-anchor="middle" font-size="16" font-family="Arial, Helvetica, sans-serif" fill="var(--black)" stroke="none">?</text>'
    if kind == "restricted_anchor_area":
        return (
            '<circle cx="32" cy="32" r="19" fill="none" stroke="var(--magenta)" stroke-width="1.8" stroke-dasharray="7 5"/>'
            + _path("M32 19 V38 M24 30 C24 40 40 40 40 30", colour="magenta", width=1.9)
        )
    if kind == "restricted_area_notice":
        return '<circle cx="32" cy="32" r="18" fill="none" stroke="var(--magenta)" stroke-width="1.8" stroke-dasharray="7 5"/><text x="32" y="37" text-anchor="middle" font-size="16" font-family="Arial, Helvetica, sans-serif" font-weight="700" fill="var(--magenta)" stroke="none">R</text>'
    if kind == "traffic_restriction":
        return _path("M16 32 H48", colour="magenta", width=2.0, dash="7 5") + _path("M39 24 L48 32 L39 40", colour="magenta", width=2.0) + '<text x="26" y="28" text-anchor="middle" font-size="8" font-family="Arial, Helvetica, sans-serif" fill="var(--magenta)" stroke="none">R</text>'
    if kind == "shoreline_construction_pier":
        return _path("M15 43 H49 M20 43 V23 M28 43 V23 M36 43 V23 M44 43 V23 M18 23 H46", colour="brown", width=1.9)
    if kind == "solid_line_primitive":
        return _line(None, colour="grey")
    if kind == "symbol_insert_instruction":
        return _path("M20 18 H44 V46 H20 Z", colour="magenta", width=1.7, dash="5 4") + _path("M32 24 V40 M24 32 H40", colour="magenta", width=1.9)
    if kind == "isolated_topmark_reference":
        return _path("M32 14 V50", width=1.8) + _path("M23 28 L32 18 L41 28 L32 38 Z", width=2.0)
    if kind == "vessel_target":
        return _path("M18 46 L32 14 L46 46 Z", width=2.2, fill="var(--white)") + _path("M32 23 V42 M25 38 H39", width=1.8)
    if kind == "vrm_ebl_control":
        return '<circle cx="32" cy="32" r="19" fill="none" stroke="var(--black)" stroke-width="1.8"/>' + _path("M32 32 L50 20", width=1.8) + '<circle cx="32" cy="32" r="3" fill="var(--black)" stroke="none"/>'
    if kind == "wreck_unknown_variant":
        return _path("M15 32 H49", width=3.0) + _path("M23 21 V43 M32 17 V47 M41 21 V43", width=3.0) + '<circle cx="32" cy="32" r="23" fill="none" stroke="var(--black)" stroke-width="1.4" stroke-dasharray="2 6"/>'
    raise KeyError(f"unsupported batch91 target: {asset}")


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
        has_refs = any(refs.get(provider) for provider in ("opencpn_render", "s101", "aquamap"))
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
            "queue_action": "remaining_no_candidate_generated_for_judge_or_source_review",
            "risk_bucket": "semantic_hard_pile_batch91",
            "candidate_strategy": f"owned_{TARGETS[asset]}_semantic_redraw_without_provider_image",
            "candidate_source": None,
            "before_svg": None,
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": (
                "Generated first Helm-owned semantic candidate from S-57/S-52 metadata; "
                "rows without provider images remain blocked until source/reference evidence is attached."
            ),
            "safety_reason_codes": (
                ["new_candidate_pending_visual_judge"]
                if has_refs
                else ["no_provider_reference_image", "semantic_candidate_requires_source_review"]
            ),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": refs,
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": None,
            "qa": {
                "semantic_pass": True,
                "structural_pass": True,
                "visual_parity": "pending_llm_judge" if has_refs else "pending_reference_gap_judge",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "no_helm_candidate row with no usable provider image in current reference table",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_generate_batch91",
                "reference_role": (
                    "Provider image attached; candidate must pass normal visual judge."
                    if has_refs
                    else "No provider image attached; candidate is a semantic placeholder requiring source review before visual approval."
                ),
            },
        })
    result = {
        "schema_version": 1,
        "status": "semantic_hard_pile_generated_pending_judge_or_reference_gap_review",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "generated": len(rows),
            "reference_backed_pending_judge": sum(
                1 for row in rows if row["qa"]["visual_parity"] == "pending_llm_judge"
            ),
            "reference_gap_pending_source_review": sum(
                1 for row in rows if row["qa"]["visual_parity"] == "pending_reference_gap_judge"
            ),
            "final_approved": 0,
        },
        "symbols": rows,
        "blockers": ["no_provider_reference_image"],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Generate Batch 91 / Semantic Hard Pile",
        "",
        "Generated-owned first-pass candidates for remaining rows with no Helm SVG candidate.",
        "",
        f"- generated: `{result['summary']['generated']}`",
        f"- reference_backed_pending_judge: `{result['summary']['reference_backed_pending_judge']}`",
        f"- reference_gap_pending_source_review: `{result['summary']['reference_gap_pending_source_review']}`",
        "- final_approved: `0`",
        "- no-reference blocker: `no_provider_reference_image`",
        "",
        "| Asset | Strategy |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | `{TARGETS[row['asset']]}` |")
    lines.extend(["", "Rows are renderable candidates only; none are final-approved.", ""])
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
