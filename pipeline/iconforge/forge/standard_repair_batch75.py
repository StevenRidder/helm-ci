"""Repair queued buoy/beacon parity rows into owned batch 83.

Run:
  python3 -m forge.standard_repair_batch75 --render
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
OUT = ROOT / "out" / "standard_repair_batch75"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch83"
REPORT = CATALOG / "owned_repair_batch83.json"
SUMMARY = CATALOG / "owned_repair_batch83.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "BCNGEN68": "beacon_black_yellow",
    "BCNGEN69": "beacon_yellow_black",
    "BCNGEN79": "beacon_orange",
    "BCNGEN80": "beacon_black",
    "BCNSPR62": "spar_beacon_yellow",
    "BOYISD12": "isolated_danger_simplified",
    "BOYMOR01": "mooring_barrel_full",
    "BOYMOR03": "mooring_can_generic",
    "BOYMOR11": "mooring_installation_simplified",
    "BOYMOR31": "mooring_can_white",
    "BOYSAW12": "safe_water_simplified",
    "BOYSPP11": "special_purpose_simplified",
    "BOYSPP15": "special_purpose_tss_starboard",
    "BOYSPP25": "special_purpose_tss_port",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch75">'
        f"<title>{asset} reference repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _pole(y0: int = 43, y1: int = 52) -> str:
    return f'<path d="M32 {y0} V{y1}" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'


def _beacon_bands(top: str, bottom: str) -> str:
    return (
        f'<path d="M27 18 H37 L39 43 H25 Z" fill="{_colour(bottom)}" stroke="none"/>'
        f'<path d="M27 18 H37 L38 30 H26 Z" fill="{_colour(top)}" stroke="none"/>'
        f'<path d="M27 18 H37 L39 43 H25 Z" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
        + _pole(43, 51)
    )


def _solid_beacon(colour: str) -> str:
    return (
        f'<path d="M27 18 H37 L39 43 H25 Z" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="1.8"/>'
        + _pole(43, 51)
    )


def _spar_beacon() -> str:
    return (
        f'<path d="M30 15 H34 L37 45 Q32 49 27 45 Z" fill="{_colour("yellow")}" '
        f'stroke="{_colour("black")}" stroke-width="1.8"/>'
        + _pole(46, 53)
    )


def _isolated_danger() -> str:
    return (
        f'<circle cx="32" cy="27" r="3.2" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.1"/>'
        f'<circle cx="32" cy="38" r="3.2" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.1"/>'
    )


def _mooring_barrel() -> str:
    return (
        f'<path d="M23 39 C23 32 28 28 32 28 C36 28 41 32 41 39" fill="{_colour("white")}" '
        f'stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M28 29 C30 25 34 25 36 29" fill="none" stroke="{_colour("black")}" stroke-width="1.6"/>'
        f'<path d="M25 39 H39" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
    )


def _mooring_can(fill: str) -> str:
    return (
        f'<path d="M24 33 L41 28 L39 39 L22 44 Z" fill="{_colour(fill)}" '
        f'stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M29 31 C30 27 35 26 36 29" fill="none" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _mooring_installation() -> str:
    return (
        f'<path d="M22 39 H42" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M26 38 C27 34 37 34 38 38 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _safe_water() -> str:
    return (
        f'<circle cx="32" cy="32" r="5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
        f'<circle cx="32" cy="32" r="1.8" fill="{_colour("white")}" stroke="none"/>'
    )


def _special_circle() -> str:
    return (
        f'<circle cx="32" cy="32" r="5" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.4"/>'
        f'<circle cx="32" cy="32" r="1.7" fill="{_colour("white")}" stroke="none"/>'
    )


def _special_triangle() -> str:
    return f'<path d="M31 25 L39 39 H24 Z" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.5"/>'


def _special_slant() -> str:
    return f'<path d="M25 30 L39 27 L36 39 L22 42 Z" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.5"/>'


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "beacon_black_yellow":
        return _beacon_bands("black", "yellow")
    if kind == "beacon_yellow_black":
        return _beacon_bands("yellow", "black")
    if kind == "beacon_orange":
        return _solid_beacon("orange")
    if kind == "beacon_black":
        return _solid_beacon("black")
    if kind == "spar_beacon_yellow":
        return _spar_beacon()
    if kind == "isolated_danger_simplified":
        return _isolated_danger()
    if kind == "mooring_barrel_full":
        return _mooring_barrel()
    if kind == "mooring_can_generic":
        return _mooring_can("white")
    if kind == "mooring_installation_simplified":
        return _mooring_installation()
    if kind == "mooring_can_white":
        return _mooring_can("white")
    if kind == "safe_water_simplified":
        return _safe_water()
    if kind == "special_purpose_simplified":
        return _special_circle()
    if kind == "special_purpose_tss_starboard":
        return _special_triangle()
    if kind == "special_purpose_tss_port":
        return _special_slant()
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
        raise RuntimeError("no batch75 target rows in standard repair queue")

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
            "queue_action": "standard_buoy_beacon_reference_consumed",
            "risk_bucket": "buoy_beacon_symbol_repair_batch83",
            "candidate_strategy": "owned_thin_chart_mark_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue buoy/beacon parity blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch75",
                "reference_role": "OpenCPN buoy/beacon witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 75 / Owned Repair Batch 83",
        "",
        "OpenCPN-reference repair pass for queued buoy and beacon rows using Helm's thin chart-mark style.",
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
