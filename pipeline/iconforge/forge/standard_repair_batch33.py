"""Repair prohibition/recommended notice slice into owned repair batch 41.

Run:
  python3 -m forge.standard_repair_batch33 --render
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
OUT = ROOT / "out" / "standard_repair_batch33"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch41"
REPORT = CATALOG / "owned_repair_batch41.json"
SUMMARY = CATALOG / "owned_repair_batch41.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "NMKPRH02": "entry_prohibited",
    "NMKPRH06": "passing_overtaking_prohibited",
    "NMKPRH07": "berthing_prohibited",
    "NMKPRH08": "anchoring_prohibited",
    "NMKPRH10": "turning_prohibited",
    "NMKPRH11": "avoid_wash",
    "NMKPRH12": "left_passing_prohibited",
    "NMKPRH13": "right_passing_prohibited",
    "NMKPRH14": "engine_boats_prohibited",
    "NMKRCD01": "recommended_both",
    "NMKRCD02": "recommended_one",
    "NMKRCD03": "recommended_right",
    "NMKRCD04": "recommended_left",
    "NMKRCD05": "recommended_left_traffic",
    "NMKRCD06": "recommended_right_traffic",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch33">'
        f"<title>{asset} repair batch 41 notice candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _board(fill: str, inner: str, *, stroke: str = "black") -> str:
    return (
        f'<rect x="9" y="9" width="46" height="46" rx="3" fill="{_colour(fill)}" '
        f'stroke="{_colour(stroke)}" stroke-width="2.8"/>'
        f"{inner}"
    )


def _path(d: str, colour: str = "white", width: float = 4) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _slash() -> str:
    return _path("M18 46 L46 18", "white", 5)


def _entry_prohibited() -> str:
    return _board("red", _path("M22 18 V46 M42 18 V46", "white", 6) + _slash())


def _passing_overtaking_prohibited() -> str:
    arrows = (
        _path("M23 44 V20 M16 27 L23 20 L30 27", "white", 3.5)
        + _path("M41 20 V44 M34 37 L41 44 L48 37", "white", 3.5)
    )
    return _board("red", arrows + _slash())


def _berthing_prohibited() -> str:
    glyph = (
        _path("M20 20 V47 M16 24 H25 M16 43 H25", "white", 4)
        + _path("M24 44 H44 L38 50 H25 Z", "white", 3.5)
    )
    return _board("red", glyph + _slash())


def _anchoring_prohibited() -> str:
    anchor = (
        _path("M32 17 V43 M24 26 H40 M27 17 H37", "white", 4)
        + _path("M20 37 C23 48 41 48 44 37 M20 37 L25 38 M44 37 L39 38", "white", 4)
    )
    return _board("red", anchor + _slash())


def _turning_prohibited() -> str:
    turn = (
        _path("M43 31 C43 22 34 17 26 21 C18 25 17 37 25 43 C32 48 42 44 45 36", "white", 4)
        + _path("M39 25 L45 31 L51 25", "white", 4)
    )
    return _board("red", turn + _slash())


def _avoid_wash() -> str:
    waves = (
        _path("M17 29 C22 24 27 34 32 29 C37 24 42 34 47 29", "white", 3.5)
        + _path("M17 40 C22 35 27 45 32 40 C37 35 42 45 47 40", "white", 3.5)
    )
    return _board("red", waves + _slash())


def _split_diamond(side: str) -> str:
    if side == "left":
        left = f'<polygon points="32,12 32,52 12,32" fill="{_colour("red")}" stroke="{_colour("white")}" stroke-width="3"/>'
        right = f'<polygon points="32,12 52,32 32,52" fill="{_colour("white")}" stroke="{_colour("red")}" stroke-width="3"/>'
    else:
        left = f'<polygon points="32,12 32,52 12,32" fill="{_colour("white")}" stroke="{_colour("red")}" stroke-width="3"/>'
        right = f'<polygon points="32,12 52,32 32,52" fill="{_colour("red")}" stroke="{_colour("white")}" stroke-width="3"/>'
    return left + right + f'<path d="M19 45 L45 19" fill="none" stroke="{_colour("black")}" stroke-width="3"/>'


def _engine_boats_prohibited() -> str:
    boat = (
        _path("M18 39 H46 L40 47 H24 Z", "white", 3.8)
        + _path("M31 39 V26 H41 V39", "white", 3.2)
    )
    return _board("red", boat + _slash())


def _yellow_diamond(inner: str = "") -> str:
    return (
        f'<polygon points="32,9 55,32 32,55 9,32" fill="{_colour("yellow")}" '
        f'stroke="{_colour("black")}" stroke-width="2.8"/>'
        f"{inner}"
    )


def _recommended_both() -> str:
    return _yellow_diamond(_path("M21 32 H43 M28 25 L21 32 L28 39 M36 25 L43 32 L36 39", "black", 3.3))


def _recommended_one() -> str:
    return (
        f'<polygon points="24,13 42,31 24,49 6,31" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
        f'<polygon points="40,13 58,31 40,49 22,31" fill="{_colour("yellow")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
        + _path("M24 31 H43 M36 24 L43 31 L36 38", "black", 3)
    )


def _recommended_side(side: str) -> str:
    if side == "right":
        green = f'<polygon points="32,9 55,32 32,55" fill="{_colour("green")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
        white = f'<polygon points="32,9 32,55 9,32" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
    else:
        green = f'<polygon points="32,9 32,55 9,32" fill="{_colour("green")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
        white = f'<polygon points="32,9 55,32 32,55" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
    return green + white + _path("M22 32 H42", "black", 3)


def _recommended_traffic(direction: str) -> str:
    if direction == "left":
        arrow = _path("M45 32 H20 M27 25 L20 32 L27 39", "white", 4)
    else:
        arrow = _path("M19 32 H44 M37 25 L44 32 L37 39", "white", 4)
    return _board("blue", arrow)


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "entry_prohibited":
        return _svg(asset, _entry_prohibited())
    if kind == "passing_overtaking_prohibited":
        return _svg(asset, _passing_overtaking_prohibited())
    if kind == "berthing_prohibited":
        return _svg(asset, _berthing_prohibited())
    if kind == "anchoring_prohibited":
        return _svg(asset, _anchoring_prohibited())
    if kind == "turning_prohibited":
        return _svg(asset, _turning_prohibited())
    if kind == "avoid_wash":
        return _svg(asset, _avoid_wash())
    if kind == "left_passing_prohibited":
        return _svg(asset, _split_diamond("left"))
    if kind == "right_passing_prohibited":
        return _svg(asset, _split_diamond("right"))
    if kind == "engine_boats_prohibited":
        return _svg(asset, _engine_boats_prohibited())
    if kind == "recommended_both":
        return _svg(asset, _recommended_both())
    if kind == "recommended_one":
        return _svg(asset, _recommended_one())
    if kind == "recommended_right":
        return _svg(asset, _recommended_side("right"))
    if kind == "recommended_left":
        return _svg(asset, _recommended_side("left"))
    if kind == "recommended_left_traffic":
        return _svg(asset, _recommended_traffic("left"))
    if kind == "recommended_right_traffic":
        return _svg(asset, _recommended_traffic("right"))
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
            "risk_bucket": "prohibition_recommendation_notice_repair_batch41",
            "candidate_strategy": "owned_notice_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue NMKPRH/NMKRCD notice slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch33",
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
        "# Standard Repair Batch 33 / Owned Repair Batch 41",
        "",
        "Owned redraws for prohibition and recommended-passage notice judge failures.",
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
