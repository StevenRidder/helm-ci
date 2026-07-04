"""Repair the first triad judge batch from one-symbol visual verdicts.

This batch is deliberately narrow: it consumes the first judge output and writes
owned redraw candidates for the failed rows only. The symbols stay pending
visual review; this is a repair iteration, not approval.

Run:
  python -m forge.triad_judge_repair_batch1 --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "out" / "triad_reference_candidate_pack" / "judge_batch_001.json"
OUT = ROOT / "out" / "triad_judge_repair_batch1"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch7"
CATALOG = ROOT / "catalog" / "owned_repair_batch7.json"
SUMMARY = ROOT / "catalog" / "owned_repair_batch7.md"
JUDGE_ARCHIVE_JSON = ROOT / "catalog" / "triad_judge_batch_001.json"
JUDGE_ARCHIVE_MD = ROOT / "catalog" / "triad_judge_batch_001.md"
PALETTES = ("day", "dusk", "night")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _tok(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="triad-judge-batch1">'
        f"<title>{asset} triad judge repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _anchor(colour: str = "magenta", scale: float = 1.0) -> str:
    sw = 2.6 * scale
    return (
        f'<path d="M32 16V43" fill="none" stroke="{_tok(colour)}" stroke-width="{sw:g}"/>'
        f'<circle cx="32" cy="13" r="3.2" fill="none" stroke="{_tok(colour)}" stroke-width="{sw:g}"/>'
        f'<path d="M18 31H46" fill="none" stroke="{_tok(colour)}" stroke-width="{sw:g}"/>'
        f'<path d="M18 39C22 48 42 48 46 39" fill="none" stroke="{_tok(colour)}" stroke-width="{sw:g}"/>'
        f'<path d="M18 39L16 45M46 39L48 45" fill="none" stroke="{_tok(colour)}" stroke-width="{sw:g}"/>'
    )


def _anchor_restriction(kind: str) -> str:
    mark = "!" if kind == "caution" else "i"
    return (
        _anchor("magenta")
        + '<path d="M17 48L49 18" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
        + f'<text x="52" y="48" font-family="Arial, Helvetica, sans-serif" font-size="14" '
        f'font-weight="700" text-anchor="middle" fill="{_tok("magenta")}">{mark}</text>'
    )


def _anchor_berth() -> str:
    return (
        _anchor("magenta", 0.9)
        + '<circle cx="32" cy="32" r="21" fill="none" stroke="var(--magenta)" stroke-width="2.3"/>'
    )


def _additional(direction: str) -> str:
    if direction == "right":
        points = "18,16 18,48 48,32"
    elif direction == "left":
        points = "46,16 46,48 16,32"
    else:
        return _svg(
            "ADDMRK05",
            '<rect x="14" y="27" width="36" height="10" fill="var(--blue)" stroke="var(--black)" stroke-width="2.6"/>',
        )
    return _svg(
        f"ADDMRK-{direction}",
        f'<polygon points="{points}" fill="{_tok("white")}" stroke="{_tok("black")}" stroke-width="2.6"/>',
    )


def _airport() -> str:
    return _svg(
        "AIRARE02",
        '<circle cx="32" cy="32" r="17" fill="none" stroke="var(--brown)" stroke-width="2.4"/>'
        '<path d="M32 18L35 31L48 34L48 38L35 37L31 49L27 49L29 37L16 38L16 34L29 31Z" '
        'fill="none" stroke="var(--brown)" stroke-width="2.4"/>',
    )


def _ais_target(asset: str) -> str:
    if asset in {"AISONE01", "ARPONE01"}:
        return _svg(asset, '<path d="M25 33H39" fill="none" stroke="var(--green)" stroke-width="2.6"/>')
    if asset in {"AISSIX01", "ARPSIX01"}:
        return _svg(asset, '<path d="M22 36H42M25 31H39" fill="none" stroke="var(--green)" stroke-width="2.6"/>')
    if asset == "AISDEF01":
        return _svg(
            asset,
            '<path d="M32 15L24 47H40Z" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
            '<circle cx="32" cy="39" r="2" fill="var(--green)"/>'
            '<text x="49" y="34" font-family="Arial, Helvetica, sans-serif" font-size="20" '
            'font-weight="700" text-anchor="middle" fill="var(--magenta)">?</text>',
        )
    if asset == "AISSLP01":
        return _svg(asset, '<path d="M32 14L24 49H40Z" fill="none" stroke="var(--green)" stroke-width="2.6"/>')
    if asset == "ARPATG01":
        return _svg(
            asset,
            '<circle cx="32" cy="32" r="9" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
            '<circle cx="32" cy="32" r="2.4" fill="var(--green)"/>',
        )
    return _svg(
        asset,
        '<path d="M32 13L23 50H41Z" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
        '<path d="M32 13V7" fill="none" stroke="var(--green)" stroke-width="2.6"/>',
    )


def _beacon(asset: str) -> str:
    fill = "black"
    if asset.endswith("05"):
        fill = "white"
    elif asset.endswith("60"):
        fill = "red"
    elif asset.endswith("61"):
        fill = "green"
    elif asset.endswith("64"):
        return _svg(
            asset,
            '<rect x="28" y="12" width="8" height="34" fill="var(--white)" stroke="var(--black)" stroke-width="2.4"/>'
            '<rect x="28" y="12" width="8" height="17" fill="var(--red)" stroke="var(--black)" stroke-width="2.4"/>'
            '<path d="M32 46V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>',
        )
    question = ""
    if asset in {"BCNDEF13", "BCNGEN03"}:
        fill = "gray" if asset == "BCNDEF13" else "black"
        question = (
            '<text x="47" y="33" font-family="Arial, Helvetica, sans-serif" font-size="18" '
            'font-weight="700" text-anchor="middle" fill="var(--magenta)">?</text>'
        )
    return _svg(
        asset,
        f'<rect x="28" y="13" width="8" height="31" fill="{_tok(fill)}" stroke="{_tok("black")}" stroke-width="2.4"/>'
        '<path d="M32 44V56" fill="none" stroke="var(--black)" stroke-width="2.4"/>'
        + question,
    )


def _redraw(asset: str) -> str:
    if asset == "ACHARE02":
        return _svg(asset, _anchor("magenta", 0.86))
    if asset == "ACHARE51":
        return _svg(asset, _anchor("magenta", 1.05))
    if asset == "ACHBRT07":
        return _svg(asset, _anchor_berth())
    if asset == "ACHPNT01":
        return _svg(asset, _anchor("magenta", 0.78))
    if asset == "ACHRES61":
        return _svg(asset, _anchor_restriction("caution"))
    if asset == "ACHRES71":
        return _svg(asset, _anchor_restriction("info"))
    if asset == "ADDMRK01":
        return _additional("right").replace("ADDMRK-right", asset)
    if asset == "ADDMRK02":
        return _additional("left").replace("ADDMRK-left", asset)
    if asset == "ADDMRK05":
        return _additional("bottom")
    if asset == "AIRARE02":
        return _airport()
    if asset.startswith(("AIS", "ARP")):
        return _ais_target(asset)
    if asset.startswith("BCN"):
        return _beacon(asset)
    raise KeyError(asset)


def _render_svg(svg: str, asset: str, palette: str) -> str:
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def _load_judge() -> list[dict]:
    data = json.loads(JUDGE.read_text())
    if isinstance(data, dict):
        return data.get("verdicts") or data.get("items") or []
    return data


def build(*, render_outputs: bool = False) -> dict:
    verdicts = _load_judge()
    failed = [verdict for verdict in verdicts if not verdict.get("pass")]
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    symbols = []
    for verdict in failed:
        asset = verdict["symbol_id"]
        svg = _redraw(asset)
        svg_path = SVG_OUT / f"{_safe(asset)}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        symbols.append({
            "asset": asset,
            "name": verdict.get("expected"),
            "queue_action": "triad_judge_failed_repair",
            "risk_bucket": "judge_batch_001_fail",
            "candidate_strategy": "owned_redraw_from_triad_judge_feedback",
            "candidate_source": verdict.get("candidate_svg"),
            "before_svg": verdict.get("candidate_svg"),
            "before_render": None,
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": verdict.get("required_change"),
            "judge": {
                "batch": "triad_judge_batch_001",
                "confidence": verdict.get("confidence"),
                "comments": verdict.get("judge_comments"),
                "observed": verdict.get("observed"),
                "expected": verdict.get("expected"),
                "safety_reason_codes": verdict.get("safety_reason_codes", []),
                "source_refs_used": verdict.get("source_refs_used", []),
            },
            "visual_examples": verdict.get("source_refs_used", []),
            "qa": {
                "semantic_pass": False,
                "structural_pass": True,
                "visual_parity": "repaired_pending_judge_rerun",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_priority_basis": "triad_judge_repair",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.triad_judge_repair_batch1",
                "reference_role": "S-101/Aqua Map/OpenCPN visual reference; redrawn owned SVG",
            },
        })
    report = {
        "schema_version": 1,
        "status": "repair_batch_pending_judge_rerun",
        "source_judge": str(JUDGE.relative_to(ROOT)),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(CATALOG.relative_to(ROOT)),
            "report": str((OUT / "report.json").relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "judged": len(verdicts),
            "passed_without_repair": len(verdicts) - len(failed),
            "failed_repaired": len(symbols),
            "visual_parity": "repaired_pending_judge_rerun",
        },
        "symbols": symbols,
    }
    CATALOG.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "report.json").parent.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    _write_summary(report)
    _archive_judge(verdicts, report)
    return report


def _archive_judge(verdicts: list[dict], report: dict) -> None:
    JUDGE_ARCHIVE_JSON.write_text(json.dumps({
        "schema_version": 1,
        "status": "archived_first_triad_llm_judge_batch",
        "summary": report["summary"],
        "verdicts": verdicts,
    }, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Triad Judge Batch 001",
        "",
        f"- Judged: `{report['summary']['judged']}`",
        f"- Passed without repair: `{report['summary']['passed_without_repair']}`",
        f"- Failed and repaired: `{report['summary']['failed_repaired']}`",
        "- Approval: no row final-approved; repaired rows require judge rerun.",
        "",
        "## Failed Rows Repaired",
        "",
    ]
    for row in report["symbols"]:
        lines.append(f"- `{row['asset']}`: {row['repair_note']}")
    JUDGE_ARCHIVE_MD.write_text("\n".join(lines) + "\n")


def _write_summary(report: dict) -> None:
    lines = [
        "# Triad Judge Repair Batch 1",
        "",
        "Owned redraws for the first failed triad visual-judge batch.",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "Rows are repaired candidates only. They must pass the same one-symbol visual judge before promotion.",
    ])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    report = build(render_outputs=args.render)
    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "outputs": report["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
