"""Repair tide/current and related chart glyphs into owned repair batch 35.

Run:
  python3 -m forge.standard_repair_batch27 --render
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
OUT = ROOT / "out" / "standard_repair_batch27"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch35"
REPORT = CATALOG / "owned_repair_batch35.json"
SUMMARY = CATALOG / "owned_repair_batch35.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "PRDINS02": "mine_quarry",
    "PSSARE01": "pssa_text",
    "QUARRY01": "quarry",
    "SNDWAV02": "sand_waves",
    "SPRING02": "spring",
    "SWPARE51": "swept_area",
    "TIDCUR01": "tidal_stream_predicted",
    "TIDCUR02": "tidal_stream_actual",
    "TIDCUR03": "current_strength_box",
    "TIDEHT01": "tide_height",
    "TIDSTR01": "tidal_stream_table",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch27">'
        f"<title>{asset} repair batch 35 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _tidal_arrow(*, actual: bool) -> str:
    c = _colour("orange")
    shaft = f'<path d="M32 55 V10" fill="none" stroke="{c}" stroke-width="3.1"/>'
    head = f'<path d="M21 22 L32 10 L43 22" fill="none" stroke="{c}" stroke-width="3.1"/>'
    barbs = (
        f'<path d="M20 35 L32 24 L44 35 M22 47 L32 37 L42 47" fill="none" '
        f'stroke="{c}" stroke-width="2.9"/>'
    )
    dot = f'<circle cx="43" cy="13" r="1.7" fill="{c}" stroke="none"/>' if actual else ""
    return shaft + head + barbs + dot


def _current_box() -> str:
    c = _colour("orange")
    return f'<rect x="18" y="23" width="28" height="18" fill="none" stroke="{c}" stroke-width="3"/>'


def _tide_height() -> str:
    c = _colour("gray")
    return f'<path d="M10 32 H54 M16 32 C18 20 34 20 35 32 C36 44 50 44 52 32" fill="none" stroke="{c}" stroke-width="3.2"/>'


def _tidal_stream_table() -> str:
    c = _colour("gray")
    return f'<path d="M32 11 L53 32 L32 53 L11 32 Z" fill="none" stroke="{c}" stroke-width="3.4"/>'


def _sand_waves() -> str:
    c = _colour("gray")
    return (
        f'<path d="M9 36 C14 36 14 25 19 25 C24 25 24 36 29 36 '
        f'C34 36 34 25 39 25 C44 25 44 36 49 36 C54 36 54 25 58 25" '
        f'fill="none" stroke="{c}" stroke-width="3.1"/>'
    )


def _spring() -> str:
    c = _colour("gray")
    return (
        f'<path d="M16 48 H48 M32 48 V21" fill="none" stroke="{c}" stroke-width="4"/>'
        f'<path d="M17 23 C17 14 29 14 29 23 C29 14 41 14 41 23 C41 14 53 15 51 26" '
        f'fill="none" stroke="{c}" stroke-width="4"/>'
    )


def _swept_area() -> str:
    c = _colour("gray")
    return f'<path d="M14 18 V46 H50 V18" fill="none" stroke="{c}" stroke-width="4"/>'


def _crossed_picks(*, circle: bool) -> str:
    c = _colour("brown")
    body = (
        f'<path d="M22 18 L46 42 M42 18 L18 42" fill="none" stroke="{c}" stroke-width="6"/>'
        f'<path d="M17 15 L25 9 L32 18 L20 30 L14 30 Z" fill="{c}" fill-opacity="0.55" stroke="{c}" stroke-width="3"/>'
        f'<path d="M47 15 L39 9 L32 18 L44 30 L50 30 Z" fill="{c}" fill-opacity="0.55" stroke="{c}" stroke-width="3"/>'
    )
    if circle:
        body += f'<circle cx="32" cy="32" r="24" fill="none" stroke="{c}" stroke-width="3.3"/>'
    return body


def _pssa_text() -> str:
    return (
        f'<text x="32" y="42" fill="{_colour("magenta")}" font-family="Arial, sans-serif" '
        'font-size="25" font-weight="700" text-anchor="middle">PSSA</text>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "tidal_stream_predicted":
        return _svg(asset, _tidal_arrow(actual=False))
    if kind == "tidal_stream_actual":
        return _svg(asset, _tidal_arrow(actual=True))
    if kind == "current_strength_box":
        return _svg(asset, _current_box())
    if kind == "tide_height":
        return _svg(asset, _tide_height())
    if kind == "tidal_stream_table":
        return _svg(asset, _tidal_stream_table())
    if kind == "sand_waves":
        return _svg(asset, _sand_waves())
    if kind == "spring":
        return _svg(asset, _spring())
    if kind == "swept_area":
        return _svg(asset, _swept_area())
    if kind == "mine_quarry":
        return _svg(asset, _crossed_picks(circle=False))
    if kind == "quarry":
        return _svg(asset, _crossed_picks(circle=True))
    if kind == "pssa_text":
        return _svg(asset, _pssa_text())
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
            "risk_bucket": "tide_current_area_symbol_repair_batch35",
            "candidate_strategy": "owned_redraw_from_s101_opencpn_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": judge.get("required_change"),
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
                "source_priority_basis": "standard_repair_queue tide/current/area slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch27",
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
    lines = ["# Standard Repair Batch 27 / Owned Repair Batch 35", "", "Owned redraws for tide/current and related chart glyphs.", ""]
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
