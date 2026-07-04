"""Repair Standard Judge Batch 004 failures.

Run:
  python -m forge.standard_repair_batch2 --render
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
SOURCE_JUDGE = CATALOG / "standard_judge_batch_004.json"
OUT = ROOT / "out" / "standard_repair_batch2"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch10"
REPORT = CATALOG / "owned_repair_batch10.json"
SUMMARY = CATALOG / "owned_repair_batch10.md"
PALETTES = ("day", "dusk", "night")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="standard-repair-batch2">'
        f"<title>{asset} standard source repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _bands_rect(asset: str, bands: list[str], *, x: float, y: float, w: float, h: float, outline: str = "rect") -> str:
    body = []
    band_h = h / len(bands)
    if outline == "cone":
        top_w = w * 0.45
        bot_w = w
        for idx, colour in enumerate(bands):
            y0 = y + idx * band_h
            y1 = y + (idx + 1) * band_h
            t0 = (y0 - y) / h
            t1 = (y1 - y) / h
            w0 = top_w + (bot_w - top_w) * t0
            w1 = top_w + (bot_w - top_w) * t1
            points = f"{32 - w0 / 2:g},{y0:g} {32 + w0 / 2:g},{y0:g} {32 + w1 / 2:g},{y1:g} {32 - w1 / 2:g},{y1:g}"
            body.append(f'<polygon points="{points}" fill="var(--{colour})"/>')
        outline_points = f"{32 - top_w / 2:g},{y:g} {32 + top_w / 2:g},{y:g} {32 + bot_w / 2:g},{y + h:g} {32 - bot_w / 2:g},{y + h:g}"
        body.append(f'<polygon points="{outline_points}" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    elif outline == "barrel":
        body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="5" fill="var(--white)" stroke="var(--black)" stroke-width="2.4"/>')
        for idx, colour in enumerate(bands):
            body.append(f'<rect x="{x:g}" y="{y + idx * band_h:g}" width="{w:g}" height="{band_h:g}" fill="var(--{colour})"/>')
        body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="5" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    else:
        for idx, colour in enumerate(bands):
            body.append(f'<rect x="{x:g}" y="{y + idx * band_h:g}" width="{w:g}" height="{band_h:g}" fill="var(--{colour})"/>')
        body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    body.append('<path d="M32 46V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>')
    return _svg(asset, "".join(body))


def _can(asset: str, bands: list[str]) -> str:
    return _bands_rect(asset, bands, x=22, y=14, w=20, h=32)


def _cone(asset: str, bands: list[str]) -> str:
    return _bands_rect(asset, bands, x=20, y=14, w=24, h=32, outline="cone")


def _barrel(asset: str, bands: list[str]) -> str:
    return _bands_rect(asset, bands, x=20, y=16, w=24, h=28, outline="barrel")


def _tower(asset: str, bands: list[str]) -> str:
    return _bands_rect(asset, bands, x=22, y=14, w=20, h=32, outline="cone")


def _blkadj(asset: str) -> str:
    return _svg(
        asset,
        '<rect x="17" y="17" width="30" height="30" fill="var(--black)" stroke="var(--black)" stroke-width="2.4"/>'
        '<rect x="25" y="25" width="14" height="14" fill="var(--gray)" stroke="var(--black)" stroke-width="2.2"/>',
    )


def _border(asset: str) -> str:
    return _svg(
        asset,
        '<path d="M15 49L49 15" fill="none" stroke="var(--red)" stroke-width="6"/>'
        '<path d="M15 49L49 15" fill="none" stroke="var(--white)" stroke-width="2.6"/>',
    )


def _redraw(asset: str) -> str:
    mapping = {
        "BCNTOW90": lambda: _tower(asset, ["brown"]),
        "BLKADJ01": lambda: _blkadj(asset),
        "BORDER01": lambda: _border(asset),
        "BOYBAR01": lambda: _barrel(asset, ["white"]),
        "BOYCAN01": lambda: _can(asset, ["white"]),
        "BOYCAN62": lambda: _can(asset, ["white"]),
        "BOYCAN72": lambda: _can(asset, ["red", "green", "red"]),
        "BOYCAN73": lambda: _can(asset, ["green", "red", "green"]),
        "BOYCAN74": lambda: _can(asset, ["red", "white", "red"]),
        "BOYCAN76": lambda: _can(asset, ["black", "red", "black"]),
        "BOYCAN77": lambda: _can(asset, ["white", "orange", "white"]),
        "BOYCAN78": lambda: _can(asset, ["white", "orange", "white"]),
        "BOYCAN79": lambda: _can(asset, ["yellow"]),
        "BOYCAN81": lambda: _can(asset, ["white", "orange", "white"]),
        "BOYCAN82": lambda: _can(asset, ["red", "white", "red"]),
        "BOYCAN83": lambda: _can(asset, ["red", "white", "red"]),
        "BOYCON01": lambda: _cone(asset, ["white"]),
        "BOYCON63": lambda: _cone(asset, ["black", "red", "black"]),
        "BOYCON66": lambda: _cone(asset, ["red", "green", "red"]),
        "BOYCON67": lambda: _cone(asset, ["green", "red", "green"]),
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
    failed = [verdict for verdict in judge.get("verdicts", []) if not verdict.get("pass")]
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for verdict in failed:
        asset = verdict["symbol_id"]
        source_row = source_rows.get(asset, {})
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
            "queue_action": "standard_source_table_repair",
            "risk_bucket": "standard_judge_batch_004_fail",
            "candidate_strategy": "owned_redraw_from_standard_judge_feedback",
            "candidate_source": source_row.get("helm_candidate", {}).get("canonical_svg"),
            "before_svg": source_row.get("helm_candidate", {}).get("canonical_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": verdict.get("required_change"),
            "visual_examples": source_row.get("reference_providers", {}),
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
                "generator": "forge.standard_repair_batch2",
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
            "source_judge_failed_rows": len(failed),
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
        "# Standard Repair Batch 2",
        "",
        "Owned redraws for Standard Judge Batch 004 failures.",
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
