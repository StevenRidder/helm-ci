"""Repair terminal glyph slice into owned repair batch 44.

Run:
  python3 -m forge.standard_repair_batch36 --render
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
OUT = ROOT / "out" / "standard_repair_batch36"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch44"
REPORT = CATALOG / "owned_repair_batch44.json"
SUMMARY = CATALOG / "owned_repair_batch44.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIRS = {
    "ROLROL01": "roro_label",
    "TERMNL01": "passenger",
    "TERMNL02": "ferry",
    "TERMNL03": "container",
    "TERMNL04": "bulk",
    "TERMNL05": "oil",
    "TERMNL06": "fuel",
    "TERMNL07": "chemical",
    "TERMNL08": "liquid",
    "TERMNL09": "explosive",
    "TERMNL10": "fish",
    "TERMNL11": "car",
    "TERMNL12": "cargo",
    "TERMNL13": "roro",
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch36">'
        f"<title>{asset} repair batch 44 terminal candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _path(d: str, colour: str = "black", width: float = 3.5) -> str:
    return f'<path d="{d}" fill="none" stroke="{_colour(colour)}" stroke-width="{width}"/>'


def _text(label: str, colour: str = "black", y: int = 38, size: int = 13) -> str:
    return (
        f'<text x="32" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" font-weight="700" '
        f'fill="{_colour(colour)}" stroke="none">{label}</text>'
    )


def _circle(inner: str, colour: str = "black") -> str:
    return f'<circle cx="32" cy="32" r="21" fill="none" stroke="{_colour(colour)}" stroke-width="3.4"/>{inner}'


def _passenger() -> str:
    return _circle(f'<circle cx="32" cy="22" r="4" fill="{_colour("black")}" stroke="none"/>' + _path("M32 27 V43 M24 32 H40", "black", 3.5))


def _ferry() -> str:
    return _circle(_path("M18 38 H46 L40 47 H24 Z", "black", 3.5) + _path("M24 38 V29 H40 V38", "black", 3))


def _container() -> str:
    return _circle(
        f'<rect x="20" y="23" width="24" height="18" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2.8"/>'
        + _path("M26 23 V41 M32 23 V41 M38 23 V41", "black", 2.2)
    )


def _bulk() -> str:
    return _circle(f'<path d="M20 42 L32 22 L44 42 Z" fill="{_colour("white")}" stroke="{_colour("black")}" stroke-width="3"/>')


def _fish() -> str:
    return _circle(_path("M19 33 C26 24 38 24 45 33 C38 42 26 42 19 33 Z", "black", 3) + _path("M45 33 L52 27 V39 Z", "black", 3))


def _car() -> str:
    return _circle(
        _path("M20 36 H45 L40 27 H25 Z", "black", 3)
        + f'<circle cx="26" cy="40" r="3" fill="{_colour("black")}" stroke="none"/>'
        + f'<circle cx="39" cy="40" r="3" fill="{_colour("black")}" stroke="none"/>'
    )


def _cargo() -> str:
    return _circle(f'<rect x="22" y="23" width="20" height="20" fill="none" stroke="{_colour("black")}" stroke-width="3.4"/>')


def _explosive() -> str:
    return _circle(
        f'<circle cx="32" cy="33" r="7" fill="{_colour("red")}" stroke="{_colour("black")}" stroke-width="2.5"/>'
        + _path("M32 16 V24 M32 42 V50 M16 33 H24 M40 33 H48 M21 22 L27 28 M43 22 L37 28 M21 44 L27 38 M43 44 L37 38", "black", 2.5),
        "black",
    )


def _label_circle(label: str, size: int = 13) -> str:
    return _circle(_text(label, "black", 38, size))


def _roro_label() -> str:
    return _text("RoRo", "black", 39, 20)


def _redraw(asset: str) -> str:
    kind = REPAIRS[asset]
    if kind == "roro_label":
        return _svg(asset, _roro_label())
    if kind == "passenger":
        return _svg(asset, _passenger())
    if kind == "ferry":
        return _svg(asset, _ferry())
    if kind == "container":
        return _svg(asset, _container())
    if kind == "bulk":
        return _svg(asset, _bulk())
    if kind == "oil":
        return _svg(asset, _label_circle("OIL", 13))
    if kind == "fuel":
        return _svg(asset, _label_circle("FUEL", 10))
    if kind == "chemical":
        return _svg(asset, _label_circle("CH", 14))
    if kind == "liquid":
        return _svg(asset, _label_circle("LIQ", 13))
    if kind == "explosive":
        return _svg(asset, _explosive())
    if kind == "fish":
        return _svg(asset, _fish())
    if kind == "car":
        return _svg(asset, _car())
    if kind == "cargo":
        return _svg(asset, _cargo())
    if kind == "roro":
        return _svg(asset, _label_circle("RoRo", 10))
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
            "risk_bucket": "terminal_repair_batch44",
            "candidate_strategy": "owned_terminal_glyph_redraw_from_semantic_brief_and_provider_witnesses",
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
                "source_priority_basis": "standard_repair_queue terminal slice",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch36",
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
        "# Standard Repair Batch 36 / Owned Repair Batch 44",
        "",
        "Owned redraws for terminal judge failures.",
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
