"""Audit current Helm SVG candidates against the OpenBridge-style contract.

Run:
  python3 -m forge.standard_style_audit
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from .style_contract import OPENBRIDGE_STYLE_ID, OPENBRIDGE_STROKE_WIDTH


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
REPORT_JSON = CATALOG / "standard_style_audit.json"
REPORT_CSV = CATALOG / "standard_style_audit.csv"
REPORT_MD = CATALOG / "standard_style_audit.md"
CONTACT_SHEET_SVG = CATALOG / "proofs" / "style_contract_satellite_contact_sheet.svg"

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
GRAPHIC_TAGS = {
    "circle",
    "ellipse",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    "text",
}
CHART_AID_PREFIXES = ("BOY", "BCN")
COLOUR_BODY_TOKENS = ("red", "green", "yellow", "orange", "blue", "magenta", "brown")
BLACK_EDGE_MARKERS = (
    'stroke="var(--black)"',
    "stroke='var(--black)'",
    'stroke="var(--ink)"',
    "stroke='var(--ink)'",
    'stroke="#070707"',
    "stroke='#070707'",
    'stroke="#000"',
    'stroke="#000000"',
)
COORD_ATTRS = {
    "cx",
    "cy",
    "d",
    "height",
    "points",
    "r",
    "rx",
    "ry",
    "width",
    "x",
    "x1",
    "x2",
    "y",
    "y1",
    "y2",
}
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
TARGET_CONTACT_ASSETS = [
    "BOYCAN60",
    "BOYCON68",
    "BOYBAR01",
    "BOYSPH68",
    "BOYSPR68",
    "BOYPIL60",
    "BCNGEN68",
    "BCNLAT15",
    "BCNSTK02",
    "BCNTOW01",
    "TOPSHP00",
    "TOPMAR87",
    "ACHRES71",
    "ACHBRT07",
    "NMKINF24",
    "NMKREG20",
    "AIRARE02",
    "WRECKS01",
    "OBSTRN11",
    "UWTROC03",
    "DANGER53",
    "NEWOBJ01",
    "AISVES01",
    "MSTCON04",
    "LIGHTS11",
]
BACKGROUND_PROFILES = [
    ("open water", "#3f7591", "#6ba6bd"),
    ("marina", "#58747a", "#c4c0a0"),
    ("green/park", "#577e4b", "#8ca36f"),
    ("roads/roofs", "#777b7f", "#b57b62"),
]


def _read_source_rows() -> list[dict]:
    return json.loads(SOURCE_TABLE.read_text()).get("rows", [])


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _parse_svg(svg: str) -> tuple[ET.Element | None, str | None]:
    try:
        return ET.fromstring(svg), None
    except ET.ParseError as exc:
        return None, str(exc)


def _viewbox(root: ET.Element | None) -> tuple[list[float] | None, str | None]:
    if root is None:
        return None, "svg_parse_error"
    raw = root.attrib.get("viewBox")
    if not raw:
        return None, "missing_viewbox"
    try:
        values = [float(value) for value in re.split(r"[,\s]+", raw.strip()) if value]
    except ValueError:
        return None, "invalid_viewbox"
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        return None, "invalid_viewbox"
    return values, None


def _graphic_elements(root: ET.Element | None) -> list[ET.Element]:
    if root is None:
        return []
    return [elem for elem in root.iter() if _strip_ns(elem.tag) in GRAPHIC_TAGS]


def _coordinate_values(root: ET.Element | None) -> list[float]:
    values: list[float] = []
    if root is None:
        return values
    for elem in root.iter():
        for name, raw in elem.attrib.items():
            if name not in COORD_ATTRS:
                continue
            values.extend(float(value) for value in NUMBER.findall(raw))
    return values


def _transform_issues(svg: str) -> list[str]:
    issues = []
    for raw in re.findall(r'transform="([^"]+)"', svg):
        lowered = raw.lower()
        numbers = [float(value) for value in NUMBER.findall(raw)]
        if "scale" in lowered and any(abs(value) > 4 for value in numbers):
            issues.append("oversized_transform")
        if "translate" in lowered and any(abs(value) > 128 for value in numbers):
            issues.append("oversized_transform")
        if "matrix" in lowered and any(abs(value) > 8 for value in numbers[:4]):
            issues.append("oversized_transform")
    return issues


def _has_black_edge(svg: str) -> bool:
    return any(marker in svg for marker in BLACK_EDGE_MARKERS)


def _uses_coloured_body(svg: str) -> bool:
    return any(f"var(--{token})" in svg for token in COLOUR_BODY_TOKENS)


def _gate_status(status: str) -> str:
    if status == "style_pass":
        return "pass"
    if status == "style_blocked":
        return "failed"
    return "pending"


def audit_svg_text(asset: str, svg: str, *, path_label: str = "inline") -> dict:
    issues = []
    notes = []
    root, parse_error = _parse_svg(svg)
    if parse_error:
        issues.append("svg_parse_error")
        notes.append(f"parse_error={parse_error}")
    elif root is not None and _strip_ns(root.tag) != "svg":
        issues.append("root_not_svg")

    viewbox, viewbox_issue = _viewbox(root)
    if viewbox_issue:
        issues.append(viewbox_issue)
    elif viewbox:
        notes.append("viewbox=" + ",".join(f"{value:g}" for value in viewbox))

    graphics = _graphic_elements(root)
    if not graphics:
        issues.append("blank_svg")
    else:
        notes.append(f"graphic_elements={len(graphics)}")

    coords = _coordinate_values(root)
    if viewbox and coords:
        min_x, min_y, width, height = viewbox
        margin = max(width, height) * 0.25
        low = min(min_x, min_y) - margin
        high = max(min_x + width, min_y + height) + margin
        if min(coords) < low or max(coords) > high:
            issues.append("off_canvas_geometry")

    issues.extend(_transform_issues(svg))

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
    if asset.startswith(CHART_AID_PREFIXES) and _uses_coloured_body(svg) and not _has_black_edge(svg):
        issues.append("missing_black_edge")

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

    blocking = {
        "bad_font_family",
        "blank_svg",
        "diamond_placeholder",
        "generic_symbol",
        "invalid_viewbox",
        "missing_black_edge",
        "missing_viewbox",
        "off_canvas_geometry",
        "oversized_transform",
        "root_not_svg",
        "svg_parse_error",
    }
    if blocking.intersection(issues):
        status = "style_blocked"
    elif issues:
        status = "style_review"
    else:
        status = "style_pass"

    return {
        "asset": asset,
        "path": path_label,
        "status": status,
        "gate_status": _gate_status(status),
        "issues": sorted(set(issues)),
        "reason_codes": [f"style_contract:{issue}" for issue in sorted(set(issues))],
        "notes": sorted(set(notes)),
    }


def _audit_svg(asset: str, path: Path, svg: str) -> dict:
    return audit_svg_text(asset, svg, path_label=_display_path(path))


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
        "schema": "helm.iconforge.standard_style_audit.v1",
        "schema_version": 2,
        "status": "style_audit_complete",
        "style_contract": {
            "id": OPENBRIDGE_STYLE_ID,
            "primary_stroke_width": OPENBRIDGE_STROKE_WIDTH,
            "allowed_colour_mode": "semantic CSS variables, none/transparent/currentColor, or url() refs",
            "allowed_text_fonts": list(ALLOWED_FONT_FAMILIES),
            "runtime_gate_mapping": {
                "style_pass": "pass",
                "style_review": "pending",
                "style_blocked": "failed",
            },
        },
        "summary": {
            "source_table_rows": len(rows),
            "candidates_audited": len(all_rows),
            "style_pass": status_counts["style_pass"],
            "style_review": status_counts["style_review"],
            "style_blocked": status_counts["style_blocked"],
            "runtime_gate_status_counts": {
                "pass": status_counts["style_pass"],
                "pending": status_counts["style_review"],
                "failed": status_counts["style_blocked"],
            },
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "rows": sorted(all_rows, key=lambda row: (row["status"], row["asset"])),
    }
    result["contact_sheets"] = _write_contact_sheet(result["rows"])
    _write_reports(result)
    return result


def _contact_sheet_rows(rows: list[dict], *, limit: int = 32) -> list[dict]:
    by_asset = {row["asset"]: row for row in rows}
    selected: list[dict] = []
    seen: set[str] = set()

    def add(row: dict | None) -> None:
        if not row or row["asset"] in seen:
            return
        selected.append(row)
        seen.add(row["asset"])

    for asset in TARGET_CONTACT_ASSETS:
        add(by_asset.get(asset))
    for row in rows:
        if row["status"] != "style_pass":
            add(row)
        if len(selected) >= limit:
            break
    for row in rows:
        if len(selected) >= limit:
            break
        if row["asset"].startswith(("BOY", "BCN", "TOP", "ACH", "NMK", "WRECKS", "OBSTRN", "UWTROC", "AIRARE")):
            add(row)
    for row in rows:
        if len(selected) >= limit:
            break
        add(row)
    return selected[:limit]


def _sheet_href(row: dict) -> str:
    source = ROOT / "proof" / "svg-day" / Path(str(row["path"])).name
    if not source.exists():
        source = ROOT / row["path"]
    return os.path.relpath(source, CONTACT_SHEET_SVG.parent)


def _write_contact_sheet(rows: list[dict]) -> dict:
    CONTACT_SHEET_SVG.parent.mkdir(parents=True, exist_ok=True)
    selected = _contact_sheet_rows(rows)
    cell_w = 136
    label_w = 112
    row_h = 92
    header_h = 64
    width = label_w + (cell_w * len(BACKGROUND_PROFILES)) + 32
    height = header_h + (row_h * len(selected)) + 28
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>Helm style contract satellite-background contact sheet</title>",
        "<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172033}.tiny{font-size:10px}.label{font-size:12px;font-weight:700}.status{font-size:10px}.tile{stroke:#d7dde8;stroke-width:1}.failed{fill:#b00020}.pending{fill:#975a16}.pass{fill:#176b38}</style>",
        '<rect width="100%" height="100%" fill="#f6f8fb"/>',
        '<text x="16" y="24" class="label">FORGE-32 style contract contact sheet</text>',
        '<text x="16" y="43" class="tiny">Current Helm resolved SVGs over representative satellite-like backgrounds. This is a gate witness, not visual approval.</text>',
    ]
    for col, (label, _, _) in enumerate(BACKGROUND_PROFILES):
        x = label_w + col * cell_w + 16
        parts.append(f'<text x="{x}" y="59" class="tiny">{html.escape(label)}</text>')
    for index, row in enumerate(selected):
        y = header_h + index * row_h
        gate_class = row["gate_status"]
        parts.append(f'<text x="16" y="{y + 27}" class="label">{html.escape(row["asset"])}</text>')
        parts.append(f'<text x="16" y="{y + 45}" class="status {gate_class}">{html.escape(row["status"])}</text>')
        if row["issues"]:
            issue_note = ", ".join(row["issues"][:2])
            parts.append(f'<text x="16" y="{y + 62}" class="tiny">{html.escape(issue_note)}</text>')
        href = _sheet_href(row)
        for col, (_, color_a, color_b) in enumerate(BACKGROUND_PROFILES):
            x = label_w + col * cell_w + 16
            parts.extend([
                f'<rect class="tile" x="{x}" y="{y + 8}" width="112" height="72" rx="6" fill="{color_a}"/>',
                f'<path d="M{x} {y + 58} C{x + 22} {y + 43} {x + 50} {y + 76} {x + 112} {y + 42} L{x + 112} {y + 80} L{x} {y + 80} Z" fill="{color_b}" opacity="0.78"/>',
                f'<path d="M{x + 6} {y + 26} H{x + 106} M{x + 22} {y + 13} V{y + 75} M{x + 74} {y + 11} V{y + 79}" stroke="#ffffff" stroke-width="1" opacity="0.18"/>',
                f'<image href="{html.escape(href)}" x="{x + 34}" y="{y + 12}" width="48" height="48" preserveAspectRatio="xMidYMid meet"/>',
            ])
    parts.append("</svg>")
    CONTACT_SHEET_SVG.write_text("\n".join(parts) + "\n")
    return {
        "style_contract_satellite_svg": _display_path(CONTACT_SHEET_SVG),
        "sample_count": len(selected),
        "background_profiles": [label for label, _, _ in BACKGROUND_PROFILES],
        "status": "written",
    }


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
        f"- satellite_contact_sheet: `{result['contact_sheets']['style_contract_satellite_svg']}`",
        f"- contact_sheet_samples: `{result['contact_sheets']['sample_count']}`",
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
