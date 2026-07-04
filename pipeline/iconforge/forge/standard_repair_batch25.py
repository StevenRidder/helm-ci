"""Repair daymark/light/radar slice into owned repair batch 33.

Run:
  python3 -m forge.standard_repair_batch25 --render
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
OUT = ROOT / "out" / "standard_repair_batch25"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch33"
REPORT = CATALOG / "owned_repair_batch33.json"
SUMMARY = CATALOG / "owned_repair_batch33.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "DAYSQR01": "day_square_simplified",
    "DAYSQR21": "day_square_paper",
    "DAYTRI01": "day_triangle_up",
    "DAYTRI05": "day_triangle_down",
    "LITFLT01": "light_float_full",
    "LITFLT02": "light_float_simple",
    "LITVES01": "light_vessel_full",
    "LITVES02": "light_vessel_simple",
    "RADRFL03": "radar_reflector",
    "RASCAN01": "radar_scanner",
    "RASCAN11": "radar_scanner_conspicuous",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch25">'
        f"<title>{asset} repair batch 33 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _day_square(*, paper: bool = False) -> str:
    c = _colour("magenta")
    base = f'<rect x="18" y="12" width="28" height="25" fill="none" stroke="{c}" stroke-width="3.4"/>'
    if paper:
        return base + f'<path d="M32 37 V49 M22 49 H42" fill="none" stroke="{c}" stroke-width="3.2"/><circle cx="32" cy="49" r="5" fill="{_colour("white")}" stroke="{c}" stroke-width="3.2"/>'
    return base + f'<path d="M32 37 V53" fill="none" stroke="{c}" stroke-width="3.2"/><circle cx="32" cy="39" r="6" fill="{c}" stroke="none"/>'


def _day_triangle(up: bool) -> str:
    c = _colour("magenta")
    d = "M32 10 L52 43 H12 Z" if up else "M12 17 H52 L32 50 Z"
    dot_y = 43 if up else 48
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="3.5"/><path d="M32 {dot_y} V56" fill="none" stroke="{c}" stroke-width="3.2"/><circle cx="32" cy="{dot_y}" r="6" fill="{c}" stroke="none"/>'


def _boat(full: bool, vessel: bool = False) -> str:
    c = _colour("black")
    hull = f'<path d="M13 39 H51 L45 51 H19 Z" fill="{c}" stroke="{c}" stroke-width="2.4"/>'
    cabin = f'<path d="M26 31 H38 V39 H26 Z" fill="none" stroke="{c}" stroke-width="3.2"/>'
    if not full:
        mast = f'<path d="M32 18 V39" fill="none" stroke="{c}" stroke-width="3.2"/>' if vessel else ""
        return hull + cabin + mast
    rail = f'<path d="M10 51 H54" fill="none" stroke="{c}" stroke-width="4"/>'
    light = f'<circle cx="32" cy="51" r="6" fill="{_colour("white")}" stroke="{c}" stroke-width="3.5"/>'
    mast = ""
    if vessel:
        mast = (
            f'<path d="M32 17 V38" fill="none" stroke="{c}" stroke-width="3.4"/>'
            f'<path d="M32 17 L32 10 M25 14 L39 14 M27 9 L37 19 M37 9 L27 19" fill="none" stroke="{c}" stroke-width="3.1"/>'
        )
    return hull + cabin + mast + rail + light


def _radar_reflector() -> str:
    c = _colour("magenta")
    rays = "M32 8 V20 M32 44 V56 M8 32 H20 M44 32 H56 M15 15 L23 23 M41 41 L49 49 M49 15 L41 23 M23 41 L15 49"
    return f'<circle cx="32" cy="32" r="13" fill="{_colour("white")}" stroke="{c}" stroke-width="3.5"/><path d="{rays}" fill="none" stroke="{c}" stroke-width="3.5"/>'


def _radar_scanner(conspicuous: bool = False) -> str:
    c = _colour("black") if conspicuous else _colour("brown")
    return (
        f'<path d="M20 54 H44 M32 54 V25 M22 25 H42" fill="none" stroke="{c}" stroke-width="4"/>'
        f'<path d="M18 15 H46" fill="none" stroke="{c}" stroke-width="4"/>'
        f'<path d="M26 25 V45 H38 V25" fill="none" stroke="{c}" stroke-width="4"/>'
        f'<circle cx="32" cy="54" r="6" fill="{_colour("white")}" stroke="{c}" stroke-width="3.4"/>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "day_square_simplified":
        return _svg(asset, _day_square())
    if kind == "day_square_paper":
        return _svg(asset, _day_square(paper=True))
    if kind == "day_triangle_up":
        return _svg(asset, _day_triangle(True))
    if kind == "day_triangle_down":
        return _svg(asset, _day_triangle(False))
    if kind == "light_float_full":
        return _svg(asset, _boat(True))
    if kind == "light_float_simple":
        return _svg(asset, _boat(False))
    if kind == "light_vessel_full":
        return _svg(asset, _boat(True, vessel=True))
    if kind == "light_vessel_simple":
        return _svg(asset, _boat(False, vessel=True))
    if kind == "radar_reflector":
        return _svg(asset, _radar_reflector())
    if kind == "radar_scanner":
        return _svg(asset, _radar_scanner())
    if kind == "radar_scanner_conspicuous":
        return _svg(asset, _radar_scanner(conspicuous=True))
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
    for asset in sorted(REPAIRS):
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
            "risk_bucket": "daymark_light_radar_repair_batch33",
            "candidate_strategy": "owned_redraw_from_s101_opencpn_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": source_row.get("required_change"),
            "judge_required_change": judge.get("required_change"),
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
                "source_priority_basis": "standard_repair_queue daymark/light/radar slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch25",
                "reference_role": "S-101/OpenCPN refs are shape witnesses; SVG is owned redraw",
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
    lines = ["# Standard Repair Batch 25 / Owned Repair Batch 33", "", "Owned redraws for a daymark/light/radar slice.", ""]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('name')}")
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
