"""Repair the wreck/rock hazard slice into owned repair batch 27.

Run:
  python3 -m forge.standard_repair_batch19 --render
"""
from __future__ import annotations

import argparse
import ctypes.util
import json
import math
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT = ROOT / "out" / "standard_repair_batch19"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch27"
REPORT = CATALOG / "owned_repair_batch27.json"
SUMMARY = CATALOG / "owned_repair_batch27.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS: dict[str, dict] = {
    "UWTROC03": {"kind": "dangerous_underwater_rock"},
    "UWTROC04": {"kind": "awash_rock"},
    "WRECKS01": {"kind": "exposed_wreck"},
    "WRECKS04": {"kind": "non_dangerous_wreck"},
    "WRECKS05": {"kind": "dangerous_wreck"},
}

REPAIR_NOTES = {
    "UWTROC03": "Judge repair: dangerous underwater rock with danger-depth fill, perimeter dots, and cross cue.",
    "UWTROC04": "Judge repair: awash rock X/asterisk witness; no mountain or generic rock outline.",
    "WRECKS01": "Judge repair: exposed wreck/hull-superstructure witness in black; no generic triangle-over-curve substitute.",
    "WRECKS04": "Judge repair: non-dangerous depth-unknown wreck hash/fence geometry in black.",
    "WRECKS05": "Judge repair: dangerous depth-unknown wreck with danger-depth fill, perimeter dots, and internal hash grid.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch19">'
        f"<title>{asset} wreck rock hazard repair batch 27 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _perimeter_dots(cx: float, cy: float, rx: float, ry: float, *, count: int = 18) -> str:
    dots = []
    for index in range(count):
        angle = (math.tau * index) / count
        x = cx + math.cos(angle) * rx
        y = cy + math.sin(angle) * ry
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{_colour("black")}" stroke="none"/>')
    return "".join(dots)


def _dangerous_underwater_rock() -> str:
    black = _colour("black")
    blue = _colour("blue")
    return (
        f'<circle cx="32" cy="32" r="20" fill="{blue}" stroke="none"/>'
        f'{_perimeter_dots(32, 32, 20, 20, count=20)}'
        f'<path d="M32 17 V47 M17 32 H47" fill="none" stroke="{black}" stroke-width="6"/>'
    )


def _awash_rock() -> str:
    black = _colour("black")
    return (
        f'<path d="M15 32 H49" fill="none" stroke="{black}" stroke-width="5.4"/>'
        f'<path d="M21 16 L43 48 M43 16 L21 48" fill="none" stroke="{black}" stroke-width="5.4"/>'
    )


def _exposed_wreck() -> str:
    black = _colour("black")
    return (
        f'<path d="M15 42 H49" fill="none" stroke="{black}" stroke-width="7"/>'
        f'<path d="M20 22 L41 42 H23 Z" fill="{black}" stroke="{black}" stroke-width="2.8"/>'
        f'<path d="M38 18 L33 42" fill="none" stroke="{black}" stroke-width="7"/>'
        f'<circle cx="32" cy="42" r="4.2" fill="var(--white)" stroke="{black}" stroke-width="3"/>'
    )


def _non_dangerous_wreck() -> str:
    black = _colour("black")
    return (
        f'<path d="M15 32 H49" fill="none" stroke="{black}" stroke-width="4.2"/>'
        f'<path d="M22 20 V44 M32 16 V48 M42 20 V44" fill="none" stroke="{black}" stroke-width="4.2"/>'
    )


def _dangerous_wreck() -> str:
    black = _colour("black")
    blue = _colour("blue")
    return (
        f'<path d="M11 26 C16 16 27 12 38 15 C47 18 53 25 53 32 '
        f'C53 40 45 47 34 49 C22 50 13 43 10 35 Z" fill="{blue}" stroke="none"/>'
        f'{_perimeter_dots(32, 32, 21, 17, count=18)}'
        f'<path d="M17 32 H48" fill="none" stroke="{black}" stroke-width="4.2"/>'
        f'<path d="M24 22 V42 M32 18 V46 M40 22 V42" fill="none" stroke="{black}" stroke-width="4.2"/>'
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]["kind"]
    if kind == "dangerous_underwater_rock":
        return _svg(asset, _dangerous_underwater_rock())
    if kind == "awash_rock":
        return _svg(asset, _awash_rock())
    if kind == "exposed_wreck":
        return _svg(asset, _exposed_wreck())
    if kind == "non_dangerous_wreck":
        return _svg(asset, _non_dangerous_wreck())
    if kind == "dangerous_wreck":
        return _svg(asset, _dangerous_wreck())
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
            "risk_bucket": "wreck_rock_hazard_repair_batch27",
            "candidate_strategy": "owned_redraw_from_s101_opencpn_aquamap_shape_witnesses",
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
                "source_priority_basis": "s101_opencpn_aquamap_visual_witnesses",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch19",
                "reference_role": "provider refs are shape witnesses; SVG is owned redraw",
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
        "# Standard Repair Batch 19 / Owned Repair Batch 27",
        "",
        "Owned redraws for the wreck/rock hazard repair slice.",
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
