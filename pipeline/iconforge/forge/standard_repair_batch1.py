"""Repair the first Standard Source Table renderer queue.

This consumes the archived `catalog/standard_judge_batch_002.json` failures and
writes owned SVG redraws for those beacon/stake/tower rows. Rows remain pending
judge rerun until `standard_judge_batch_003` is archived.

Run:
  python -m forge.standard_repair_batch1 --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
SOURCE_JUDGE = CATALOG / "standard_judge_batch_002.json"
OUT = ROOT / "out" / "standard_repair_batch1"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch9"
REPORT = CATALOG / "owned_repair_batch9.json"
SUMMARY = CATALOG / "owned_repair_batch9.md"
PALETTES = ("day", "dusk", "night")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch1">'
        f"<title>{asset} standard source repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _rect_body(asset: str, bands: list[str], *, x: float = 27, y: float = 13, w: float = 10, h: float = 32) -> str:
    body = [
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="var(--white)" '
        'stroke="var(--black)" stroke-width="2.4"/>'
    ]
    band_h = h / len(bands)
    for idx, colour in enumerate(bands):
        by = y + idx * band_h
        body.append(
            f'<rect x="{x:g}" y="{by:g}" width="{w:g}" height="{band_h:g}" '
            f'fill="var(--{colour})"/>'
        )
    body.append(
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" '
        'stroke="var(--black)" stroke-width="2.4"/>'
    )
    body.append('<path d="M32 45V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    return _svg(asset, "".join(body))


def _stake(asset: str, bands: list[str]) -> str:
    return _rect_body(asset, bands, x=29, y=12, w=6, h=36)


def _tower(asset: str, bands: list[str]) -> str:
    h = 34
    y = 12
    top_w = 8
    bot_w = 22
    top_x = 32 - top_w / 2
    bot_x = 32 - bot_w / 2
    band_h = h / len(bands)
    body = []
    for idx, colour in enumerate(bands):
        y0 = y + idx * band_h
        y1 = y + (idx + 1) * band_h
        t0 = (y0 - y) / h
        t1 = (y1 - y) / h
        w0 = top_w + (bot_w - top_w) * t0
        w1 = top_w + (bot_w - top_w) * t1
        x0 = 32 - w0 / 2
        x1 = 32 - w1 / 2
        points = f"{x0:g},{y0:g} {x0 + w0:g},{y0:g} {x1 + w1:g},{y1:g} {x1:g},{y1:g}"
        body.append(f'<polygon points="{points}" fill="var(--{colour})"/>')
    outline = f"{top_x:g},{y:g} {top_x + top_w:g},{y:g} {bot_x + bot_w:g},{y + h:g} {bot_x:g},{y + h:g}"
    body.append(f'<polygon points="{outline}" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    body.append('<path d="M32 46V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    return _svg(asset, "".join(body))


def _lattice(asset: str) -> str:
    return _svg(
        asset,
        '<path d="M20 52L32 12L44 52Z" fill="none" stroke="var(--black)" stroke-width="2.4"/>'
        '<path d="M24 39H40M27 28H37M22 52L39 28M42 52L25 28" fill="none" '
        'stroke="var(--black)" stroke-width="2.2"/>'
    )


def _isolated_danger(asset: str) -> str:
    return _svg(
        asset,
        '<circle cx="32" cy="18" r="5" fill="var(--black)" stroke="var(--black)" stroke-width="2.2"/>'
        '<circle cx="32" cy="32" r="5" fill="var(--black)" stroke="var(--black)" stroke-width="2.2"/>'
        '<path d="M32 37V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>'
    )


def _safe_water(asset: str, minor: bool = False) -> str:
    if minor:
        return _rect_body(asset, ["red", "white", "red", "white"], x=29, y=12, w=6, h=36)
    return _tower(asset, ["red", "white", "red", "white"])


def _redraw(asset: str) -> str:
    mapping = {
        "BCNCON81": lambda: _rect_body(asset, ["black"]),
        "BCNGEN65": lambda: _rect_body(asset, ["green", "white", "green", "white"]),
        "BCNGEN70": lambda: _rect_body(asset, ["black", "yellow", "black"]),
        "BCNGEN71": lambda: _rect_body(asset, ["yellow", "black", "yellow"]),
        "BCNGEN76": lambda: _rect_body(asset, ["black", "red", "black"]),
        "BCNISD21": lambda: _isolated_danger(asset),
        "BCNLAT15": lambda: _rect_body(asset, ["red"]),
        "BCNLAT16": lambda: _rect_body(asset, ["green"]),
        "BCNLAT21": lambda: _stake(asset, ["red"]),
        "BCNLAT22": lambda: _stake(asset, ["green"]),
        "BCNLAT23": lambda: _rect_body(asset, ["red", "green"]),
        "BCNLAT50": lambda: _stake(asset, ["black"]),
        "BCNLTC01": lambda: _lattice(asset),
        "BCNSAW13": lambda: _safe_water(asset),
        "BCNSAW21": lambda: _safe_water(asset, minor=True),
        "BCNSPP13": lambda: _rect_body(asset, ["yellow"]),
        "BCNSPP21": lambda: _stake(asset, ["yellow"]),
        "BCNSTK02": lambda: _stake(asset, ["black"]),
        "BCNSTK03": lambda: _stake(asset, ["black"]),
        "BCNSTK77": lambda: _stake(asset, ["green", "white", "green", "white"]),
        "BCNSTK79": lambda: _stake(asset, ["red", "green", "red"]),
        "BCNSTK80": lambda: _stake(asset, ["green", "red", "green"]),
        "BCNTOW01": lambda: _lattice(asset),
        "BCNTOW63": lambda: _tower(asset, ["white", "red", "white", "red"]),
        "BCNTOW66": lambda: _tower(asset, ["white", "green", "white", "green"]),
        "BCNTOW70": lambda: _tower(asset, ["black", "yellow", "black"]),
        "BCNTOW71": lambda: _tower(asset, ["yellow", "black", "yellow"]),
        "BCNTOW74": lambda: _tower(asset, ["red", "green", "red"]),
        "BCNTOW76": lambda: _tower(asset, ["black", "red", "black"]),
    }
    if asset not in mapping:
        raise KeyError(asset)
    return mapping[asset]()


def _render_svg(svg: str, asset: str, palette: str) -> str:
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def build(*, render_outputs: bool = False) -> dict:
    source_rows = {
        row["asset"]: row
        for row in json.loads(SOURCE_TABLE.read_text()).get("rows", [])
    }
    judge = json.loads(SOURCE_JUDGE.read_text())
    queue_items = []
    for verdict in judge.get("verdicts", []):
        if verdict.get("pass"):
            continue
        row = source_rows.get(verdict["symbol_id"], {})
        queue_items.append({
            "asset": verdict["symbol_id"],
            "name": row.get("name"),
            "required_change": verdict.get("required_change"),
            "helm_candidate": row.get("helm_candidate", {}),
            "reference_providers": row.get("reference_providers", {}),
        })
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in queue_items:
        asset = item["asset"]
        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "name": item.get("name"),
            "queue_action": "standard_source_table_repair",
            "risk_bucket": "standard_judge_batch_002_fail",
            "candidate_strategy": "owned_redraw_from_standard_repair_queue",
            "candidate_source": item.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": item.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": item.get("required_change"),
            "visual_examples": item.get("reference_providers", {}),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "standard_source_table_repair",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.standard_repair_batch1",
                "reference_role": "S-101/Aqua Map/OpenCPN visual reference; redrawn owned SVG",
            },
        })
    result = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_judge": str(SOURCE_JUDGE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(REPORT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "source_judge_failed_rows": len(queue_items),
            "failed_repaired": len(rows),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": rows,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Standard Repair Batch 1",
        "",
        "Owned redraws for the first normalized Standard Source Table repair queue.",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "Rows remain pending the one-symbol judge rerun."])
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
