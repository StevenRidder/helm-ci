"""Repair queued windmotor/windmill symbols into owned batch 81.

Run:
  python3 -m forge.standard_repair_batch73 --render
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
OUT = ROOT / "out" / "standard_repair_batch73"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch81"
REPORT = CATALOG / "owned_repair_batch81.json"
SUMMARY = CATALOG / "owned_repair_batch81.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "WIMCON01": "windmotor_brown",
    "WIMCON11": "windmotor_black",
    "WNDFRM51": "wind_farm_brown",
    "WNDFRM61": "wind_farm_black",
    "WNDMIL02": "windmill_brown",
    "WNDMIL12": "windmill_black",
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
        'data-repair-batch="standard-repair-batch73">'
        f"<title>{asset} reference repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _windmotor(colour: str) -> str:
    return (
        f'<path d="M32 27 V43 M26 43 H38" fill="none" stroke="{_colour(colour)}" stroke-width="2"/>'
        f'<path d="M32 28 L24 23 M32 28 L40 23 M32 28 L32 18" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="2"/>'
        f'<circle cx="32" cy="28" r="1.7" fill="{_colour("white")}" stroke="{_colour(colour)}" stroke-width="1.2"/>'
    )


def _wind_farm(colour: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="10" fill="none" stroke="{_colour(colour)}" stroke-width="2"/>'
        f'<path d="M32 32 V42 M27 42 H37" fill="none" stroke="{_colour(colour)}" stroke-width="1.8"/>'
        f'<path d="M32 32 L25 28 M32 32 L39 28 M32 32 L32 23" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="1.8"/>'
    )


def _windmill(colour: str) -> str:
    return (
        f'<path d="M26 26 L38 38 M38 26 L26 38" fill="none" stroke="{_colour(colour)}" stroke-width="1.8"/>'
        f'<circle cx="32" cy="32" r="2.1" fill="{_colour("white")}" stroke="{_colour(colour)}" stroke-width="1.2"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "windmotor_brown":
        return _windmotor("brown")
    if kind == "windmotor_black":
        return _windmotor("black")
    if kind == "wind_farm_brown":
        return _wind_farm("brown")
    if kind == "wind_farm_black":
        return _wind_farm("black")
    if kind == "windmill_brown":
        return _windmill("brown")
    if kind == "windmill_black":
        return _windmill("black")
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
        raise RuntimeError("no batch73 target rows in standard repair queue")

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
            "queue_action": "standard_wind_reference_consumed",
            "risk_bucket": "wind_symbol_repair_batch81",
            "candidate_strategy": "owned_wind_symbol_redraw_from_opencpn_reference",
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
                "source_priority_basis": "standard_repair_queue windmotor/windmill blockers",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch73",
                "reference_role": "OpenCPN wind symbol witnesses and S-52 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 73 / Owned Repair Batch 81",
        "",
        "OpenCPN-reference repair pass for queued windmotor, windmill, and wind-farm rows.",
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
