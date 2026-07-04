"""Repair final evidence-backed hard-queue rows into owned batch 84.

Run:
  python3 -m forge.standard_repair_batch76 --render
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
OUT = ROOT / "out" / "standard_repair_batch76"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch84"
REPORT = CATALOG / "owned_repair_batch84.json"
SUMMARY = CATALOG / "owned_repair_batch84.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

TARGETS = {
    "BCNCON81": "conical_blue_red_white_blue",
    "TOPSHP09;TE('%s'": "small_triangle_red_red_green",
    "TOPSHP15;TE('%s'": "small_triangle_red_red_yellow",
    "TOPSHP33": "slanted_hollow_square_topmark",
    "TOWERS74|;TX(OBJNAM": "thin_tower_white_orange",
    "VEHTRF01": "vehicle_traffic_signal",
    "boyspp50": "yellow_special_purpose_buoy",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{'gray' if name == 'grey' else name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch76">'
        f"<title>{asset} hard-queue repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _banded_cone(colours: list[str]) -> str:
    points = "32,11 47,49 17,49"
    clip_id = "clip_bcncon81_cone"
    h = 38 / len(colours)
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="17" y="{11 + index * h:.1f}" width="30" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>')
    parts.append(f'<path d="M32 49 V56" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>')
    return "".join(parts)


def _small_triangle(asset: str, colours: list[str]) -> str:
    points = "32,18 22,42 42,42"
    clip_id = f"clip_{_safe(asset)}"
    h = 24 / len(colours)
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="22" y="{18 + index * h:.1f}" width="20" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="s57-horizontal-topmark"/>'
        )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>')
    parts.append(
        f'<text x="32" y="56" text-anchor="middle" font-size="8" font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="700" fill="{_colour("black")}" stroke="none" data-cue="s52-text-bearing-row">T</text>'
    )
    return "".join(parts)


def _slanted_square() -> str:
    return (
        f'<path d="M27 21 H40 L37 43 H24 Z" fill="{_colour("white")}" '
        f'stroke="{_colour("black")}" stroke-width="2.4"/>'
        f'<path d="M29 25 H36 L34 39 H27 Z" fill="{_colour("white")}" stroke="none"/>'
    )


def _tower() -> str:
    return (
        f'<path d="M32 14 L43 48 H21 Z" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M28 25 H36 M26 34 H38 M24 43 H40" fill="none" stroke="{_colour("orange")}" stroke-width="1.8"/>'
        f'<path d="M32 14 V48 M24 48 H40" fill="none" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _vehicle_traffic() -> str:
    return (
        f'<rect x="21" y="18" width="22" height="28" rx="3" fill="{_colour("white")}" '
        f'stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<circle cx="32" cy="26" r="3.2" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="1.0"/>'
        f'<circle cx="32" cy="36" r="3.2" fill="{_colour("green")}" stroke="{_colour("black")}" stroke-width="1.0"/>'
        f'<path d="M24 50 H40" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M32 46 V50" fill="none" stroke="{_colour("black")}" stroke-width="1.4"/>'
    )


def _yellow_buoy() -> str:
    return (
        f'<path d="M26 39 C26 32 29 26 32 22 C35 26 38 32 38 39 Z" '
        f'fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M25 39 H39" fill="none" stroke="{_colour("black")}" stroke-width="1.8"/>'
        f'<path d="M32 18 V22" fill="none" stroke="{_colour("black")}" stroke-width="1.6"/>'
    )


def _body(asset: str) -> str:
    kind = TARGETS[asset]
    if kind == "conical_blue_red_white_blue":
        return _banded_cone(["blue", "red", "white", "blue"])
    if kind == "small_triangle_red_red_green":
        return _small_triangle(asset, ["red", "red", "green"])
    if kind == "small_triangle_red_red_yellow":
        return _small_triangle(asset, ["red", "red", "yellow"])
    if kind == "slanted_hollow_square_topmark":
        return _slanted_square()
    if kind == "thin_tower_white_orange":
        return _tower()
    if kind == "vehicle_traffic_signal":
        return _vehicle_traffic()
    if kind == "yellow_special_purpose_buoy":
        return _yellow_buoy()
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
        raise RuntimeError("no batch76 target rows in standard repair queue")

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
            "queue_action": "standard_hard_queue_reference_improved",
            "risk_bucket": "final_hard_queue_candidate_repair_batch84",
            "candidate_strategy": "owned_thin_redraw_from_chart1_crop_s57_metadata_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue remaining evidence-backed rows",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch76",
                "reference_role": "Chart 1 crops, S-57 metadata, and provider witnesses guide generated-owned redraw",
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
        "blockers": [
            {
                "asset": asset,
                "reason": "kept_in_repair_queue_until_exact_reference_crop_or_render_exists",
            }
            for asset in ("DANGER53", "DGPS01DRFSTA01", "NEWOBJ 01", "NEWOBJ01")
        ],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 76 / Owned Repair Batch 84",
        "",
        "Owned redraws for remaining evidence-backed hard-queue rows. These are better candidates, not approvals.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "- exact-reference blockers preserved: `4`",
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
