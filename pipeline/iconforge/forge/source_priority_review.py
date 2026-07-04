"""Render review sheets for the source-priority icon pack.

The source-priority pack selects the best current SVG per symbol row. This
module turns that into human-reviewable pages: exact S-101 reference rows,
Helm-style draft fallback rows, and the hard-pile.

Run:
  python -m forge.source_priority_review
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

from . import multisource_svg_pack, render


ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "catalog" / "source_priority_icon_pack.json"
OUT = ROOT / "out" / "source_priority_icon_pack"
REVIEW_JSON = OUT / "source_priority_review.json"
PDF = OUT / "source_priority_review.pdf"
HARD_PILE = OUT / "hard_pile.txt"
PNG_DIR = OUT / "renders"
SHEET_DIR = OUT / "sheets"

PAGE_W = 1600
PAGE_H = 2100
COLS = 5
ROWS = 7
CELL_W = PAGE_W // COLS
CELL_H = 265
ICON = 120


def _font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = _font(30, True)
FONT_HEAD = _font(18, True)
FONT_BODY = _font(15)
FONT_SMALL = _font(12)
FONT_TINY = _font(10)


def _wrap(draw: ImageDraw.ImageDraw, text: str, width: int, font) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _rasterize(row: dict) -> Path | None:
    if not row.get("asset_file"):
        return None
    svg_path = ROOT / row["asset_file"]
    png = PNG_DIR / f"{row['asset']}__day.png"
    if png.exists() and png.stat().st_mtime >= svg_path.stat().st_mtime:
        return png
    svg = svg_path.read_text()
    try:
        if "var(--" in svg:
            data = render.rasterize(svg, multisource_svg_pack.PALETTES["day"], size=160)
        else:
            data = cairosvg.svg2png(url=str(svg_path), output_width=160, output_height=160)
    except Exception as exc:  # noqa: BLE001 - review artifact must log every failed row.
        return _render_error(row, str(exc))
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(data)).convert("RGBA").save(png)
    return png


def _render_error(row: dict, error: str) -> None:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    png = PNG_DIR / f"{row['asset']}__render_error.png"
    image = Image.new("RGBA", (160, 160), (255, 244, 235, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([8, 8, 152, 152], outline=(180, 60, 35), width=3)
    draw.text((18, 60), "render", fill=(150, 35, 20), font=FONT_BODY)
    draw.text((18, 82), "error", fill=(150, 35, 20), font=FONT_BODY)
    image.save(png)
    row.setdefault("review_render_error", error)
    return png


def _basis_label(row: dict) -> tuple[str, tuple[int, int, int]]:
    basis = row["source_priority"]["selected_basis"]
    if basis == "s101_exact_svg":
        return "S-101 exact reference", (33, 93, 142)
    if basis == "helm_multisource_draft_svg":
        return "Helm-style draft fallback", (105, 87, 28)
    return "Hard-pile gap", (130, 48, 42)


def _style_status(row: dict) -> str:
    basis = row["source_priority"]["selected_basis"]
    if basis == "s101_exact_svg":
        return "shape locked; redraw into Helm style after license/IP gate"
    if basis == "helm_multisource_draft_svg":
        return "already Helm style; repair against references"
    return "needs renderer/manual symbol before style pass"


def _draw_card(page: Image.Image, row: dict, icon_path: Path | None, x: int, y: int) -> None:
    draw = ImageDraw.Draw(page)
    label, color = _basis_label(row)
    draw.rounded_rectangle([x + 12, y + 10, x + CELL_W - 12, y + CELL_H - 12], radius=8, outline=(205, 211, 218), width=1, fill=(255, 255, 255))
    draw.text((x + 22, y + 20), row["asset"], fill=(20, 28, 36), font=FONT_HEAD)
    draw.text((x + 22, y + 43), label, fill=color, font=FONT_TINY)
    if icon_path and icon_path.exists():
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((ICON, ICON), Image.Resampling.LANCZOS)
        ix = x + (CELL_W - icon.width) // 2
        page.paste(icon, (ix, y + 70), icon)
    else:
        draw.rectangle([x + 100, y + 75, x + 220, y + 195], outline=(180, 180, 180), width=2)
        draw.text((x + 121, y + 126), "no SVG", fill=(110, 110, 110), font=FONT_BODY)

    text_y = y + 200
    for line in _wrap(draw, row.get("name") or "", CELL_W - 44, FONT_SMALL)[:2]:
        draw.text((x + 22, text_y), line, fill=(52, 62, 72), font=FONT_SMALL)
        text_y += 15
    draw.text((x + 22, y + CELL_H - 42), _style_status(row), fill=(78, 88, 96), font=FONT_TINY)
    s101 = row.get("source_refs", {}).get("s101", {})
    if s101.get("symbol_id"):
        draw.text((x + 22, y + CELL_H - 26), f"S-101 {s101['symbol_id']}", fill=(90, 96, 104), font=FONT_TINY)


def _sheet_rows(rows: list[dict], title: str, prefix: str) -> list[Path]:
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    per_page = COLS * ROWS
    for page_index, start in enumerate(range(0, len(rows), per_page), start=1):
        chunk = rows[start:start + per_page]
        page = Image.new("RGB", (PAGE_W, PAGE_H), (244, 247, 250))
        draw = ImageDraw.Draw(page)
        draw.rectangle([0, 0, PAGE_W, 88], fill=(32, 54, 76))
        draw.text((36, 24), title, fill=(255, 255, 255), font=FONT_TITLE)
        draw.text((36, 60), f"page {page_index} / rows {start + 1}-{start + len(chunk)} of {len(rows)}", fill=(218, 226, 232), font=FONT_BODY)
        for index, row in enumerate(chunk):
            x = (index % COLS) * CELL_W
            y = 100 + (index // COLS) * CELL_H
            _draw_card(page, row, _rasterize(row), x, y)
        path = SHEET_DIR / f"{prefix}_{page_index:02d}.png"
        page.save(path)
        pages.append(path)
    return pages


def build() -> dict:
    pack = json.loads(PACK.read_text())
    rows = pack["symbols"]
    s101_rows = [row for row in rows if row["source_priority"]["selected_basis"] == "s101_exact_svg"]
    draft_rows = [row for row in rows if row["source_priority"]["selected_basis"] == "helm_multisource_draft_svg"]
    hard_rows = [row for row in rows if row["source_priority"]["selected_basis"] == "no_svg_renderer_yet"]

    OUT.mkdir(parents=True, exist_ok=True)
    sheets = {
        "s101_exact": [str(path.relative_to(ROOT)) for path in _sheet_rows(s101_rows, "Source-Priority Pack: exact S-101 reference rows", "s101_exact")],
        "helm_draft": [str(path.relative_to(ROOT)) for path in _sheet_rows(draft_rows, "Source-Priority Pack: Helm-style draft fallback rows", "helm_draft")],
    }
    HARD_PILE.write_text("\n".join(f"{row['asset']}\t{row['kind']}\t{row.get('name') or ''}" for row in hard_rows) + "\n")

    page_images = [Image.open(ROOT / path).convert("RGB") for paths in sheets.values() for path in paths]
    if page_images:
        page_images[0].save(PDF, save_all=True, append_images=page_images[1:])

    report = {
        "schema_version": 1,
        "source_pack": str(PACK.relative_to(ROOT)),
        "outputs": {
            "pdf": str(PDF.relative_to(ROOT)),
            "sheets": sheets,
            "hard_pile": str(HARD_PILE.relative_to(ROOT)),
            "renders_dir": str(PNG_DIR.relative_to(ROOT)),
        },
        "summary": {
            "s101_exact_rows": len(s101_rows),
            "helm_draft_rows": len(draft_rows),
            "hard_pile_rows": len(hard_rows),
            "rendered_rows": len(s101_rows) + len(draft_rows),
            "style_policy": [
                "References lock semantics and known shapes.",
                "Final distributable Helm-owned icons should use the Helm visual style unless a license-cleared exact reference is intentionally selected.",
                "S-101 exact rows remain license-pending reference art until cleared.",
                "Helm draft rows are the current style surface and should be repaired against the reference columns, not thrown away.",
            ],
        },
    }
    REVIEW_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    report = build()
    summary = report["summary"]
    print("Source-priority review sheets")
    print(f"S-101 exact rows: {summary['s101_exact_rows']}")
    print(f"Helm draft rows: {summary['helm_draft_rows']}")
    print(f"Hard-pile rows: {summary['hard_pile_rows']}")
    print(f"PDF: {ROOT / report['outputs']['pdf']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
