"""Repair a conservative subset of the 621-row queue into owned batch 24.

Run:
  python3 -m forge.standard_repair_batch16 --render
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
SOURCE_QUEUE = CATALOG / "standard_repair_queue.json"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
OUT = ROOT / "out" / "standard_repair_batch16"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch24"
REPORT = CATALOG / "owned_repair_batch24.json"
SUMMARY = CATALOG / "owned_repair_batch24.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 621

REPAIRS: dict[str, dict] = {
    "BUIREL01": {"kind": "christian_cross", "colour": "brown"},
    "BUIREL13": {"kind": "christian_cross", "colour": "black"},
    "GATCON03": {"kind": "lock_gate", "mode": "navigable"},
    "GATCON04": {"kind": "lock_gate", "mode": "closed"},
    "HULKES01": {"kind": "hulk"},
    "INFORM01": {"kind": "information_marker"},
    "ITZARE51": {"kind": "it_area"},
    "LNDARE01": {"kind": "land_point"},
    "LOCMAG01": {"kind": "magnetic_anomaly", "mode": "point"},
    "LOCMAG51": {"kind": "magnetic_anomaly", "mode": "line"},
    "LOWACC01": {"kind": "low_accuracy"},
    "MAGVAR01": {"kind": "magnetic_variation", "mode": "point"},
    "MAGVAR51": {"kind": "magnetic_variation", "mode": "line"},
    "MARCUL02": {"kind": "marine_farm"},
    "MONUMT02": {"kind": "monument", "colour": "brown"},
    "MONUMT12": {"kind": "monument", "colour": "black"},
    "MORFAC03": {"kind": "mooring_dolphin"},
    "MORFAC04": {"kind": "deviation_mooring"},
    "MSTCON04": {"kind": "mast", "colour": "brown"},
    "MSTCON14": {"kind": "mast", "colour": "black"},
    "NORTHAR1": {"kind": "north_arrow"},
    "POSGEN03": {"kind": "position_conspicuous"},
    "POSGEN04": {"kind": "position_elevation"},
    "PRCARE51": {"kind": "precaution_area"},
}

REPAIR_NOTES = {
    "BUIREL01": "Redraw as a compact brown Christian cross witness; remove house outline and doorway.",
    "BUIREL13": "Redraw as a compact black conspicuous Christian cross witness; remove house outline and doorway.",
    "GATCON03": "Redraw as the magenta circular navigable lock-gate witness, not a generic black gate frame.",
    "GATCON04": "Redraw as the magenta circular non-navigable lock-gate witness with closure cue.",
    "HULKES01": "Redraw as a compact brown hulk silhouette without mast/A-frame detail.",
    "INFORM01": "Use an origin circle, leader line, and square boxed information marker at the leader end.",
    "ITZARE51": "Keep only the IT inshore-traffic letters at reference proportions; remove dashed underline.",
    "LNDARE01": "Redraw as the small land point/dot witness without the outer target ring.",
    "LOCMAG01": "Redraw as the magenta magnetic-anomaly point wedge/line glyph; remove A-letter substitution.",
    "LOCMAG51": "Redraw as the magenta magnetic-anomaly line/area wedge/line glyph; no dashed underline.",
    "LOWACC01": "Use the question-mark plus diagonal low-accuracy cue; remove endpoint ring.",
    "MAGVAR01": "Redraw as the magenta filled wedge/flag and vertical-line magnetic-variation witness.",
    "MAGVAR51": "Redraw as the magenta filled wedge/flag and vertical-line magnetic-variation line witness; no underline.",
    "MARCUL02": "Redraw as a rectangular marine-farm fish/net frame; remove wave baseline.",
    "MONUMT02": "Add the brown monument base/ring cue and align to the narrow monument witness.",
    "MONUMT12": "Add the black conspicuous monument base/ring cue and align to the narrow monument witness.",
    "MORFAC03": "Redraw as compact black mooring-dolphin piles; remove ladder frame and top ring.",
    "MORFAC04": "Redraw as narrow offset deviation mooring-dolphin piles; remove top ring and oversized frame.",
    "MSTCON04": "Redraw as a narrow brown mast/needle tower with base cue; remove arrowhead.",
    "MSTCON14": "Redraw as a narrow black conspicuous mast/needle tower with base cue; remove arrowhead.",
    "NORTHAR1": "Use a filled orange north arrowhead with the N placed as part of the arrow witness.",
    "POSGEN03": "Redraw as the black ring/dot conspicuous-position witness; remove crosshair spokes.",
    "POSGEN04": "Redraw as the black reference ring marker; remove invented internal triangle.",
    "PRCARE51": "Redraw as the magenta precautionary-area boundary triangle; remove dashed outline substitution.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _text(x: int, y: int, label: str, colour: str, size: int = 14, weight: int = 700) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="{weight}" fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch16">'
        f"<title>{asset} standard repair batch 24 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _christian_cross(colour: str) -> str:
    return (
        f'<path d="M32 13 V48 M23 24 H41" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<path d="M25 49 H39" fill="none" stroke="{_colour(colour)}" stroke-width="2.8"/>'
        f'<circle cx="32" cy="53" r="3.2" fill="none" stroke="{_colour(colour)}" stroke-width="2.5"/>'
    )


def _lock_gate(mode: str) -> str:
    body = (
        f'<circle cx="32" cy="32" r="20" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<path d="M20 43 H44" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<path d="M23 42 L32 23 L41 42" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
    )
    if mode == "closed":
        body += f'<path d="M24 23 L40 42 M40 23 L24 42" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6"/>'
    else:
        body += f'<path d="M27 23 H37" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6"/>'
    return body


def _hulk() -> str:
    return (
        f'<path d="M14 36 C24 44 40 44 50 36 L45 47 H19 Z" fill="{_colour("brown")}" '
        f'fill-opacity="0.16" stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M20 40 H44 M24 34 H40" fill="none" stroke="{_colour("brown")}" stroke-width="2.5"/>'
    )


def _information_marker() -> str:
    return (
        f'<circle cx="17" cy="48" r="4.5" fill="none" stroke="{_colour("magenta")}" stroke-width="2.7"/>'
        f'<path d="M21 44 L39 26" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<rect x="38" y="14" width="17" height="17" rx="1" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'{_text(46, 28, "i", "magenta", 17, 700)}'
    )


def _it_area() -> str:
    return _text(32, 39, "IT", "magenta", 25, 700)


def _land_point() -> str:
    return f'<circle cx="32" cy="32" r="7" fill="{_colour("brown")}" stroke="none"/>'


def _magnetic_anomaly(mode: str) -> str:
    body = (
        f'<path d="M22 47 L34 15 L46 47 Z" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<path d="M18 47 H50" fill="none" stroke="{_colour("magenta")}" stroke-width="2.7"/>'
    )
    if mode == "line":
        body += f'<path d="M28 31 H40" fill="none" stroke="{_colour("magenta")}" stroke-width="2.5"/>'
    return body


def _low_accuracy() -> str:
    return (
        f'<path d="M18 48 L46 20" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'{_text(25, 33, "?", "black", 22, 700)}'
    )


def _magnetic_variation(mode: str) -> str:
    body = (
        f'<path d="M30 15 V50" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<path d="M31 16 L48 25 L31 34 Z" fill="{_colour("magenta")}" stroke="{_colour("magenta")}" stroke-width="2.3"/>'
    )
    if mode == "line":
        body += f'<path d="M21 50 H43" fill="none" stroke="{_colour("magenta")}" stroke-width="2.5"/>'
    return body


def _marine_farm() -> str:
    return (
        f'<rect x="14" y="18" width="38" height="30" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<path d="M20 25 H46 M20 33 H46 M20 41 H46 M23 20 V46 M32 20 V46 M41 20 V46" '
        f'fill="none" stroke="{_colour("brown")}" stroke-width="2.1"/>'
        f'<path d="M19 33 C25 26 36 26 45 33 C36 40 25 40 19 33 Z" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.4"/>'
    )


def _monument(colour: str) -> str:
    return (
        f'<path d="M25 48 L30 17 H34 L39 48 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<path d="M21 49 H43" fill="none" stroke="{_colour(colour)}" stroke-width="2.7"/>'
        f'<ellipse cx="32" cy="54" rx="7" ry="3.5" fill="none" stroke="{_colour(colour)}" stroke-width="2.5"/>'
    )


def _mooring_dolphin() -> str:
    return (
        f'<path d="M23 47 V24 M32 47 V17 M41 47 V24" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M20 47 H44 M24 31 H40" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
    )


def _deviation_mooring() -> str:
    return (
        f'<path d="M23 49 V26 M33 49 V17 M43 49 V29" fill="none" stroke="{_colour("black")}" stroke-width="3.1"/>'
        f'<path d="M20 49 H46 M24 36 L42 28" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
    )


def _mast(colour: str) -> str:
    return (
        f'<path d="M32 12 V50" fill="none" stroke="{_colour(colour)}" stroke-width="3.1"/>'
        f'<path d="M25 50 H39" fill="none" stroke="{_colour(colour)}" stroke-width="2.7"/>'
        f'<ellipse cx="32" cy="54" rx="6" ry="3" fill="none" stroke="{_colour(colour)}" stroke-width="2.4"/>'
    )


def _north_arrow() -> str:
    return (
        f'<path d="M32 10 L45 33 H37 V52 H27 V33 H19 Z" fill="{_colour("orange")}" '
        f'stroke="{_colour("orange")}" stroke-width="2.4"/>'
        f'{_text(32, 46, "N", "white", 15, 800)}'
    )


def _position_conspicuous() -> str:
    return (
        f'<circle cx="32" cy="32" r="14" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<circle cx="32" cy="32" r="4.5" fill="{_colour("black")}" stroke="none"/>'
    )


def _position_elevation() -> str:
    return (
        f'<circle cx="32" cy="32" r="15" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<circle cx="32" cy="32" r="8" fill="none" stroke="{_colour("black")}" stroke-width="2.5"/>'
        f'<circle cx="32" cy="32" r="2.8" fill="{_colour("black")}" stroke="none"/>'
    )


def _precaution_area() -> str:
    return (
        f'<path d="M32 14 L51 47 H13 Z" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M32 23 V36" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<circle cx="32" cy="42" r="2.5" fill="{_colour("magenta")}" stroke="none"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "christian_cross":
        return _svg(asset, _christian_cross(spec["colour"]))
    if kind == "lock_gate":
        return _svg(asset, _lock_gate(spec["mode"]))
    if kind == "hulk":
        return _svg(asset, _hulk())
    if kind == "information_marker":
        return _svg(asset, _information_marker())
    if kind == "it_area":
        return _svg(asset, _it_area())
    if kind == "land_point":
        return _svg(asset, _land_point())
    if kind == "magnetic_anomaly":
        return _svg(asset, _magnetic_anomaly(spec["mode"]))
    if kind == "low_accuracy":
        return _svg(asset, _low_accuracy())
    if kind == "magnetic_variation":
        return _svg(asset, _magnetic_variation(spec["mode"]))
    if kind == "marine_farm":
        return _svg(asset, _marine_farm())
    if kind == "monument":
        return _svg(asset, _monument(spec["colour"]))
    if kind == "mooring_dolphin":
        return _svg(asset, _mooring_dolphin())
    if kind == "deviation_mooring":
        return _svg(asset, _deviation_mooring())
    if kind == "mast":
        return _svg(asset, _mast(spec["colour"]))
    if kind == "north_arrow":
        return _svg(asset, _north_arrow())
    if kind == "position_conspicuous":
        return _svg(asset, _position_conspicuous())
    if kind == "position_elevation":
        return _svg(asset, _position_elevation())
    if kind == "precaution_area":
        return _svg(asset, _precaution_area())
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


def _source_judge_for(item: dict) -> str | None:
    batch = item.get("judge", {}).get("batch")
    if batch:
        return f"catalog/{batch}.json"
    return None


def _provider_count(item: dict) -> int:
    refs = item.get("reference_providers") or {}
    return sum(len(refs.get(name) or []) for name in ("s101", "aquamap", "opencpn_render"))


def _required_change(item: dict) -> str | None:
    return item.get("required_change") or item.get("judge", {}).get("required_change")


def _safety_codes(item: dict) -> list[str]:
    return item.get("safety_reason_codes") or item.get("judge", {}).get("safety_reason_codes") or []


def _skip_status(item: dict) -> str:
    asset = item.get("asset", "")
    status = item.get("status", "")
    codes = set(_safety_codes(item))
    required = (_required_change(item) or "").lower()
    exact_terms = (
        "manual exception",
        "exact chart no.1",
        "exact chart",
        "exact local reference",
        "exact reference",
        "exact crop",
        "locate/render",
        "resolve the exact",
        "needs an exact",
        "attach the exact",
        "provide a valid reference",
        "verify against",
        "before passing",
    )
    if status == "queued_for_chart1_parity_repair":
        return "skipped_batch24_chart1_parity_exact_crop_or_manual_exception_required"
    if any(term in required for term in exact_terms):
        return "blocked_batch24_missing_or_unverified_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_batch24_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch24_notice_board_family_dedicated_pass"
    if asset.startswith(("TOP", "LIGHTS", "LIT", "DAY")):
        return "skipped_batch24_topmark_daymark_or_light_dedicated_pass"
    if asset.startswith(("BCN", "BOY", "PRICKE")):
        return "skipped_batch24_geometry_heavy_navigation_aid_contract"
    if _provider_count(item) < 2 and item.get("status") == "queued_for_render_repair":
        return "skipped_batch24_low_reference_confidence"
    return "skipped_batch24_outside_bounded_high_confidence_subset"


def build(*, render_outputs: bool = False) -> dict:
    queue = json.loads(SOURCE_QUEUE.read_text())
    source_table = json.loads(SOURCE_TABLE.read_text()) if SOURCE_TABLE.exists() else {"rows": []}
    source_rows = {row["asset"]: row for row in source_table.get("rows", [])}
    queue_items = {item["asset"]: item for item in queue.get("items", [])}
    actual_queue = [item["asset"] for item in queue.get("items", [])]
    if len(actual_queue) != EXPECTED_QUEUE_ROWS:
        raise RuntimeError(f"expected {EXPECTED_QUEUE_ROWS} repair queue rows, got {len(actual_queue)}")

    missing = sorted(set(REPAIRS) - set(queue_items))
    if missing:
        raise RuntimeError(f"repair target(s) missing from queue: {missing}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    blockers = []
    for asset in actual_queue:
        item = queue_items.get(asset, {})
        source_row = source_rows.get(asset, {})
        if asset not in REPAIRS:
            blockers.append({
                "asset": asset,
                "status": _skip_status(item),
                "required_change": _required_change(item),
                "safety_reason_codes": _safety_codes(item),
                "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
                "reference_providers": item.get("reference_providers") or source_row.get("reference_providers", {}),
            })
            continue

        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": item.get("name") or source_row.get("name"),
            "queue_action": item.get("status") or "standard_repair_queue_consumed",
            "risk_bucket": "standard_repair_queue_batch24_high_confidence_non_aid_subset",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg")
            or source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": REPAIR_NOTES[asset],
            "required_change": _required_change(item),
            "safety_reason_codes": _safety_codes(item),
            "semantic_brief": item.get("semantic_brief") or source_row.get("semantic_brief"),
            "visual_examples": item.get("reference_providers") or source_row.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_repair_queue",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch16",
                "reference_role": "semantic_brief/provider refs are shape witnesses; SVG is owned redraw",
            },
            "source_judge": _source_judge_for(item),
        })

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_queue": str(SOURCE_QUEUE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_queue_rows": len(actual_queue),
            "expected_queue_rows": EXPECTED_QUEUE_ROWS,
            "failed_repaired": len(rows),
            "blocked_or_skipped": len(blockers),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
        "blockers": blockers,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 16 / Owned Repair Batch 24",
        "",
        "Owned redraws for a bounded non-aid/non-light/non-notice subset of the current 621-row standard repair queue.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Repaired", ""])
    for row in result["symbols"]:
        lines.append(f"- `{row['asset']}`: {row.get('repair_note')}")
    lines.extend(["", "## Blocked / skipped", ""])
    for row in result["blockers"]:
        lines.append(f"- `{row['asset']}`: {row['status']} - {row.get('required_change')}")
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
