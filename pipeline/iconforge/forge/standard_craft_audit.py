"""Audit rendered Helm candidates for OpenBridge-like craft and tiny-size readability.

This is deliberately different from ``standard_style_audit``. The style audit
checks SVG hygiene; this audit checks the rendered result for obvious design
drift: invisible/tiny symbols, off-centre art, excessive SVG complexity, and
placeholder/generic forms that should never reach final approval.

Run:
  python3 -m forge.standard_craft_audit
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

from PIL import Image

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
SOURCE_TABLE = CATALOG / "standard_source_table.json"
STYLE_AUDIT = CATALOG / "standard_style_audit.json"
REPORT_JSON = CATALOG / "standard_craft_audit.json"
REPORT_CSV = CATALOG / "standard_craft_audit.csv"
REPORT_MD = CATALOG / "standard_craft_audit.md"
TRIAD_RENDER_DIR = ROOT / "out" / "triad_reference_candidate_pack" / "renders"

CANVAS = 160
TINY_SIZE = 24
MIN_TINY_BBOX = 5.0
MAX_CENTER_OFFSET = 0.18
MAX_SVG_ELEMENTS = 90
MAX_PATH_COMMANDS = 420
MAX_STROKE_SPREAD = 7.5
PLACEHOLDER_DIAMOND = "M32 12 L52 32 L32 52 L12 32 Z"


def _source_rows() -> list[dict]:
    return json.loads(SOURCE_TABLE.read_text()).get("rows", [])


def _style_rows() -> dict[str, dict]:
    if not STYLE_AUDIT.exists():
        return {}
    return {row["asset"]: row for row in json.loads(STYLE_AUDIT.read_text()).get("rows", [])}


def _safe(asset: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", asset).strip("_") or "unnamed_asset"


def _render_png(asset: str, svg_path: Path) -> Image.Image | None:
    cached = TRIAD_RENDER_DIR / f"{_safe(asset)}__day.png"
    if cached.exists():
        return Image.open(cached).convert("RGBA")
    if not svg_path.exists():
        return None
    try:
        png = render.rasterize(svg_path.read_text(), OPENBRIDGE_NAV_PALETTES["day"], size=CANVAS)
    except Exception:
        return None
    from io import BytesIO

    return Image.open(BytesIO(png)).convert("RGBA")


def _active_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    xs = []
    ys = []
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 16 and (abs(255 - r) + abs(255 - g) + abs(255 - b)) > 36:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _pixel_metrics(image: Image.Image) -> dict:
    bbox = _active_bbox(image)
    if bbox is None:
        return {
            "visible": False,
            "bbox": None,
            "bbox_width": 0,
            "bbox_height": 0,
            "tiny_bbox_width": 0,
            "tiny_bbox_height": 0,
            "center_offset": 1,
            "coverage": 0,
        }
    x0, y0, x1, y1 = bbox
    bbox_width = x1 - x0
    bbox_height = y1 - y0
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2
    center_offset = math.hypot(center_x - CANVAS / 2, center_y - CANVAS / 2) / CANVAS
    active = 0
    for _, _, _, alpha in image.getdata():
        if alpha > 16:
            active += 1
    return {
        "visible": True,
        "bbox": [x0, y0, x1, y1],
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "tiny_bbox_width": round(bbox_width / CANVAS * TINY_SIZE, 2),
        "tiny_bbox_height": round(bbox_height / CANVAS * TINY_SIZE, 2),
        "center_offset": round(center_offset, 3),
        "coverage": round(active / (CANVAS * CANVAS), 4),
    }


def _svg_metrics(svg: str) -> dict:
    elements = len(re.findall(r"<(path|circle|rect|polygon|polyline|line|ellipse|text)\b", svg))
    path_commands = len(re.findall(r"[MmLlHhVvCcSsQqTtAaZz]", svg))
    widths = [float(value) for value in re.findall(r'stroke-width="([0-9]+(?:\.[0-9]+)?)"', svg)]
    spread = (max(widths) - min(widths)) if widths else 0
    return {
        "element_count": elements,
        "path_command_count": path_commands,
        "stroke_width_spread": round(spread, 2),
    }


def _audit_row(row: dict, style_by_asset: dict[str, dict]) -> dict | None:
    helm = row.get("helm_candidate") or {}
    svg_rel = helm.get("canonical_svg")
    if not svg_rel:
        return None
    asset = row["asset"]
    svg_path = ROOT / svg_rel
    if not svg_path.exists():
        return {
            "asset": asset,
            "status": "craft_blocked",
            "issues": ["missing_svg_file"],
            "metrics": {},
            "path": svg_rel,
        }

    svg = svg_path.read_text()
    image = _render_png(asset, svg_path)
    pixel = _pixel_metrics(image) if image else {"visible": False}
    svg_metrics = _svg_metrics(svg)
    issues = []

    style_status = (style_by_asset.get(asset) or {}).get("status")
    style_issues = set((style_by_asset.get(asset) or {}).get("issues", []))
    if style_status == "style_blocked":
        issues.append("style_blocked_upstream")
    if "generic_symbol" in style_issues or "diamond_placeholder" in style_issues or PLACEHOLDER_DIAMOND in svg:
        issues.append("placeholder_shape")
    if not pixel.get("visible"):
        issues.append("no_visible_art")
    else:
        if min(pixel["tiny_bbox_width"], pixel["tiny_bbox_height"]) < MIN_TINY_BBOX:
            issues.append("tiny_render_too_small")
        if pixel["center_offset"] > MAX_CENTER_OFFSET:
            issues.append("off_center_art")
    if svg_metrics["element_count"] > MAX_SVG_ELEMENTS:
        issues.append("too_many_svg_elements")
    if svg_metrics["path_command_count"] > MAX_PATH_COMMANDS:
        issues.append("too_many_path_commands")
    if svg_metrics["stroke_width_spread"] > MAX_STROKE_SPREAD:
        issues.append("inconsistent_stroke_spread")

    blocking = {"style_blocked_upstream", "placeholder_shape", "no_visible_art"}
    if blocking.intersection(issues):
        status = "craft_blocked"
    elif issues:
        status = "craft_review"
    else:
        status = "craft_pass"

    return {
        "asset": asset,
        "name": row.get("name"),
        "status": status,
        "issues": sorted(set(issues)),
        "path": svg_rel,
        "candidate_status": helm.get("candidate_status"),
        "metrics": {
            **pixel,
            **svg_metrics,
        },
    }


def build() -> dict:
    style_by_asset = _style_rows()
    rows = [result for row in _source_rows() if (result := _audit_row(row, style_by_asset))]
    status_counts = Counter(row["status"] for row in rows)
    issue_counts = Counter(issue for row in rows for issue in row["issues"])
    result = {
        "schema_version": 1,
        "status": "craft_audit_complete",
        "contract": {
            "inspiration": "Helm/OpenBridge-like: thin 1.8 primary stroke, simple geometric construction, centered marks, readable at 24px, no decorative/cartoon/doodle detail",
            "tiny_size_px": TINY_SIZE,
            "max_center_offset": MAX_CENTER_OFFSET,
            "max_svg_elements": MAX_SVG_ELEMENTS,
            "max_path_commands": MAX_PATH_COMMANDS,
        },
        "summary": {
            "candidates_audited": len(rows),
            "craft_pass": status_counts["craft_pass"],
            "craft_review": status_counts["craft_review"],
            "craft_blocked": status_counts["craft_blocked"],
            "issue_counts": dict(sorted(issue_counts.items())),
        },
        "rows": sorted(rows, key=lambda item: (item["status"], item["asset"])),
    }
    _write_reports(result)
    return result


def _write_reports(result: dict) -> None:
    REPORT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with REPORT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["asset", "status", "issues", "tiny_bbox", "center_offset", "elements", "path"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in result["rows"]:
            metrics = row.get("metrics", {})
            writer.writerow({
                "asset": row["asset"],
                "status": row["status"],
                "issues": ";".join(row["issues"]),
                "tiny_bbox": f"{metrics.get('tiny_bbox_width', 0)}x{metrics.get('tiny_bbox_height', 0)}",
                "center_offset": metrics.get("center_offset", ""),
                "elements": metrics.get("element_count", ""),
                "path": row["path"],
            })

    lines = [
        "# Standard Craft Audit",
        "",
        "Rendered quality/readability audit for current Helm SVG candidates.",
        "",
        f"- candidates_audited: `{result['summary']['candidates_audited']}`",
        f"- craft_pass: `{result['summary']['craft_pass']}`",
        f"- craft_review: `{result['summary']['craft_review']}`",
        f"- craft_blocked: `{result['summary']['craft_blocked']}`",
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
        "| Asset | Status | Issues | Tiny BBox | Center Offset | Elements |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ])
    for row in result["rows"]:
        if row["status"] == "craft_pass":
            continue
        metrics = row.get("metrics", {})
        lines.append(
            f"| `{row['asset']}` | `{row['status']}` | `{', '.join(row['issues'])}` | "
            f"{metrics.get('tiny_bbox_width', 0)}x{metrics.get('tiny_bbox_height', 0)} | "
            f"{metrics.get('center_offset', '')} | {metrics.get('element_count', '')} |"
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
