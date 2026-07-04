"""Repair table-driven remaining buoy slice into owned repair batch 54.

Run:
  python3 -m forge.standard_repair_batch46 --render
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
OUT = ROOT / "out" / "standard_repair_batch46"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch54"
REPORT = CATALOG / "owned_repair_batch54.json"
SUMMARY = CATALOG / "owned_repair_batch54.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = [
    "BOYCAN72", "BOYCON67", "BOYCON74", "BOYCON78", "BOYCON79", "BOYISD12",
    "BOYLAT13", "BOYLAT14", "BOYLAT23", "BOYLAT24", "BOYLAT25",
    "BOYLAT50", "BOYLAT51", "BOYLAT52", "BOYLAT53", "BOYLAT54", "BOYLAT55", "BOYLAT56",
    "BOYMOR01", "BOYMOR03", "BOYMOR11", "BOYMOR31",
    "BOYPIL01", "BOYPIL59", "BOYPIL60", "BOYPIL61", "BOYPIL62", "BOYPIL66", "BOYPIL67",
    "BOYPIL68", "BOYPIL69", "BOYPIL70", "BOYPIL71", "BOYPIL72", "BOYPIL73", "BOYPIL74", "BOYPIL81",
    "BOYSAW12", "BOYSPH01", "BOYSPH05", "BOYSPH60", "BOYSPH62", "BOYSPH65", "BOYSPH66",
    "BOYSPH68", "BOYSPH69", "BOYSPH70", "BOYSPH71", "BOYSPH74", "BOYSPH75", "BOYSPH77", "BOYSPH79",
    "BOYSPP11", "BOYSPP15", "BOYSPP25",
    "BOYSPR02", "BOYSPR03", "BOYSPR04", "BOYSPR05", "BOYSPR60", "BOYSPR61", "BOYSPR62",
    "BOYSPR65", "BOYSPR68", "BOYSPR69",
    "BOYSUP01", "BOYSUP02", "BOYSUP03", "BOYSUP62", "BOYSUP65", "BOYSUP66",
]

COLOUR_CODES = {
    "1": "white",
    "2": "black",
    "3": "red",
    "4": "green",
    "5": "blue",
    "6": "yellow",
    "8": "gray",
    "11": "orange",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch46">'
        f"<title>{asset} repair batch 54 table-driven buoy candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _shape_points(shape: str) -> str:
    if shape == "cone":
        return "32,11 16,48 48,48"
    if shape == "barrel":
        return "20,18 44,18 50,32 44,46 20,46 14,32"
    if shape == "pillar":
        return "24,12 40,12 46,48 18,48"
    if shape == "spar":
        return "28,10 36,10 40,52 24,52"
    if shape == "super":
        return "18,18 46,18 52,40 42,52 22,52 12,40"
    return "20,16 44,16 48,48 16,48"


def _banded_shape(asset: str, shape: str, colours: list[str]) -> str:
    if shape == "sphere":
        return _banded_circle(asset, colours)
    points = _shape_points(shape)
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    h = 40 / len(colours)
    for i, colour in enumerate(colours):
        parts.append(
            f'<rect x="12" y="{12 + i * h:.1f}" width="40" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 48 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _banded_circle(asset: str, colours: list[str]) -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><circle cx="32" cy="32" r="18"/></clipPath></defs>']
    h = 36 / len(colours)
    for i, colour in enumerate(colours):
        parts.append(
            f'<rect x="14" y="{14 + i * h:.1f}" width="36" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        )
    parts.append(f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<path d="M32 50 V56" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    return "".join(parts)


def _shape_for(asset: str) -> str:
    if asset.startswith("BOYCON"):
        return "cone"
    if asset in {"BOYLAT13", "BOYLAT14", "BOYLAT51", "BOYSPP15", "BOYSPH79"}:
        return "cone"
    if asset.startswith("BOYBAR"):
        return "barrel"
    if asset in {"BOYMOR01", "BOYMOR11"}:
        return "barrel"
    if asset.startswith("BOYPIL") or asset.startswith("BOYSPP"):
        return "pillar"
    if asset.startswith("BOYSPH") or asset in {"BOYSAW12", "BOYISD12"}:
        return "sphere"
    if asset.startswith("BOYSPR"):
        return "spar"
    if asset.startswith("BOYSUP"):
        return "super"
    return "can"


def _colours_for(row: dict) -> list[str]:
    conditions = ((row.get("s57_structure") or {}).get("conditions") or [])
    for condition in conditions:
        if not condition.startswith("COLOUR"):
            continue
        value = condition.removeprefix("COLOUR")
        parts = [part for part in re.split(r"[,.;]", value) if part]
        colours = [COLOUR_CODES.get(part) for part in parts]
        return [colour for colour in colours if colour] or ["white"]
    name = (row.get("name") or "").lower()
    for colour in ("red", "green", "yellow", "black", "orange", "blue", "white"):
        if colour in name:
            return [colour]
    return ["black" if asset_is_cardinal(row.get("asset", "")) else "white"]


def asset_is_cardinal(asset: str) -> bool:
    return asset.endswith(("68", "69", "70", "71", "72", "76"))


def _redraw(asset: str, row: dict) -> str:
    return _svg(asset, _banded_shape(asset, _shape_for(asset), _colours_for(row)))


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


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    missing_source = sorted(set(REPAIRS) - set(source_rows))
    if missing_source:
        raise RuntimeError(f"source table missing repair target(s): {missing_source}")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
        svg = _redraw(asset, source_row)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "judge_failure_consumed",
            "risk_bucket": "buoy_table_repair_batch54",
            "candidate_strategy": "table_driven_owned_buoy_redraw_from_s57_shape_and_colour_conditions",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": judge.get("required_change"),
            "safety_reason_codes": judge.get("safety_reason_codes", []),
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
                "source_priority_basis": "standard_repair_queue buoy/beacon family slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch46",
                "reference_role": "S-57 conditions drive shape/color; provider refs remain visual witnesses",
            },
            "source_judge": f"catalog/{judge.get('batch')}.json" if judge.get("batch") else None,
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
        "# Standard Repair Batch 46 / Owned Repair Batch 54",
        "",
        "Table-driven owned redraws for remaining buoy judge-failure slice.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {_shape_for(row['asset'])} / {','.join(_colours_for(row))}")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved."])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
