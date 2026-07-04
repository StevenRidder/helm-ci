"""Preview a Helm-owned BCNSTK stake-beacon family template.

The BCNSTK family is drawn from the user-provided BNKSTK.svg pattern: a narrow
vertical stake with a small lower block and horizontal foot.

Run:
  python3 -m forge.stake_beacon_family_template_preview --render
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
OUT = ROOT / "out" / "stake_beacon_family_template_preview"
SVG_OUT = ROOT / "assets" / "svg" / "stake_beacon_family_template_preview"
REPORT = CATALOG / "stake_beacon_family_template_preview.json"
SUMMARY = CATALOG / "stake_beacon_family_template_preview.md"
SOURCE_ART = Path("/Users/steveridder/Downloads/BNKSTK.svg")
PALETTES = ("day", "dusk", "night")

SAMPLES = {
    "BCNSTK02": {"label": "black stake/pole beacon", "fills": ["black"], "reference_family": "BCNSTK"},
    "BCNSTK03": {"label": "black river stake/pole beacon", "fills": ["black"], "reference_family": "BCNSTK"},
    "BCNSTK05": {"label": "white stake/pole beacon", "fills": ["white"], "reference_family": "BCNSTK"},
    "BCNSTK08": {"label": "yellow stake/pole beacon", "fills": ["yellow"], "reference_family": "BCNSTK"},
    "BCNSTK60": {"label": "red stake/pole beacon", "fills": ["red"], "reference_family": "BCNSTK"},
    "BCNSTK61": {"label": "green stake/pole beacon", "fills": ["green"], "reference_family": "BCNSTK"},
    "BCNSTK62": {"label": "yellow stake/pole beacon", "fills": ["yellow"], "reference_family": "BCNSTK"},
    "BCNSTK77": {"label": "white/green/white stake beacon", "fills": ["white", "green", "white"], "reference_family": "BCNSTK"},
    "BCNSTK78": {"label": "red/white stake beacon", "fills": ["red", "white"], "reference_family": "BCNSTK"},
    "BCNSTK79": {"label": "red/green/red stake beacon", "fills": ["red", "green", "red"], "reference_family": "BCNSTK"},
    "BCNSTK80": {"label": "green/red/green stake beacon", "fills": ["green", "red", "green"], "reference_family": "BCNSTK"},
    "BCNSTK81": {"label": "green/white stake beacon", "fills": ["green", "white"], "reference_family": "BCNSTK"},
    "BCNSTK82": {"label": "red/green stake beacon", "fills": ["red", "green"], "reference_family": "BCNSTK"},
    "BCNSTK83": {"label": "green/red stake beacon", "fills": ["green", "red"], "reference_family": "BCNSTK"},
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
            '<rect x="29.5" y="10" width="5" height="39" rx="1.1"/>'
            '<rect x="30.5" y="49" width="3" height="4" rx="0.6"/>'
            '<rect x="24" y="46" width="16" height="3" rx="1"/>'
            "</g>"
        )
    if 2 <= len(fills) <= 4:
        band_h = 39 / len(fills)
        band_rects = []
        for index, fill in enumerate(fills):
            y = 10 + index * band_h
            next_y = 10 + (index + 1) * band_h if index < len(fills) - 1 else 49
            rx = ' rx="1.1"' if index == 0 else ""
            band_rects.append(
                f'<rect x="29.5" y="{y:g}" width="5" height="{next_y - y:g}"{rx} '
                f'fill="{_colour(fill)}"/>'
            )
        lower = _colour(fills[-1])
        return "".join([
            f'<g data-fill-pattern="{len(fills)}-band-horizontal">',
            "".join(band_rects),
            f'<rect x="30.5" y="49" width="3" height="4" rx="0.6" fill="{lower}"/>',
            f'<rect x="24" y="46" width="16" height="3" rx="1" fill="{lower}"/>',
            "</g>",
        ])
    raise ValueError(f"{asset} unsupported fill pattern: {fills}")


def _outer_outline() -> str:
    return (
        '<g data-outline-role="outer-visible-edges" fill="none" '
        f'stroke="{_colour("ink")}" stroke-width="1.6">'
        '<path d="M30.6 10H33.4Q34.5 10 34.5 11.1V46H39Q40 46 40 47V48'
        'Q40 49 39 49H33.5V52Q33.5 53 32.5 53H31.5Q30.5 53 30.5 52V49H25'
        'Q24 49 24 48V47Q24 46 25 46H29.5V11.1Q29.5 10 30.6 10Z"/>'
        "</g>"
    )


def _tiny_cutout() -> str:
    return (
        '<circle data-hole-role="s101-tiny-stake-cutout" '
        f'cx="32" cy="46" r="2.2" fill="{_colour("white")}"/>'
    )


def stake_beacon_template_svg(asset: str, fills: list[str], title: str | None = None) -> str:
    """Return one stake beacon drawn from the user BNKSTK pattern."""
    title = title or asset
    fill_body = _fill_body(asset, fills)
    body = (
        '<defs>'
        f'<clipPath id="clip-{asset}">'
        '<rect x="29.5" y="10" width="5" height="39" rx="1.1"/>'
        '<rect x="30.5" y="49" width="3" height="4" rx="0.6"/>'
        '<rect x="24" y="46" width="16" height="3" rx="1"/>'
        '</clipPath>'
        '</defs>'
        f"{fill_body}"
        f"{_tiny_cutout()}"
        f"{_outer_outline()}"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-source-art="user-provided-BNKSTK" data-shape-family="beacon-bcnstk-bank-stake-template">'
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
    path = OUT / "stake_beacon_family_template_preview_day.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.relative_to(ROOT))


def build(*, render_outputs: bool = False) -> dict:
    if not SOURCE_ART.exists():
        raise FileNotFoundError(f"missing user-provided stake source art: {SOURCE_ART}")
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset, spec in SAMPLES.items():
        svg = stake_beacon_template_svg(asset, spec["fills"], f"{asset} BCNSTK stake-beacon template")
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
            "template_role": "stake_beacon_family_geometry_preview",
            "svg": str(svg_path.relative_to(ROOT)),
            "renders": renders,
            "provenance": {
                "origin": "generated-owned-artwork",
                "source_art": str(SOURCE_ART),
                "source_art_role": "user_directed_shape_reference",
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.stake_beacon_family_template_preview",
            },
        })
    contact_sheet = _write_contact_sheet(rows) if render_outputs else None
    result = {
        "schema_version": 1,
        "status": "stake_beacon_family_template_preview_written",
        "project": "vulkan",
        "task_id": "FORGE-15",
        "source_art": str(SOURCE_ART),
        "policy": "Preview only: does not replace BCNSTK family assets until human approves the template.",
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "renders": str((OUT / "renders").relative_to(ROOT)) if render_outputs else None,
            "contact_sheet": contact_sheet,
        },
        "summary": {
            "template_shape": "bank_stake_pattern_from_user_BNKSTK",
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
        "# Stake Beacon Family Template Preview",
        "",
        "BCNSTK redrawn from user-provided `BNKSTK.svg` as a narrow stake with lower block and foot.",
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
        print(f"stake beacon family template preview: {result['summary']['sample_count']} samples")


if __name__ == "__main__":
    main()
