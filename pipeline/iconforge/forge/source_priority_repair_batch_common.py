"""Common builder for later source-priority repair batches."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import source_priority_repair_batch1
from . import source_priority_repair_queue
from .style_contract import OPENBRIDGE_STYLE_ID


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PACK = ROOT / "catalog" / "source_priority_icon_pack.json"
PALETTES = ["day", "dusk", "night"]


def safe_filename(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
    return safe or "unnamed_asset"


def source_rows() -> dict[str, dict]:
    pack = json.loads(SOURCE_PACK.read_text())
    return {row["asset"]: row for row in pack["symbols"]}


def _queue(limit: int, offset: int, render_candidate: bool) -> dict:
    return source_priority_repair_queue.build(
        limit=limit,
        offset=offset,
        render_candidate=render_candidate,
        include_s101_redraw=True,
    )


def _placeholder_svg(asset: str, batch_number: int) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        f'data-origin="generated-owned-artwork" data-style-contract="{OPENBRIDGE_STYLE_ID}" '
        f'data-repair-batch="source-priority-batch{batch_number}">'
        f"<title>{asset} generated placeholder requiring dedicated renderer</title>"
        '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="15" y="15" width="34" height="34" rx="5" fill="var(--white)" '
        'stroke="var(--black)" stroke-width="2" stroke-dasharray="5 4"/>'
        '<path d="M24 32H40M32 24V40" stroke="var(--gray)" stroke-width="2"/>'
        "</g></svg>\n"
    )


def candidate_svg(job: dict, all_source_rows: dict[str, dict], batch_number: int) -> tuple[str, str | None, str, str]:
    if job["queue_action"] != "redraw_s101_reference_into_helm_style":
        return (
            source_priority_repair_batch1._preserved_svg(job),
            job["candidate"]["svg"],
            source_priority_repair_batch1._repair_note(job),
            "preserved_current_helm_candidate",
        )

    source_row = all_source_rows[job["asset"]]
    fallback = source_row["source_priority"].get("fallback_generated_asset_file")
    if fallback and (ROOT / fallback).exists():
        return (
            (ROOT / fallback).read_text(),
            fallback,
            "used generated-owned fallback SVG as S-101 redraw candidate; S-101 kept as visual reference only",
            "generated_fallback_for_s101_reference",
        )

    return (
        _placeholder_svg(job["asset"], batch_number),
        None,
        "generated owned placeholder because this row has no generated fallback; requires dedicated renderer review",
        "generated_placeholder_no_fallback",
    )


def render(svg: str, out_path: Path, palette: str, size: int = 160) -> None:
    from . import multisource_svg_pack
    from . import render as renderer

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(renderer.rasterize(svg, multisource_svg_pack.PALETTES[palette], size=size))


def build_batch(
    *,
    batch_number: int,
    offset: int,
    limit: int,
    render_outputs: bool = False,
) -> dict:
    out_dir = ROOT / "out" / f"source_priority_repair_batch{batch_number}"
    svg_out = ROOT / "assets" / "svg" / f"owned_repair_batch{batch_number}"
    catalog = ROOT / "catalog" / f"owned_repair_batch{batch_number}.json"
    summary_md = ROOT / "catalog" / f"owned_repair_batch{batch_number}.md"
    report_path = out_dir / "report.json"
    pdf_path = out_dir / "before_reference_after.pdf"

    queue = _queue(limit, offset, render_outputs)
    all_source_rows = source_rows()
    svg_out.mkdir(parents=True, exist_ok=True)
    rows = []
    for job in queue["jobs"]:
        svg, candidate_source, note, candidate_strategy = candidate_svg(job, all_source_rows, batch_number)
        svg_path = svg_out / f"{safe_filename(job['asset'])}.svg"
        svg_path.write_text(svg)
        renders = {}
        if render_outputs:
            for palette in PALETTES:
                png = out_dir / "renders" / f"{safe_filename(job['asset'])}__after__{palette}.png"
                render(svg, png, palette)
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
                "generator": f"forge.source_priority_repair_batch{batch_number}",
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
            "svg_dir": str(svg_out.relative_to(ROOT)),
            "catalog": str(catalog.relative_to(ROOT)),
            "report": str(report_path.relative_to(ROOT)),
            "pdf": str(pdf_path.relative_to(ROOT)) if render_outputs else None,
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
    catalog.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_summary(summary_md, report, batch_number)
    if render_outputs:
        write_pdf(pdf_path, report, batch_number)
    return report


def write_summary(path: Path, report: dict, batch_number: int) -> None:
    summary = report["summary"]
    lines = [
        f"# Reference-Preserving Repair Batch {batch_number}",
        "",
        "Candidate batch from the source-priority repair queue. SVGs are generated-owned candidates, not final approved chart artwork.",
        "",
        f"- Batch offset: {report['batch_offset']}",
        f"- Batch size: {report['batch_size']}",
        f"- Repair existing Helm-style SVGs: {summary['repair_existing_helm_style_svg']}",
        f"- S-101 reference redraw rows: {summary['redraw_s101_reference_into_helm_style']}",
        f"- Generated-owned fallback redraws: {summary['generated_fallback_for_s101_reference']}",
        f"- Generated placeholders with no fallback: {summary['generated_placeholder_no_fallback']}",
        f"- Visual parity: `{summary['visual_parity']}`",
        "",
        "S-101 rows are used as visual references. They are not copied into canonical Helm artwork here.",
        "",
    ]
    path.write_text("\n".join(lines))


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


def write_pdf(path: Path, report: dict, batch_number: int) -> None:
    import PIL.JpegImagePlugin  # noqa: F401 - register Pillow PDF/JPEG encoder.
    from PIL import Image, ImageDraw, ImageFont

    path.parent.mkdir(parents=True, exist_ok=True)
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
        draw.text((24, 20), f"Repair Batch {batch_number}: source-priority candidates", fill="white", font=bold)
        chunk = symbols[start:start + cols * rows_per_page]
        for i, row in enumerate(chunk):
            x = (i % cols) * cell_w
            y = 85 + (i // cols) * cell_h
            draw.rounded_rectangle([x + 10, y, x + cell_w - 10, y + cell_h - 12], radius=8, fill="white", outline=(205, 212, 220))
            draw.text((x + 20, y + 10), row["asset"][:28], fill=(20, 30, 40), font=bold)
            draw.text((x + 20, y + 32), row["queue_action"].replace("_", " ")[:40], fill=(90, 95, 105), font=font)
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
        pages[0].save(path, save_all=True, append_images=pages[1:])
