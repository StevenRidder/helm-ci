"""Repair batch37 judge failures into owned repair batch 40.

Run:
  python3 -m forge.standard_repair_batch32 --render
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
OUT = ROOT / "out" / "standard_repair_batch32"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch40"
REPORT = CATALOG / "owned_repair_batch40.json"
SUMMARY = CATALOG / "owned_repair_batch40.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "RCLDEF01": "radio_unknown_open_v",
    "RDOCAL02": "radio_one_way_open_v",
    "RDOCAL03": "radio_two_way_open_v",
    "RECTRC56": "track_two_way_fixed_no_dot",
    "RECTRC58": "track_one_way_fixed_no_dot",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch32">'
        f"<title>{asset} repair batch 40 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _radio(*, two_way: bool = False, unknown: bool = False) -> str:
    c = _colour("magenta")
    body = (
        f'<circle cx="32" cy="32" r="10" fill="{_colour("white")}" stroke="{c}" stroke-width="3.2"/>'
        f'<path d="M21 22 L32 10 L43 22" fill="none" stroke="{c}" stroke-width="3.4"/>'
    )
    if two_way or unknown:
        body += f'<path d="M21 42 L32 54 L43 42" fill="none" stroke="{c}" stroke-width="3.4"/>'
    if unknown:
        body += (
            f'<text x="12" y="40" fill="{c}" font-family="Arial, sans-serif" font-size="23" '
            'font-weight="700" text-anchor="middle">?</text>'
            f'<text x="52" y="40" fill="{c}" font-family="Arial, sans-serif" font-size="23" '
            'font-weight="700" text-anchor="middle">?</text>'
        )
    return body


def _track(*, two_way: bool) -> str:
    c = _colour("gray")
    body = f'<path d="M32 7 V57" fill="none" stroke="{c}" stroke-width="3.2"/>'
    if two_way:
        body += (
            f'<path d="M22 22 L32 11 L42 22" fill="none" stroke="{c}" stroke-width="3.2"/>'
            f'<path d="M22 42 L32 53 L42 42" fill="none" stroke="{c}" stroke-width="3.2"/>'
        )
    else:
        body += f'<path d="M22 38 L32 25 L42 38" fill="none" stroke="{c}" stroke-width="3.2"/>'
    return body


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "radio_unknown_open_v":
        return _svg(asset, _radio(unknown=True))
    if kind == "radio_one_way_open_v":
        return _svg(asset, _radio())
    if kind == "radio_two_way_open_v":
        return _svg(asset, _radio(two_way=True))
    if kind == "track_two_way_fixed_no_dot":
        return _svg(asset, _track(two_way=True))
    if kind == "track_one_way_fixed_no_dot":
        return _svg(asset, _track(two_way=False))
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
            "risk_bucket": "batch37_followup_repair_batch40",
            "candidate_strategy": "owned_redraw_from_standard_judge_batch_037_feedback",
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
                "source_priority_basis": "standard_judge_batch_037_rerun_feedback",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch32",
                "reference_role": "judge feedback and provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": "catalog/standard_judge_batch_037_rerun.json",
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
        "# Standard Repair Batch 32 / Owned Repair Batch 40",
        "",
        "Owned redraws for five batch37 judge failures.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('required_change')}")
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
