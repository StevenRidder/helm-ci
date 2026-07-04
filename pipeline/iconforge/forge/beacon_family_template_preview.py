"""Preview a Helm-owned BCNGEN6 beacon-family template.

The source concept is user-provided art in BCNGEN6.svg. This module redraws the
idea into the Helm/OpenBridge-style SVG contract and renders representative
colour variants before applying it across the beacon family.

Run:
  python3 -m forge.beacon_family_template_preview --render
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
OUT = ROOT / "out" / "beacon_family_template_preview"
SVG_OUT = ROOT / "assets" / "svg" / "beacon_family_template_preview"
REPORT = CATALOG / "beacon_family_template_preview.json"
SUMMARY = CATALOG / "beacon_family_template_preview.md"
SOURCE_ART = Path("/Users/steveridder/Downloads/BCNGEN6.svg")
PALETTES = ("day", "dusk", "night")

SAMPLES = {
    "BCNGEN01": {
        "label": "black general beacon",
        "fills": ["black"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN03": {
        "label": "black default paper-chart beacon",
        "fills": ["black"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN05": {
        "label": "white general beacon",
        "fills": ["white"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN60": {
        "label": "red general beacon",
        "fills": ["red"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN61": {
        "label": "green general beacon",
        "fills": ["green"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN64": {
        "label": "red/white general beacon",
        "fills": ["red", "white", "red", "white"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN65": {
        "label": "green/white general beacon",
        "fills": ["green", "white", "green", "white"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN68": {
        "label": "black/yellow beacon",
        "fills": ["black", "yellow"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN69": {
        "label": "yellow/black beacon",
        "fills": ["yellow", "black"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN70": {
        "label": "black/yellow/black beacon",
        "fills": ["black", "yellow", "black"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN71": {
        "label": "yellow/black/yellow beacon",
        "fills": ["yellow", "black", "yellow"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN76": {
        "label": "black/red/black beacon",
        "fills": ["black", "red", "black"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN79": {
        "label": "orange beacon",
        "fills": ["orange"],
        "reference_family": "BCNGEN",
    },
    "BCNGEN80": {
        "label": "black general beacon",
        "fills": ["black"],
        "reference_family": "BCNGEN",
    },
}


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "unnamed_asset"


def _colour(name: str) -> str:
    return f"var(--{name})"


def _fill_body(asset: str, fills: list[str]) -> str:
    if len(fills) == 1:
        fill = _colour(fills[0])
        return (
            f'<g data-fill-pattern="solid" fill="{fill}">'
            '<rect x="25" y="12" width="14" height="34" rx="2"/>'
            '<rect x="18" y="46" width="28" height="4" rx="1.4"/>'
            '<circle cx="32" cy="46" r="7"/>'
            "</g>"
        )
    if 2 <= len(fills) <= 4:
        band_h = 34 / len(fills)
        band_rects = []
        for index, fill in enumerate(fills):
            y = 12 + index * band_h
            next_y = 12 + (index + 1) * band_h if index < len(fills) - 1 else 46
            rx = ' rx="2"' if index == 0 else ""
            band_rects.append(
                f'<rect x="25" y="{y:g}" width="14" height="{next_y - y:g}"{rx} '
                f'fill="{_colour(fill)}"/>'
            )
        lower = _colour(fills[-1])
        return "".join([
            f'<g data-fill-pattern="{len(fills)}-band-horizontal">',
            "".join(band_rects),
            f'<rect x="18" y="46" width="28" height="4" rx="1.4" fill="{lower}"/>',
            f'<circle cx="32" cy="46" r="7" fill="{lower}"/>',
            "</g>",
        ])
    raise ValueError(f"{asset} unsupported fill pattern: {fills}")


def _outer_outline() -> str:
    return (
        '<g data-outline-role="outer-visible-edges" fill="none" '
        f'stroke="{_colour("ink")}" stroke-width="1.8">'
        '<path d="M27 12H37Q39 12 39 14V46H44.6Q46 46 46 47.4V48.6'
        'Q46 50 44.6 50H38.3C36.9 51.8 34.7 53 32 53'
        'C29.3 53 27.1 51.8 25.7 50H19.4Q18 50 18 48.6V47.4'
        'Q18 46 19.4 46H25V14Q25 12 27 12Z"/>'
        "</g>"
    )


def beacon_template_svg(asset: str, fills: list[str], title: str | None = None) -> str:
    """Return one beacon drawn from the user BCNGEN6 concept in Helm style."""
    title = title or asset
    fill_body = _fill_body(asset, fills)
    # Geometry is intentionally the same for every sample: post, foot, and round beacon head.
    # Colour variants are applied through a single clipping group so future BCNGEN variants can
    # reuse the shape without redrawing the silhouette.
    body = (
        '<defs>'
        f'<clipPath id="clip-{asset}">'
        '<rect x="25" y="12" width="14" height="34" rx="2"/>'
        '<rect x="18" y="46" width="28" height="4" rx="1.4"/>'
        '<circle cx="32" cy="46" r="7"/>'
        '</clipPath>'
        '</defs>'
        f"{fill_body}"
        f'<circle data-hole-role="s101-center-cutout" cx="32" cy="46" r="5.6" fill="{_colour("white")}"/>'
        f"{_outer_outline()}"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-source-art="user-provided-BCNGEN6" data-shape-family="beacon-bcngen6-template">'
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
    path = OUT / "beacon_family_template_preview_day.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.relative_to(ROOT))


def build(*, render_outputs: bool = False) -> dict:
    if not SOURCE_ART.exists():
        raise FileNotFoundError(f"missing user-provided beacon source art: {SOURCE_ART}")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset, spec in SAMPLES.items():
        svg = beacon_template_svg(asset, spec["fills"], f"{asset} BCNGEN6 beacon-family template")
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
            "template_role": "beacon_family_geometry_preview",
            "svg": str(svg_path.relative_to(ROOT)),
            "renders": renders,
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_art": str(SOURCE_ART),
                "source_art_role": "user_created_shape_reference",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.beacon_family_template_preview",
            },
        })
    contact_sheet = _write_contact_sheet(rows) if render_outputs else None
    result = {
        "schema_version": 1,
        "status": "beacon_family_template_preview_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source_art": str(SOURCE_ART),
        "policy": "Preview only: does not replace beacon family assets until human approves the template.",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
            "contact_sheet": contact_sheet,
        },
        "summary": {
            "template_shape": "post_plus_foot_plus_round_head_from_user_BCNGEN6",
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
        "# Beacon Family Template Preview",
        "",
        "User-provided `BCNGEN6.svg` redrawn as a reusable Helm/OpenBridge-style beacon-family primitive.",
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
        print(
            "beacon family template preview: "
            f"{result['summary']['sample_count']} samples"
        )


if __name__ == "__main__":
    main()
