"""Repair queued unit/vector/navigation mark symbols into owned batch 80.

Run:
  python3 -m forge.standard_repair_batch72 --render
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
OUT = ROOT / "out" / "standard_repair_batch72"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch80"
REPORT = CATALOG / "owned_repair_batch80.json"
SUMMARY = CATALOG / "owned_repair_batch80.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "UNITFTH1": "unit_label_fathom",
    "UNITMTR1": "unit_label_metre",
    "VECGND01": "vector_ground_ownship",
    "VECGND21": "vector_ground_target",
    "VECWTR01": "vector_water_ownship",
    "VECWTR21": "vector_water_target",
    "VTCLMK01": "vertical_clearance_mark",
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
        'data-repair-batch="standard-repair-batch72">'
        f"<title>{asset} reference repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _unit_label(letter: str) -> str:
    return (
        f'<text x="26" y="41" text-anchor="middle" font-size="26" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="400" '
        f'fill="{_colour("orange")}" stroke="none">{letter}</text>'
    )


def _vector_arrow(colour: str) -> str:
    return (
        f'<path d="M22 38 L32 26 L42 38" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.4"/>'
        f'<path d="M27 38 L32 32 L37 38" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="1.6"/>'
    )


def _vertical_clearance() -> str:
    return (
        f'<rect x="29" y="21" width="6" height="22" rx="1.2" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="2"/>'
        f'<circle cx="32" cy="25" r="2.2" fill="{_colour("white")}" '
        f'stroke="{_colour("black")}" stroke-width="1.4"/>'
        f'<path d="M32 30 V39" fill="none" stroke="{_colour("black")}" stroke-width="1.6"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "unit_label_fathom":
        return _unit_label("F")
    if kind == "unit_label_metre":
        return _unit_label("M")
    if kind == "vector_ground_ownship":
        return _vector_arrow("black")
    if kind == "vector_ground_target":
        return _vector_arrow("green")
    if kind == "vector_water_ownship":
        return _vector_arrow("black")
    if kind == "vector_water_target":
        return _vector_arrow("green")
    if kind == "vertical_clearance_mark":
        return _vertical_clearance()
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
        raise RuntimeError("no batch72 target rows in standard repair queue")

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
            "queue_action": "standard_unit_vector_reference_consumed",
            "risk_bucket": "unit_vector_symbol_repair_batch80",
            "candidate_strategy": "owned_unit_vector_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue unit/vector/clearance blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch72",
                "reference_role": "OpenCPN unit/vector/clearance witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 72 / Owned Repair Batch 80",
        "",
        "OpenCPN-reference repair pass for queued unit labels, vector arrows, and clearance marks.",
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
