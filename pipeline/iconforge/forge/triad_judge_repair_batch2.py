"""Second repair pass for the first triad judge batch rerun.

Consumes `judge_batch_001_rerun.json` and writes a smaller owned redraw batch
for rows that still failed after repair batch 7.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
JUDGE = ROOT / "out" / "triad_reference_candidate_pack" / "judge_batch_001_rerun.json"
OUT = ROOT / "out" / "triad_judge_repair_batch2"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch8"
CATALOG = ROOT / "catalog" / "owned_repair_batch8.json"
SUMMARY = ROOT / "catalog" / "owned_repair_batch8.md"
JUDGE_ARCHIVE_JSON = ROOT / "catalog" / "triad_judge_batch_001_rerun.json"
JUDGE_ARCHIVE_MD = ROOT / "catalog" / "triad_judge_batch_001_rerun.md"
PALETTES = ("day", "dusk", "night")


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="triad-judge-batch2">'
        f"<title>{asset} triad judge repair candidate</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _square_anchor(asset: str, *, large: bool = False, ring: bool = False, restricted: str | None = None) -> str:
    colour = "var(--magenta)"
    sw = 2.6
    if large:
        shank = '<path d="M32 10V48M20 24H44" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
        flukes = '<path d="M13 39L25 51H39L51 39M13 39L17 47M51 39L47 47" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
    else:
        shank = '<path d="M32 15V45M22 28H42" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
        flukes = '<path d="M17 38L26 47H38L47 38M17 38L20 44M47 38L44 44" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
    body = shank + flukes
    if ring:
        body += '<circle cx="32" cy="32" r="10" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
    if restricted:
        body += '<path d="M17 48L49 18" fill="none" stroke="var(--magenta)" stroke-width="2.6"/>'
        mark = "!" if restricted == "caution" else "i"
        x = "54" if restricted == "caution" else "12"
        body += (
            f'<text x="{x}" y="51" font-family="Arial, Helvetica, sans-serif" font-size="14" '
            f'font-weight="700" text-anchor="middle" fill="{colour}">{mark}</text>'
        )
    return _svg(asset, body)


def _ais_chevron(asset: str, *, doubled: bool = False) -> str:
    body = '<path d="M17 39L32 25L47 39" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
    body += '<path d="M20 42H44" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
    if doubled:
        body += '<path d="M22 46H42" fill="none" stroke="var(--green)" stroke-width="2.6"/>'
    return _svg(asset, body)


def _arpa_six(asset: str) -> str:
    return _svg(asset, '<path d="M15 32H49" fill="none" stroke="var(--green)" stroke-width="5.2"/>')


def _beacon_general(asset: str, *, question: bool = False) -> str:
    body = (
        '<path d="M32 12V49" fill="none" stroke="var(--black)" stroke-width="5.2"/>'
        '<path d="M22 37H42" fill="none" stroke="var(--black)" stroke-width="3"/>'
        '<circle cx="32" cy="49" r="5" fill="none" stroke="var(--black)" stroke-width="3"/>'
    )
    if question:
        body += (
            '<text x="48" y="34" font-family="Arial, Helvetica, sans-serif" font-size="24" '
            'font-weight="700" text-anchor="middle" fill="var(--magenta)">?</text>'
        )
    return _svg(asset, body)


def _redraw(asset: str) -> str:
    if asset == "ACHARE02":
        return _square_anchor(asset)
    if asset == "ACHARE51":
        return _square_anchor(asset, large=True)
    if asset == "ACHBRT07":
        return _square_anchor(asset, ring=True)
    if asset == "ACHPNT01":
        return _square_anchor(asset)
    if asset == "ACHRES61":
        return _square_anchor(asset, large=True, restricted="caution")
    if asset == "ACHRES71":
        return _square_anchor(asset, large=True, restricted="info")
    if asset == "AISONE01":
        return _ais_chevron(asset)
    if asset == "AISSIX01":
        return _ais_chevron(asset, doubled=True)
    if asset == "ARPSIX01":
        return _arpa_six(asset)
    if asset == "BCNGEN01":
        return _beacon_general(asset)
    if asset == "BCNGEN03":
        return _beacon_general(asset, question=True)
    if asset == "BCNCON81":
        return _beacon_general(asset)
    raise KeyError(asset)


def _load_verdicts() -> list[dict]:
    data = json.loads(JUDGE.read_text())
    return data.get("verdicts") or data.get("items") or data


def _render_svg(svg: str, asset: str, palette: str) -> str:
    out = OUT / "renders" / f"{_safe(asset)}__after__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
    return str(out.relative_to(ROOT))


def build(*, render_outputs: bool = False) -> dict:
    verdicts = _load_verdicts()
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
            "queue_action": "triad_judge_rerun_failed_repair",
            "risk_bucket": "judge_batch_001_rerun_fail",
            "candidate_strategy": "owned_redraw_from_triad_judge_rerun_feedback",
            "candidate_source": verdict.get("candidate_svg"),
            "before_svg": verdict.get("candidate_svg"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": verdict.get("required_change"),
            "judge": {
                "batch": "triad_judge_batch_001_rerun",
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
                "source_priority_basis": "triad_judge_rerun_repair",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.triad_judge_repair_batch2",
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
        "status": "archived_triad_llm_judge_batch_rerun",
        "summary": report["summary"],
        "verdicts": verdicts,
    }, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Triad Judge Batch 001 Rerun",
        "",
        f"- Judged: `{report['summary']['judged']}`",
        f"- Passed without repair: `{report['summary']['passed_without_repair']}`",
        f"- Failed and repaired: `{report['summary']['failed_repaired']}`",
        "- Approval: no row final-approved; repaired rows require judge rerun.",
        "",
        "## Remaining Failed Rows Repaired",
        "",
    ]
    for row in report["symbols"]:
        lines.append(f"- `{row['asset']}`: {row['repair_note']}")
    JUDGE_ARCHIVE_MD.write_text("\n".join(lines) + "\n")


def _write_summary(report: dict) -> None:
    lines = [
        "# Triad Judge Repair Batch 2",
        "",
        "Owned redraws for rows still failing after the first triad judge rerun.",
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
