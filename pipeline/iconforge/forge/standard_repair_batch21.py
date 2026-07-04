"""Repair the WRECKS01 rerun failure into owned repair batch 29.

Run:
  python3 -m forge.standard_repair_batch21 --render
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
OUT = ROOT / "out" / "standard_repair_batch21"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch29"
REPORT = CATALOG / "owned_repair_batch29.json"
SUMMARY = CATALOG / "owned_repair_batch29.md"
PALETTES = ("day", "dusk", "night")
HOMEBREW_CAIRO = Path("/opt/homebrew/lib/libcairo.2.dylib")

REPAIR_ASSET = "WRECKS01"
REPAIR_NOTE = (
    "Judge rerun repair: remove the invented white aperture and redraw as the "
    "exposed wreck low hull plus sloped wreckage/mast witness."
)


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch21">'
        f"<title>{asset} rerun repair batch 29 candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _wrecks01() -> str:
    black = _colour("black")
    return (
        f'<path d="M13 43 H51" fill="none" stroke="{black}" stroke-width="7"/>'
        f'<path d="M18 31 L31 43 H18 Z" fill="{black}" stroke="{black}" stroke-width="2.4"/>'
        f'<path d="M39 20 L33 43" fill="none" stroke="{black}" stroke-width="7"/>'
        f'<path d="M27 43 H37" fill="none" stroke="{black}" stroke-width="5"/>'
    )


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
    if REPAIR_ASSET not in source_rows:
        raise RuntimeError(f"source table missing repair target: {REPAIR_ASSET}")

    source_row = source_rows[REPAIR_ASSET]
    helm = source_row.get("helm_candidate") or {}
    judge = (source_row.get("judge") or {}).get("latest") or {}
    svg = _svg(REPAIR_ASSET, _wrecks01())
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    svg_path = SVG_OUT / f"{_safe(REPAIR_ASSET)}.svg"
    svg_path.write_text(svg)
    renders = {}
    if render_outputs:
        for palette in PALETTES:
            renders[palette] = _render_svg(svg, REPAIR_ASSET, palette)

    row = {
        "asset": REPAIR_ASSET,
        "name": source_row.get("name"),
        "queue_action": "judge_rerun_failure_consumed",
        "risk_bucket": "wrecks01_rerun_repair_batch29",
        "candidate_strategy": "owned_redraw_from_judge_rerun_feedback",
        "candidate_source": helm.get("canonical_svg"),
        "before_svg": helm.get("canonical_svg"),
        "after_svg": str(svg_path.relative_to(ROOT)),
        "after_renders": renders,
        "repair_note": REPAIR_NOTE,
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
            "source_priority_basis": "standard_judge_batch_026_027_rerun_feedback",
            "style_contract_id": OPENBRIDGE_STYLE_ID,
            "generator": "forge.standard_repair_batch21",
            "reference_role": "judge feedback and provider refs are shape witnesses; SVG is owned redraw",
        },
        "source_judge": "catalog/standard_judge_batch_026_027_rerun.json",
    }

    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "failed_repaired": 1,
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": [row],
        "blockers": [],
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    row = result["symbols"][0]
    lines = [
        "# Standard Repair Batch 21 / Owned Repair Batch 29",
        "",
        "Owned redraw for the WRECKS01 failure found by the batch26/27 judge rerun.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Repaired",
        "",
        f"- `{row['asset']}`: {row.get('repair_note')}",
    ])
    required = row.get("required_change")
    if required:
        lines.append(f"  - Judge required change: {required}")
    lines.extend(["", "Row remains pending judge rerun; it is not final-approved."])
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
