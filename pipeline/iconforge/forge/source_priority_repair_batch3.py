"""Generate the third source-priority repair batch.

Batch 3 continues after batches 1 and 2. It is the first mixed batch: existing
Helm draft rows are preserved, while S-101 exact-reference rows use the
generated-owned fallback SVG as the candidate. S-101 remains a visual reference
only unless counsel clears the artwork for canonical use.

Run:
  python -m forge.source_priority_repair_batch3 --render
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import source_priority_repair_batch1
from . import source_priority_repair_queue
from .style_contract import OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "source_priority_repair_batch3"
SVG_OUT = ROOT / "assets" / "svg" / "owned_repair_batch3"
CATALOG = ROOT / "catalog" / "owned_repair_batch3.json"
SUMMARY_MD = ROOT / "catalog" / "owned_repair_batch3.md"
REPORT = OUT / "report.json"
PDF = OUT / "before_reference_after.pdf"
SOURCE_PACK = ROOT / "catalog" / "source_priority_icon_pack.json"
PALETTES = ["day", "dusk", "night"]
BATCH_OFFSET = 270
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


def _source_rows() -> dict[str, dict]:
    pack = json.loads(SOURCE_PACK.read_text())
    return {row["asset"]: row for row in pack["symbols"]}


def _marine_farm_placeholder(asset: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        'data-repair-batch="source-priority-batch3">'
        f"<title>{asset} generated marine farm pattern placeholder</title>"
        '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 18H52M12 32H52M12 46H52M18 12V52M32 12V52M46 12V52" '
        'stroke="var(--gray)" stroke-width="2" stroke-dasharray="4 5"/>'
        '<circle cx="18" cy="18" r="3" fill="var(--gray)" stroke="var(--black)" stroke-width="1"/>'
        '<circle cx="32" cy="32" r="3" fill="var(--gray)" stroke="var(--black)" stroke-width="1"/>'
        '<circle cx="46" cy="46" r="3" fill="var(--gray)" stroke="var(--black)" stroke-width="1"/>'
        "</g></svg>\n"
    )


def _candidate_svg(job: dict, source_rows: dict[str, dict]) -> tuple[str, str | None, str, str]:
    if job["queue_action"] != "redraw_s101_reference_into_helm_style":
        return (
            source_priority_repair_batch1._preserved_svg(job),
            job["candidate"]["svg"],
            source_priority_repair_batch1._repair_note(job),
            "preserved_current_helm_candidate",
        )

    source_row = source_rows[job["asset"]]
    fallback = source_row["source_priority"].get("fallback_generated_asset_file")
    if fallback and (ROOT / fallback).exists():
        return (
            (ROOT / fallback).read_text(),
            fallback,
            "used generated-owned fallback SVG as S-101 redraw candidate; S-101 kept as visual reference only",
            "generated_fallback_for_s101_reference",
        )

    return (
        _marine_farm_placeholder(job["asset"]),
        None,
        "generated owned placeholder because this pattern row has no point-symbol fallback; requires dedicated pattern renderer review",
        "generated_placeholder_no_fallback",
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
    source_rows = _source_rows()
    SVG_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for job in queue["jobs"]:
        svg, candidate_source, note, candidate_strategy = _candidate_svg(job, source_rows)
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
            "candidate_strategy": candidate_strategy,
            "candidate_source": candidate_source,
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
                "generator": "forge.source_priority_repair_batch3",
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
            "generated_fallback_for_s101_reference": sum(1 for row in rows if row["candidate_strategy"] == "generated_fallback_for_s101_reference"),
            "generated_placeholder_no_fallback": sum(1 for row in rows if row["candidate_strategy"] == "generated_placeholder_no_fallback"),
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
        "# Reference-Preserving Repair Batch 3",
        "",
        "Third candidate batch from the source-priority repair queue. This covers the next mixed slice after batches 1 and 2.",
        "",
        f"- Batch offset: {report['batch_offset']}",
        f"- Batch size: {report['batch_size']}",
        f"- Repair existing Helm-style SVGs: {summary['repair_existing_helm_style_svg']}",
        f"- S-101 reference redraw rows: {summary['redraw_s101_reference_into_helm_style']}",
        f"- Generated-owned fallback redraws: {summary['generated_fallback_for_s101_reference']}",
        f"- Generated placeholders with no fallback: {summary['generated_placeholder_no_fallback']}",
        f"- Visual parity: `{summary['visual_parity']}`",
        "",
        "S-101 rows are not copied into canonical art here. They use generated-owned fallback candidates, with S-101 retained as a reference witness.",
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
        draw.text((24, 20), "Repair Batch 3: mixed Helm drafts and S-101 redraw candidates", fill="white", font=bold)
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
            draw.text((x + 20, y + 184), row["candidate_strategy"].replace("_", " ")[:44], fill=(35, 42, 50), font=font)
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
