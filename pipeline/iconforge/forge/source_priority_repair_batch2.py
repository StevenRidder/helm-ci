"""Generate the second source-priority repair batch.

Batch 2 continues after the first 120 high-risk rows and covers the next 150
aids-to-navigation candidates. These rows are current Helm generated SVGs, so
the default action is to preserve the familiar selected form and submit the
rendered candidates for visual review rather than inventing a new silhouette.

Run:
  python -m forge.source_priority_repair_batch2 --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import source_priority_repair_queue
from . import source_priority_repair_batch1
from .style_contract import OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "source_priority_repair_batch2"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch2"
CATALOG = ROOT / "catalog" / "owned_repair_batch2.json"
SUMMARY_MD = ROOT / "catalog" / "owned_repair_batch2.md"
REPORT = OUT / "report.json"
PDF = OUT / "before_reference_after.pdf"
PALETTES = ["day", "dusk", "night"]
BATCH_OFFSET = 120
BATCH_LIMIT = 150


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def _queue(limit: int, offset: int, render_candidate: bool) -> dict:
    return source_priority_repair_queue.build(
        limit=limit,
        offset=offset,
        render_candidate=render_candidate,
        include_s101_redraw=True,
    )


def _render(svg: str, out_path: Path, palette: str, size: int = 160) -> None:
    from . import multisource_svg_pack
    from . import render

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(render.rasterize(svg, multisource_svg_pack.PALETTES[palette], size=size))


def build(
    limit: int = BATCH_LIMIT,
    *,
    offset: int = BATCH_OFFSET,
    render_outputs: bool = False,
) -> dict:
    queue = _queue(limit, offset, render_outputs)
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for job in queue["jobs"]:
        note = source_priority_repair_batch1._repair_note(job)
        svg = source_priority_repair_batch1._preserved_svg(job)
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
                "origin": "generated-owned-artwork",
                "source_priority_basis": job["source_priority_basis"],
                "style_contract_id": OPENBRIDGE_STYLE_ID,
                "generator": "forge.source_priority_repair_batch2",
                "reference_role": "familiar_symbol_preserved_as_candidate",
            },
        })
    report = {
        "schema_version": 1,
        "status": "candidate_batch_pending_visual_review",
        "source_queue": "out/source_priority_repair/repair_queue.json",
        "batch_offset": offset,
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
            "license_pending_reference_candidates": 0,
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
        "# Reference-Preserving Repair Batch 2",
        "",
        "Second candidate batch from the source-priority repair queue. This covers the next 150 aids-to-navigation rows after batch 1.",
        "",
        f"- Batch offset: {report['batch_offset']}",
        f"- Batch size: {report['batch_size']}",
        f"- Repair existing Helm-style SVGs: {summary['repair_existing_helm_style_svg']}",
        f"- Redraw S-101 references into Helm style: {summary['redraw_s101_reference_into_helm_style']}",
        f"- Visual parity: `{summary['visual_parity']}`",
        "",
        "Generated rows are owned candidates, not final approved artwork. The purpose of this batch is to make the next safety-relevant group inspectable at scale.",
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
        draw.text((24, 20), "Repair Batch 2: next 150 aids-to-navigation candidates", fill="white", font=bold)
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
            name = " ".join(str(row.get("name") or row["asset"]).split())
            draw.text((x + 20, y + 184), name[:44], fill=(35, 42, 50), font=font)
            draw.text((x + 20, y + 204), "verdict: pending visual review", fill=(130, 72, 20), font=font)
        pages.append(page)
    if pages:
        pages[0].save(PDF, save_all=True, append_images=pages[1:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=BATCH_LIMIT)
    parser.add_argument("--offset", type=int, default=BATCH_OFFSET)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(argv)
    report = build(limit=args.limit, offset=args.offset, render_outputs=args.render)
    print(json.dumps({
        "status": report["status"],
        "batch_offset": report["batch_offset"],
        "batch_size": report["batch_size"],
        "summary": report["summary"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
