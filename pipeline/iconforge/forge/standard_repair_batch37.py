"""Repair industrial/signal/utility glyph slice into owned repair batch 45.

Run:
  python3 -m forge.standard_repair_batch37 --render
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
OUT = ROOT / "out" / "standard_repair_batch37"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch45"
REPORT = CATALOG / "owned_repair_batch45.json"
SUMMARY = CATALOG / "owned_repair_batch45.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "REFDMP01": "refuse_dump",
    "RFNERY01": "refinery_brown",
    "RFNERY11": "refinery_black",
    "RTLDEF51": "route_unknown",
    "SCALEB10": "scale_one",
    "SCALEB11": "scale_ten",
    "SILBUI01": "silo_brown",
    "SILBUI11": "silo_black",
    "SISTAT02": "signal_station",
    "SSENTR01": "signal_entry",
    "SSLOCK01": "signal_lock",
    "SSWARS01": "signal_wahrschau",
    "STARPT01": "star_point",
    "TMBYRD01": "timber_yard",
    "TNKCON02": "tank_brown",
    "TNKCON12": "tank_black",
    "TNKFRM01": "tank_farm_brown",
    "TNKFRM11": "tank_farm_black",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch37">'
        f"<title>{asset} repair batch 45 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 3.5, dash: str | None = None) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"{extra}/>'


def _text(label: str, colour: str = "black", y: int = 38, size: int = 16) -> str:
    return (
        f'<text x="32" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _refuse_dump() -> str:
    return (
        f'<rect x="22" y="24" width="20" height="24" rx="3" fill="none" stroke="{_colour("green")}" stroke-width="3.5"/>'
        + _path("M20 22 H44 M26 18 H38 M27 29 V44 M32 29 V44 M37 29 V44", "black", 2.5)
    )


def _refinery(colour: str) -> str:
    return (
        _path("M20 51 V25 H31 V51 M33 51 V17 H45 V51 M16 51 H49", colour, 3.5)
        + _path("M24 25 C26 18 31 18 33 25", colour, 3)
        + _path("M38 17 C41 9 47 10 48 17", colour, 3)
    )


def _route_unknown() -> str:
    return (
        _path("M14 38 C24 26 40 26 50 38", "magenta", 3.2, "6 5")
        + _path("M42 29 L51 38 L42 47", "magenta", 3.2)
        + _text("?", "magenta", 26, 17)
        + _text("?", "magenta", 55, 17)
    )


def _scale(label: str, segments: int) -> str:
    y0 = 10
    seg_h = 44 / segments
    pieces = []
    for i in range(segments):
        fill = "black" if i % 2 == 0 else "white"
        y = y0 + i * seg_h
        pieces.append(
            f'<rect x="25" y="{y:.1f}" width="14" height="{seg_h:.1f}" fill="{_colour(fill)}" '
            f'stroke="{_colour("black")}" stroke-width="1.8"/>'
        )
    return "".join(pieces) + _path("M43 10 H50 M43 54 H50", "black", 2.4) + _text(label, "black", 34, 11)


def _silo(colour: str) -> str:
    return (
        f'<ellipse cx="32" cy="21" rx="11" ry="6" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        + _path("M21 21 V46 C21 54 43 54 43 46 V21", colour, 3.2)
        + _path("M21 46 C21 54 43 54 43 46", colour, 3.2)
    )


def _signal(label: str) -> str:
    return (
        f'<rect x="16" y="17" width="32" height="24" rx="3" fill="none" stroke="{_colour("black")}" stroke-width="3.5"/>'
        + _text(label, "black", 35, 14)
        + _path("M32 41 V54 M23 54 H41", "black", 3.5)
    )


def _star() -> str:
    return f'<path d="M32 9 L37 25 L54 25 L40 35 L45 52 L32 42 L19 52 L24 35 L10 25 L27 25 Z" fill="{_colour("black")}" stroke="none"/>'


def _timber_yard() -> str:
    return (
        _path("M15 20 H49 M15 32 H49 M15 44 H49", "brown", 3)
        + _path("M20 15 V49 M32 15 V49 M44 15 V49", "brown", 3)
    )


def _tank(colour: str) -> str:
    return f'<circle cx="32" cy="32" r="17" fill="none" stroke="{_colour(colour)}" stroke-width="4.2"/>'


def _tank_farm(colour: str) -> str:
    dots = "".join(
        f'<circle cx="{x}" cy="{y}" r="3.2" fill="{_colour(colour)}" stroke="none"/>'
        for x, y in [(26, 27), (38, 27), (26, 39), (38, 39), (32, 33)]
    )
    return f'<circle cx="32" cy="33" r="19" fill="none" stroke="{_colour(colour)}" stroke-width="3.5"/>{dots}'


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "refuse_dump":
        return _svg(asset, _refuse_dump())
    if kind == "refinery_brown":
        return _svg(asset, _refinery("brown"))
    if kind == "refinery_black":
        return _svg(asset, _refinery("black"))
    if kind == "route_unknown":
        return _svg(asset, _route_unknown())
    if kind == "scale_one":
        return _svg(asset, _scale("1", 4))
    if kind == "scale_ten":
        return _svg(asset, _scale("10", 5))
    if kind == "silo_brown":
        return _svg(asset, _silo("brown"))
    if kind == "silo_black":
        return _svg(asset, _silo("black"))
    if kind == "signal_station":
        return _svg(asset, _signal("SS"))
    if kind == "signal_entry":
        return _svg(asset, _signal("PE"))
    if kind == "signal_lock":
        return _svg(asset, _signal("LK"))
    if kind == "signal_wahrschau":
        return _svg(asset, _signal("WS"))
    if kind == "star_point":
        return _svg(asset, _star())
    if kind == "timber_yard":
        return _svg(asset, _timber_yard())
    if kind == "tank_brown":
        return _svg(asset, _tank("brown"))
    if kind == "tank_black":
        return _svg(asset, _tank("black"))
    if kind == "tank_farm_brown":
        return _svg(asset, _tank_farm("brown"))
    if kind == "tank_farm_black":
        return _svg(asset, _tank_farm("black"))
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
            "risk_bucket": "industrial_signal_utility_repair_batch45",
            "candidate_strategy": "owned_industrial_signal_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue industrial/signal/utility slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch37",
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
        "# Standard Repair Batch 37 / Owned Repair Batch 45",
        "",
        "Owned redraws for industrial, signal, and utility judge failures.",
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
