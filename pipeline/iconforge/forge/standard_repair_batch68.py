"""Human-repair queued BOYBAR barrel buoy rows into owned batch 76.

Run:
  python3 -m forge.standard_repair_batch68 --render
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
OUT = ROOT / "out" / "standard_repair_batch68"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch76"
REPORT = CATALOG / "owned_repair_batch76.json"
SUMMARY = CATALOG / "owned_repair_batch76.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")
TARGETS = ("BOYBAR01", "BOYBAR60", "BOYBAR61", "BOYBAR62")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    if name == "grey":
        name = "gray"
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch68">'
        f"<title>{asset} human-repaired sideways barrel buoy candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _source_rows() -> dict[str, dict]:
    table = json.loads(SOURCE_TABLE.read_text())
    return {row["asset"]: row for row in table.get("rows", [])}


def _fill_colour(asset: str) -> str:
    if asset == "BOYBAR60":
        return "red"
    if asset == "BOYBAR61":
        return "green"
    if asset == "BOYBAR62":
        return "yellow"
    return "white"


def _barrel(asset: str) -> str:
    fill = _fill_colour(asset)
    stroke = "black"
    # Helm-style translation of the user-provided cylinder symbol: full side-on
    # barrel, prominent front oval, rounded right end, and waterline through the
    # middle. No oil mark, spout, top hardware, or decorative bands.
    body = (
        f'<path d="M18 17 H47 C55 17 59 25 59 33 '
        f'C59 41 55 49 47 49 H18 '
        f'C10 49 6 41 6 33 C6 25 10 17 18 17 Z" '
        f'fill="{_colour(fill)}" stroke="none"/>'
        f'<path d="M18 17 H47 C55 17 59 25 59 33 '
        f'C59 41 55 49 47 49 H18" '
        f'fill="none" stroke="{_colour(stroke)}" stroke-width="3"/>'
        f'<path d="M18 17 C27 17 30 49 18 49 C9 49 6 17 18 17" '
        f'fill="none" stroke="{_colour(stroke)}" stroke-width="3"/>'
        f'<path d="M3 36 C7 36 9 38 13 38 '
        f'C18 38 19 35 24 35 C29 35 30 38 35 38 '
        f'C40 38 41 35 46 35 C51 35 52 38 56 38 '
        f'C59 38 60 36 61 36" '
        f'fill="none" stroke="{_colour(stroke)}" stroke-width="2.6"/>'
    )
    if asset == "BOYBAR01":
        return body
    return body


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


def build(*, render_outputs: bool = False) -> dict:
    source_rows = _source_rows()
    missing = sorted(set(TARGETS) - set(source_rows))
    if missing:
        raise RuntimeError(f"source table missing repair target(s): {missing}")

    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in TARGETS:
        source_row = source_rows[asset]
        helm = source_row.get("helm_candidate") or {}
        svg = _svg(asset, _barrel(asset))
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": source_row.get("name"),
            "queue_action": "human_rejection_superseded_batch75",
            "risk_bucket": "barrel_buoy_human_repair_batch76",
            "candidate_strategy": "owned_sideways_barrel_buoy_redraw_from_opencpn_s101_and_human_feedback",
            "candidate_source": helm.get("canonical_svg"),
            "before_svg": helm.get("source_svg") or helm.get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "required_change": (
                "Human rejected upright/capped barrel body. Redraw as a low sideways floating barrel/drum "
                "matching OpenCPN/S-101 witness; BOYBAR01 is black-outline/reference style, colour-specific "
                "rows keep red/green/yellow fill."
            ),
            "safety_reason_codes": ["human_rejected_wrong_barrel_orientation", "wrong_symbol_body"],
            "semantic_brief": source_row.get("semantic_brief"),
            "visual_examples": source_row.get("reference_providers", {}),
            "s57_structure": source_row.get("s57_structure"),
            "chart1_parity_gate": source_row.get("chart1_parity_gate"),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "human review rejection plus OpenCPN/S-101 barrel-buoy witnesses",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch68",
                "reference_role": "OpenCPN/S-101/Chart No.1 witnesses and human feedback drive generated-owned redraw",
            },
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
        "# Standard Repair Batch 68 / Owned Repair Batch 76",
        "",
        "Human-review repair pass for `BOYBAR*` barrel buoy rows after batch75 rejection.",
        "",
        f"- failed_repaired: `{result['summary']['failed_repaired']}`",
        "- visual_parity: `repaired_pending_judge_rerun`",
        "",
        "| Asset | Repair |",
        "| --- | --- |",
    ]
    for row in result["symbols"]:
        lines.append(f"| `{row['asset']}` | sideways low barrel/drum silhouette |")
    lines.extend(["", "Rows remain pending judge rerun; none are final-approved.", ""])
    SUMMARY.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "outputs": result["outputs"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
