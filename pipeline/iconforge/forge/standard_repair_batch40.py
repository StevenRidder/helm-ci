"""Repair second TOPSHP board slice into owned repair batch 48.

Run:
  python3 -m forge.standard_repair_batch40 --render
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
OUT = ROOT / "out" / "standard_repair_batch40"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch48"
REPORT = CATALOG / "owned_repair_batch48.json"
SUMMARY = CATALOG / "owned_repair_batch48.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "TOPSHP22": "board_red",
    "TOPSHP23": "board_black",
    "TOPSHP24": "board_green",
    "TOPSHP25": "board_white_orange_vertical",
    "TOPSHP28": "board_green_white_black_vertical",
    "TOPSHP29": "board_red_green_red_vertical",
    "TOPSHP30": "board_green_green_yellow_vertical",
    "TOPSHP31": "board_orange_white_vertical",
    "TOPSHP32": "board_red_white_vertical",
    "TOPSHP33": "board_green_red_green_vertical",
    "TOPSHP34": "board_white_orange_white_vertical",
    "TOPSHP35": "board_yellow",
    "TOPSHP36": "board_orange",
    "TOPSHP37": "board_black",
    "TOPSHP38": "board_orange_white_checker",
    "TOPSHP40": "board_white_black_vertical",
    "TOPSHP41": "board_orange_orange_horizontal",
    "TOPSHP42": "board_red_white_horizontal",
    "TOPSHP43": "board_green_red_green_horizontal",
    "TOPSHP44": "board_yellow",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch40">'
        f"<title>{asset} repair batch 48 TOPSHP board candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 3.5) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _board(fill: str, *, border: str = "black", width: float = 3.2) -> str:
    return f'<rect x="19" y="12" width="26" height="40" fill="{_colour(fill)}" stroke="{_colour(border)}" stroke-width="{width}"/>'


def _vertical_board(colours: list[str], *, border: str = "black") -> str:
    w = 26 / len(colours)
    parts = []
    for i, colour in enumerate(colours):
        parts.append(f'<rect x="{19 + i * w:.1f}" y="12" width="{w:.1f}" height="40" fill="{_colour(colour)}" stroke="none"/>')
    parts.append(f'<rect x="19" y="12" width="26" height="40" fill="none" stroke="{_colour(border)}" stroke-width="3.2"/>')
    return "".join(parts)


def _horizontal_board(colours: list[str], *, border: str = "black") -> str:
    h = 40 / len(colours)
    parts = []
    for i, colour in enumerate(colours):
        parts.append(f'<rect x="19" y="{12 + i * h:.1f}" width="26" height="{h:.1f}" fill="{_colour(colour)}" stroke="none"/>')
    parts.append(f'<rect x="19" y="12" width="26" height="40" fill="none" stroke="{_colour(border)}" stroke-width="3.2"/>')
    return "".join(parts)


def _checker_board(colours: list[str], *, border: str = "black") -> str:
    parts = []
    for row in range(2):
        for col in range(2):
            colour = colours[(row * 2 + col) % len(colours)]
            parts.append(
                f'<rect x="{19 + col * 13}" y="{12 + row * 20}" width="13" height="20" '
                f'fill="{_colour(colour)}" stroke="none"/>'
            )
    parts.append(f'<rect x="19" y="12" width="26" height="40" fill="none" stroke="{_colour(border)}" stroke-width="3.2"/>')
    return "".join(parts)


def _framed_board(frame: str, fill: str = "white") -> str:
    return (
        f'<rect x="18" y="11" width="28" height="42" fill="{_colour(frame)}" stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'<rect x="24" y="18" width="16" height="28" fill="{_colour(fill)}" stroke="none"/>'
    )


def _triangle(asset: str, direction: str, colours: list[str], *, orientation: str = "horizontal", label: str | None = None) -> str:
    points = "32,10 15,48 49,48" if direction == "up" else "15,16 49,16 32,54"
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if orientation == "vertical":
        w = 34 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="{15 + i * w:.1f}" y="10" width="{w:.1f}" height="44" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    else:
        h = 44 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="15" y="{10 + i * h:.1f}" width="34" height="{h:.1f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>')
    if label:
        parts.append(
            f'<text x="32" y="37" text-anchor="middle" font-size="13" '
            f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
            f'fill="{_colour("black")}" stroke="none">{label}</text>'
        )
    return "".join(parts)


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "board_red":
        return _svg(asset, _board("red"))
    if kind == "board_black":
        return _svg(asset, _board("black"))
    if kind == "board_green":
        return _svg(asset, _board("green"))
    if kind == "board_white_orange_vertical":
        return _svg(asset, _vertical_board(["white", "orange"]))
    if kind == "board_green_white_black_vertical":
        return _svg(asset, _vertical_board(["green", "white", "black"]))
    if kind == "board_red_green_red_vertical":
        return _svg(asset, _vertical_board(["red", "green", "red"]))
    if kind == "board_green_green_yellow_vertical":
        return _svg(asset, _vertical_board(["green", "green", "yellow"]))
    if kind == "board_orange_white_vertical":
        return _svg(asset, _vertical_board(["orange", "white"]))
    if kind == "board_red_white_vertical":
        return _svg(asset, _vertical_board(["red", "white"]))
    if kind == "board_green_red_green_vertical":
        return _svg(asset, _vertical_board(["green", "red", "green"]))
    if kind == "board_white_orange_white_vertical":
        return _svg(asset, _vertical_board(["white", "orange", "white"]))
    if kind == "board_yellow":
        return _svg(asset, _board("yellow"))
    if kind == "board_orange":
        return _svg(asset, _board("orange"))
    if kind == "board_orange_white_checker":
        return _svg(asset, _checker_board(["orange", "white"]))
    if kind == "board_white_black_vertical":
        return _svg(asset, _vertical_board(["white", "black"]))
    if kind == "board_orange_orange_horizontal":
        return _svg(asset, _horizontal_board(["orange", "orange"]))
    if kind == "board_red_white_horizontal":
        return _svg(asset, _horizontal_board(["red", "white"]))
    if kind == "board_green_red_green_horizontal":
        return _svg(asset, _horizontal_board(["green", "red", "green"]))
    if kind == "board_white":
        return _svg(asset, _board("white"))
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
            "risk_bucket": "topshape_repair_batch48",
            "candidate_strategy": "owned_topshape_board_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue topmark slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch40",
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
        "# Standard Repair Batch 40 / Owned Repair Batch 48",
        "",
        "Owned redraws for second TOPSHP board judge-failure slice.",
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
