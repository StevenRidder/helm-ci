"""Repair standard judge batch 054 failures into owned repair batch 56.

Run:
  python3 -m forge.standard_repair_batch48 --render
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
JUDGE_FILE = CATALOG / "standard_judge_batch_054_rerun.json"
OUT = ROOT / "out" / "standard_repair_batch48"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch56"
REPORT = CATALOG / "owned_repair_batch56.json"
SUMMARY = CATALOG / "owned_repair_batch56.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = (
    "BOYCON78",
    "BOYCON79",
    "BOYISD12",
    "BOYMOR01",
    "BOYMOR03",
    "BOYMOR11",
    "BOYPIL01",
    "BOYPIL73",
    "BOYSAW12",
    "BOYSPH01",
    "BOYSPH65",
    "BOYSPP11",
    "BOYSPP15",
    "BOYSPP25",
    "BOYSUP01",
    "BOYSUP03",
    "BOYSUP65",
)

CAN = "20,16 44,16 48,48 16,48"
CONE = "32,11 16,48 48,48"
PILLAR = "24,12 40,12 46,48 18,48"
SUPER = "18,18 46,18 52,40 42,52 22,52 12,40"


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch48">'
        f"<title>{asset} repair batch 56 targeted buoy/beacon candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _outline(points: str) -> str:
    return f'<polygon points="{points}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'


def _stem(y1: int = 48, y2: int = 56) -> str:
    return f'<path d="M32 {y1} V{y2}" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'


def _clip_polygon(asset: str, points: str) -> tuple[str, str]:
    clip_id = f"clip_{_safe(asset)}"
    return clip_id, f'<defs><clipPath id="{clip_id}"><polygon points="{points}"/></clipPath></defs>'


def _clip_circle(asset: str) -> tuple[str, str]:
    clip_id = f"clip_{_safe(asset)}"
    return clip_id, f'<defs><clipPath id="{clip_id}"><circle cx="32" cy="32" r="18"/></clipPath></defs>'


def _solid_polygon(asset: str, points: str, colour: str) -> str:
    clip_id, defs = _clip_polygon(asset, points)
    return (
        defs
        + f'<rect x="12" y="10" width="40" height="42" fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        + _outline(points)
        + _stem()
    )


def _banded_polygon(asset: str, points: str, colours: list[str]) -> str:
    clip_id, defs = _clip_polygon(asset, points)
    h = 42 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="12" y="{10 + index * h:.1f}" width="40" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        )
    parts.append(_outline(points))
    parts.append(_stem())
    return "".join(parts)


def _striped_polygon(asset: str, points: str, colours: list[str]) -> str:
    clip_id, defs = _clip_polygon(asset, points)
    w = 40 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{12 + index * w:.1f}" y="10" width="{w:.1f}" height="42" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-stripe"/>'
        )
    parts.append(_outline(points))
    parts.append(_stem())
    return "".join(parts)


def _solid_circle(asset: str, colour: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="{_colour(colour)}" stroke="{_colour("black")}" stroke-width="3"/>'
        + _stem(50)
    )


def _banded_circle(asset: str, colours: list[str]) -> str:
    clip_id, defs = _clip_circle(asset)
    h = 36 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="14" y="{14 + index * h:.1f}" width="36" height="{h:.1f}" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})"/>'
        )
    parts.append(f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(_stem(50))
    return "".join(parts)


def _striped_circle(asset: str, colours: list[str]) -> str:
    clip_id, defs = _clip_circle(asset)
    w = 36 / len(colours)
    parts = [defs]
    for index, colour in enumerate(colours):
        parts.append(
            f'<rect x="{14 + index * w:.1f}" y="14" width="{w:.1f}" height="36" '
            f'fill="{_colour(colour)}" clip-path="url(#{clip_id})" data-pattern="vertical-stripe"/>'
        )
    parts.append(f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("black")}" stroke-width="3"/>')
    parts.append(_stem(50))
    return "".join(parts)


def _stake_beacon(asset: str) -> str:
    clip_id, defs = _clip_polygon(asset, "23,16 41,16 45,40 19,40")
    return (
        '<path d="M32 10 V56" fill="none" stroke="var(--black)" stroke-width="4"/>'
        + defs
        + f'<rect x="19" y="16" width="13" height="24" fill="{_colour("red")}" clip-path="url(#{clip_id})"/>'
        + f'<rect x="32" y="16" width="13" height="24" fill="{_colour("green")}" clip-path="url(#{clip_id})"/>'
        + f'<polygon points="23,16 41,16 45,40 19,40" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        + f'<circle cx="32" cy="10" r="3" fill="{_colour("black")}"/>'
    )


def _isolated_danger(asset: str) -> str:
    return (
        f'<circle cx="32" cy="41" r="12" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>'
        + f'<circle cx="27" cy="23" r="6" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2" data-mark="paired-red"/>'
        + f'<circle cx="37" cy="23" r="6" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2" data-mark="paired-red"/>'
        + _stem(52)
    )


def _mooring_black_sphere(asset: str) -> str:
    return (
        f'<circle cx="32" cy="34" r="15" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="3"/>'
        + f'<circle cx="32" cy="17" r="5" fill="none" stroke="{_colour("black")}" stroke-width="3" data-mark="mooring-ring"/>'
        + _stem(49)
    )


def _mooring_black_ring(asset: str) -> str:
    return (
        f'<circle cx="32" cy="30" r="13" fill="none" stroke="{_colour("black")}" stroke-width="6" data-mark="mooring-ring"/>'
        + f'<circle cx="32" cy="47" r="7" fill="{_colour("black")}" stroke="{_colour("black")}" stroke-width="2"/>'
        + _stem(52)
    )


def _lanby_topmark() -> str:
    return (
        f'<path d="M32 8 V24 M22 16 H42 M25 9 L39 23 M39 9 L25 23" '
        f'fill="none" stroke="{_colour("black")}" stroke-width="3" data-topmark="lanby-asterisk"/>'
    )


def _body_for(asset: str) -> str:
    red_white = ["red", "white", "red", "white"]
    if asset == "BOYCON78":
        return _striped_polygon(asset, CONE, red_white)
    if asset == "BOYCON79":
        return _stake_beacon(asset)
    if asset == "BOYISD12":
        return _isolated_danger(asset)
    if asset == "BOYMOR01":
        return _mooring_black_sphere(asset)
    if asset == "BOYMOR03":
        return _banded_polygon(asset, CAN, ["green", "black"])
    if asset == "BOYMOR11":
        return _mooring_black_ring(asset)
    if asset == "BOYPIL01":
        return _solid_polygon(asset, PILLAR, "black")
    if asset == "BOYPIL73":
        return _striped_polygon(asset, PILLAR, red_white)
    if asset == "BOYSAW12":
        return _solid_circle(asset, "red")
    if asset == "BOYSPH01":
        return _banded_circle(asset, ["red", "black"])
    if asset == "BOYSPH65":
        return _striped_circle(asset, red_white)
    if asset == "BOYSPP11":
        return _solid_polygon(asset, PILLAR, "yellow")
    if asset == "BOYSPP15":
        return _solid_polygon(asset, CONE, "yellow")
    if asset == "BOYSPP25":
        return _solid_polygon(asset, CAN, "yellow")
    if asset == "BOYSUP01":
        return _banded_polygon(asset, SUPER, ["red", "black"])
    if asset == "BOYSUP03":
        return _lanby_topmark() + _banded_polygon(asset, SUPER, ["red", "black"])
    if asset == "BOYSUP65":
        return _striped_polygon(asset, SUPER, red_white)
    raise KeyError(asset)


def _repair_svg(asset: str) -> str:
    return _svg(asset, _body_for(asset))


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


def _judge_rows() -> dict[str, dict]:
    data = json.loads(JUDGE_FILE.read_text())
    return {row["symbol_id"]: row for row in data.get("verdicts", [])}


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    judge_rows = _judge_rows()
    missing_source = sorted(set(REPAIRS) - set(source_rows))
    missing_judge = sorted(set(REPAIRS) - set(judge_rows))
    if missing_source or missing_judge:
        raise RuntimeError(f"missing repair inputs: source={missing_source}, judge={missing_judge}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in REPAIRS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        judge = judge_rows[asset]
        svg = _repair_svg(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "standard_judge_batch_054_failure_consumed",
            "risk_bucket": "buoy_beacon_targeted_repair_batch56",
            "candidate_strategy": "judge54_required_change_targeted_owned_redraw",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
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
                "source_priority_basis": "standard_judge_batch_054_rerun failed-symbol required_change",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch48",
                "reference_role": "judge54 required_change and safety_reason_codes drive repair semantics",
            },
            "source_judge": "catalog/standard_judge_batch_054_rerun.json",
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
        "# Standard Repair Batch 48 / Owned Repair Batch 56",
        "",
        "Targeted owned redraws for the 17 failures from `standard_judge_batch_054_rerun`.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Required change | Safety reason codes |",
        "| --- | --- | --- |",
    ]
    for row in result["symbols"]:
        reasons = ", ".join(f"`{code}`" for code in row.get("safety_reason_codes") or []) or "-"
        change = (row.get("required_change") or "").replace("|", "\\|")
        lines.append(f"| `{row['asset']}` | {change} | {reasons} |")
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
