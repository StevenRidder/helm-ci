"""Repair a small batch23 follow-up slice into owned repair batch 30.

Run:
  python3 -m forge.standard_repair_batch22 --render
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
OUT = ROOT / "out" / "standard_repair_batch22"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch30"
REPORT = CATALOG / "owned_repair_batch30.json"
SUMMARY = CATALOG / "owned_repair_batch30.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS: dict[str, dict] = {
    "FAIRWY51": {"kind": "fairway_one_way"},
    "FAIRWY52": {"kind": "fairway_two_way"},
    "FLDSTR01": {"kind": "flood_stream_ticks"},
    "FRYARE51": {"kind": "ferry_area"},
    "FSHFAC02": {"kind": "fishing_stakes_box"},
    "FSHFAC03": {"kind": "fishing_stakes_pattern"},
    "HRBFAC09": {"kind": "fishing_harbour"},
    "PILPNT02": {"kind": "pile_point"},
}

REPAIR_NOTES = {
    "FAIRWY51": "Judge repair: keep hollow one-way arrow but use the CHGRD/gray reference stroke colour.",
    "FAIRWY52": "Judge repair: keep hollow two-way arrow but use the CHGRD/gray reference stroke colour.",
    "FLDSTR01": "Judge repair: replace horizontal crossbar with spring-rate tick geometry on the gray flood-stream arrow.",
    "FRYARE51": "Judge repair: keep ferry-on-route geometry but use the magenta ferry-area reference colour.",
    "FSHFAC02": "Judge repair: use the gray simple fishing-stakes rectangle and diagonal witness.",
    "FSHFAC03": "Judge repair: use the gray low fishing-stakes comb pattern.",
    "HRBFAC09": "Judge repair: redraw as the magenta fishing-harbour fish/arc mark; remove black ring and F text.",
    "PILPNT02": "Judge repair: redraw as the small filled black pile/bollard point witness.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch22">'
        f"<title>{asset} repair batch 30 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _fairway_one_way() -> str:
    c = _colour("gray")
    return f'<path d="M26 50 H38 V25 H46 L32 11 L18 25 H26 Z" fill="none" stroke="{c}" stroke-width="3.1"/>'


def _fairway_two_way() -> str:
    c = _colour("gray")
    return (
        f'<path d="M26 50 H38 V25 H46 L32 11 L18 25 H26 Z" fill="none" stroke="{c}" stroke-width="3.1"/>'
        f'<path d="M26 14 H38 V39 H46 L32 53 L18 39 H26 Z" fill="none" stroke="{c}" stroke-width="3.1"/>'
    )


def _flood_stream_ticks() -> str:
    c = _colour("gray")
    return (
        f'<path d="M32 52 V14 M23 24 L32 14 L41 24" fill="none" stroke="{c}" stroke-width="3.2"/>'
        f'<path d="M32 33 L42 43 M32 42 L39 49" fill="none" stroke="{c}" stroke-width="2.8"/>'
    )


def _ferry_area() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M9 38 H23 M43 38 H55" fill="none" stroke="{c}" stroke-width="2.8" stroke-dasharray="7 6"/>'
        f'<path d="M22 34 H40 L47 38 L40 42 H22 Z" fill="none" stroke="{c}" stroke-width="2.8"/>'
    )


def _fishing_stakes_box() -> str:
    c = _colour("gray")
    return (
        f'<rect x="15" y="30" width="36" height="19" fill="none" stroke="{c}" stroke-width="3"/>'
        f'<path d="M20 30 L38 48" fill="none" stroke="{c}" stroke-width="3"/>'
    )


def _fishing_stakes_pattern() -> str:
    c = _colour("gray")
    return (
        f'<path d="M13 44 H51" fill="none" stroke="{c}" stroke-width="3.1"/>'
        f'<path d="M13 44 V32 M22 44 V31 M31 44 V31 M40 44 V31 M49 44 V32" '
        f'fill="none" stroke="{c}" stroke-width="3.1"/>'
    )


def _fishing_harbour() -> str:
    c = _colour("magenta")
    return (
        f'<path d="M13 31 C22 20 37 20 50 31 C37 42 22 42 13 31 Z" fill="none" stroke="{c}" stroke-width="3.1"/>'
        f'<path d="M13 31 L7 24 M13 31 L7 38" fill="none" stroke="{c}" stroke-width="3.1"/>'
        f'<path d="M12 19 C24 9 44 10 55 21 M12 45 C24 55 44 54 55 43" fill="none" stroke="{c}" stroke-width="3.1"/>'
    )


def _pile_point() -> str:
    return f'<circle cx="32" cy="32" r="12" fill="{_colour("black")}" stroke="none"/>'


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]["kind"]
    if kind == "fairway_one_way":
        return _svg(asset, _fairway_one_way())
    if kind == "fairway_two_way":
        return _svg(asset, _fairway_two_way())
    if kind == "flood_stream_ticks":
        return _svg(asset, _flood_stream_ticks())
    if kind == "ferry_area":
        return _svg(asset, _ferry_area())
    if kind == "fishing_stakes_box":
        return _svg(asset, _fishing_stakes_box())
    if kind == "fishing_stakes_pattern":
        return _svg(asset, _fishing_stakes_pattern())
    if kind == "fishing_harbour":
        return _svg(asset, _fishing_harbour())
    if kind == "pile_point":
        return _svg(asset, _pile_point())
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
            "risk_bucket": "batch23_followup_repair_batch30",
            "candidate_strategy": "owned_redraw_from_judge_feedback_and_provider_witnesses",
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
                "source_priority_basis": "standard_judge_batch_023_rerun_feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch22",
                "reference_role": "judge feedback and provider refs are shape witnesses; SVG is owned redraw",
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
        "# Standard Repair Batch 22 / Owned Repair Batch 30",
        "",
        "Owned redraws for the batch23 follow-up repair slice.",
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
