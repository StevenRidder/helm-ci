"""Repair the traffic-separation / two-way route slice into owned batch 28.

Run:
  python3 -m forge.standard_repair_batch20 --render
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
OUT = ROOT / "out" / "standard_repair_batch20"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch28"
REPORT = CATALOG / "owned_repair_batch28.json"
SUMMARY = CATALOG / "owned_repair_batch28.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS: dict[str, dict] = {
    "TSSCRS51": {"kind": "traffic_crossing"},
    "TSSLPT51": {"kind": "one_way_lane_arrow"},
    "TSSRON51": {"kind": "traffic_roundabout"},
    "TWRDEF51": {"kind": "two_way_undefined"},
    "TWRTPT52": {"kind": "two_way_reciprocal"},
    "TWRTPT53": {"kind": "two_way_single"},
}

REPAIR_NOTES = {
    "TSSCRS51": "Judge repair: traffic crossing area circle with short vertical/tick cue in magenta.",
    "TSSLPT51": "Judge repair: filled one-way lane arrow, preserving traffic directionality.",
    "TSSRON51": "Judge repair: traffic roundabout circular arrow, not a generic dashed box.",
    "TWRDEF51": "Judge repair: reciprocal route arrows plus side question marks for undefined direction.",
    "TWRTPT52": "Judge repair: reciprocal up/down traffic arrows for a two-way route.",
    "TWRTPT53": "Judge repair: single traffic-direction arrow with dashed two-way route stem.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch20">'
        f"<title>{asset} traffic separation repair batch 28 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _text(x: int, y: int, label: str, *, size: int = 18) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour("magenta")}" stroke="none">{label}</text>'
    )


def _traffic_crossing() -> str:
    c = _colour("magenta")
    return (
        f'<circle cx="32" cy="32" r="17" fill="none" stroke="{c}" stroke-width="3.2" opacity="0.62"/>'
        f'<path d="M32 20 V36" fill="none" stroke="{c}" stroke-width="3.2" opacity="0.62"/>'
        f'<path d="M28 43 H36" fill="none" stroke="{c}" stroke-width="3.2" opacity="0.62"/>'
    )


def _one_way_lane_arrow() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M20 27 L32 9 L44 27 H38 V55 H26 V27 Z" '
        f'fill="{c}" fill-opacity="0.24" stroke="{c}" stroke-width="3.1"/>'
    )


def _traffic_roundabout() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M21 15 H21 V29 H35 L27 21" fill="none" stroke="{c}" stroke-width="3.5" opacity="0.62"/>'
        f'<path d="M20 40 C24 50 38 54 48 45 C58 35 55 19 43 13 '
        f'C35 9 25 12 21 19" fill="none" stroke="{c}" stroke-width="3.5" opacity="0.62"/>'
    )


def _reciprocal_arrows(*, question_marks: bool = False) -> str:
    c = _colour("magenta")
    body = (
        f'<path d="M25 19 L32 9 L39 19 M20 26 H28 M36 26 H44" fill="none" stroke="{c}" stroke-width="3.4"/>'
        f'<path d="M25 45 L32 55 L39 45 M20 38 H28 M36 38 H44" fill="none" stroke="{c}" stroke-width="3.4"/>'
        f'<path d="M25 30 V34 M39 30 V34" fill="none" stroke="{c}" stroke-width="3.4"/>'
    )
    if question_marks:
        body += _text(12, 39, "?", size=20)
        body += _text(52, 39, "?", size=20)
    return body


def _single_route_arrow() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M25 19 L32 9 L39 19 M20 26 H28 M36 26 H44" fill="none" stroke="{c}" stroke-width="3.4"/>'
        f'<path d="M25 52 H39 M25 52 V45 M25 38 V32 M39 52 V45 M39 38 V32" '
        f'fill="none" stroke="{c}" stroke-width="3.4"/>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]["kind"]
    if kind == "traffic_crossing":
        return _svg(asset, _traffic_crossing())
    if kind == "one_way_lane_arrow":
        return _svg(asset, _one_way_lane_arrow())
    if kind == "traffic_roundabout":
        return _svg(asset, _traffic_roundabout())
    if kind == "two_way_undefined":
        return _svg(asset, _reciprocal_arrows(question_marks=True))
    if kind == "two_way_reciprocal":
        return _svg(asset, _reciprocal_arrows())
    if kind == "two_way_single":
        return _svg(asset, _single_route_arrow())
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
            "risk_bucket": "traffic_separation_route_repair_batch28",
            "candidate_strategy": "owned_redraw_from_s101_opencpn_traffic_geometry_witnesses",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
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
                "source_priority_basis": "s101_opencpn_traffic_geometry_witnesses",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch20",
                "reference_role": "provider refs are shape/direction witnesses; SVG is owned redraw",
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
        "# Standard Repair Batch 20 / Owned Repair Batch 28",
        "",
        "Owned redraws for the traffic-separation / two-way route repair slice.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
        required = row.get("required_change")
        if required:
            lines.append(f"  - Judge required change: {required}")
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
