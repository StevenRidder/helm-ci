"""Render local OpenCPN/S-52 reference graphics for Icon Forge.

This writes reference-only PNG crops/renders from the local S-52 presentation
library into out/opencpn_s52_reference/. The PNGs are an oracle for visual
repair; they are not canonical Helm artwork and are not meant to be committed
into the owned SVG pack.

Run:  python -m forge.opencpn_reference_render
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
MASTER = CATALOG / "master_symbol_list.json"
S52 = Path("/Users/steveridder/.helm/runtime/s57data/chartsymbols.xml")
S52_DIR = S52.parent
OUT_DIR = ROOT / "out" / "opencpn_s52_reference"
REPORT = OUT_DIR / "report.json"
SUMMARY_MD = OUT_DIR / "README.md"

PALETTE_SHEETS = {
    "day": "rastersymbols-day.png",
    "dusk": "rastersymbols-dusk.png",
    "night": "rastersymbols-dark.png",
}

PALETTE_TABLES = {
    "day": "DAY_BRIGHT",
    "dusk": "DUSK",
    "night": "NIGHT",
}


def _safe_asset_filename(asset: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", asset).strip("_")
    return safe or "unnamed_asset"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _text(node: ET.Element, child: str) -> str:
    return node.findtext(child) or ""


def _bitmap_payload(node: ET.Element) -> dict | None:
    bitmap = node.find("bitmap")
    if bitmap is None:
        return None
    location = bitmap.find("graphics-location")
    pivot = bitmap.find("pivot")
    origin = bitmap.find("origin")
    if location is None:
        return None
    return {
        "width": int(bitmap.get("width") or 0),
        "height": int(bitmap.get("height") or 0),
        "x": int(location.get("x") or 0),
        "y": int(location.get("y") or 0),
        "pivot": {
            "x": int(pivot.get("x") or 0),
            "y": int(pivot.get("y") or 0),
        } if pivot is not None else None,
        "origin": {
            "x": int(origin.get("x") or 0),
            "y": int(origin.get("y") or 0),
        } if origin is not None else None,
    }


def _vector_payload(node: ET.Element) -> dict | None:
    vector = node.find("vector")
    hpgl = node.findtext("HPGL") or vector.findtext("HPGL") if vector is not None else node.findtext("HPGL")
    if vector is None and not hpgl:
        return None
    pivot = vector.find("pivot") if vector is not None else None
    origin = vector.find("origin") if vector is not None else None
    return {
        "width": int(vector.get("width") or 0) if vector is not None else 0,
        "height": int(vector.get("height") or 0) if vector is not None else 0,
        "pivot": {
            "x": int(pivot.get("x") or 0),
            "y": int(pivot.get("y") or 0),
        } if pivot is not None else None,
        "origin": {
            "x": int(origin.get("x") or 0),
            "y": int(origin.get("y") or 0),
        } if origin is not None else None,
        "hpgl": hpgl or "",
    }


def _asset_registry() -> dict[tuple[str, str], list[dict]]:
    root = ET.parse(S52).getroot()
    assets: dict[tuple[str, str], list[dict]] = {}
    for kind, container, item in [
        ("symbol", "symbols", "symbol"),
        ("line-style", "line-styles", "line-style"),
        ("pattern", "patterns", "pattern"),
    ]:
        parent = root.find(container)
        if parent is None:
            continue
        for node in parent.findall(item):
            name = _text(node, "name")
            if not name:
                continue
            assets.setdefault((name, kind), []).append({
                "kind": kind,
                "rcid": node.get("RCID"),
                "name": name,
                "description": _text(node, "description"),
                "color_ref": _text(node, "color-ref"),
                "definition": _text(node, "definition"),
                "bitmap": _bitmap_payload(node),
                "vector": _vector_payload(node),
            })
    return assets


def _resolve_asset_def(registry: dict[tuple[str, str], list[dict]], asset: str, master_kind: str) -> dict | None:
    kind_order = {
        "symbol": ["symbol", "pattern", "line-style"],
        "line-style": ["line-style", "symbol", "pattern"],
        "pattern": ["pattern", "symbol", "line-style"],
        "conditional-procedure": ["symbol", "pattern", "line-style"],
    }.get(master_kind, ["symbol", "pattern", "line-style"])
    candidates: list[dict] = []
    for kind in kind_order:
        candidates.extend(registry.get((asset, kind), []))
    if not candidates:
        return None
    for candidate in candidates:
        bitmap = candidate.get("bitmap")
        if bitmap and bitmap["width"] > 0 and bitmap["height"] > 0:
            return candidate
    for candidate in candidates:
        vector = candidate.get("vector")
        if vector and vector.get("hpgl"):
            return candidate
    return candidates[0]


def _load_sheets() -> dict[str, Image.Image]:
    sheets = {}
    for palette, filename in PALETTE_SHEETS.items():
        path = S52_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"missing S-52 raster sheet: {path}")
        sheets[palette] = Image.open(path).convert("RGBA")
    return sheets


def _palette_colors() -> dict[str, dict[str, tuple[int, int, int, int]]]:
    root = ET.parse(S52).getroot()
    palettes: dict[str, dict[str, tuple[int, int, int, int]]] = {}
    for palette, table_name in PALETTE_TABLES.items():
        table = root.find(f"./color-tables/color-table[@name='{table_name}']")
        if table is None:
            table = root.find("./color-tables/color-table")
        colors: dict[str, tuple[int, int, int, int]] = {}
        if table is not None:
            for color in table.findall("color"):
                colors[color.get("name") or ""] = (
                    int(color.get("r") or 0),
                    int(color.get("g") or 0),
                    int(color.get("b") or 0),
                    255,
                )
        palettes[palette] = colors
    return palettes


def _crop(sheet: Image.Image, bitmap: dict) -> Image.Image:
    x = bitmap["x"]
    y = bitmap["y"]
    width = bitmap["width"]
    height = bitmap["height"]
    return sheet.crop((x, y, x + width, y + height))


def _color_name(color_ref: str, palette: dict[str, tuple[int, int, int, int]]) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", color_ref.upper())
    names = sorted((name for name in palette if name), key=len, reverse=True)
    for name in names:
        if name in cleaned:
            return name
    return "CHBLK"


def _parse_hpgl(hpgl: str) -> tuple[list[dict], list[tuple[float, float]]]:
    commands = [command.strip() for command in hpgl.replace("\n", "").split(";") if command.strip()]
    current = (0.0, 0.0)
    pen_down = False
    stroke_width = 1
    segments: list[dict] = []
    points: list[tuple[float, float]] = []
    active_polyline: list[tuple[float, float]] = []

    def flush() -> None:
        nonlocal active_polyline
        if len(active_polyline) >= 2:
            segments.append({"type": "polyline", "points": active_polyline[:], "stroke_width": stroke_width})
        active_polyline = []

    for command in commands:
        op = command[:2].upper()
        payload = command[2:]
        if op == "SW":
            flush()
            match = re.search(r"\d+", payload)
            stroke_width = max(1, int(match.group(0))) if match else 1
        elif op == "PU":
            flush()
            pen_down = False
            coords = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", payload)]
            if len(coords) >= 2:
                current = (coords[-2], coords[-1])
                points.append(current)
        elif op == "PD":
            coords = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", payload)]
            if not pen_down:
                active_polyline = [current]
            pen_down = True
            if not coords:
                continue
            for idx in range(0, len(coords) - 1, 2):
                current = (coords[idx], coords[idx + 1])
                active_polyline.append(current)
                points.append(current)
        elif op == "CI":
            flush()
            match = re.search(r"-?\d+(?:\.\d+)?", payload)
            if match:
                radius = float(match.group(0))
                segments.append({"type": "circle", "center": current, "radius": radius, "stroke_width": stroke_width})
                points.extend([
                    (current[0] - radius, current[1] - radius),
                    (current[0] + radius, current[1] + radius),
                ])
        elif op in {"SP", "PM", "FP", "ST"}:
            flush()
    flush()
    return segments, points


def _render_hpgl(vector: dict, color_ref: str, palette: dict[str, tuple[int, int, int, int]]) -> Image.Image | None:
    segments, points = _parse_hpgl(vector.get("hpgl") or "")
    if not segments or not points:
        return None
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    width = max(max_x - min_x, 1)
    height = max(max_y - min_y, 1)
    target = 96
    padding = 8
    scale = min((target - 2 * padding) / width, (target - 2 * padding) / height)
    image = Image.new("RGBA", (target, target), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    color = palette.get(_color_name(color_ref, palette), palette.get("CHBLK", (0, 0, 0, 255)))

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        x = padding + (point[0] - min_x) * scale
        y = padding + (point[1] - min_y) * scale
        return x, y

    for segment in segments:
        stroke = max(1, int(round(segment.get("stroke_width", 1) * scale * 2)))
        if segment["type"] == "polyline":
            draw.line([transform(point) for point in segment["points"]], fill=color, width=stroke, joint="curve")
        elif segment["type"] == "circle":
            center = transform(segment["center"])
            radius = max(1, segment["radius"] * scale)
            draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=color, width=stroke)
    return image


def build() -> dict:
    master = _read_json(MASTER)
    registry = _asset_registry()
    sheets = _load_sheets()
    palettes = _palette_colors()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    rendered = 0
    bitmap_rendered = 0
    vector_rendered = 0
    for master_row in master["rows"]:
        asset = master_row["asset"]
        asset_def = _resolve_asset_def(registry, asset, master_row["s52_asset_kind"])
        bitmap = asset_def.get("bitmap") if asset_def else None
        vector = asset_def.get("vector") if asset_def else None
        output_paths: dict[str, str] = {}
        status = "rendered"
        reasons: list[str] = []
        render_source = None
        if not asset_def:
            status = "missing_opencpn_asset_definition"
            reasons.append(status)
        elif bitmap and bitmap["width"] > 0 and bitmap["height"] > 0:
            safe = _safe_asset_filename(asset)
            for palette, sheet in sheets.items():
                out_path = OUT_DIR / f"{safe}__{palette}.png"
                _crop(sheet, bitmap).save(out_path)
                output_paths[palette] = str(out_path.relative_to(ROOT))
            rendered += 1
            bitmap_rendered += 1
            render_source = "bitmap_crop"
        elif vector and vector.get("hpgl"):
            safe = _safe_asset_filename(asset)
            for palette, colors in palettes.items():
                out_path = OUT_DIR / f"{safe}__{palette}.png"
                image = _render_hpgl(vector, asset_def.get("color_ref") or "", colors)
                if image is None:
                    continue
                image.save(out_path)
                output_paths[palette] = str(out_path.relative_to(ROOT))
            if output_paths:
                rendered += 1
                vector_rendered += 1
                status = "rendered_vector"
                render_source = "hpgl_vector"
            else:
                status = "vector_render_failed"
                reasons.append(status)
        else:
            status = "missing_bitmap_or_vector"
            reasons.append(status)
        rows.append({
            "asset": asset,
            "kind": master_row["s52_asset_kind"],
            "family": master_row["family"],
            "description": master_row.get("description") or (asset_def or {}).get("description"),
            "status": status,
            "reason_codes": reasons,
            "render_source": render_source,
            "bitmap": bitmap,
            "vector": {
                key: value for key, value in (vector or {}).items() if key != "hpgl"
            } if vector else None,
            "opencpn_definition": {
                "kind": asset_def.get("kind"),
                "rcid": asset_def.get("rcid"),
                "definition": asset_def.get("definition"),
                "color_ref": asset_def.get("color_ref"),
            } if asset_def else None,
            "palette_paths": output_paths,
            "source": {
                "chartsymbols_xml": str(S52),
                "raster_sheets": {palette: str((S52_DIR / filename)) for palette, filename in PALETTE_SHEETS.items()},
                "license_boundary": "reference_oracle_not_canonical_artwork",
                "forbidden_use": ["canonical_owned_svg_source", "bulk_vendor_artwork"],
            },
        })

    status_counts = Counter(row["status"] for row in rows)
    kind_counts = Counter(row["kind"] for row in rows)
    output = {
        "schema_version": 1,
        "scope": "OpenCPN/S-52 reference-only raster crops and HPGL vector renders for visual repair",
        "summary": {
            "master_rows": len(rows),
            "rendered_assets": rendered,
            "bitmap_rendered_assets": bitmap_rendered,
            "vector_rendered_assets": vector_rendered,
            "reference_pngs": rendered * len(PALETTE_SHEETS),
            "palettes": list(PALETTE_SHEETS),
            "status_counts": dict(sorted(status_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "limits": [
                "Reference PNGs are derived from OpenCPN/S-52 raster sheets or HPGL vector definitions and are not canonical Helm-owned artwork.",
                "Use these files as local visual-oracle inputs for repair and QA only.",
                "Do not commit or package the PNG crops into the owned SVG asset pack without a deliberate license decision.",
            ],
        },
        "rows": rows,
    }
    REPORT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    _write_md(output)
    return output


def _write_md(output: dict) -> None:
    summary = output["summary"]
    lines = [
        "# OpenCPN S-52 Reference Renders",
        "",
        "Reference-only local PNG crops/renders from the OpenCPN/S-52 presentation raster sheets and HPGL vector definitions.",
        "",
        "## Summary",
        "",
        f"- Master rows: {summary['master_rows']}",
        f"- Rendered assets: {summary['rendered_assets']}",
        f"- Bitmap-rendered assets: {summary['bitmap_rendered_assets']}",
        f"- Vector-rendered assets: {summary['vector_rendered_assets']}",
        f"- Reference PNGs: {summary['reference_pngs']}",
        f"- Palettes: {', '.join(summary['palettes'])}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "These PNGs are a visual oracle for local repair and QA. They are not owned canonical SVG artwork.",
        "",
    ])
    SUMMARY_MD.write_text("\n".join(lines))


def main() -> int:
    output = build()
    summary = output["summary"]
    print("OpenCPN S-52 reference renders")
    print(f"rendered assets: {summary['rendered_assets']}")
    print(f"reference PNGs: {summary['reference_pngs']}")
    print(f"report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
