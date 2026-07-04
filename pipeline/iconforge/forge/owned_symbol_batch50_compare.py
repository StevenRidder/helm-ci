"""Compare the owned batch50 SVGs against the source-variant uber list.

Run:
  python -m forge.owned_symbol_batch50_compare
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import owned_symbol_batch50, render, source_variant_matrix


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "owned_symbol_batch50"
COMPARE_PDF = OUT / "owned_batch50_vs_uber_list.pdf"
COMPARE_HTML = OUT / "owned_batch50_vs_uber_list.html"
COMPARE_JSON = OUT / "owned_batch50_vs_uber_list.json"
PALETTES = ["day", "dusk", "night"]

REFERENCE_GROUPS = [
    ("OpenCPN S-52", ["opencpn_s52_reference_render"]),
    ("Chart 1", ["chart1_parity_reference_crop", "chart1_mappings_symbol_reference"]),
    ("Aqua Map", ["aquamap_map_symbols"]),
    ("S-101", ["s101_portrayal_catalogue_svg"]),
    ("Commons", ["wikimedia_commons_svg"]),
    ("OpenBridge", ["openbridge_concept"]),
    ("Concept refs", ["noto_emoji_concept", "openmoji_concept", "open_source_icon_concept"]),
]

STYLES = getSampleStyleSheet()
STYLES["Title"].fontSize = 23
STYLES["Title"].leading = 28
STYLES["Heading2"].fontSize = 14
STYLES["Heading2"].leading = 17
STYLES.add(ParagraphStyle(name="Tiny", parent=STYLES["BodyText"], fontSize=7.4, leading=8.5))
STYLES.add(ParagraphStyle(name="TinyMuted", parent=STYLES["BodyText"], fontSize=6.8, leading=7.8, textColor=colors.HexColor("#4d5864")))
STYLES.add(ParagraphStyle(name="Small", parent=STYLES["BodyText"], fontSize=8.6, leading=9.8))
STYLES.add(ParagraphStyle(name="HeaderCell", parent=STYLES["BodyText"], fontSize=7.2, leading=8.3, textColor=colors.white, alignment=1))
STYLES.add(ParagraphStyle(name="Readable", parent=STYLES["BodyText"], fontSize=11.5, leading=14.2))


def _para(text: str, style: ParagraphStyle = STYLES["Tiny"]) -> Paragraph:
    return Paragraph(html.escape(str(text or "")), style)


def _pdf_image(path: str | Path | None, width: float, max_height: float = 0.82 * inch) -> list:
    if not path:
        return [_para("none", STYLES["TinyMuted"])]
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = ROOT / image_path
    if not image_path.exists():
        return [_para("missing", STYLES["TinyMuted"])]
    image = Image(str(image_path))
    scale = min(width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return [image]


def _entry_flows(entries: list[dict], limit: int = 2) -> list:
    flows: list = []
    for entry in entries[:limit]:
        flows.extend(_pdf_image(entry.get("image"), 1.15 * inch))
        flows.append(_para(entry.get("label") or entry.get("source") or "reference", STYLES["Tiny"]))
        flows.append(_para(entry.get("status") or "", STYLES["TinyMuted"]))
        flows.append(Spacer(1, 0.03 * inch))
    return flows or [_para("none", STYLES["TinyMuted"])]


def _reference_entries(row: dict, providers: list[str]) -> list[dict]:
    out: list[dict] = []
    for provider in providers:
        out.extend(row.get("providers", {}).get(provider, []))
    return out


def _render_owned_day(symbol: dict) -> str:
    return symbol["asset"]["renders"]["day"]


def _meta_text(row: dict) -> list:
    s57 = row.get("s57") or {}
    s101 = row.get("s101") or {}
    brief = row.get("visual_brief") or {}
    return [
        _para(row["asset"], STYLES["Small"]),
        _para(row.get("name") or "", STYLES["Tiny"]),
        _para(f"S-57 {s57.get('object_class') or 'none'}: {'; '.join(s57.get('conditions') or [])}", STYLES["Tiny"]),
        _para(f"S-101 {s101.get('symbol_id') or s101.get('coverage') or 'none'}", STYLES["Tiny"]),
        _para(f"Chart 1 refs: {', '.join(row.get('chart1_mappings_refs') or []) or 'none'}", STYLES["Tiny"]),
        _para(f"Brief: {brief.get('model_caption') or ''}", STYLES["TinyMuted"]),
    ]


def _qa_text(symbol: dict) -> list:
    qa = symbol.get("qa") or {}
    provenance = symbol.get("provenance") or {}
    return [
        _para(f"semantic: {qa.get('semantic_pass')}", STYLES["Tiny"]),
        _para(f"structural: {qa.get('structural_pass')}", STYLES["Tiny"]),
        _para(f"visual: {qa.get('visual_parity')}", STYLES["Tiny"]),
        _para(f"origin: {provenance.get('origin')}", STYLES["TinyMuted"]),
        _para(f"style: {provenance.get('style_contract_id')}", STYLES["TinyMuted"]),
    ]


def _comparison_rows() -> tuple[dict, dict]:
    owned_report = owned_symbol_batch50.build()
    matrix = source_variant_matrix.build(owned_symbol_batch50.SELECTED_50)
    owned_by_id = {symbol["id"]: symbol for symbol in owned_report["symbols"]}
    rows = []
    for row in matrix["rows"]:
        symbol = owned_by_id[row["asset"]]
        refs = {
            label: _reference_entries(row, providers)
            for label, providers in REFERENCE_GROUPS
        }
        rows.append({
            "asset": row["asset"],
            "name": row.get("name"),
            "family": row.get("family"),
            "s57": row.get("s57"),
            "s101": row.get("s101"),
            "chart1_mappings_refs": row.get("chart1_mappings_refs"),
            "owned": {
                "canonical": symbol["asset"]["canonical"],
                "day_render": _render_owned_day(symbol),
                "qa": symbol["qa"],
                "provenance": symbol["provenance"],
            },
            "references": refs,
            "visual_brief": row.get("visual_brief"),
        })
    report = {
        "format": "helm.iconforge.owned_batch50_vs_uber_list.v1",
        "style_contract": source_variant_matrix.STYLE_CONTRACT,
        "asset_count": len(rows),
        "owned_report": owned_report["outputs"],
        "outputs": {
            "pdf": str(COMPARE_PDF.relative_to(ROOT)),
            "html": str(COMPARE_HTML.relative_to(ROOT)),
            "json": str(COMPARE_JSON.relative_to(ROOT)),
        },
        "rows": rows,
    }
    return report, matrix


def _write_pdf(report: dict, matrix: dict) -> None:
    story = [
        _para("Owned Batch50 vs Uber Source List", STYLES["Title"]),
        _para(
            "This is the inspection sheet for the first 50 generated-owned Helm SVG drafts. "
            "Each row shows the uber-list metadata, our owned SVG, and the available reference examples. "
            "Aqua Map, OpenCPN, S-101, Commons, emoji, and icon-library art are comparison references only, not canonical artwork.",
            STYLES["Readable"],
        ),
        Spacer(1, 0.15 * inch),
        _para(
            "Important: structural and semantic checks passed for this batch, but visual parity is intentionally still pending. "
            "The next gate is visual-model critique and repair against these reference columns.",
            STYLES["Readable"],
        ),
        PageBreak(),
    ]
    headers = [
        "Uber list row",
        "Our owned SVG",
        "OpenCPN S-52",
        "Chart 1",
        "Aqua Map",
        "S-101",
        "Commons",
        "OpenBridge",
        "Concept refs",
        "QA / provenance",
    ]
    data = [[_para(header, STYLES["HeaderCell"]) for header in headers]]
    owned_by_id = {symbol["id"]: symbol for symbol in owned_symbol_batch50.build()["symbols"]}
    for row in matrix["rows"]:
        symbol = owned_by_id[row["asset"]]
        cells = [
            _meta_text(row),
            _pdf_image(ROOT / symbol["asset"]["renders"]["day"], 1.15 * inch) + [
                _para(symbol["asset"]["canonical"], STYLES["Tiny"]),
                _para("generated-owned draft", STYLES["TinyMuted"]),
            ],
        ]
        for _label, providers in REFERENCE_GROUPS:
            cells.append(_entry_flows(_reference_entries(row, providers)))
        cells.append(_qa_text(symbol))
        data.append(cells)

    table = Table(
        data,
        colWidths=[2.15 * inch, 1.4 * inch, 1.3 * inch, 1.55 * inch, 1.35 * inch, 1.35 * inch, 1.15 * inch, 1.35 * inch, 1.55 * inch, 1.55 * inch],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20364c")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#aab3bd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]))
    story.append(table)
    COMPARE_PDF.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(COMPARE_PDF),
        pagesize=(18 * inch, 11 * inch),
        leftMargin=0.25 * inch,
        rightMargin=0.25 * inch,
        topMargin=0.25 * inch,
        bottomMargin=0.25 * inch,
    ).build(story)


def _write_html(report: dict) -> None:
    css = """
body { font-family: -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif; margin: 24px; }
h1 { margin-bottom: 6px; }
p { max-width: 1100px; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { border: 1px solid #b7c0ca; padding: 6px; vertical-align: top; font-size: 12px; overflow-wrap: anywhere; }
th { background: #20364c; color: white; }
img { max-width: 88px; max-height: 88px; display: block; margin: 0 auto 4px; }
.asset { font-weight: 700; }
.muted { color: #54606c; font-size: 10px; }
.missing { color: #8a4a00; }
"""
    headers = ["Uber list row", "Our owned SVG"] + [label for label, _providers in REFERENCE_GROUPS] + ["QA / provenance"]
    body = []
    for row in report["rows"]:
        cells = []
        s57 = row.get("s57") or {}
        s101 = row.get("s101") or {}
        brief = row.get("visual_brief") or {}
        cells.append(
            f"<div class='asset'>{html.escape(row['asset'])}</div>"
            f"<div>{html.escape(row.get('name') or '')}</div>"
            f"<div class='muted'>S-57 {html.escape(str(s57.get('object_class') or 'none'))}: {html.escape('; '.join(s57.get('conditions') or []))}</div>"
            f"<div class='muted'>S-101 {html.escape(str(s101.get('symbol_id') or s101.get('coverage') or 'none'))}</div>"
            f"<div class='muted'>Chart 1 refs: {html.escape(', '.join(row.get('chart1_mappings_refs') or []) or 'none')}</div>"
            f"<div class='muted'>Brief: {html.escape(brief.get('model_caption') or '')}</div>"
        )
        owned = row["owned"]
        cells.append(
            f"<img src='{html.escape(owned['day_render'])}' alt='owned {html.escape(row['asset'])}'>"
            f"<div class='muted'>{html.escape(owned['canonical'])}</div>"
            "<div class='muted'>generated-owned draft</div>"
        )
        for label, _providers in REFERENCE_GROUPS:
            entries = row["references"][label]
            if not entries:
                cells.append("<div class='missing'>none</div>")
                continue
            chunks = []
            for entry in entries[:2]:
                img = f"<img src='{html.escape(entry['image'])}' alt='{html.escape(entry.get('label') or label)}'>" if entry.get("image") else ""
                chunks.append(
                    f"<div>{img}<div>{html.escape(entry.get('label') or '')}</div>"
                    f"<div class='muted'>{html.escape(entry.get('status') or '')}</div></div>"
                )
            cells.append("".join(chunks))
        qa = owned["qa"]
        prov = owned["provenance"]
        cells.append(
            f"<div>semantic: {html.escape(str(qa.get('semantic_pass')))}</div>"
            f"<div>structural: {html.escape(str(qa.get('structural_pass')))}</div>"
            f"<div>visual: {html.escape(str(qa.get('visual_parity')))}</div>"
            f"<div class='muted'>origin: {html.escape(str(prov.get('origin')))}</div>"
            f"<div class='muted'>style: {html.escape(str(prov.get('style_contract_id')))}</div>"
        )
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    COMPARE_HTML.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Owned Batch50 vs Uber Source List</title>"
        f"<style>{css}</style>"
        "<h1>Owned Batch50 vs Uber Source List</h1>"
        "<p>One row per owned draft. Compare ours against the available source/provider evidence. "
        "Visual parity remains pending until the critic/repair gate.</p>"
        "<table><thead><tr>"
        + "".join(f"<th>{html.escape(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>\n"
    )


def build() -> dict:
    report, matrix = _comparison_rows()
    COMPARE_JSON.parent.mkdir(parents=True, exist_ok=True)
    COMPARE_JSON.write_text(json.dumps(report, indent=2))
    _write_html(report)
    _write_pdf(report, matrix)
    return report


def main() -> int:
    report = build()
    print(json.dumps({
        "asset_count": report["asset_count"],
        "outputs": report["outputs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
