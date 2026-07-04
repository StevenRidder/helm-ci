"""Repair queued small point/line symbols into owned batch 77.

Run:
  python3 -m forge.standard_repair_batch69 --render
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
OUT = ROOT / "out" / "standard_repair_batch69"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch77"
REPORT = CATALOG / "owned_repair_batch77.json"
SUMMARY = CATALOG / "owned_repair_batch77.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "HECMTR01": "hectometre_100m",
    "HECMTR02": "hectometre_1km",
    "OSPONE02": "short_black_tick",
    "OSPSIX02": "long_black_tick",
    "PLNPOS02": "planned_position_line",
    "POSITN02": "orange_position_crosshair",
    "HGWTMK01": "high_water_mark",
    "EVENTS02": "event_mark",
    "NOTMRK03": "notice_information",
    "ISODGR51": "isolated_danger",
    "PRICKE03": "withy_porthand",
    "PRICKE04": "withy_starboard",
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
        'data-repair-batch="standard-repair-batch69">'
        f"<title>{asset} point symbol repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _diamond(cx: int, cy: int, r: int, colour: str, stroke: str | None = None) -> str:
    points = f"{cx},{cy-r} {cx+r},{cy} {cx},{cy+r} {cx-r},{cy}"
    if stroke:
        return f'<polygon points="{points}" fill="{_colour(colour)}" stroke="{_colour(stroke)}" stroke-width="2"/>'
    return f'<polygon points="{points}" fill="{_colour(colour)}" stroke="none"/>'


def _hectometre(asset: str) -> str:
    size = 4 if asset == "HECMTR01" else 5
    return _diamond(32, 32, size, "magenta")


def _tick(asset: str) -> str:
    half = 4 if asset == "OSPONE02" else 6
    return f'<path d="M{32-half} 32 H{32+half}" fill="none" stroke="{_colour("black")}" stroke-width="2.6"/>'


def _planned_position_line() -> str:
    return f'<path d="M25 32 H39" fill="none" stroke="{_colour("red")}" stroke-width="2.2"/>'


def _position_crosshair() -> str:
    return (
        f'<circle cx="32" cy="32" r="7" fill="none" stroke="{_colour("orange")}" stroke-width="2.1"/>'
        f'<path d="M21 32 H43 M32 21 V43" fill="none" stroke="{_colour("orange")}" stroke-width="2.1"/>'
    )


def _high_water_mark() -> str:
    return (
        f'<rect x="23" y="18" width="18" height="16" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<path d="M25 22 H39 M25 30 H39 M28 19 V34 M36 19 V34" fill="none" stroke="{_colour("black")}" stroke-width="1.3"/>'
        f'<text x="32" y="29" text-anchor="middle" font-size="7" font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="700" fill="{_colour("black")}" stroke="none">HW</text>'
        f'<path d="M32 34 V48 M26 48 H38" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
    )


def _event_mark() -> str:
    return (
        f'<rect x="27" y="27" width="10" height="10" fill="{_colour("white")}" stroke="{_colour("orange")}" stroke-width="2.2"/>'
        f'<path d="M29 35 L35 29" fill="none" stroke="{_colour("orange")}" stroke-width="1.8"/>'
    )


def _notice_information() -> str:
    return f'<rect x="26" y="26" width="12" height="12" fill="{_colour("blue")}" stroke="{_colour("black")}" stroke-width="2"/>'


def _isolated_danger() -> str:
    return (
        f'<circle cx="32" cy="32" r="9" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6"/>'
        f'<path d="M27 27 L37 37 M37 27 L27 37" fill="none" stroke="{_colour("magenta")}" stroke-width="2.5"/>'
    )


def _withy(direction: str) -> str:
    if direction == "port":
        branch = f'<path d="M32 42 C27 35 25 28 24 21" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
    else:
        branch = f'<path d="M32 42 C37 35 39 28 40 21" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
    return (
        f'<path d="M32 47 V18" fill="none" stroke="{_colour("black")}" stroke-width="2.6"/>'
        f"{branch}"
        f'<path d="M27 28 H37 M29 35 H35" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind.startswith("hectometre"):
        return _hectometre(asset)
    if kind.endswith("black_tick"):
        return _tick(asset)
    if kind == "planned_position_line":
        return _planned_position_line()
    if kind == "orange_position_crosshair":
        return _position_crosshair()
    if kind == "high_water_mark":
        return _high_water_mark()
    if kind == "event_mark":
        return _event_mark()
    if kind == "notice_information":
        return _notice_information()
    if kind == "isolated_danger":
        return _isolated_danger()
    if kind == "withy_porthand":
        return _withy("port")
    if kind == "withy_starboard":
        return _withy("starboard")
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
        raise RuntimeError("no batch69 target rows in standard repair queue")

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
            "queue_action": "standard_point_symbol_reference_consumed",
            "risk_bucket": "point_line_symbol_repair_batch77",
            "candidate_strategy": "owned_small_symbol_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue small point/line symbol blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch69",
                "reference_role": "OpenCPN point/line witnesses and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 69 / Owned Repair Batch 77",
        "",
        "OpenCPN-reference repair pass for queued small point/line symbol rows.",
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
