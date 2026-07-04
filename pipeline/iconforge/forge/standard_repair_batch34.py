"""Repair NMKREG regulation notice slice into owned repair batch 42.

Run:
  python3 -m forge.standard_repair_batch34 --render
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
OUT = ROOT / "out" / "standard_repair_batch34"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch42"
REPORT = CATALOG / "owned_repair_batch42.json"
SUMMARY = CATALOG / "owned_repair_batch42.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "NMKREG01": "general_regulation",
    "NMKREG02": "mandatory_left",
    "NMKREG03": "mandatory_right",
    "NMKREG10": "mandatory_stop",
    "NMKREG11": "sound_signal",
    "NMKREG12": "special_attention",
    "NMKREG13": "give_way_entering",
    "NMKREG14": "give_way_crossing",
    "NMKREG15": "radiophone",
    "NMKREG16": "restricted_depth",
    "NMKREG17": "restricted_clearance",
    "NMKREG19": "restricted_width_left",
    "NMKREG20": "restricted_width_right",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch34">'
        f"<title>{asset} repair batch 42 regulation candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "white", width: float = 4) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _text(label: str, y: int = 39, size: int = 16) -> str:
    return (
        f'<text x="32" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour("white")}" stroke="none">{label}</text>'
    )


def _board(inner: str) -> str:
    return (
        f'<rect x="9" y="9" width="46" height="46" rx="3" fill="{_colour("red")}" '
        f'stroke="{_colour("black")}" stroke-width="2.8"/>'
        f"{inner}"
    )


def _general_regulation() -> str:
    return _board(
        f'<rect x="18" y="18" width="28" height="28" fill="{_colour("white")}" stroke="none"/>'
        f'<rect x="23" y="23" width="18" height="18" fill="none" stroke="{_colour("red")}" stroke-width="3"/>'
    )


def _mandatory_arrow(direction: str) -> str:
    if direction == "left":
        d = "M44 32 H20 M27 24 L20 32 L27 40"
    else:
        d = "M20 32 H44 M37 24 L44 32 L37 40"
    return _board(_path(d, "white", 5))


def _mandatory_stop() -> str:
    return _board(_path("M18 32 H46", "white", 7) + _text("STOP", 47, 10))


def _sound_signal() -> str:
    return _board(
        f'<path d="M18 38 H25 L37 47 V17 L25 26 H18 Z" fill="none" '
        f'stroke="{_colour("white")}" stroke-width="3.5"/>'
        + _path("M42 25 C47 29 47 35 42 39 M47 20 C55 27 55 37 47 44", "white", 3)
    )


def _attention() -> str:
    return _board(_path("M32 18 V38", "white", 6) + f'<circle cx="32" cy="46" r="3.5" fill="{_colour("white")}" stroke="none"/>')


def _give_way(kind: str) -> str:
    main = _path("M32 15 V49", "white", 8)
    if kind == "entering":
        side = _path("M17 35 H47", "white", 4) + _path("M40 28 L47 35 L40 42", "white", 4)
    else:
        side = _path("M17 32 H47", "white", 6)
    triangle = f'<polygon points="32,18 44,42 20,42" fill="none" stroke="{_colour("white")}" stroke-width="3.5"/>'
    return _board(main + side + triangle)


def _radiophone() -> str:
    return _board(_text("VHF", 36, 16) + _path("M22 44 H42", "white", 3))


def _restricted_depth() -> str:
    return _board(_path("M20 24 H44 M20 44 H44", "white", 4) + _text("D", 38, 18))


def _restricted_clearance() -> str:
    return _board(_path("M22 18 H42 M22 46 H42 M32 20 V44 M26 27 L32 20 L38 27 M26 37 L32 44 L38 37", "white", 3.3))


def _restricted_width(side: str) -> str:
    if side == "left":
        block = f'<rect x="14" y="16" width="14" height="32" fill="{_colour("white")}" stroke="none"/>'
        arrows = _path("M32 32 H48 M41 25 L48 32 L41 39", "white", 3.5)
    else:
        block = f'<rect x="36" y="16" width="14" height="32" fill="{_colour("white")}" stroke="none"/>'
        arrows = _path("M32 32 H16 M23 25 L16 32 L23 39", "white", 3.5)
    return _board(block + arrows)


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "general_regulation":
        return _svg(asset, _general_regulation())
    if kind == "mandatory_left":
        return _svg(asset, _mandatory_arrow("left"))
    if kind == "mandatory_right":
        return _svg(asset, _mandatory_arrow("right"))
    if kind == "mandatory_stop":
        return _svg(asset, _mandatory_stop())
    if kind == "sound_signal":
        return _svg(asset, _sound_signal())
    if kind == "special_attention":
        return _svg(asset, _attention())
    if kind == "give_way_entering":
        return _svg(asset, _give_way("entering"))
    if kind == "give_way_crossing":
        return _svg(asset, _give_way("crossing"))
    if kind == "radiophone":
        return _svg(asset, _radiophone())
    if kind == "restricted_depth":
        return _svg(asset, _restricted_depth())
    if kind == "restricted_clearance":
        return _svg(asset, _restricted_clearance())
    if kind == "restricted_width_left":
        return _svg(asset, _restricted_width("left"))
    if kind == "restricted_width_right":
        return _svg(asset, _restricted_width("right"))
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
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = (source_row.get("judge") or {}).get("latest") or {}
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
            "queue_action": "judge_failure_consumed",
            "risk_bucket": "regulation_notice_repair_batch42",
            "candidate_strategy": "owned_regulation_notice_redraw_from_semantic_brief_and_provider_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": judge.get("required_change"),
            "safety_reason_codes": judge.get("safety_reason_codes", []),
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
                "source_priority_basis": "standard_repair_queue NMKREG notice slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch34",
                "reference_role": "provider refs and semantic_brief are shape witnesses; SVG is owned redraw",
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
        "# Standard Repair Batch 34 / Owned Repair Batch 42",
        "",
        "Owned redraws for regulation notice judge failures.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {REPAIRS[row['asset']]}")
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
