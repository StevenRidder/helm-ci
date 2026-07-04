"""Repair queued TERMNL terminal rows into owned batch 74.

Run:
  python3 -m forge.standard_repair_batch66 --render
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
OUT = ROOT / "out" / "standard_repair_batch66"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch74"
REPORT = CATALOG / "owned_repair_batch74.json"
SUMMARY = CATALOG / "owned_repair_batch74.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "TERMNL01": "passenger",
    "TERMNL03": "container",
    "TERMNL04": "bulk",
    "TERMNL07": "chemical",
    "TERMNL12": "cargo",
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
        'data-repair-batch="standard-repair-batch66">'
        f"<title>{asset} terminal reference repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _badge(inner: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="20" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f"{inner}"
    )


def _passenger() -> str:
    return _badge(
        f'<path d="M18 34 H46 L40 40 H24 Z" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M22 33 Q32 24 42 33" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M23 37 H41" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _container() -> str:
    parts = [
        f'<rect x="21" y="25" width="8" height="8" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.8"/>',
        f'<rect x="30" y="25" width="8" height="8" fill="{_colour("green")}" stroke="{_colour("black")}" stroke-width="1.8"/>',
        f'<rect x="25" y="34" width="8" height="8" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.8"/>',
        f'<rect x="34" y="34" width="8" height="8" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.8"/>',
        f'<path d="M22 42 H43" fill="none" stroke="{_colour("black")}" stroke-width="2"/>',
    ]
    return _badge("".join(parts))


def _bulk() -> str:
    return _badge(
        f'<path d="M20 42 L29 25 L34 42 Z" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2"/>'
        f'<path d="M30 42 L38 27 L46 42 Z" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M32 21 V31 M27 26 H37" fill="none" stroke="{_colour("black")}" stroke-width="2"/>'
    )


def _chemical() -> str:
    return _badge(
        f'<text x="32" y="36" text-anchor="middle" font-size="13" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour("black")}" stroke="none">che</text>'
    )


def _cargo() -> str:
    return _badge(
        f'<path d="M24 44 V23 H36" fill="none" stroke="{_colour("black")}" stroke-width="2.6"/>'
        f'<path d="M24 27 H38 V42 H24" fill="none" stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M36 23 L43 29 V36" fill="none" stroke="{_colour("black")}" stroke-width="2.2"/>'
        f'<circle cx="43" cy="38" r="2.2" fill="{_colour("black")}" stroke="none"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "passenger":
        return _passenger()
    if kind == "container":
        return _container()
    if kind == "bulk":
        return _bulk()
    if kind == "chemical":
        return _chemical()
    if kind == "cargo":
        return _cargo()
    raise KeyError(f"unsupported TERMNL target: {asset}")


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
        raise RuntimeError("no TERMNL rows in standard repair queue")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
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
            "queue_action": "standard_termnl_reference_consumed",
            "risk_bucket": "terminal_reference_repair_batch74",
            "candidate_strategy": "owned_terminal_badge_redraw_from_opencpn_reference",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": f"catalog/{judge.get('batch')}.json" if judge.get("batch") else None,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue TERMNL terminal blocker",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch66",
                "reference_role": "OpenCPN terminal badge witness and S-57 metadata drive generated-owned redraw",
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
        "# Standard Repair Batch 66 / Owned Repair Batch 74",
        "",
        "OpenCPN-reference repair pass for queued `TERMNL*` terminal badge rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Strategy |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | {TARGETS[row['asset']]} |")
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
