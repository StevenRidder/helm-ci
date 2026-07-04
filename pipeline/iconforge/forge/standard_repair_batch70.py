"""Repair queued operational/reference symbols into owned batch 78.

Run:
  python3 -m forge.standard_repair_batch70 --render
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
OUT = ROOT / "out" / "standard_repair_batch70"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch78"
REPORT = CATALOG / "owned_repair_batch78.json"
SUMMARY = CATALOG / "owned_repair_batch78.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "DISMAR03": "distance_okm",
    "DISMAR04": "distance_km",
    "LITFLT10": "light_float_red_white",
    "LITFLT61": "light_float_green",
    "LITVES60": "light_vessel_red",
    "LITVES61": "light_vessel_green",
    "OWNSHP01": "ownship_target",
    "OWNSHP05": "ownship_hull",
    "RFNERY01": "refinery_yellow",
    "RFNERY11": "refinery_black",
    "SCALEB10": "scale_bar_orange",
    "SCALEB11": "scale_bar_black",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    if name == "grey":
        name = "gray"
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch70">'
        f"<title>{asset} operational symbol repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _distance_text(text: str) -> str:
    return (
        f'<text x="32" y="35" text-anchor="middle" font-size="9" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour("magenta")}" stroke="none">{text}</text>'
    )


def _light_float(colour: str, striped: bool = False) -> str:
    fill = _colour(colour)
    parts = []
    if striped:
        parts.append(
            f'<path d="M20 37 H44 L40 43 H24 Z" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.2"/>'
        )
        parts.append(f'<path d="M24 37 H31 V43 H24 Z" fill="{_colour("red")}" stroke="none"/>')
        parts.append(f'<path d="M34 37 H40 V43 H34 Z" fill="{_colour("red")}" stroke="none"/>')
    else:
        parts.append(f'<path d="M20 37 H44 L40 43 H24 Z" fill="{fill}" stroke="{_colour("black")}" stroke-width="2.2"/>')
    parts.append(f'<path d="M27 37 Q32 29 37 37" fill="none" stroke="{_colour("black")}" stroke-width="2.1"/>')
    parts.append(f'<path d="M32 29 V22 M27 25 H37" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>')
    parts.append(f'<circle cx="32" cy="21" r="2.2" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.3"/>')
    return "".join(parts)


def _light_vessel(colour: str) -> str:
    return (
        f'<path d="M18 39 H46 L40 45 H24 Z" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M24 39 L30 32 H38 L44 39" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<path d="M32 32 V21 M27 25 H37" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<circle cx="32" cy="20" r="2.3" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.2"/>'
    )


def _ownship_target() -> str:
    return (
        f'<circle cx="32" cy="32" r="14" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<circle cx="32" cy="32" r="5" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _ownship_hull() -> str:
    return f'<path d="M26 48 V18 Q32 12 38 18 V48 Z" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.5"/>'


def _refinery(colour: str) -> str:
    return (
        f'<circle cx="28" cy="32" r="7" fill="none" stroke="{_colour(colour)}" stroke-width="2.3"/>'
        f'<path d="M35 23 V41" fill="none" stroke="{_colour(colour)}" stroke-width="2.3"/>'
        f'<path d="M39 24 V40" fill="none" stroke="{_colour(colour)}" stroke-width="2.3"/>'
    )


def _scale_bar(colour: str) -> str:
    return (
        f'<path d="M32 18 V46" fill="none" stroke="{_colour(colour)}" stroke-width="2.1"/>'
        f'<path d="M29 18 H35 M29 46 H35" fill="none" stroke="{_colour(colour)}" stroke-width="1.8"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "distance_okm":
        return _distance_text("okm")
    if kind == "distance_km":
        return _distance_text("km")
    if kind == "light_float_red_white":
        return _light_float("red", striped=True)
    if kind == "light_float_green":
        return _light_float("green")
    if kind == "light_vessel_red":
        return _light_vessel("red")
    if kind == "light_vessel_green":
        return _light_vessel("green")
    if kind == "ownship_target":
        return _ownship_target()
    if kind == "ownship_hull":
        return _ownship_hull()
    if kind == "refinery_yellow":
        return _refinery("yellow")
    if kind == "refinery_black":
        return _refinery("black")
    if kind == "scale_bar_orange":
        return _scale_bar("orange")
    if kind == "scale_bar_black":
        return _scale_bar("black")
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
                "source_judge": row.get("source_judge"),
            }
            for row in prior.get("symbols", [])
        ]
    return []


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    if not items:
        raise RuntimeError("no batch70 target rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        latest_judge = (source_row.get("judge") or {}).get("latest") or {}
        source_judge = (
            item.get("source_judge")
            or (f"catalog/{item.get('judge', {}).get('batch')}.json" if item.get("judge", {}).get("batch") else None)
            or (f"catalog/{latest_judge.get('batch')}.json" if latest_judge.get("batch") else None)
        )
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
            "queue_action": "standard_operational_symbol_reference_consumed",
            "risk_bucket": "operational_symbol_repair_batch78",
            "candidate_strategy": "owned_operational_symbol_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue operational symbol blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch70",
                "reference_role": "OpenCPN operational-symbol witnesses and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 70 / Owned Repair Batch 78",
        "",
        "OpenCPN-reference repair pass for queued operational symbol rows.",
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
