"""Repair queued industrial/vegetation/waterway symbols into owned batch 79.

Run:
  python3 -m forge.standard_repair_batch71 --render
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
OUT = ROOT / "out" / "standard_repair_batch71"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch79"
REPORT = CATALOG / "owned_repair_batch79.json"
SUMMARY = CATALOG / "owned_repair_batch79.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "SILBUI01": "silo_brown",
    "SILBUI11": "silo_black",
    "TMBYRD01": "timber_yard",
    "TNKFRM01": "tank_farm_brown",
    "TNKFRM11": "tank_farm_black",
    "TREPNT04": "tree",
    "TREPNT05": "mangrove",
    "TRNBSN01": "turning_basin",
    "WATTUR02": "overfalls",
    "WEDKLP03": "kelp",
    "WTLVGG01": "water_gauge",
    "WTLVGG02": "recording_water_gauge",
    "WAYPNT01": "waypoint_red",
    "WAYPNT03": "waypoint_orange",
    "WAYPNT11": "waypoint_next",
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
        'data-repair-batch="standard-repair-batch71">'
        f"<title>{asset} reference repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _silo(colour: str) -> str:
    return f'<circle cx="32" cy="32" r="5" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="1.4"/>'


def _timber_yard() -> str:
    return (
        f'<path d="M26 24 V40 M32 24 V40 M38 24 V40 M24 29 H40 M24 35 H40" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="2.1"/>'
    )


def _tank_farm(colour: str) -> str:
    dots = "".join(
        f'<circle cx="{x}" cy="{y}" r="2.1" fill="{_colour(colour)}" stroke="none"/>'
        for x, y in ((28, 28), (36, 28), (28, 36), (36, 36))
    )
    return f'<circle cx="32" cy="32" r="10" fill="none" stroke="{_colour(colour)}" stroke-width="2.2"/>{dots}'


def _tree() -> str:
    return (
        f'<path d="M32 42 V27" fill="none" stroke="{_colour("brown")}" stroke-width="2.2"/>'
        f'<path d="M24 29 H40 M27 25 L32 20 L37 25 M28 34 H36" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="2"/>'
    )


def _mangrove() -> str:
    return (
        f'<path d="M23 39 H41" fill="none" stroke="{_colour("brown")}" stroke-width="2"/>'
        f'<path d="M26 38 C26 28 38 28 38 38" fill="none" stroke="{_colour("brown")}" stroke-width="2.2"/>'
        f'<path d="M29 38 C30 34 34 34 35 38" fill="none" stroke="{_colour("brown")}" stroke-width="1.8"/>'
    )


def _turning_basin() -> str:
    return (
        f'<path d="M39 24 A12 12 0 1 0 42 36" fill="none" stroke="{_colour("magenta")}" stroke-width="2.5"/>'
        f'<path d="M39 24 H47 V16" fill="none" stroke="{_colour("magenta")}" stroke-width="2.5"/>'
        f'<circle cx="32" cy="32" r="3" fill="none" stroke="{_colour("magenta")}" stroke-width="2"/>'
    )


def _overfalls() -> str:
    return (
        f'<path d="M17 36 C20 31 24 31 27 36 S34 41 37 36 S44 31 47 36" '
        f'fill="none" stroke="{_colour("gray")}" stroke-width="2.2"/>'
    )


def _kelp() -> str:
    return (
        f'<path d="M20 35 C28 31 36 37 44 32" fill="none" stroke="{_colour("gray")}" stroke-width="2.1"/>'
        f'<path d="M30 33 L26 28 M35 35 L39 40 M39 34 L45 37" fill="none" stroke="{_colour("gray")}" stroke-width="1.8"/>'
    )


def _water_gauge(recording: bool = False) -> str:
    if recording:
        return (
            f'<rect x="29" y="20" width="7" height="24" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2"/>'
            f'<path d="M31 25 H35 M31 32 H35 M31 39 H35" fill="none" stroke="{_colour("black")}" stroke-width="1.3"/>'
        )
    return (
        f'<rect x="24" y="22" width="16" height="12" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<text x="32" y="31" text-anchor="middle" font-size="6.5" font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="700" fill="{_colour("black")}" stroke="none">WL</text>'
        f'<path d="M32 34 V47 M27 47 H37" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _waypoint(colour: str, double: bool = False) -> str:
    body = f'<circle cx="32" cy="32" r="8" fill="none" stroke="{_colour(colour)}" stroke-width="2.5"/>'
    if double:
        body += f'<circle cx="32" cy="32" r="4" fill="none" stroke="{_colour(colour)}" stroke-width="2"/>'
    return body


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "silo_brown":
        return _silo("brown")
    if kind == "silo_black":
        return _silo("black")
    if kind == "timber_yard":
        return _timber_yard()
    if kind == "tank_farm_brown":
        return _tank_farm("brown")
    if kind == "tank_farm_black":
        return _tank_farm("black")
    if kind == "tree":
        return _tree()
    if kind == "mangrove":
        return _mangrove()
    if kind == "turning_basin":
        return _turning_basin()
    if kind == "overfalls":
        return _overfalls()
    if kind == "kelp":
        return _kelp()
    if kind == "water_gauge":
        return _water_gauge(False)
    if kind == "recording_water_gauge":
        return _water_gauge(True)
    if kind == "waypoint_red":
        return _waypoint("red")
    if kind == "waypoint_orange":
        return _waypoint("orange")
    if kind == "waypoint_next":
        return _waypoint("red", True)
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
        raise RuntimeError("no batch71 target rows in standard repair queue")

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
            "queue_action": "standard_industrial_waterway_reference_consumed",
            "risk_bucket": "industrial_waterway_symbol_repair_batch79",
            "candidate_strategy": "owned_industrial_waterway_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue industrial/waterway symbol blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch71",
                "reference_role": "OpenCPN industrial/waterway witnesses and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 71 / Owned Repair Batch 79",
        "",
        "OpenCPN-reference repair pass for queued industrial/vegetation/waterway rows.",
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
