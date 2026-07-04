"""Repair the six failures from judge rerun 24/25 into owned repair batch 31.

Run:
  python3 -m forge.standard_repair_batch23 --render
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
OUT = ROOT / "out" / "standard_repair_batch23"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch31"
REPORT = CATALOG / "owned_repair_batch31.json"
SUMMARY = CATALOG / "owned_repair_batch31.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "HULKES01": "hulk",
    "LNDARE01": "land_point",
    "LOCMAG01": "local_magnetic_point",
    "LOCMAG51": "local_magnetic_line_area",
    "MAGVAR01": "magvar_point",
    "MAGVAR51": "magvar_line_area",
}

REPAIR_NOTES = {
    "HULKES01": "Judge repair: redraw as the compact brown low hulk silhouette; remove upright leaf/ribs.",
    "LNDARE01": "Judge repair: redraw as the tiny point witness; remove target/ring treatment.",
    "LOCMAG01": "Judge repair: redraw as the small magenta wedge/vertical-line cursor glyph.",
    "LOCMAG51": "Judge repair: redraw as the pale magenta line/area magnetic anomaly wedge glyph.",
    "MAGVAR01": "Judge repair: redraw as the compact filled magenta wedge with short vertical reference line.",
    "MAGVAR51": "Judge repair: redraw as the pale compact magenta variation wedge/vertical-line glyph.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch23">'
        f"<title>{asset} repair batch 31 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _hulk() -> str:
    return (
        f'<path d="M25 30 C31 28 38 29 42 32 C38 35 31 36 25 34 Z" '
        f'fill="{_colour("brown")}" stroke="{_colour("black")}" stroke-width="1.7"/>'
    )


def _land_point() -> str:
    return f'<circle cx="32" cy="32" r="2.3" fill="{_colour("gray")}" stroke="none"/>'


def _local_magnetic(*, opacity: str = "1") -> str:
    c = _colour("magenta")
    return (
        f'<path d="M35 20 V44" fill="none" stroke="{c}" stroke-width="1.8" opacity="{opacity}"/>'
        f'<path d="M35 25 L27 34 L35 39" fill="none" stroke="{c}" stroke-width="1.8" opacity="{opacity}"/>'
    )


def _magvar(*, opacity: str = "1") -> str:
    c = _colour("magenta")
    return (
        f'<path d="M35 22 V44" fill="none" stroke="{c}" stroke-width="2.1" opacity="{opacity}"/>'
        f'<path d="M35 25 L28 36 L35 40 Z" fill="{c}" stroke="none" opacity="{opacity}"/>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "hulk":
        return _svg(asset, _hulk())
    if kind == "land_point":
        return _svg(asset, _land_point())
    if kind == "local_magnetic_point":
        return _svg(asset, _local_magnetic())
    if kind == "local_magnetic_line_area":
        return _svg(asset, _local_magnetic(opacity="0.48"))
    if kind == "magvar_point":
        return _svg(asset, _magvar())
    if kind == "magvar_line_area":
        return _svg(asset, _magvar(opacity="0.48"))
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


def _latest_judge(row: dict) -> dict:
    return (row.get("judge") or {}).get("latest") or {}


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
        judge = _latest_judge(source_row)
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
            "risk_bucket": "batch24_25_judge_failure_repair_batch31",
            "candidate_strategy": "owned_compact_redraw_from_judge_feedback_and_provider_witnesses",
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
                "source_priority_basis": "standard_judge_batch_024_025_rerun_feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch23",
                "reference_role": "judge feedback and provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": "catalog/standard_judge_batch_024_025_rerun.json",
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
        "# Standard Repair Batch 23 / Owned Repair Batch 31",
        "",
        "Owned compact redraws for the six failures from judge rerun 24/25.",
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
