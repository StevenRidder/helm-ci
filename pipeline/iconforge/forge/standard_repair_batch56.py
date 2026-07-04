"""Repair queued TOPSHQ topmark rows into owned repair batch 64.

Run:
  python3 -m forge.standard_repair_batch56 --render
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
JUDGE_FILE = CATALOG / "standard_judge_batch_015.json"
OUT = ROOT / "out" / "standard_repair_batch56"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch64"
REPORT = CATALOG / "owned_repair_batch64.json"
SUMMARY = CATALOG / "owned_repair_batch64.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")


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
        'data-repair-batch="standard-repair-batch56">'
        f"<title>{asset} topmark repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _fill(row: dict) -> str:
    colours = (row.get("semantic_brief") or {}).get("required_colours") or []
    for colour in colours:
        if colour not in {"black", "white"}:
            return _colour(colour)
    return _colour("white")


def _stroke() -> str:
    return _colour("black")


def _outline(points: str, fill: str, width: str = "3") -> str:
    return f'<polygon points="{points}" fill="{fill}" stroke="{_stroke()}" stroke-width="{width}"/>'


def _rect(x: int, y: int, w: int, h: int, fill: str) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'


def _circle(cx: int, cy: int, r: int, fill: str) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'


def _compound(asset: str, row: dict) -> str:
    fill = _fill(row)
    white = _colour("white")
    shapes = {
        "TOPSHQ06": lambda: _rect(26, 16, 12, 32, fill),
        "TOPSHQ07": lambda: (
            f'<path d="M18 24 L24 18 L32 26 L40 18 L46 24 L38 32 L46 40 L40 46 L32 38 L24 46 L18 40 L26 32 Z" '
            f'fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'
        ),
        "TOPSHQ08": lambda: (
            f'<path d="M27 16 H37 V27 H48 V37 H37 V48 H27 V37 H16 V27 H27 Z" '
            f'fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'
        ),
        "TOPSHQ15": lambda: _outline("20,42 44,42 40,34 35,34 35,17 29,17 29,34 24,34", fill),
        "TOPSHQ16": lambda: _outline("18,20 46,20 44,28 36,28 36,49 28,49 28,28 20,28", fill),
        "TOPSHQ17": lambda: (
            f'<path d="M20 18 H27 L27 22 Q32 25 37 22 L37 18 H44 V44 H38 Q32 49 26 44 H20 Z" '
            f'fill="{white}" stroke="{_stroke()}" stroke-width="3"/>'
        ),
        "TOPSHQ18": lambda: _circle(32, 22, 8, fill) + _outline("32,32 42,42 32,52 22,42", fill),
        "TOPSHQ19": lambda: _rect(20, 18, 24, 28, fill),
        "TOPSHQ20": lambda: _rect(18, 24, 28, 16, white),
        "TOPSHQ21": lambda: _rect(24, 16, 16, 32, fill),
        "TOPSHQ22": lambda: _outline("22,45 42,45 39,19 25,19", fill),
        "TOPSHQ23": lambda: _outline("20,18 44,18 44,35 39,35 39,46 25,46 25,35 20,35", fill),
        "TOPSHQ24": lambda: _outline("32,15 48,46 16,46", fill),
        "TOPSHQ25": lambda: _outline("16,18 48,18 32,48", fill),
        "TOPSHQ26": lambda: _circle(32, 32, 17, fill) + _circle(32, 32, 5, white),
        "TOPSHQ27": lambda: (
            f'<path d="M20 20 H30 V12 H38 V20 H48 V28 H38 V36 H48 V44 H38 V52 H30 V44 H20 V36 H30 V28 H20 Z" '
            f'fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'
        ),
        "TOPSHQ28": lambda: _outline("18,18 46,18 46,28 36,28 36,50 28,50 28,28 18,28", fill),
        "TOPSHQ29": lambda: _outline("32,14 48,30 16,30", fill) + _circle(32, 43, 12, fill),
        "TOPSHQ30": lambda: (
            f'<path d="M22 18 H30 V11 H38 V18 H48 V28 H38 V35 H48 V45 H38 V52 H30 V45 H20 V35 H30 V28 H22 Z" '
            f'fill="{fill}" stroke="{_stroke()}" stroke-width="3"/>'
            + _circle(32, 45, 11, fill)
        ),
        "TOPSHQ31": lambda: _circle(32, 21, 12, fill) + _circle(32, 43, 12, fill),
        "TOPSHQ32": lambda: _circle(32, 20, 12, fill) + _outline("32,32 45,50 19,50", fill),
    }
    return shapes[asset]()


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


def _repair_items() -> dict[str, dict]:
    queue = json.loads(REPAIR_QUEUE.read_text())
    items = {row["asset"]: row for row in queue.get("items", []) if row.get("asset", "").startswith("TOPSHQ")}
    if items:
        return items
    if REPORT.exists():
        prior = json.loads(REPORT.read_text())
        return {row["asset"]: row for row in prior.get("symbols", [])}
    return items


def _judge_rows() -> dict[str, dict]:
    data = json.loads(JUDGE_FILE.read_text())
    return {row.get("symbol_id") or row.get("asset"): row for row in data.get("verdicts", [])}


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    items = _repair_items()
    judge_rows = _judge_rows()
    if not items:
        raise RuntimeError("no TOPSHQ rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in sorted(items):
        source_row = source_rows[asset]
        item = items[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = judge_rows.get(asset, {})
        svg = _svg(asset, _compound(asset, source_row))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_judge_batch_015_topshq_failure_consumed",
            "risk_bucket": "topshq_shape_repair_batch64",
            "candidate_strategy": "owned_topmark_shape_redraw_from_opencpn_witness",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change") or judge.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes") or judge.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_judge_batch_015 TOPSHQ topmark shape feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch56",
                "reference_role": "OpenCPN/Chart No.1 witness silhouettes drive generated-owned topmark shapes",
            },
            "source_judge": "catalog/standard_judge_batch_015.json",
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
        "# Standard Repair Batch 56 / Owned Repair Batch 64",
        "",
        "OpenCPN-witnessed topmark shape redraws for queued `TOPSHQ*` rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Required colours |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        semantic = row.get("semantic_brief") or {}
        colours = ", ".join(semantic.get("required_colours") or []) or "reference-defined"
        lines.append(f"| `{row['asset']}` | {colours} |")
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
