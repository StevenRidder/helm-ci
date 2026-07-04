"""Audit current Helm SVG candidates against the OpenBridge-style contract.

Run:
  python3 -m forge.standard_style_audit
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from .style_contract import OPENBRIDGE_STYLE_ID, OPENBRIDGE_STROKE_WIDTH


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPORT_JSON = CATALOG / "standard_style_audit.json"
REPORT_CSV = CATALOG / "standard_style_audit.csv"
REPORT_MD = CATALOG / "standard_style_audit.md"

ALLOWED_COLOUR_VALUES = {"none", "transparent", "currentColor"}
ALLOWED_FONT_FAMILIES = (
    "Arial",
    "Helvetica",
    "Inter",
    "system-ui",
    "-apple-system",
    "sans-serif",
)
BAD_FONT_MARKERS = ("comic", "cursive", "papyrus", "marker", "chalk")
PLACEHOLDER_DIAMOND = "M32 12 L52 32 L32 52 L12 32 Z"
HEAVY_STROKE_MAX = 5.2
HAIRLINE_STROKE_MIN = 1.0


def _read_source_rows() -> list[dict]:
    return json.loads(SOURCE_TABLE.read_text()).get("rows", [])


def _colour_issues(svg: str, attr: str) -> list[str]:
    issues = []
    for match in re.finditer(attr + r'="([^"]+)"', svg):
        value = match.group(1).strip()
        if value in ALLOWED_COLOUR_VALUES or value.startswith("var(--") or value.startswith("url("):
            continue
        issues.append(value)
    return issues


def _font_issues(svg: str) -> tuple[list[str], list[str]]:
    bad_fonts = []
    disallowed_fonts = []
    for match in re.finditer(r'font-family="([^"]+)"', svg):
        value = match.group(1)
        lowered = value.lower()
        if any(marker in lowered for marker in BAD_FONT_MARKERS):
            bad_fonts.append(value)
        if not any(allowed.lower() in lowered for allowed in ALLOWED_FONT_FAMILIES):
            disallowed_fonts.append(value)
    return bad_fonts, disallowed_fonts


def _stroke_widths(svg: str) -> list[float]:
    return [float(value) for value in re.findall(r'stroke-width="([0-9]+(?:\.[0-9]+)?)"', svg)]


def _audit_svg(asset: str, path: Path, svg: str) -> dict:
    issues = []
    notes = []

    if f'data-style-contract="{OPENBRIDGE_STYLE_ID}"' not in svg:
        issues.append("missing_style_contract")
    if 'data-origin="generated-owned-artwork"' not in svg and "data-origin='generated-owned-artwork'" not in svg:
        issues.append("missing_generated_origin")
    if "generic_symbol" in svg or 'data-shape="generic_symbol"' in svg:
        issues.append("generic_symbol")
    if PLACEHOLDER_DIAMOND in svg:
        issues.append("diamond_placeholder")
    if "stroke=" in svg and 'stroke-linecap="round"' not in svg:
        issues.append("missing_round_linecap")
    if "stroke=" in svg and 'stroke-linejoin="round"' not in svg:
        issues.append("missing_round_linejoin")

    literal_fills = _colour_issues(svg, "fill")
    literal_strokes = _colour_issues(svg, "stroke")
    if literal_fills:
        issues.append("literal_fill_colour")
        notes.append(f"literal_fill={','.join(sorted(set(literal_fills)))}")
    if literal_strokes:
        issues.append("literal_stroke_colour")
        notes.append(f"literal_stroke={','.join(sorted(set(literal_strokes)))}")

    bad_fonts, disallowed_fonts = _font_issues(svg)
    if bad_fonts:
        issues.append("bad_font_family")
        notes.append(f"bad_font={','.join(sorted(set(bad_fonts)))}")
    if disallowed_fonts:
        issues.append("disallowed_font_family")
        notes.append(f"font={','.join(sorted(set(disallowed_fonts)))}")

    widths = _stroke_widths(svg)
    if widths:
        min_width = min(widths)
        max_width = max(widths)
        if min_width < HAIRLINE_STROKE_MIN:
            issues.append("hairline_stroke")
        if max_width > HEAVY_STROKE_MAX:
            issues.append("oversized_stroke")
        notes.append(f"stroke_range={min_width:g}-{max_width:g}")
        if not any(abs(width - OPENBRIDGE_STROKE_WIDTH) <= 0.25 for width in widths):
            notes.append("no_primary_contract_stroke")

    blocking = {"bad_font_family", "generic_symbol", "diamond_placeholder"}
    if blocking.intersection(issues):
        status = "style_blocked"
    elif issues:
        status = "style_review"
    else:
        status = "style_pass"

    return {
        "asset": asset,
        "path": str(path.relative_to(ROOT)),
        "status": status,
        "issues": sorted(set(issues)),
        "notes": sorted(set(notes)),
    }


def build() -> dict:
    rows = _read_source_rows()
    audited = []
    missing = []
    for row in rows:
        helm = row.get("helm_candidate") or {}
        svg_rel = helm.get("canonical_svg")
        if not svg_rel:
            continue
        path = ROOT / svg_rel
        if not path.exists():
            missing.append({
                "asset": row["asset"],
                "path": svg_rel,
                "status": "style_blocked",
                "issues": ["missing_svg_file"],
                "notes": [],
            })
            continue
        audited.append(_audit_svg(row["asset"], path, path.read_text()))

    all_rows = audited + missing
    issue_counts = Counter(issue for row in all_rows for issue in row["issues"])
    status_counts = Counter(row["status"] for row in all_rows)
    result = {
        "schema_version": 1,
        "status": "style_audit_complete",
        "style_contract": {
            "id": OPENBRIDGE_STYLE_ID,
            "primary_stroke_width": OPENBRIDGE_STROKE_WIDTH,
            "allowed_colour_mode": "semantic CSS variables, none/transparent/currentColor, or url() refs",
            "allowed_text_fonts": list(ALLOWED_FONT_FAMILIES),
        },
        "summary": {
            "source_table_rows": len(rows),
            "candidates_audited": len(all_rows),
            "style_pass": status_counts["style_pass"],
            "style_review": status_counts["style_review"],
            "style_blocked": status_counts["style_blocked"],
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "rows": sorted(all_rows, key=lambda row: (row["status"], row["asset"])),
    }
    _write_reports(result)
    return result


def _write_reports(result: dict) -> None:
    REPORT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with REPORT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["asset", "status", "issues", "notes", "path"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow({
                "asset": row["asset"],
                "status": row["status"],
                "issues": ";".join(row["issues"]),
                "notes": ";".join(row["notes"]),
                "path": row["path"],
            })

    lines = [
        "# Standard Style Audit",
        "",
        "Audit of current canonical Helm SVG candidates against the Helm/OpenBridge navigation style contract.",
        "",
        f"- style_contract: `{result['style_contract']['id']}`",
        f"- candidates_audited: `{result['summary']['candidates_audited']}`",
        f"- style_pass: `{result['summary']['style_pass']}`",
        f"- style_review: `{result['summary']['style_review']}`",
        f"- style_blocked: `{result['summary']['style_blocked']}`",
        "",
        "## Issue Counts",
        "",
        "| Issue | Count |",
        "| --- | ---: |",
    ]
    for issue, count in result["summary"]["issue_counts"].items():
        lines.append(f"| `{issue}` | {count} |")
    lines.extend([
        "",
        "## Non-Passing Assets",
        "",
        "| Asset | Status | Issues | Notes |",
        "| --- | --- | --- | --- |",
    ])
    for row in result["rows"]:
        if row["status"] == "style_pass":
            continue
        lines.append(
            f"| `{row['asset']}` | `{row['status']}` | "
            f"`{', '.join(row['issues'])}` | `{', '.join(row['notes'])}` |"
        )
    lines.append("")
    REPORT_MD.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = build()
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
