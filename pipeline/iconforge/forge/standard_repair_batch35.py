"""Repair notice/ownship/planned-position slice into owned repair batch 43.

Run:
  python3 -m forge.standard_repair_batch35 --render
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
OUT = ROOT / "out" / "standard_repair_batch35"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch43"
REPORT = CATALOG / "owned_repair_batch43.json"
SUMMARY = CATALOG / "owned_repair_batch43.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "NOTBRD12": "yellow_notice_board",
    "NOTMRK01": "prohibition_board",
    "NOTMRK02": "regulation_board",
    "NOTMRK03": "information_board",
    "OSPONE02": "one_minute_tick",
    "OSPSIX02": "six_minute_tick",
    "OWNSHP01": "ownship_target",
    "OWNSHP05": "scaled_ownship",
    "PIER0001": "pier_circle",
    "PLNPOS01": "planned_position_ellipse",
    "PLNPOS02": "planned_position_crossline",
    "PLNSPD03": "planned_speed_box",
    "PLNSPD04": "alternate_speed_box",
    "POSITN02": "position_fix",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch35">'
        f"<title>{asset} repair batch 43 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 4) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _rect(x: int, y: int, w: int, h: int, fill: str, stroke: str = "black") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{_colour(fill)}" stroke="{_colour(stroke)}" stroke-width="3"/>'


def _text(label: str, colour: str, y: int = 38, size: int = 16) -> str:
    return (
        f'<text x="32" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _notice(kind: str) -> str:
    if kind == "yellow_notice_board":
        return (
            _rect(18, 13, 28, 24, "yellow")
            + _path("M32 37 V53 M23 53 H41", "black", 4)
        )
    if kind == "prohibition_board":
        return _rect(13, 13, 38, 38, "red") + _path("M20 44 L44 20", "white", 5)
    if kind == "regulation_board":
        return _rect(13, 13, 38, 38, "red") + _rect(22, 22, 20, 20, "white", "white")
    if kind == "information_board":
        return _rect(17, 13, 30, 25, "white") + _text("i", "black", 33, 20) + _path("M32 38 V53 M23 53 H41", "black", 4)
    raise KeyError(kind)


def _ownship_vector(minutes: int) -> str:
    c = "orange" if minutes == 1 else "black"
    bars = "".join(_path(f"M{24 + i * 6} 22 V42", c, 3) for i in range(minutes if minutes < 6 else 3))
    if minutes == 6:
        bars += _path("M20 32 H44", c, 3)
    return bars


def _ownship_target() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("orange")}" stroke-width="3.5"/>'
        + _path("M32 10 V54 M10 32 H54", "orange", 3)
        + f'<circle cx="32" cy="32" r="4" fill="{_colour("orange")}" stroke="none"/>'
    )


def _scaled_ownship() -> str:
    return (
        f'<path d="M32 8 L45 52 H19 Z" fill="none" stroke="{_colour("orange")}" stroke-width="3.8"/>'
        + _path("M32 16 V46 M25 39 H39", "orange", 3)
        + f'<circle cx="32" cy="29" r="3.2" fill="{_colour("orange")}" stroke="none"/>'
    )


def _pier_circle() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("blue")}" stroke-width="4"/>'
        + _path("M32 15 V32 H48", "blue", 4)
    )


def _planned_position_ellipse() -> str:
    return f'<ellipse cx="32" cy="32" rx="21" ry="13" fill="none" stroke="{_colour("orange")}" stroke-width="4"/>'


def _planned_position_crossline() -> str:
    return _path("M13 32 H51 M32 13 V51", "orange", 3.8)


def _planned_speed_box(alternate: bool) -> str:
    dash = ' stroke-dasharray="5 4"' if alternate else ""
    return (
        f'<rect x="15" y="19" width="34" height="26" rx="3" fill="none" '
        f'stroke="{_colour("orange")}" stroke-width="3.5"{dash}/>'
        + _text("S", "orange", 38, 18)
    )


def _position_fix() -> str:
    return (
        f'<circle cx="32" cy="32" r="14" fill="none" stroke="{_colour("orange")}" stroke-width="3.5"/>'
        + _path("M18 18 L46 46 M46 18 L18 46", "orange", 3.2)
    )


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind in {"yellow_notice_board", "prohibition_board", "regulation_board", "information_board"}:
        return _svg(asset, _notice(kind))
    if kind == "one_minute_tick":
        return _svg(asset, _ownship_vector(1))
    if kind == "six_minute_tick":
        return _svg(asset, _ownship_vector(6))
    if kind == "ownship_target":
        return _svg(asset, _ownship_target())
    if kind == "scaled_ownship":
        return _svg(asset, _scaled_ownship())
    if kind == "pier_circle":
        return _svg(asset, _pier_circle())
    if kind == "planned_position_ellipse":
        return _svg(asset, _planned_position_ellipse())
    if kind == "planned_position_crossline":
        return _svg(asset, _planned_position_crossline())
    if kind == "planned_speed_box":
        return _svg(asset, _planned_speed_box(False))
    if kind == "alternate_speed_box":
        return _svg(asset, _planned_speed_box(True))
    if kind == "position_fix":
        return _svg(asset, _position_fix())
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
            "risk_bucket": "notice_ownship_planning_repair_batch43",
            "candidate_strategy": "owned_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue notice/ownship/planning slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch35",
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
        "# Standard Repair Batch 35 / Owned Repair Batch 43",
        "",
        "Owned redraws for notice, ownship, and planned-position judge failures.",
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
