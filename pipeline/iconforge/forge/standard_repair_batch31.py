"""Repair second NMKINF notice-board slice into owned repair batch 39.

Run:
  python3 -m forge.standard_repair_batch31 --render
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
OUT = ROOT / "out" / "standard_repair_batch31"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch39"
REPORT = CATALOG / "owned_repair_batch39.json"
SUMMARY = CATALOG / "owned_repair_batch39.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "NMKINF25": "left_branch_waterway",
    "NMKINF26": "main_fairway_right",
    "NMKINF27": "main_fairway_left",
    "NMKINF28": "side_left_main_right",
    "NMKINF29": "side_right_main_left",
    "NMKINF38": "end_regulation",
    "NMKINF40": "telephone",
    "NMKINF43": "waterski",
    "NMKINF44": "sailing",
    "NMKINF45": "non_powered_boat",
    "NMKINF46": "windsurfing",
    "NMKINF47": "vhf",
    "NMKINF48": "jetski",
    "NMKINF49": "speedboat",
    "NMKINF50": "boat_ramp",
    "NMKINF53": "three_vessels",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch31">'
        f"<title>{asset} repair batch 39 notice-board candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _board(inner: str) -> str:
    return (
        f'<rect x="9" y="9" width="46" height="46" rx="3" fill="{_colour("blue")}" '
        f'stroke="{_colour("black")}" stroke-width="2.8"/>'
        f"{inner}"
    )


def _white_path(d: str, width: float = 4) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour("white")}" stroke-width="{width}"/>'


def _text(label: str, size: int = 15) -> str:
    return (
        f'<text x="32" y="38" fill="{_colour("white")}" stroke="none" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'font-size="{size}" text-anchor="middle">{label}</text>'
    )


def _waterway(kind: str) -> str:
    main = _white_path("M32 14 V50", 10)
    parts = {
        "left_branch_waterway": _white_path("M32 32 H14", 8),
        "main_fairway_right": _white_path("M18 48 L46 20", 10) + _white_path("M18 20 V48", 5),
        "main_fairway_left": _white_path("M46 48 L18 20", 10) + _white_path("M46 20 V48", 5),
        "side_left_main_right": _white_path("M32 36 L48 20", 10) + _white_path("M32 36 H16", 5),
        "side_right_main_left": _white_path("M32 36 L16 20", 10) + _white_path("M32 36 H48", 5),
    }
    if kind == "left_branch_waterway":
        return _board(main + parts[kind])
    return _board(parts[kind])


def _end_regulation() -> str:
    return _board(_white_path("M20 20 L44 44", 5) + _white_path("M20 44 L44 20", 3))


def _telephone() -> str:
    return _board(
        _white_path("M24 20 C23 30 34 41 44 40", 4)
        + _white_path("M24 20 L31 24 M44 40 L39 47", 4)
    )


def _waterski() -> str:
    return _board(
        f'<circle cx="27" cy="21" r="3.5" fill="{_colour("white")}" stroke="none"/>'
        + _white_path("M28 25 L35 36 L42 26", 3.5)
        + _white_path("M20 47 H48 M18 42 C25 47 37 47 46 42", 3)
    )


def _sailing() -> str:
    return _board(
        f'<path d="M31 17 V45 M31 20 L44 41 H31 M31 23 L20 43 H31" '
        f'fill="none" stroke="{_colour("white")}" stroke-width="3.5"/>'
        + _white_path("M20 47 H44", 3)
    )


def _non_powered_boat() -> str:
    return _board(
        _white_path("M18 39 H46 L40 47 H24 Z", 3.8)
        + _white_path("M24 30 L42 46 M40 30 L22 46", 3)
    )


def _windsurfing() -> str:
    return _board(
        _white_path("M19 47 H47", 3)
        + _white_path("M31 44 V18 L45 38 H31", 3.5)
        + _white_path("M31 24 L20 42", 3)
    )


def _vhf() -> str:
    return _board(_text("VHF", 16) + _white_path("M20 45 H44", 3))


def _jetski() -> str:
    return _board(
        _white_path("M18 40 C25 33 38 34 46 41 L41 47 H24 Z", 3.5)
        + _white_path("M33 33 L41 25 M41 25 H48", 3)
        + _white_path("M18 50 C25 46 39 46 46 50", 2.8)
    )


def _speedboat() -> str:
    return _board(
        _white_path("M16 38 H48 L41 47 H23 Z", 3.8)
        + _white_path("M26 38 L35 27 H44", 3)
        + _white_path("M15 49 H31 M19 53 H42", 2.8)
    )


def _boat_ramp() -> str:
    return _board(
        _white_path("M17 48 L47 22", 4)
        + _white_path("M21 40 H39 L35 47 H24 Z", 3)
        + _white_path("M18 52 H46", 3)
    )


def _three_vessels() -> str:
    return _board(
        _white_path("M18 24 H46 L42 30 H22 Z", 3)
        + _white_path("M18 34 H46 L42 40 H22 Z", 3)
        + _white_path("M18 44 H46 L42 50 H22 Z", 3)
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind in {
        "left_branch_waterway",
        "main_fairway_right",
        "main_fairway_left",
        "side_left_main_right",
        "side_right_main_left",
    }:
        return _svg(asset, _waterway(kind))
    if kind == "end_regulation":
        return _svg(asset, _end_regulation())
    if kind == "telephone":
        return _svg(asset, _telephone())
    if kind == "waterski":
        return _svg(asset, _waterski())
    if kind == "sailing":
        return _svg(asset, _sailing())
    if kind == "non_powered_boat":
        return _svg(asset, _non_powered_boat())
    if kind == "windsurfing":
        return _svg(asset, _windsurfing())
    if kind == "vhf":
        return _svg(asset, _vhf())
    if kind == "jetski":
        return _svg(asset, _jetski())
    if kind == "speedboat":
        return _svg(asset, _speedboat())
    if kind == "boat_ramp":
        return _svg(asset, _boat_ramp())
    if kind == "three_vessels":
        return _svg(asset, _three_vessels())
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
            "risk_bucket": "notice_board_repair_batch39",
            "candidate_strategy": "owned_notice_board_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue NMKINF notice-board slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch31",
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
        "# Standard Repair Batch 31 / Owned Repair Batch 39",
        "",
        "Owned redraws for the second NMKINF notice-board judge-failure slice.",
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
