"""Repair precise judge-fail symbols into owned batch 86.

Run:
  python3 -m forge.standard_repair_batch86 --render
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
OUT = ROOT / "out" / "standard_repair_batch86"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch86"
REPORT = CATALOG / "owned_repair_batch86.json"
SUMMARY = CATALOG / "owned_repair_batch86.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "NMKINF38": ("notice_end_single_slash", "catalog/standard_judge_batch_039_rerun.json"),
    "NMKINF53": ("notice_three_vessels_bars", "catalog/standard_judge_batch_039_rerun.json"),
    "SCALEB10": ("one_mile_segmented_scale_bar", "catalog/standard_judge_batch_078_rerun.json"),
    "SCALEB11": ("ten_mile_segmented_scale_bar", "catalog/standard_judge_batch_078_rerun.json"),
    "TOPMAR90": ("pricken_point_down", "catalog/standard_judge_batch_072_rerun.json"),
    "TOPMAR93": ("pricken_point_up", "catalog/standard_judge_batch_072_rerun.json"),
    "WATTUR02": ("three_wave_turbulence", "catalog/standard_judge_batch_079_rerun.json"),
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch86">'
        f"<title>{asset} precise repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _notice_panel(inner: str) -> str:
    return (
        f'<rect x="16" y="16" width="32" height="32" rx="2.5" fill="{_colour("blue")}" '
        f'stroke="{_colour("black")}" stroke-width="2.2"/>'
        f"{inner}"
    )


def _scale_bar(colour: str, accent: str | None = None) -> str:
    segments = []
    y = 14
    for index in range(6):
        seg_colour = accent if accent and index % 2 else colour
        segments.append(
            f'<path d="M32 {y} V{y + 5}" fill="none" stroke="{_colour(seg_colour)}" stroke-width="2.2"/>'
        )
        y += 7
    return "".join(segments)


def _pricken(direction: str) -> str:
    if direction == "down":
        return (
            f'<path d="M32 14 V48 M32 48 L24 38 M32 48 L40 38" fill="none" '
            f'stroke="{_colour("black")}" stroke-width="2.4"/>'
            f'<path d="M32 28 L24 24 M32 34 L40 30" fill="none" '
            f'stroke="{_colour("black")}" stroke-width="2.0"/>'
        )
    return (
        f'<path d="M32 50 V16 M32 16 L24 26 M32 16 L40 26" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M32 30 L24 34 M32 24 L40 28" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2.0"/>'
    )


def _body(asset: str) -> str:
    if asset == "NMKINF38":
        return _notice_panel(f'<path d="M24 40 L40 24" fill="none" stroke="{_colour("white")}" stroke-width="4.8"/>')
    if asset == "NMKINF53":
        return _notice_panel(
            f'<path d="M25 23 V41 M32 23 V41 M39 23 V41" fill="none" '
            f'stroke="{_colour("white")}" stroke-width="4.2"/>'
        )
    if asset == "SCALEB10":
        return _scale_bar("orange", "blue")
    if asset == "SCALEB11":
        return _scale_bar("black")
    if asset == "TOPMAR90":
        return _pricken("down")
    if asset == "TOPMAR93":
        return _pricken("up")
    if asset == "WATTUR02":
        return (
            f'<path d="M14 35 Q17 30 20 35 T26 35 M28 35 Q31 30 34 35 T40 35 '
            f'M42 35 Q45 30 48 35 T54 35" fill="none" '
            f'stroke="{_colour("gray")}" stroke-width="2.3"/>'
        )
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
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


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
        raise RuntimeError("no batch86 target rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        repair_kind, source_judge = TARGETS[asset]
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
            "queue_action": "standard_precise_failure_consumed",
            "risk_bucket": "precise_symbol_repair_batch86",
            "candidate_strategy": f"owned_{repair_kind}_redraw_from_judge_feedback",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": source_judge,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": f"{source_judge} precise repair feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch86",
                "reference_role": "OpenCPN/Chart No.1 witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 86 / Owned Repair Batch 86",
        "",
        "Targeted deterministic redraws for precise visual-judge failures.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Repair |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | `{TARGETS[row['asset']][0]}` |")
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
