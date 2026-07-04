"""Repair first NMKINF notice-board slice into owned repair batch 38.

Run:
  python3 -m forge.standard_repair_batch30 --render
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
OUT = ROOT / "out" / "standard_repair_batch30"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch38"
REPORT = CATALOG / "owned_repair_batch38.json"
SUMMARY = CATALOG / "owned_repair_batch38.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "NMKINF01": "entry_permitted",
    "NMKINF02": "power_line",
    "NMKINF03": "weir",
    "NMKINF04": "cable_ferry",
    "NMKINF05": "ferry",
    "NMKINF06": "berthing",
    "NMKINF19": "anchor",
    "NMKINF20": "making_fast",
    "NMKINF21": "loading",
    "NMKINF22": "turning",
    "NMKINF23": "crossing_waterway",
    "NMKINF24": "right_branch_waterway",
}

REPAIR_NOTES = {
    "NMKINF01": "Redraw as a rectangular entry-permitted board with green field and white vertical-bar cue.",
    "NMKINF02": "Redraw as a blue notice board carrying a white overhead-power lightning glyph.",
    "NMKINF03": "Redraw as a blue notice board carrying a white weir/stepped-water glyph.",
    "NMKINF04": "Redraw as a blue notice board carrying a cable-ferry line and ferry body glyph.",
    "NMKINF05": "Redraw as a blue notice board carrying a ferry/boat glyph.",
    "NMKINF06": "Redraw as a blue notice board carrying a berthing-permitted bollard/boat glyph.",
    "NMKINF19": "Redraw as a blue notice board carrying the white anchoring-permitted anchor glyph.",
    "NMKINF20": "Redraw as a blue notice board carrying a making-fast bollard and rope glyph.",
    "NMKINF21": "Redraw as a blue notice board carrying a vehicle loading/unloading ramp glyph.",
    "NMKINF22": "Redraw as a blue notice board carrying a turning-permitted circular arrow glyph.",
    "NMKINF23": "Redraw as a blue/white crossing-waterway diagram.",
    "NMKINF24": "Redraw as a blue/white right-side secondary-waterway diagram.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch30">'
        f"<title>{asset} repair batch 38 notice-board candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _board(inner: str, *, fill: str = "blue", stroke: str = "black") -> str:
    return (
        f'<rect x="9" y="9" width="46" height="46" rx="3" fill="{_colour(fill)}" '
        f'stroke="{_colour(stroke)}" stroke-width="2.8"/>'
        f"{inner}"
    )


def _entry_permitted() -> str:
    return (
        f'<rect x="9" y="9" width="46" height="46" rx="3" fill="{_colour("green")}" '
        f'stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'<path d="M22 18 V46 M42 18 V46" fill="none" stroke="{_colour("white")}" stroke-width="6"/>'
        f'<path d="M31 21 L39 32 L31 43" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
    )


def _power_line() -> str:
    return _board(
        f'<path d="M20 20 H44" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M35 17 L25 34 H34 L28 48 L43 28 H34 Z" fill="{_colour("white")}" stroke="none"/>'
    )


def _weir() -> str:
    return _board(
        f'<path d="M18 22 H44 L35 32 H45 L34 43 H46" fill="none" '
        f'stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M18 43 C23 38 29 48 34 43 C39 38 45 48 50 43" fill="none" '
        f'stroke="{_colour("white")}" stroke-width="3"/>'
    )


def _cable_ferry() -> str:
    return _board(
        f'<path d="M16 20 H48" fill="none" stroke="{_colour("white")}" stroke-width="3.5"/>'
        f'<path d="M22 35 H42 L38 44 H26 Z" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M25 35 L32 20 L39 35" fill="none" stroke="{_colour("white")}" stroke-width="3.2"/>'
    )


def _ferry() -> str:
    return _board(
        f'<path d="M18 37 H46 L41 47 H23 Z" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M24 37 V27 H40 V37 M27 31 H37" fill="none" stroke="{_colour("white")}" stroke-width="3.2"/>'
    )


def _berthing() -> str:
    return _board(
        f'<path d="M22 43 H45 L39 49 H24 Z" fill="none" stroke="{_colour("white")}" stroke-width="3.5"/>'
        f'<path d="M20 21 V49 M16 25 H24 M16 45 H24" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
    )


def _anchor() -> str:
    return _board(
        f'<path d="M32 17 V43 M24 26 H40 M27 17 H37" fill="none" '
        f'stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M20 37 C23 48 41 48 44 37 M20 37 L25 38 M44 37 L39 38" '
        f'fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
    )


def _making_fast() -> str:
    return _board(
        f'<path d="M24 22 V45 M40 22 V45 M20 45 H44" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M22 31 C30 23 36 39 44 31" fill="none" stroke="{_colour("white")}" stroke-width="3.5"/>'
    )


def _loading() -> str:
    return _board(
        f'<path d="M17 43 H45 L50 35" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<rect x="20" y="25" width="18" height="12" fill="none" stroke="{_colour("white")}" stroke-width="3"/>'
        f'<circle cx="25" cy="39" r="3" fill="{_colour("white")}" stroke="none"/>'
        f'<circle cx="36" cy="39" r="3" fill="{_colour("white")}" stroke="none"/>'
    )


def _turning() -> str:
    return _board(
        f'<path d="M43 31 C43 22 34 17 26 21 C18 25 17 37 25 43 C32 48 42 44 45 36" '
        f'fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
        f'<path d="M39 25 L45 31 L51 25" fill="none" stroke="{_colour("white")}" stroke-width="4"/>'
    )


def _waterway(branch: str) -> str:
    main = f'<path d="M32 14 V50" fill="none" stroke="{_colour("white")}" stroke-width="10"/>'
    if branch == "cross":
        extra = f'<path d="M15 32 H49" fill="none" stroke="{_colour("white")}" stroke-width="8"/>'
    elif branch == "right":
        extra = f'<path d="M32 32 H50" fill="none" stroke="{_colour("white")}" stroke-width="8"/>'
    else:
        raise KeyError(branch)
    return _board(main + extra)


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "entry_permitted":
        return _svg(asset, _entry_permitted())
    if kind == "power_line":
        return _svg(asset, _power_line())
    if kind == "weir":
        return _svg(asset, _weir())
    if kind == "cable_ferry":
        return _svg(asset, _cable_ferry())
    if kind == "ferry":
        return _svg(asset, _ferry())
    if kind == "berthing":
        return _svg(asset, _berthing())
    if kind == "anchor":
        return _svg(asset, _anchor())
    if kind == "making_fast":
        return _svg(asset, _making_fast())
    if kind == "loading":
        return _svg(asset, _loading())
    if kind == "turning":
        return _svg(asset, _turning())
    if kind == "crossing_waterway":
        return _svg(asset, _waterway("cross"))
    if kind == "right_branch_waterway":
        return _svg(asset, _waterway("right"))
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
            "risk_bucket": "notice_board_repair_batch38",
            "candidate_strategy": "owned_notice_board_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue NMKINF notice-board slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch30",
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
        "# Standard Repair Batch 30 / Owned Repair Batch 38",
        "",
        "Owned redraws for the first NMKINF notice-board judge-failure slice.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
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
