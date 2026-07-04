"""Repair a high-confidence subset of the 190-row queue into owned batch 19.

Run:
  python3 -m forge.standard_repair_batch11 --render
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
OUT = ROOT / "out" / "standard_repair_batch11"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch19"
REPORT = CATALOG / "owned_repair_batch19.json"
SUMMARY = CATALOG / "owned_repair_batch19.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
EXPECTED_QUEUE_ROWS = 190

REPAIRS: dict[str, dict] = {
    "BOYSUP01": {"kind": "super_buoy", "fills": ("red", "black")},
    "BOYSUP02": {"kind": "super_buoy", "fills": ("black",)},
    "BOYSUP03": {"kind": "super_buoy", "fills": ("red", "black"), "star": True},
    "BUIREL01": {"kind": "christian", "colour": "brown"},
    "BUIREL04": {"kind": "non_christian", "colour": "brown"},
    "BUIREL05": {"kind": "mosque", "colour": "brown"},
    "BUIREL13": {"kind": "christian", "colour": "black"},
    "BUIREL14": {"kind": "non_christian", "colour": "black"},
    "BUIREL15": {"kind": "mosque", "colour": "black"},
    "CHIMNY01": {"kind": "chimney", "colour": "brown"},
    "CHIMNY11": {"kind": "chimney", "colour": "black"},
    "CURSRB01": {"kind": "open_cursor"},
    "CUSTOM01": {"kind": "customs"},
    "DAYSQR01": {"kind": "day_square"},
    "DAYTRI01": {"kind": "day_triangle_up"},
    "DAYTRI05": {"kind": "day_triangle_down"},
    "ESSARE01": {"kind": "essa"},
    "FORSTC01": {"kind": "fortified", "colour": "brown"},
    "FORSTC11": {"kind": "fortified", "colour": "black"},
    "HILTOP01": {"kind": "hilltop", "colour": "brown"},
    "HILTOP11": {"kind": "hilltop", "colour": "black"},
    "LOCMAG01": {"kind": "magnetic", "mode": "point"},
    "LOCMAG51": {"kind": "magnetic", "mode": "line"},
    "LOWACC01": {"kind": "low_accuracy"},
    "MAGVAR01": {"kind": "magnetic", "mode": "variation_point"},
    "MAGVAR51": {"kind": "magnetic", "mode": "variation_line"},
}

REPAIR_NOTES = {
    "BOYSUP01": "Redraw as a super-buoy trapezoid/platform with lower ring cue and red/black load-bearing bands.",
    "BOYSUP02": "Redraw as a black super-buoy trapezoid/platform silhouette instead of a rounded capsule.",
    "BOYSUP03": "Redraw as a super-buoy platform and add the LANBY star/asterisk topmark cue.",
    "BUIREL01": "Replace the church-outline body with a compact brown Christian religious-building cross mark.",
    "BUIREL04": "Rotate the non-Christian witness to a horizontal rectangle/hourglass and remove the baseline.",
    "BUIREL05": "Move the crescent over the stem and add the circular base/dot cue.",
    "BUIREL13": "Replace the church-outline body with a compact black conspicuous Christian mark.",
    "BUIREL14": "Use a black horizontal non-Christian rectangle/hourglass and remove the baseline.",
    "BUIREL15": "Use a black crescent-over-stem minaret cue with circular base/dot.",
    "CHIMNY01": "Add the chimney base ring/dot marker and stronger top smoke form in brown.",
    "CHIMNY11": "Add the conspicuous chimney base ring/dot marker and stronger top smoke form in black.",
    "CURSRB01": "Remove the invented center dot and leave a clean open center between cursor arms.",
    "CUSTOM01": "Replace overlapping circles with a single red/white customs roundel and central white band.",
    "DAYSQR01": "Use a provider-coloured square/rectangular daymark on a stem with lower node cue.",
    "DAYTRI01": "Use an upright provider-coloured triangular daymark on a stem.",
    "DAYTRI05": "Use an inverted provider-coloured triangular daymark on a stem.",
    "ESSARE01": "Replace the dashed placeholder with an ESSA/PSSA boundary text and line marker.",
    "FORSTC01": "Replace the castle top with a compact brown fortified-structure square/outline.",
    "FORSTC11": "Replace the castle top with a compact black conspicuous fortified-structure square/outline.",
    "HILTOP01": "Replace the mountain arch with a brown radial hill/mountain-top starburst.",
    "HILTOP11": "Replace the mountain arch with a black radial conspicuous hill/mountain-top starburst.",
    "LOCMAG01": "Remove the enclosure and draw a magenta magnetic-anomaly point wedge/line.",
    "LOCMAG51": "Remove the arch/T-base and draw the magenta magnetic-anomaly line/area wedge.",
    "LOWACC01": "Replace the contour arc with a low-accuracy question mark and diagonal leader cue.",
    "MAGVAR01": "Replace the arrow/crossbar with a magenta magnetic-variation point wedge/line.",
    "MAGVAR51": "Replace the arrow/dashed arc with a magenta magnetic-variation line/area wedge.",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _text(x: int, y: int, label: str, colour: str, size: int = 16, weight: int = 700) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        'font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="{weight}" fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch11">'
        f"<title>{asset} standard repair batch 19 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _super_buoy(asset: str, fills: tuple[str, ...], star: bool = False) -> str:
    clip = f"clip-{asset}"
    body = (
        '<defs>'
        f'<clipPath id="{clip}"><path d="M18 30 L24 16 H40 L46 30 L42 45 H22 Z"/></clipPath>'
        '</defs>'
        f'<g clip-path="url(#{clip})">'
    )
    if len(fills) == 1:
        body += f'<rect x="0" y="0" width="64" height="64" fill="{_colour(fills[0])}"/>'
    else:
        body += f'<rect x="0" y="0" width="64" height="32" fill="{_colour(fills[0])}"/>'
        body += f'<rect x="0" y="32" width="64" height="32" fill="{_colour(fills[1])}"/>'
    body += (
        '</g>'
        f'<path d="M18 30 L24 16 H40 L46 30 L42 45 H22 Z" fill="none" '
        f'stroke="{_colour("black")}" stroke-width="3.5"/>'
        f'<path d="M24 45 C27 52 37 52 40 45" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
        f'<circle cx="32" cy="55" r="4.2" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )
    if star:
        body += (
            f'<path d="M32 6 V20 M25 9 L39 17 M39 9 L25 17" fill="none" '
            f'stroke="{_colour("black")}" stroke-width="3"/>'
        )
    return body


def _christian(colour: str) -> str:
    return (
        f'<path d="M32 13 V47 M23 24 H41" fill="none" stroke="{_colour(colour)}" stroke-width="5"/>'
        f'<circle cx="32" cy="52" r="4" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'
    )


def _non_christian(colour: str) -> str:
    return (
        f'<rect x="18" y="24" width="28" height="17" rx="1.5" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M18 24 L46 41 M46 24 L18 41" fill="none" stroke="{_colour(colour)}" stroke-width="3.5"/>'
    )


def _mosque(colour: str) -> str:
    return (
        f'<path d="M34 11 C27 13 25 23 31 28 C27 27 24 24 24 20 C24 14 29 10 34 11 Z" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="3.3"/>'
        f'<path d="M32 29 V47" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<circle cx="32" cy="52" r="4" fill="none" stroke="{_colour(colour)}" stroke-width="3.3"/>'
    )


def _chimney(colour: str) -> str:
    return (
        f'<path d="M27 20 H38 L40 47 H25 Z" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M29 16 C34 8 45 11 42 21 M35 16 C39 12 47 15 45 23" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="3"/>'
        f'<circle cx="32" cy="55" r="4" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'
    )


def _open_cursor() -> str:
    return (
        f'<path d="M32 8 V23 M32 41 V56 M8 32 H23 M41 32 H56" fill="none" '
        f'stroke="{_colour("orange")}" stroke-width="5.5"/>'
    )


def _customs() -> str:
    return (
        f'<circle cx="32" cy="32" r="18" fill="{_colour("red")}" stroke="{_colour("red")}" stroke-width="4"/>'
        f'<rect x="16" y="26" width="32" height="12" fill="{_colour("white")}" stroke="none"/>'
        f'<circle cx="32" cy="32" r="18" fill="none" stroke="{_colour("red")}" stroke-width="4"/>'
    )


def _day_square() -> str:
    return (
        f'<rect x="20" y="12" width="24" height="24" fill="{_colour("yellow")}" '
        f'stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="M32 36 V52" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<circle cx="32" cy="56" r="4" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'
    )


def _day_triangle(up: bool) -> str:
    points = "32,11 48,39 16,39" if up else "16,17 48,17 32,45"
    stem = "M32 39 V56" if up else "M32 45 V56"
    return (
        f'<polygon points="{points}" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="3.2"/>'
        f'<path d="{stem}" fill="none" stroke="{_colour("black")}" stroke-width="4"/>'
        f'<circle cx="32" cy="57" r="3" fill="none" stroke="{_colour("black")}" stroke-width="2.8"/>'
    )


def _essa() -> str:
    return (
        f'<path d="M15 43 C24 35 40 35 49 43" fill="none" stroke="{_colour("magenta")}" '
        'stroke-width="3.2" stroke-dasharray="7 5"/>'
        f'<rect x="17" y="16" width="30" height="20" rx="2" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
        f'{_text(32, 31, "PSSA", "magenta", 12)}'
    )


def _fortified(colour: str) -> str:
    return (
        f'<rect x="20" y="19" width="24" height="24" fill="none" stroke="{_colour(colour)}" stroke-width="4"/>'
        f'<path d="M25 24 H39 M25 32 H39 M25 40 H39" fill="none" stroke="{_colour(colour)}" stroke-width="2.7"/>'
    )


def _hilltop(colour: str) -> str:
    return (
        f'<circle cx="32" cy="32" r="3.5" fill="{_colour(colour)}" stroke="none"/>'
        f'<path d="M32 13 V24 M32 40 V51 M13 32 H24 M40 32 H51 '
        f'M19 19 L27 27 M45 19 L37 27 M19 45 L27 37 M45 45 L37 37" '
        f'fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>'
    )


def _magnetic(mode: str) -> str:
    area = mode.endswith("line")
    variation = mode.startswith("variation")
    body = (
        f'<path d="M19 44 L32 13 L45 44" fill="none" stroke="{_colour("magenta")}" stroke-width="3.5"/>'
        f'<path d="M26 36 H38" fill="none" stroke="{_colour("magenta")}" stroke-width="3"/>'
    )
    if variation:
        body += f'{_text(32, 55, "V", "magenta", 13)}'
    else:
        body += f'{_text(32, 55, "M", "magenta", 13)}'
    if area:
        body += (
            f'<path d="M14 50 C24 45 40 45 50 50" fill="none" stroke="{_colour("magenta")}" '
            'stroke-width="2.8" stroke-dasharray="5 5"/>'
        )
    else:
        body += f'<circle cx="32" cy="58" r="2.5" fill="{_colour("magenta")}" stroke="none"/>'
    return body


def _low_accuracy() -> str:
    return (
        f'{_text(29, 35, "?", "black", 24)}'
        f'<path d="M39 19 L23 47" fill="none" stroke="{_colour("black")}" stroke-width="3.5"/>'
        f'<path d="M16 50 H48" fill="none" stroke="{_colour("black")}" stroke-width="2.8" stroke-dasharray="5 5"/>'
    )


def _redraw(asset: str) -> str:
    spec = REPAIRS[asset]
    kind = spec["kind"]
    if kind == "super_buoy":
        return _svg(asset, _super_buoy(asset, spec["fills"], spec.get("star", False)))
    if kind == "christian":
        return _svg(asset, _christian(spec["colour"]))
    if kind == "non_christian":
        return _svg(asset, _non_christian(spec["colour"]))
    if kind == "mosque":
        return _svg(asset, _mosque(spec["colour"]))
    if kind == "chimney":
        return _svg(asset, _chimney(spec["colour"]))
    if kind == "open_cursor":
        return _svg(asset, _open_cursor())
    if kind == "customs":
        return _svg(asset, _customs())
    if kind == "day_square":
        return _svg(asset, _day_square())
    if kind == "day_triangle_up":
        return _svg(asset, _day_triangle(True))
    if kind == "day_triangle_down":
        return _svg(asset, _day_triangle(False))
    if kind == "essa":
        return _svg(asset, _essa())
    if kind == "fortified":
        return _svg(asset, _fortified(spec["colour"]))
    if kind == "hilltop":
        return _svg(asset, _hilltop(spec["colour"]))
    if kind == "magnetic":
        return _svg(asset, _magnetic(spec["mode"]))
    if kind == "low_accuracy":
        return _svg(asset, _low_accuracy())
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
    codes = set(_safety_codes(item))
    required = (_required_change(item) or "").lower()
    if "regenerate" in required or "attach the exact" in required or "before passing" in required:
        return "blocked_missing_or_unverified_reference_render"
    if "locate/render" in required or "resolve the exact" in required or "needs an exact" in required:
        return "blocked_missing_exact_reference"
    if {"missing_reference_crop", "missing_exact_reference", "insufficient_visual_evidence"}.intersection(codes):
        return "hard_blocked_missing_exact_reference"
    if asset.startswith(("NMKINF", "NMKPRH", "NMKRCD", "NMKREG", "NOTBRD", "NOTMRK")):
        return "skipped_batch19_notice_board_family_dedicated_pass"
    if _provider_count(item) < 2:
        return "skipped_batch19_low_reference_confidence"
    if asset.startswith(("BOY", "BCN", "HRBFAC", "LIT", "MORFAC", "PRICKE")):
        return "skipped_batch19_geometry_heavy_navigation_aid_contract"
    return "skipped_batch19_outside_bounded_high_confidence_subset"


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
            "risk_bucket": "standard_repair_queue_batch19_high_confidence_subset",
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
                "generator": "forge.standard_repair_batch11",
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
        "# Standard Repair Batch 11 / Owned Repair Batch 19",
        "",
        "Owned redraws for a bounded high-confidence subset of the current 190-row standard repair queue.",
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
