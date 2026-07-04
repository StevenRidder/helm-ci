"""Preview a Helm-owned BCNLAT beacon-family template.

The source concept is user-provided art in BCNLAT.svg. This module redraws the
idea into the Helm/OpenBridge-style SVG contract and renders the full BCNLAT
family as colour variants before applying it through the human review overlay.

Run:
  python3 -m forge.lateral_beacon_family_template_preview --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES, OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "out" / "lateral_beacon_family_template_preview"
SVG_OUT = ROOT / "assets" / "svg" / "lateral_beacon_family_template_preview"
REPORT = CATALOG / "lateral_beacon_family_template_preview.json"
SUMMARY = CATALOG / "lateral_beacon_family_template_preview.md"
SOURCE_ART = Path("/Users/steveridder/Downloads/BCNLAT.svg")
PALETTES = ("day", "dusk", "night")

SAMPLES = {
    "BCNLAT15": {
        "label": "major lateral beacon red/green/red",
        "fills": ["red", "green", "red"],
        "reference_family": "BCNLAT",
    },
    "BCNLAT16": {
        "label": "major lateral beacon green/red/green",
        "fills": ["green", "red", "green"],
        "reference_family": "BCNLAT",
    },
    "BCNLAT21": {
        "label": "minor lateral beacon red/green/red",
        "fills": ["red", "green", "red"],
        "reference_family": "BCNLAT",
    },
    "BCNLAT22": {
        "label": "minor lateral beacon green/red/green",
        "fills": ["green", "red", "green"],
        "reference_family": "BCNLAT",
    },
    "BCNLAT23": {
        "label": "minor lateral beacon red/green/black",
        "fills": ["red", "green", "black"],
        "reference_family": "BCNLAT",
    },
    "BCNLAT50": {
        "label": "river beacon stake/pole",
        "fills": ["black"],
        "reference_family": "BCNLAT",
    },
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _fill_body(fills: list[str]) -> str:
    if len(fills) == 1:
        return (
            f'<g data-fill-pattern="solid" fill="{_colour(fills[0])}">'
            '<rect x="23" y="9" width="18" height="46" rx="2.2"/>'
            "</g>"
        )
    if 2 <= len(fills) <= 4:
        band_h = 46 / len(fills)
        bands = []
        for index, fill in enumerate(fills):
            y = 9 + index * band_h
            next_y = 9 + (index + 1) * band_h if index < len(fills) - 1 else 55
            rx = ' rx="2.2"' if index == 0 else ""
            bands.append(
                f'<rect x="23" y="{y:g}" width="18" height="{next_y - y:g}"{rx} '
                f'fill="{_colour(fill)}"/>'
            )
        return "".join([
            f'<g data-fill-pattern="{len(fills)}-band-horizontal">',
            "".join(bands),
            "</g>",
        ])
    raise ValueError(f"unsupported fill pattern: {fills}")


def _outer_outline() -> str:
    return (
        '<g data-outline-role="outer-visible-edges" fill="none" '
        f'stroke="{_colour("ink")}" stroke-width="1.8">'
        '<path d="M25.2 9H38.8Q41 9 41 11.2V52.8Q41 55 38.8 55H25.2'
        'Q23 55 23 52.8V11.2Q23 9 25.2 9Z"/>'
        "</g>"
    )


def lateral_beacon_template_svg(asset: str, fills: list[str], title: str | None = None) -> str:
    """Return one lateral beacon drawn from the user BCNLAT concept in Helm style."""
    title = title or asset
    body = (
        '<defs>'
        f'<clipPath id="clip-{asset}">'
        '<rect x="23" y="9" width="18" height="46" rx="2.2"/>'
        '</clipPath>'
        '</defs>'
        f'<g clip-path="url(#clip-{asset})">{_fill_body(fills)}</g>'
        f'{_outer_outline()}'
        f'<circle cx="32" cy="32" r="2.7" fill="{_colour("ink")}"/>'
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-source-art="user-provided-BCNLAT" data-shape-family="beacon-bcnlat-template">'
        f"<title>{title}</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _render_svg(svg: str, asset: str, palette: str) -> str:
    out = OUT / "renders" / f"{_safe(asset)}__template__{palette}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=192))
    return str(out.relative_to(ROOT))


def _write_contact_sheet(rows: list[dict]) -> str:
    day_paths = [(row["asset"], ROOT / row["renders"]["day"]) for row in rows]
    cell_w, cell_h = 180, 214
    pad = 18
    sheet = Image.new("RGB", (pad * 2 + cell_w * len(day_paths), cell_h + pad * 2), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("Arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for index, (asset, path) in enumerate(day_paths):
        x = pad + index * cell_w
        draw.rectangle([x, pad, x + cell_w - 10, pad + cell_h], outline="#d0d4d8", width=1)
        with Image.open(path) as icon:
            icon = icon.convert("RGBA")
            icon.thumbnail((132, 132), Image.Resampling.LANCZOS)
            sheet.paste(icon, (x + (cell_w - 10 - icon.width) // 2, pad + 18), icon)
        draw.text((x + 12, pad + 164), asset, fill="#111111", font=font)
        draw.text((x + 12, pad + 184), ", ".join(SAMPLES[asset]["fills"]), fill="#444444", font=font)
    path = OUT / "lateral_beacon_family_template_preview_day.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.relative_to(ROOT))


def build(*, render_outputs: bool = False) -> dict:
    if not SOURCE_ART.exists():
        raise FileNotFoundError(f"missing user-provided lateral beacon source art: {SOURCE_ART}")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset, spec in SAMPLES.items():
        svg = lateral_beacon_template_svg(asset, spec["fills"], f"{asset} BCNLAT beacon-family template")
        svg_path = SVG_OUT / f"{asset}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                renders[palette] = _render_svg(svg, asset, palette)
        rows.append({
            "asset": asset,
            "label": spec["label"],
            "fills": spec["fills"],
            "reference_family": spec["reference_family"],
            "template_role": "lateral_beacon_family_geometry_preview",
            "svg": str(svg_path.relative_to(ROOT)),
            "renders": renders,
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_art": str(SOURCE_ART),
                "source_art_role": "user_created_shape_reference",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.lateral_beacon_family_template_preview",
            },
        })
    contact_sheet = _write_contact_sheet(rows) if render_outputs else None
    result = {
        "schema_version": 1,
        "status": "lateral_beacon_family_template_preview_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source_art": str(SOURCE_ART),
        "policy": "Preview only: does not replace BCNLAT family assets until human approves the template.",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
            "contact_sheet": contact_sheet,
        },
        "summary": {
            "template_shape": "tall_rectangular_lateral_beacon_from_user_BCNLAT",
            "sample_count": len(rows),
            "palette_count": len(PALETTES) if render_outputs else 0,
            "render_count": len(rows) * len(PALETTES) if render_outputs else 0,
            "status": "awaiting_human_template_approval",
        },
        "samples": rows,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary(result)
    return result


def _write_summary(result: dict) -> None:
    lines = [
        "# Lateral Beacon Family Template Preview",
        "",
        "User-provided `BCNLAT.svg` redrawn as a reusable Helm/OpenBridge-style BCNLAT primitive.",
        "",
        result["policy"],
        "",
        "## Samples",
        "",
        "| Asset | Variant | SVG | Day render |",
        "| --- | --- | --- | --- |",
    ]
    for row in result["samples"]:
        lines.append(
            f"| `{row['asset']}` | `{', '.join(row['fills'])}` | `{row['svg']}` | "
            f"`{row['renders'].get('day', '')}` |"
        )
    if result["outputs"]["contact_sheet"]:
        lines.extend(["", f"Contact sheet: `{result['outputs']['contact_sheet']}`"])
    SUMMARY.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(render_outputs=args.render)
    if args.json:
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    else:
        print(f"lateral beacon family template preview: {result['summary']['sample_count']} samples")


if __name__ == "__main__":
    main()
