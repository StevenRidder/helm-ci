"""Repair a high-reference beacon slice into owned repair batch 32.

Run:
  python3 -m forge.standard_repair_batch24 --render
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
OUT = ROOT / "out" / "standard_repair_batch24"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch32"
REPORT = CATALOG / "owned_repair_batch32.json"
SUMMARY = CATALOG / "owned_repair_batch32.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "BCNDEF13": "default_rect_question",
    "BCNGEN01": "pile_beacon",
    "BCNGEN03": "pile_beacon_question",
    "BCNISD21": "isolated_danger_simplified",
    "BCNLTC01": "lattice_beacon",
    "BCNSAW13": "safe_water_major",
    "BCNSAW21": "safe_water_minor",
    "BCNSPP13": "special_purpose_major",
    "BCNSPP21": "special_purpose_minor",
    "BCNSTK02": "stake_beacon",
    "BCNTOW01": "tower_beacon",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch24">'
        f"<title>{asset} repair batch 32 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _question(x: int = 47, y: int = 17) -> str:
    return (
        f'<text x="{x}" y="{y + 24}" fill="{_colour("magenta")}" font-family="Arial, sans-serif" '
        'font-size="28" font-weight="700" text-anchor="middle">?</text>'
    )


def _rect_beacon(x: int, y: int, w: int, h: int, fill: str, *, dot: str | None = None) -> str:
    dot_svg = ""
    if dot:
        dot_svg = f'<circle cx="{x + w / 2:g}" cy="{y + h / 2:g}" r="3.1" fill="{dot}" stroke="none"/>'
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="1.5" fill="{fill}" '
        f'stroke="{_colour("black")}" stroke-width="4"/>'
        f"{dot_svg}"
    )


def _default_rect_question() -> str:
    return _rect_beacon(15, 8, 19, 38, _colour("gray")) + _question(49, 15)


def _pile_beacon(*, question: bool = False) -> str:
    body = (
        f'<path d="M31 10 V50" fill="none" stroke="{_colour("black")}" stroke-width="7"/>'
        f'<path d="M18 46 H46" fill="none" stroke="{_colour("black")}" stroke-width="5"/>'
        f'<circle cx="32" cy="50" r="7" fill="{_colour("blue")}" stroke="{_colour("black")}" stroke-width="4"/>'
    )
    return body + (_question(49, 15) if question else "")


def _isolated_danger_simplified() -> str:
    return (
        f'<circle cx="32" cy="22" r="9.5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<circle cx="32" cy="45" r="9.5" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="4"/>'
    )


def _lattice_beacon() -> str:
    c = _colour("black")
    return (
        f'<path d="M17 54 L24 13 H40 L47 54 Z" fill="none" stroke="{c}" stroke-width="5"/>'
        f'<path d="M23 20 L41 28 L21 38 L43 46 M41 20 L23 28 L43 38 L21 46" fill="none" stroke="{c}" stroke-width="3.7"/>'
        f'<path d="M13 55 H51" fill="none" stroke="{c}" stroke-width="6"/>'
        f'<circle cx="32" cy="55" r="7" fill="{_colour("white")}" stroke="{c}" stroke-width="4"/>'
    )


def _safe_water_major() -> str:
    return _rect_beacon(22, 8, 20, 48, _colour("black"), dot=_colour("blue"))


def _safe_water_minor() -> str:
    return _rect_beacon(27, 10, 10, 44, _colour("black"), dot=_colour("blue"))


def _special_purpose_major() -> str:
    return _rect_beacon(20, 10, 24, 44, _colour("yellow"), dot=_colour("black"))


def _special_purpose_minor() -> str:
    return _rect_beacon(27, 10, 11, 44, _colour("yellow"), dot=_colour("black"))


def _stake_beacon() -> str:
    c = _colour("black")
    return f'<path d="M32 12 V53 M18 53 H46" fill="none" stroke="{c}" stroke-width="7"/>'


def _tower_beacon() -> str:
    c = _colour("black")
    return (
        f'<path d="M17 55 L25 13 H39 L47 55" fill="none" stroke="{c}" stroke-width="5"/>'
        f'<path d="M14 55 H50" fill="none" stroke="{c}" stroke-width="6"/>'
        f'<circle cx="32" cy="55" r="7" fill="{_colour("white")}" stroke="{c}" stroke-width="4"/>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "default_rect_question":
        return _svg(asset, _default_rect_question())
    if kind == "pile_beacon":
        return _svg(asset, _pile_beacon())
    if kind == "pile_beacon_question":
        return _svg(asset, _pile_beacon(question=True))
    if kind == "isolated_danger_simplified":
        return _svg(asset, _isolated_danger_simplified())
    if kind == "lattice_beacon":
        return _svg(asset, _lattice_beacon())
    if kind == "safe_water_major":
        return _svg(asset, _safe_water_major())
    if kind == "safe_water_minor":
        return _svg(asset, _safe_water_minor())
    if kind == "special_purpose_major":
        return _svg(asset, _special_purpose_major())
    if kind == "special_purpose_minor":
        return _svg(asset, _special_purpose_minor())
    if kind == "stake_beacon":
        return _svg(asset, _stake_beacon())
    if kind == "tower_beacon":
        return _svg(asset, _tower_beacon())
    raise KeyError(f"unsupported repair kind: {kind}")


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
    for asset in sorted(REPAIRS):
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "chart1_or_judge_failure_consumed",
            "risk_bucket": "high_reference_beacon_repair_batch32",
            "candidate_strategy": "owned_redraw_from_s101_opencpn_aquamap_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": source_row.get("required_change"),
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue high-reference beacon slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch24",
                "reference_role": "S-101/OpenCPN/AquaMap refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": None,
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "failed_repaired": len(rows),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 24 / Owned Repair Batch 32",
        "",
        "Owned redraws for a high-reference beacon slice.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('name')}")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved."])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
