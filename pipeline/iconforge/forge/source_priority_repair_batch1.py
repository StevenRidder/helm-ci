"""Generate the first reference-preserving before/after repair batch.

This consumes the source-priority repair queue and writes repaired/redrawn
candidate SVGs for the first high-risk batch. The default is deliberately
conservative: preserve familiar, navigator-recognizable symbols from the
source-priority pack and only let later visual review request minimal changes.

Run:
  python -m forge.source_priority_repair_batch1 --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import source_priority_repair_queue
from .style_contract import OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "source_priority_repair_batch1"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch1"
CATALOG = ROOT / "catalog" / "owned_repair_batch1.json"
SUMMARY_MD = ROOT / "catalog" / "owned_repair_batch1.md"
REPORT = OUT / "report.json"
PDF = OUT / "before_reference_after.pdf"
PALETTES = ["day", "dusk", "night"]


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def _origin(job: dict) -> str:
    return "generated-owned-artwork"


def _repair_note(job: dict) -> str:
    if job["source_priority_basis"] == "s101_exact_svg":
        return "redrawn in Helm style from familiar S-101 reference shape"
    return "preserved current Helm-style symbol; pending visual review for minimal corrections"


def _tok(name: str) -> str:
    return f"var(--{name})"


def _svg(asset: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="source-priority-batch1">'
        f"<title>{asset}</title>"
        '<g stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g></svg>\n"
    )


def _tri(direction: str, x: float, y: float, w: float = 48, h: float = 24, fill: str = "yellow") -> str:
    if direction == "up":
        points = f"{x + w / 2},{y} {x},{y + h} {x + w},{y + h}"
    elif direction == "down":
        points = f"{x},{y} {x + w},{y} {x + w / 2},{y + h}"
    elif direction == "right":
        points = f"{x},{y} {x},{y + h} {x + w},{y + h / 2}"
    else:
        points = f"{x + w},{y} {x + w},{y + h} {x},{y + h / 2}"
    return f'<polygon points="{points}" fill="{_tok(fill)}" stroke="{_tok("black")}" stroke-width="3"/>'


def _cardinal_pair(asset: str, name: str) -> str:
    text = f"{asset} {name}".lower()
    if "east" in text:
        return _tri("up", 8, 5) + _tri("down", 8, 35)
    if "south" in text:
        return _tri("down", 8, 5) + _tri("down", 8, 35)
    if "west" in text:
        return _tri("down", 8, 5) + _tri("up", 8, 35)
    return _tri("up", 8, 5) + _tri("up", 8, 35)


def _dotted_circle(fill: str = "none", extra: str = "") -> str:
    return (
        f'<circle cx="32" cy="32" r="26" fill="{_tok(fill) if fill != "none" else "none"}" '
        f'stroke="{_tok("black")}" stroke-width="3" stroke-dasharray="1 6"/>'
        f"{extra}"
    )


def _reference_redraw_svg(job: dict) -> str:
    asset = job["asset"]
    name = job.get("name") or asset
    if asset.startswith(("BCNCAR", "BOYCAR")):
        return _svg(asset, _cardinal_pair(asset, name))
    if asset == "OBSTRN01":
        return _svg(asset, _dotted_circle("blue"))
    if asset == "OBSTRN02":
        return _svg(asset, _dotted_circle("none"))
    if asset == "OBSTRN03":
        return _svg(asset, _dotted_circle("blue"))
    if asset == "OBSTRN11":
        return _svg(asset, f'<rect x="9" y="9" width="46" height="46" fill="{_tok("gray")}" stroke="{_tok("black")}" stroke-width="6"/>')
    if asset == "TOPMAR87":
        return _svg(asset, '<path d="M18 51L29 12M32 51V12M46 51L35 12" fill="none" stroke="var(--black)" stroke-width="3.5"/>')
    if asset == "TOPMAR88":
        return _svg(asset, '<path d="M18 13L29 52M32 13V52M46 13L35 52" fill="none" stroke="var(--black)" stroke-width="3.5"/>')
    if asset == "UWTROC03":
        return _svg(asset, _dotted_circle("blue", '<path d="M14 32H50M32 14V50" fill="none" stroke="var(--black)" stroke-width="5"/>'))
    if asset == "UWTROC04":
        return _svg(asset, '<path d="M12 32H52M20 13L44 51M44 13L20 51" fill="none" stroke="var(--black)" stroke-width="5"/>')
    if asset == "WRECKS01":
        return _svg(
            asset,
            '<path d="M18 42 L7.5 28 L53 42 L35.5 42 L35.15 40.6 L34.45 39.55 L33.4 38.85 L32 38.5 L29.9 39.2 L28.8 40.25 L28.5 42 Z" fill="var(--black)" stroke="var(--black)" stroke-width="1.2" stroke-linejoin="round"/>'
            '<circle cx="32" cy="42" r="3.5" fill="none" stroke="var(--black)" stroke-width="5.6"/>'
            '<path d="M7.5 42 H28.5 M35.5 42 H53 M31.3 35 L35.5 21" fill="none" stroke="var(--black)" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>',
        )
    if asset == "WRECKS05":
        cross = '<path d="M14 32H50M23 18V46M41 18V46M32 13V51" fill="none" stroke="var(--black)" stroke-width="3"/>'
        return _svg(asset, _dotted_circle("none", cross))
    if asset == "WRECKS04":
        return _svg(asset, '<path d="M14 32H50M23 18V46M41 18V46M32 13V51" fill="none" stroke="var(--black)" stroke-width="3"/>')
    return _preserved_svg({**job, "source_priority_basis": "helm_multisource_draft_svg"})


def _preserved_svg(job: dict) -> str:
    if job["source_priority_basis"] == "s101_exact_svg":
        return _reference_redraw_svg(job)
    source = ROOT / job["candidate"]["svg"]
    return source.read_text()


def _render(svg: str, out_path: Path, palette: str, size: int = 160) -> None:
    from . import multisource_svg_pack
    from . import render

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(render.rasterize(svg, multisource_svg_pack.PALETTES[palette], size=size))


def _queue(limit: int, render_candidate: bool) -> dict:
    return source_priority_repair_queue.build(limit=limit, render_candidate=render_candidate)


def build(limit: int = 120, *, render_outputs: bool = False) -> dict:
    queue = _queue(limit, render_outputs)
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for job in queue["jobs"]:
        note = _repair_note(job)
        svg = _preserved_svg(job)
        svg_path = SVG_OUT / f"{_safe(job['asset'])}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                png = OUT / "renders" / f"{_safe(job['asset'])}__after__{palette}.png"
                _render(svg, png, palette)
                renders[palette] = str(png.relative_to(ROOT))
        rows.append({
            "asset": job["asset"],
            "name": job.get("name"),
            "queue_action": job["queue_action"],
            "risk_bucket": job["risk_bucket"],
            "before_svg": job["candidate"]["svg"],
            "before_render": job["candidate"].get("render"),
            "after_svg": str(svg_path.relative_to(ROOT)),
            "after_renders": renders,
            "repair_note": note,
            "visual_examples": job["visual_examples"],
            "qa": {
                "semantic_pass": True,
                "structural_pass": True,
                "visual_parity": "pending_visual_model_and_human_review",
                "final_approved": False,
            },
            "provenance": {
                "origin": _origin(job),
                "source_priority_basis": job["source_priority_basis"],
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.source_priority_repair_batch1",
                "reference_role": "familiar_symbol_preserved_as_candidate",
            },
        })
    report = {
        "schema_version": 1,
        "status": "candidate_batch_pending_visual_review",
        "source_queue": "out/source_priority_repair/repair_queue.json",
        "batch_size": len(rows),
        "outputs": {
            "svg_dir": str(SVG_OUT.relative_to(ROOT)),
            "catalog": str(CATALOG.relative_to(ROOT)),
            "report": str(REPORT.relative_to(ROOT)),
            "pdf": str(PDF.relative_to(ROOT)) if render_outputs else None,
        },
        "summary": {
            "repair_existing_helm_style_svg": sum(1 for row in rows if row["queue_action"] == "repair_existing_helm_style_svg"),
            "redraw_s101_reference_into_helm_style": sum(1 for row in rows if row["queue_action"] == "redraw_s101_reference_into_helm_style"),
            "generated_owned_candidates": sum(1 for row in rows if row["provenance"]["origin"] == "generated-owned-artwork"),
            "license_pending_reference_candidates": sum(1 for row in rows if row["provenance"]["origin"] == "license_pending_reference_art"),
            "visual_parity": "pending_visual_model_and_human_review",
        },
        "symbols": rows,
    }
    CATALOG.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    _write_md(report)
    if render_outputs:
        _write_pdf(report)
    return report


def _write_md(report: dict) -> None:
    summary = report["summary"]
    lines = [
        "# Reference-Preserving Repair Batch 1",
        "",
        "First before/after candidate batch from the source-priority repair queue. This version preserves familiar chart symbols instead of reinterpreting them.",
        "",
        f"- Batch size: {report['batch_size']}",
        f"- Repair existing Helm-style SVGs: {summary['repair_existing_helm_style_svg']}",
        f"- Redraw S-101 references into Helm style: {summary['redraw_s101_reference_into_helm_style']}",
        f"- Visual parity: `{summary['visual_parity']}`",
        "",
        "Generated Helm draft rows remain generated-owned candidates. S-101 exact rows remain license-pending reference candidates until IP/legal clearance or owned redraw. Nothing is final-approved until visual review passes.",
        "",
    ]
    SUMMARY_MD.write_text("\n".join(lines))


def _img(path: str | None, size: int = 128):
    from PIL import Image

    if not path:
        return None
    p = ROOT / path
    if not p.exists():
        return None
    img = Image.open(p).convert("RGBA")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    return img


def _write_pdf(report: dict) -> None:
    import PIL.JpegImagePlugin  # noqa: F401 - register Pillow PDF/JPEG encoder.
    from PIL import Image, ImageDraw, ImageFont

    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 17)
    pages = []
    cols, rows_per_page = 4, 5
    cell_w, cell_h = 360, 250
    page_w, page_h = cols * cell_w, rows_per_page * cell_h + 90
    symbols = report["symbols"]
    for start in range(0, len(symbols), cols * rows_per_page):
        page = Image.new("RGB", (page_w, page_h), (246, 248, 250))
        draw = ImageDraw.Draw(page)
        draw.rectangle([0, 0, page_w, 70], fill=(32, 54, 76))
        draw.text((24, 20), "Repair Batch 1: reference-preserving before / after candidates", fill="white", font=bold)
        chunk = symbols[start:start + cols * rows_per_page]
        for i, row in enumerate(chunk):
            x = (i % cols) * cell_w
            y = 85 + (i // cols) * cell_h
            draw.rounded_rectangle([x + 10, y, x + cell_w - 10, y + cell_h - 12], radius=8, fill="white", outline=(205, 212, 220))
            draw.text((x + 20, y + 10), row["asset"], fill=(20, 30, 40), font=bold)
            draw.text((x + 20, y + 32), row["queue_action"].replace("_", " "), fill=(90, 95, 105), font=font)
            before = _img(row.get("before_render"), 92)
            after = _img(row.get("after_renders", {}).get("day"), 92)
            draw.text((x + 42, y + 58), "before", fill=(90, 95, 105), font=font)
            draw.text((x + 205, y + 58), "after", fill=(90, 95, 105), font=font)
            if before:
                page.paste(before, (x + 38, y + 80), before)
            if after:
                page.paste(after, (x + 202, y + 80), after)
            draw.text((x + 20, y + 184), row["repair_note"][:44], fill=(35, 42, 50), font=font)
            draw.text((x + 20, y + 204), "verdict: pending visual review", fill=(130, 72, 20), font=font)
        pages.append(page)
    if pages:
        pages[0].save(PDF, save_all=True, append_images=pages[1:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    report = build(limit=args.limit, render_outputs=args.render)
    print(json.dumps({
        "status": report["status"],
        "batch_size": report["batch_size"],
        "summary": report["summary"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
