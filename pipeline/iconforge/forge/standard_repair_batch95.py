"""Repair Aqua Map-backed pictogram failures into owned batch 95.

Run:
  python3 -m forge.standard_repair_batch95 --render
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
OUT = ROOT / "out" / "standard_repair_batch95"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch95"
REPORT = CATALOG / "owned_repair_batch95.json"
SUMMARY = CATALOG / "owned_repair_batch95.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
SOURCE_JUDGE = "catalog/standard_judge_batch_088_091_initial.json"

TARGETS = {
    "LIGHTS05": "light_flare_teardrop",
    "OBSTRN04": "bottom_obstruction_dotted_circle",
    "TOWERS74|;TX(OBJNAM": "tower_landmark_rectangular_body",
    "WRECKS02": "submerged_wreck_dotted_hull",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch95">'
        f"<title>{asset} Aqua Map-backed pictogram repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _text(text: str, x: float, y: float, colour: str = "black", size: float = 7.0) -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" text-anchor="middle" font-size="{size:g}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="600" '
        f'fill="{_colour(colour)}" stroke="none">{text}</text>'
    )


def _body(asset: str) -> str:
    if asset == "LIGHTS05":
        return '<path d="M18 18 C31 22 44 30 47 40 C43 46 36 46 30 40 C25 35 21 26 18 18 Z" fill="var(--magenta)" fill-opacity="0.55" stroke="var(--black)" stroke-width="1.2"/>'
    if asset == "OBSTRN04":
        return '<circle cx="32" cy="28" r="8" fill="none" stroke="var(--gray)" stroke-width="1.3" stroke-dasharray="1.2 2.6"/>' + _text("Obstn", 32, 44, "black", 7.0)
    if asset == "TOWERS74|;TX(OBJNAM":
        return (
            '<rect x="25" y="18" width="14" height="28" fill="var(--yellow)" fill-opacity="0.45" stroke="var(--black)" stroke-width="1.2"/>'
            '<path d="M28 46 H36 M26 50 H23 M38 50 H41 M25 18 H39" fill="none" stroke="var(--black)" stroke-width="1.1"/>'
            '<circle cx="30" cy="26" r="1.2" fill="var(--black)" stroke="none"/>'
            '<circle cx="34" cy="34" r="1.2" fill="var(--black)" stroke="none"/>'
        )
    if asset == "WRECKS02":
        return '<path d="M18 39 C27 29 39 23 50 20" fill="none" stroke="var(--blue)" stroke-width="1.4" stroke-dasharray="1.2 3"/>' + _text("Wk", 38, 47, "black", 7.0)
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
    return {row["asset"]: row for row in json.loads(SOURCE_TABLE.read_text())["rows"]}


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
        raise RuntimeError("no batch95 rows in standard repair queue")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        asset = item["asset"]
        source_row = source_rows[asset]
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
            "queue_action": "standard_aquamap_pictogram_failure_consumed",
            "risk_bucket": "aquamap_pictogram_repair_batch95",
            "candidate_strategy": f"owned_{TARGETS[asset]}_redraw_from_aquamap_witness",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": item.get("required_change"),
            "safety_reason_codes": item.get("safety_reason_codes", []),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "source_judge": SOURCE_JUDGE,
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue Aqua Map-backed pictogram failures",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch95",
                "reference_role": "Aqua Map support-page witnesses guide generated-owned redraw; source images are not canonical art",
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
        "# Owned Repair Batch 95",
        "",
        "- Source: Aqua Map-backed rows from `standard_repair_queue`",
        "- Status: `repair_batch_pending_judge_rerun`",
        "- Final approval: none; visual judge plus human review still required.",
        "",
        "| Asset | Strategy | After SVG | Required change |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(
            f"| `{row['asset']}` | {row['candidate_strategy']} | `{row['after_svg']}` | "
            f"{row.get('required_change') or ''} |"
        )
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="also rasterize day/dusk/night preview PNGs")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": "ok", "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
