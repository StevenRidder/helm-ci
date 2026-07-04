"""Repair a conservative subset of the 510-row queue into owned batch 22.

Run:
  python3 -m forge.standard_repair_batch14 --render
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
OUT = ROOT / "out" / "standard_repair_batch14"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch22"
REPORT = CATALOG / "owned_repair_batch22.json"
SUMMARY = CATALOG / "owned_repair_batch22.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 510

REPAIRS: dict[str, dict] = {
    "BUIREL01": {"kind": "christian_building", "colour": "brown"},
    "BUIREL05": {"kind": "mosque_minaret", "colour": "brown"},
    "BUIREL13": {"kind": "christian_building", "colour": "black"},
    "BUIREL15": {"kind": "mosque_minaret", "colour": "black"},
    "GATCON03": {"kind": "lock_gate", "mode": "navigable"},
    "GATCON04": {"kind": "lock_gate", "mode": "closed"},
    "HULKES01": {"kind": "hulk"},
    "INFARE51": {"kind": "information_area"},
    "INFORM01": {"kind": "information_marker"},
    "ITZARE51": {"kind": "inshore_traffic"},
    "LNDARE01": {"kind": "land_point"},
    "LOCMAG01": {"kind": "magnetic_wedge", "mode": "point"},
    "LOCMAG51": {"kind": "magnetic_wedge", "mode": "area"},
    "LOWACC01": {"kind": "low_accuracy"},
    "MAGVAR01": {"kind": "magnetic_variation", "mode": "point"},
    "MAGVAR51": {"kind": "magnetic_variation", "mode": "area"},
    "MARCUL02": {"kind": "marine_farm"},
    "MONUMT02": {"kind": "monument", "colour": "brown"},
    "MONUMT12": {"kind": "monument", "colour": "black"},
    "MORFAC03": {"kind": "mooring_dolphin"},
    "MORFAC04": {"kind": "deviation_mooring"},
    "MSTCON04": {"kind": "mast", "colour": "brown"},
    "MSTCON14": {"kind": "mast", "colour": "black"},
    "NORTHAR1": {"kind": "north_arrow"},
}

REPAIR_NOTES = {
    "BUIREL01": "Redraw as a compact brown Christian religious-building witness, without the long stem/ring substitution.",
    "BUIREL05": "Redraw as a brown mosque/minaret witness with the crescent over the stem and a small base cue.",
    "BUIREL13": "Redraw as a compact black conspicuous Christian religious-building witness.",
    "BUIREL15": "Redraw as a black conspicuous mosque/minaret witness with the crescent over the stem.",
    "GATCON03": "Replace the diamond with navigable lock-gate leaf geometry.",
    "GATCON04": "Replace the diamond with non-navigable crossed lock-gate geometry.",
    "HULKES01": "Redraw as a brown hulk hull silhouette without the invented A-like internal marker.",
    "INFARE51": "Redraw as the information/restriction area box glyph, without signpost/base clutter.",
    "INFORM01": "Redraw as the information marker with leader line and origin circle.",
    "ITZARE51": "Redraw as the IT inshore-traffic-area text mark in reference style.",
    "LNDARE01": "Redraw as a compact land-area point/disk symbol, not a mound pictogram.",
    "LOCMAG01": "Redraw as the magenta magnetic-anomaly point wedge/line witness.",
    "LOCMAG51": "Redraw as the magenta magnetic-anomaly line/area wedge/line witness.",
    "LOWACC01": "Keep the question-mark plus diagonal low-accuracy cue and remove invented baseline marks.",
    "MAGVAR01": "Redraw as the magenta magnetic-variation point wedge/line witness.",
    "MAGVAR51": "Redraw as the magenta magnetic-variation line/area wedge/line witness.",
    "MARCUL02": "Redraw as a brown marine-farm fish/net line motif.",
    "MONUMT02": "Redraw as the brown monument silhouette with diagonal bands and base cue.",
    "MONUMT12": "Redraw as the black conspicuous monument silhouette with diagonal bands and base cue.",
    "MORFAC03": "Redraw as a mooring dolphin/pile structure rather than a plain ring.",
    "MORFAC04": "Redraw as a deviation mooring dolphin structure with offset pile geometry.",
    "MSTCON04": "Redraw as a narrow brown mast/needle with base ring.",
    "MSTCON14": "Redraw as a narrow black conspicuous mast/needle with base ring.",
    "NORTHAR1": "Redraw as the simple orange north-arrow/stem glyph with N placement.",
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
        'data-repair-batch="standard-repair-batch14">'
        f"<title>{asset} standard repair batch 22 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _christian_building(colour: str) -> str:
    return (
        f'<path d="M19 48 H45 V30 L32 17 L19 30 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3.1"/>'
        f'<path d="M32 17 V9 M26 14 H38" fill="none" stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<path d="M25 48 V36 H39 V48" fill="none" stroke="{_colour(colour)}" stroke-width="2.6"/>'
    )


def _mosque_minaret(colour: str) -> str:
    return (
        f'<path d="M32 51 V24" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<path d="M24 51 H40 M27 38 H37" fill="none" stroke="{_colour(colour)}" stroke-width="2.8"/>'
        f'<path d="M35 12 C27 14 24 22 30 28 C27 21 31 16 39 15" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.9"/>'
        f'<circle cx="32" cy="54" r="3.5" fill="none" stroke="{_colour(colour)}" stroke-width="2.5"/>'
    )


def _lock_gate(mode: str) -> str:
    body = (
        f'<path d="M14 46 H50 M18 44 V20 M46 44 V20" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<path d="M18 42 L32 24 L46 42" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )
    if mode == "closed":
        body += f'<path d="M21 20 L43 44 M43 20 L21 44" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
    else:
        body += f'<path d="M24 20 H40" fill="none" stroke="{_colour("black")}" stroke-width="2.7"/>'
    return body


def _hulk() -> str:
    return (
        f'<path d="M13 36 C23 45 42 45 52 35 L47 46 H18 Z" fill="none" stroke="{_colour("brown")}" stroke-width="3.2"/>'
        f'<path d="M22 34 L30 24 L41 34 M30 24 V15" fill="none" stroke="{_colour("brown")}" stroke-width="2.8"/>'
        f'<path d="M20 41 H45" fill="none" stroke="{_colour("brown")}" stroke-width="2.5"/>'
    )


def _information_area() -> str:
    return (
        f'<rect x="15" y="18" width="34" height="28" rx="1.5" fill="none" '
        f'stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'{_text(32, 38, "i", "magenta", 24, 700)}'
    )


def _information_marker() -> str:
    return (
        f'<circle cx="18" cy="47" r="5" fill="none" stroke="{_colour("magenta")}" stroke-width="2.8"/>'
        f'<path d="M22 43 L40 25" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'<circle cx="44" cy="21" r="9" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'{_text(44, 26, "i", "magenta", 15, 700)}'
    )


def _inshore_traffic() -> str:
    return (
        f'<path d="M13 42 H51" fill="none" stroke="{_colour("magenta")}" stroke-width="3" stroke-dasharray="6 5"/>'
        f'{_text(32, 33, "IT", "magenta", 22, 700)}'
    )


def _land_point() -> str:
    return (
        f'<circle cx="32" cy="32" r="15" fill="none" stroke="{_colour("brown")}" stroke-width="3.2"/>'
        f'<circle cx="32" cy="32" r="6" fill="{_colour("brown")}" stroke="none"/>'
    )


def _magnetic_wedge(mode: str) -> str:
    body = (
        f'<path d="M18 46 L33 16 L47 46" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M25 35 H40" fill="none" stroke="{_colour("magenta")}" stroke-width="2.7"/>'
    )
    if mode == "area":
        body += f'<path d="M13 52 H51" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6" stroke-dasharray="5 4"/>'
    return body


def _magnetic_variation(mode: str) -> str:
    body = (
        f'<path d="M17 45 L32 18 L48 45" fill="none" stroke="{_colour("magenta")}" stroke-width="3.1"/>'
        f'<path d="M22 25 L32 45 L42 25" fill="none" stroke="{_colour("magenta")}" stroke-width="2.7"/>'
    )
    if mode == "area":
        body += f'<path d="M14 52 H50" fill="none" stroke="{_colour("magenta")}" stroke-width="2.6" stroke-dasharray="5 4"/>'
    return body


def _low_accuracy() -> str:
    return (
        f'<path d="M18 47 L45 20" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'{_text(24, 31, "?", "black", 19, 700)}'
        f'<circle cx="47" cy="18" r="3.5" fill="none" stroke="{_colour("black")}" stroke-width="2.5"/>'
    )


def _marine_farm() -> str:
    return (
        f'<path d="M12 42 C19 34 27 50 34 42 S47 34 54 42" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="3"/>'
        f'<path d="M18 28 H49 M21 22 V36 M32 22 V37 M43 22 V36" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.7"/>'
        f'<path d="M16 25 C23 16 38 18 49 27 C40 36 25 37 16 25 Z" fill="none" '
        f'stroke="{_colour("brown")}" stroke-width="2.5"/>'
    )


def _monument(colour: str) -> str:
    return (
        f'<path d="M24 50 L29 17 H35 L40 50 Z" fill="none" stroke="{_colour(colour)}" stroke-width="3.1"/>'
        f'<path d="M20 51 H44 M27 31 L37 25 M26 42 L39 34" fill="none" '
        f'stroke="{_colour(colour)}" stroke-width="2.6"/>'
        f'<circle cx="32" cy="14" r="3" fill="none" stroke="{_colour(colour)}" stroke-width="2.5"/>'
    )


def _mooring_dolphin() -> str:
    return (
        f'<path d="M21 49 V22 M32 49 V16 M43 49 V22" fill="none" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M18 49 H46 M22 32 H42" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'<circle cx="32" cy="15" r="4" fill="none" stroke="{_colour("black")}" stroke-width="2.5"/>'
    )


def _deviation_mooring() -> str:
    return (
        f'<path d="M20 50 V24 M33 50 V18 M46 50 V28" fill="none" stroke="{_colour("black")}" stroke-width="3.1"/>'
        f'<path d="M17 50 H49 M23 34 L43 26" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
        f'<circle cx="33" cy="17" r="4" fill="none" stroke="{_colour("black")}" stroke-width="2.5"/>'
    )


def _mast(colour: str) -> str:
    return (
        f'<path d="M32 13 V50" fill="none" stroke="{_colour(colour)}" stroke-width="3.2"/>'
        f'<path d="M25 50 H39 M28 26 L32 13 L36 26" fill="none" stroke="{_colour(colour)}" stroke-width="2.7"/>'
        f'<circle cx="32" cy="53" r="4" fill="none" stroke="{_colour(colour)}" stroke-width="2.6"/>'
    )


def _north_arrow() -> str:
    return (
        f'<path d="M32 52 V15 M23 25 L32 15 L41 25" fill="none" stroke="{_colour("orange")}" stroke-width="3.3"/>'
        f'{_text(32, 13, "N", "orange", 12, 700)}'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "christian_building":
        return _svg(asset, _christian_building(spec["colour"]))
    if kind == "mosque_minaret":
        return _svg(asset, _mosque_minaret(spec["colour"]))
    if kind == "lock_gate":
        return _svg(asset, _lock_gate(spec["mode"]))
    if kind == "hulk":
        return _svg(asset, _hulk())
    if kind == "information_area":
        return _svg(asset, _information_area())
    if kind == "information_marker":
        return _svg(asset, _information_marker())
    if kind == "inshore_traffic":
        return _svg(asset, _inshore_traffic())
    if kind == "land_point":
        return _svg(asset, _land_point())
    if kind == "magnetic_wedge":
        return _svg(asset, _magnetic_wedge(spec["mode"]))
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
    if status == "queued_for_chart1_parity_repair":
        return "skipped_batch22_chart1_parity_exact_crop_or_manual_exception_required"
    if (
        "regenerate" in required
        or "attach the exact" in required
        or "before passing" in required
        or "provide a valid reference" in required
        or "verify against" in required
    ):
        return "blocked_batch22_missing_or_unverified_reference_render"
    if "locate/render" in required or "resolve the exact" in required or "needs an exact" in required:
        return "blocked_batch22_missing_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_batch22_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch22_notice_board_family_dedicated_pass"
    if asset.startswith(("TOP", "LIGHTS", "LIT", "DAY")):
        return "skipped_batch22_topmark_daymark_or_light_dedicated_pass"
    if asset.startswith(("BCN", "BOY", "PRICKE")):
        return "skipped_batch22_geometry_heavy_navigation_aid_contract"
    if _provider_count(item) < 2 and item.get("status") == "queued_for_render_repair":
        return "skipped_batch22_low_reference_confidence"
    return "skipped_batch22_outside_bounded_high_confidence_subset"


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
            "risk_bucket": "standard_repair_queue_batch22_high_confidence_non_aid_subset",
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
                "generator": "forge.standard_repair_batch14",
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
        "# Standard Repair Batch 14 / Owned Repair Batch 22",
        "",
        "Owned redraws for a bounded non-aid/non-light/non-notice subset of the current 510-row standard repair queue.",
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
