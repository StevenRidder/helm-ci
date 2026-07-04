"""Repair queued HRBFAC rows into owned repair batch 62.

Run:
  python3 -m forge.standard_repair_batch54 --render
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
JUDGE_FILE = CATALOG / "standard_judge_batch_008.json"
OUT = ROOT / "out" / "standard_repair_batch54"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch62"
REPORT = CATALOG / "owned_repair_batch62.json"
SUMMARY = CATALOG / "owned_repair_batch62.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
REPAIRS = tuple(f"HRBFAC{index}" for index in range(10, 19))


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
        'data-repair-batch="standard-repair-batch54">'
        f"<title>{asset} harbour facility repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _disk(inner: str, *, shape: str) -> str:
    return (
        f'<g data-shape="{shape}">'
        f'<circle cx="32" cy="32" r="21" fill="{_colour("gray")}" stroke="{_colour("black")}" stroke-width="3"/>'
        f"{inner}</g>"
    )


def _text(label: str, *, size: int = 24, y: int = 40) -> str:
    return (
        f'<text x="32" y="{y}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="700" fill="{_colour("black")}" stroke="none">{label}</text>'
    )


def _default() -> str:
    return _disk(
        f'<path d="M32 22 V42" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>',
        shape="default_harbour_facility_vertical_mark",
    )


def _naval_base() -> str:
    return _disk(
        f'<path d="M23 43 V23 L41 43 V22" fill="none" stroke="{_colour("black")}" stroke-width="3.1"/>',
        shape="naval_base_n_mark",
    )


def _ship_yard() -> str:
    return _disk(
        f'<path d="M24 23 L32 34 L40 23 M32 34 V44" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>',
        shape="ship_yard_y_mark",
    )


def _harbour_master() -> str:
    return _disk(
        f'<path d="M32 20 V44" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
        f'<path d="M24 26 H40" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
        f'<path d="M22 40 Q32 48 42 40" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>'
        f'<path d="M22 40 L18 35 M42 40 L46 35" fill="none" stroke="{_colour("black")}" stroke-width="3.3"/>',
        shape="harbour_master_anchor_mark",
    )


def _pilot() -> str:
    return _disk(_text("P", size=26, y=41), shape="pilot_station_p_mark")


def _water_police() -> str:
    return _disk(_text("WP", size=18, y=39), shape="water_police_wp_mark")


def _customs() -> str:
    return _disk(
        f'<path d="M15 32 H49" fill="none" stroke="{_colour("black")}" stroke-width="4.2"/>',
        shape="customs_horizontal_band_mark",
    )


def _service_repair() -> str:
    return _disk(
        f'<path d="M23 22 L42 41" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<path d="M21 22 Q27 18 31 23 L25 29 Q20 28 21 22 Z" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M39 39 L45 45" fill="none" stroke="{_colour("black")}" stroke-width="4"/>',
        shape="service_repair_wrench_mark",
    )


def _quarantine() -> str:
    return _disk(
        f'<path d="M32 16 V48 M16 32 H48" fill="none" stroke="{_colour("black")}" stroke-width="4"/>',
        shape="quarantine_cross_mark",
    )


def _body(asset: str) -> str:
    return {
        "HRBFAC10": _default,
        "HRBFAC11": _naval_base,
        "HRBFAC12": _ship_yard,
        "HRBFAC13": _harbour_master,
        "HRBFAC14": _pilot,
        "HRBFAC15": _water_police,
        "HRBFAC16": _customs,
        "HRBFAC17": _service_repair,
        "HRBFAC18": _quarantine,
    }[asset]()


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
    items = {row["asset"]: row for row in queue.get("items", []) if row.get("asset") in REPAIRS}
    if len(items) == len(REPAIRS):
        return items

    judge = json.loads(JUDGE_FILE.read_text())
    for verdict in judge.get("verdicts", []):
        asset = verdict.get("symbol_id")
        if asset in REPAIRS and asset not in items:
            items[asset] = {
                "asset": asset,
                "required_change": verdict.get("required_change"),
                "judge_comments": verdict.get("judge_comments"),
                "safety_reason_codes": verdict.get("safety_reason_codes", []),
                "status": "archived_failure_fallback_for_idempotent_rebuild",
            }
    return items


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    repair_items = _repair_items()
    missing = sorted(set(REPAIRS) - set(repair_items))
    if missing:
        raise RuntimeError(f"missing HRBFAC repair queue rows: {', '.join(missing)}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        item = repair_items[asset]
        helm = source_row.get("helm_candidate") or {}
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
            "queue_action": "standard_repair_queue_hrbfac_consumed",
            "risk_bucket": "harbour_facility_reference_repair_batch62",
            "candidate_strategy": "owned_opencpn_facility_disk_redraw",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
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
                "source_priority_basis": "standard_repair_queue HRBFAC OpenCPN/S-101/AquaMap facility reference mismatch",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch54",
                "reference_role": "reference-provider images drive facility glyph vocabulary; Helm SVG remains generated-owned artwork",
            },
            "source_judge": "catalog/standard_judge_batch_008.json",
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
        "# Standard Repair Batch 54 / Owned Repair Batch 62",
        "",
        "Reference-shaped harbour-facility redraws for queued `HRBFAC10` through `HRBFAC18` rows.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Shape | Required change |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        svg = (ROOT / row["after_svg"]).read_text()
        shape = re.search(r'data-shape="([^"]+)"', svg).group(1)  # type: ignore[union-attr]
        lines.append(f"| `{row['asset']}` | `{shape}` | {row.get('required_change') or ''} |")
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
