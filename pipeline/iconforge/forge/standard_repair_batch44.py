"""Repair final TOPSHP topmark slice into owned repair batch 52.

Run:
  python3 -m forge.standard_repair_batch44 --render
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
OUT = ROOT / "out" / "standard_repair_batch44"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch52"
REPORT = CATALOG / "owned_repair_batch52.json"
SUMMARY = CATALOG / "owned_repair_batch52.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "TOPSHPT2": "slanted_red_white_vertical",
    "TOPSHPT3": "slanted_black",
    "TOPSHPT4": "slanted_black_white_vertical",
    "TOPSHPT5": "slanted_white_black_vertical",
    "TOPSHPT6": "slanted_orange_black_vertical",
    "TOPSHPT7": "slanted_black_orange_vertical",
    "TOPSHPT8;TE('%s'": "slanted_white_black_white_vertical_text",
    "TOPSHPU1": "triangle_green",
    "TOPSHPU2": "triangle_white_red_diagonal",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch44">'
        f"<title>{asset} repair batch 52 final TOPSHP topmark candidate</title>"
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


def _diamond_board(asset: str, colours: list[str], *, pattern: str = "solid", label: str | None = None) -> str:
    points = "32,8 56,32 32,56 8,32"
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if pattern == "vertical":
        w = 48 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="{8 + i * w:.1f}" y="8" width="{w:.1f}" height="48" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    elif pattern == "horizontal":
        h = 48 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="8" y="{8 + i * h:.1f}" width="48" height="{h:.1f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    elif pattern == "checker":
        for row in range(2):
            for col in range(2):
                colour = colours[(row * 2 + col) % len(colours)]
                parts.append(
                    f'<rect x="{8 + col * 24}" y="{8 + row * 24}" width="24" height="24" '
                    f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
                )
    else:
        parts.append(f'<polygon points="{points}" fill="{_colour(colours[0])}" stroke="none"/>')
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    if label:
        parts.append(
            f'<text x="32" y="37" text-anchor="middle" font-size="13" '
            f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
            f'fill="{_colour("black")}" stroke="none">{label}</text>'
        )
    return "".join(parts)


def _slanted_board(
    asset: str,
    colours: list[str],
    *,
    pattern: str = "solid",
    label: str | None = None,
    border: bool = False,
) -> str:
    points = "24,10 52,18 40,54 12,46"
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if pattern == "vertical":
        w = 40 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="{12 + i * w:.1f}" y="10" width="{w:.1f}" height="44" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    elif pattern == "horizontal":
        h = 44 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="12" y="{10 + i * h:.1f}" width="40" height="{h:.1f}" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    elif pattern == "checker":
        for row in range(2):
            for col in range(2):
                colour = colours[(row * 2 + col) % len(colours)]
                parts.append(
                    f'<rect x="{12 + col * 20}" y="{10 + row * 22}" width="20" height="22" '
                    f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
                )
    else:
        parts.append(f'<polygon points="{points}" fill="{_colour(colours[0])}" stroke="none"/>')
    if border:
        parts.append(f'<polygon points="27,15 47,21 37,49 17,43" fill="none" stroke="{_colour("white")}" stroke-width="3"/>')
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    if label:
        parts.append(
            f'<text x="32" y="37" text-anchor="middle" font-size="12" '
            f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
            f'fill="{_colour("black")}" stroke="none">{label}</text>'
        )
    return "".join(parts)


def _round_board(asset: str, colours: list[str], *, pattern: str = "solid") -> str:
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><circle cx="32" cy="32" r="20"/></clipPath></defs>']
    if pattern == "vertical":
        w = 40 / len(colours)
        for i, colour in enumerate(colours):
            parts.append(
                f'<rect x="{12 + i * w:.1f}" y="12" width="{w:.1f}" height="40" '
                f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
            )
    else:
        parts.append(f'<circle cx="32" cy="32" r="20" fill="{_colour(colours[0])}" stroke="none"/>')
    parts.append(f'<circle cx="32" cy="32" r="20" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(f'<circle cx="32" cy="32" r="5" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.4"/>')
    return "".join(parts)


def _x_topmark(colours: list[str], *, diagonal: bool = False) -> str:
    if diagonal:
        return (
            _path("M18 46 L46 18", colours[0], 7)
            + _path("M18 18 L46 46", colours[-1], 7)
            + _path("M18 46 L46 18 M18 18 L46 46", "black", 2.4)
        )
    return _path("M18 18 L46 46 M46 18 L18 46", colours[0], 7)


def _staff(colours: list[str], *, horizontal: bool = False) -> str:
    if horizontal and len(colours) > 1:
        return _path("M18 46 L46 18", colours[0], 8) + _path("M23 51 L51 23", colours[1], 5) + _path("M18 46 L46 18", "black", 2.2)
    if len(colours) == 3:
        return _path("M20 48 L44 16", colours[0], 9) + _path("M24 43 L40 21", colours[1], 5) + _path("M20 48 L44 16", "black", 2.2)
    return _path("M20 48 L44 16", colours[0], 7)


def _triangle_topmark(asset: str, colours: list[str], *, diagonal: bool = False) -> str:
    points = "32,10 14,50 50,50"
    clip_id = f"clip_{_safe(asset)}"
    parts = [f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>']
    if diagonal:
        parts.append(f'<polygon points="14,10 50,10 14,50" fill="{_colour(colours[0])}" clip-path="url(#{clip_id})"/>')
        parts.append(f'<polygon points="50,10 50,50 14,50" fill="{_colour(colours[1])}" clip-path="url(#{clip_id})"/>')
    else:
        parts.append(f'<polygon points="{points}" fill="{_colour(colours[0])}" stroke="none"/>')
    parts.append(f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
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
    if kind == "slanted_red_white_vertical":
        return _svg(asset, _slanted_board(asset, ["red", "white"], pattern="vertical"))
    if kind == "slanted_black":
        return _svg(asset, _slanted_board(asset, ["black"]))
    if kind == "slanted_black_white_vertical":
        return _svg(asset, _slanted_board(asset, ["black", "white"], pattern="vertical"))
    if kind == "slanted_white_black_vertical":
        return _svg(asset, _slanted_board(asset, ["white", "black"], pattern="vertical"))
    if kind == "slanted_orange_black_vertical":
        return _svg(asset, _slanted_board(asset, ["orange", "black"], pattern="vertical"))
    if kind == "slanted_black_orange_vertical":
        return _svg(asset, _slanted_board(asset, ["black", "orange"], pattern="vertical"))
    if kind == "slanted_white_black_white_vertical_text":
        return _svg(asset, _slanted_board(asset, ["white", "black", "white"], pattern="vertical", label="T"))
    if kind == "triangle_green":
        return _svg(asset, _triangle_topmark(asset, ["green"]))
    if kind == "triangle_white_red_diagonal":
        return _svg(asset, _triangle_topmark(asset, ["white", "red"], diagonal=True))
    if kind == "slanted_white_black_white_vertical":
        return _svg(asset, _slanted_board(asset, ["white", "black", "white"], pattern="vertical"))
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
            "risk_bucket": "topshape_repair_batch52",
            "candidate_strategy": "owned_final_topshape_redraw_from_semantic_brief_and_provider_witnesses",
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
                "generator": "forge.standard_repair_batch44",
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
        "# Standard Repair Batch 44 / Owned Repair Batch 52",
        "",
        "Owned redraws for final TOPSHP topmark judge-failure slice.",
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
