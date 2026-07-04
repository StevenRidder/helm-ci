"""Build FORGE-41 OpenCPN/S-52 reference renders for electronic Chart 1 fixtures.

This is a fixture-oriented reference harness. It consumes the FORGE-40
electronic Chart 1 fixture contract, renders comparison-only OpenCPN/S-52
evidence from the local presentation-library resources, and writes a tracked
catalog report plus local PNGs under ignored `out/`.

The PNGs are comparison evidence only. They are not Helm canonical art.

Run:
  python3 -m forge.electronic_chart1_opencpn_reference
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import opencpn_reference_render


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
FIXTURES_JSON = CATALOG / "electronic_chart1_fixtures.json"
REFERENCE_JSON = CATALOG / "electronic_chart1_opencpn_reference.json"
REFERENCE_MD = CATALOG / "electronic_chart1_opencpn_reference.md"
OUT_DIR = ROOT / "out" / "electronic_chart1_opencpn_reference"
SCHEMA = "helm.forge.electronic_chart1_opencpn_reference.v1"
CANVAS_SIZE = 128


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe(value: str) -> str:
    return opencpn_reference_render._safe_asset_filename(value)


def _load_fixtures(path: Path = FIXTURES_JSON) -> dict[str, Any]:
    return json.loads(path.read_text())


def _palette_source() -> dict[str, Any]:
    chartsymbols = opencpn_reference_render.S52
    sheets = {
        palette: opencpn_reference_render.S52_DIR / filename
        for palette, filename in opencpn_reference_render.PALETTE_SHEETS.items()
    }
    missing = [str(path) for path in [chartsymbols, *sheets.values()] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing OpenCPN/S-52 reference inputs: {missing}")
    return {
        "chartsymbols_xml": str(chartsymbols),
        "chartsymbols_xml_sha256": _sha256(chartsymbols),
        "raster_sheets": {
            palette: {
                "path": str(path),
                "sha256": _sha256(path),
            }
            for palette, path in sheets.items()
        },
    }


def _blank_canvas() -> Image.Image:
    return Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 0))


def _fit(image: Image.Image, max_size: int = 86) -> Image.Image:
    image = image.convert("RGBA")
    if image.width <= max_size and image.height <= max_size:
        return image
    copy = image.copy()
    copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return copy


def _paste_center(canvas: Image.Image, image: Image.Image) -> None:
    image = _fit(image)
    x = (canvas.width - image.width) // 2
    y = (canvas.height - image.height) // 2
    canvas.alpha_composite(image, (x, y))


def _palette_color(color_refs: list[str], colors: dict[str, tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    for color_ref in color_refs:
        name = opencpn_reference_render._color_name(color_ref, colors)
        if name in colors:
            return colors[name]
    return colors.get("CHBLK", (0, 0, 0, 255))


def _line_style(line_refs: list[str]) -> tuple[str, tuple[int, ...]]:
    joined = " ".join(line_refs).upper()
    if "DASH" in joined:
        return "dash", (10, 7)
    if "DOTT" in joined:
        return "dot", (3, 6)
    return "solid", ()


def _draw_pattern_or_area(
    canvas: Image.Image,
    pattern_refs: list[str],
    color_refs: list[str],
    palette: str,
    colors: dict[str, tuple[int, int, int, int]],
    registry: dict[tuple[str, str], list[dict[str, Any]]],
    sheets: dict[str, Image.Image],
) -> list[str]:
    refs_used: list[str] = []
    draw = ImageDraw.Draw(canvas)
    area = (22, 24, 106, 104)
    if pattern_refs:
        asset = pattern_refs[0]
        asset_def = opencpn_reference_render._resolve_asset_def(registry, asset, "pattern")
        bitmap = asset_def.get("bitmap") if asset_def else None
        vector = asset_def.get("vector") if asset_def else None
        tile = None
        if bitmap and bitmap["width"] > 0 and bitmap["height"] > 0:
            tile = opencpn_reference_render._crop(sheets[palette], bitmap)
            refs_used.append(asset)
        elif asset_def and vector and vector.get("hpgl"):
            tile = opencpn_reference_render._render_hpgl(vector, asset_def.get("color_ref") or "", colors)
            refs_used.append(asset)
        if tile:
            tile = tile.convert("RGBA")
            for y in range(area[1], area[3], max(1, tile.height)):
                for x in range(area[0], area[2], max(1, tile.width)):
                    canvas.alpha_composite(tile, (x, y))
        else:
            draw.rectangle(area, fill=_palette_color(color_refs, colors))
    elif color_refs:
        draw.rectangle(area, fill=_palette_color(color_refs, colors))
    draw.rectangle(area, outline=_palette_color(color_refs, colors), width=2)
    return refs_used


def _draw_line(canvas: Image.Image, line_refs: list[str], color_refs: list[str], colors: dict[str, tuple[int, int, int, int]]) -> None:
    draw = ImageDraw.Draw(canvas)
    color = _palette_color(color_refs, colors)
    style, dash = _line_style(line_refs)
    points = [(18, 84), (48, 48), (78, 76), (110, 38)]
    if style == "solid":
        draw.line(points, fill=color, width=4, joint="curve")
        return
    if style == "dot":
        for x, y in points:
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
        return
    # Simple segmented dash along the representative polyline.
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy
        steps = max(abs(dx), abs(dy), 1)
        cursor = 0
        while cursor < steps:
            seg = min(dash[0], steps - cursor)
            gap = dash[1]
            p0 = (sx + dx * cursor / steps, sy + dy * cursor / steps)
            p1 = (sx + dx * (cursor + seg) / steps, sy + dy * (cursor + seg) / steps)
            draw.line([p0, p1], fill=color, width=4)
            cursor += seg + gap


def _asset_image(
    asset: str,
    kind: str,
    palette: str,
    registry: dict[tuple[str, str], list[dict[str, Any]]],
    sheets: dict[str, Image.Image],
    colors: dict[str, tuple[int, int, int, int]],
) -> tuple[Image.Image | None, dict[str, Any] | None, str | None]:
    asset_def = opencpn_reference_render._resolve_asset_def(registry, asset, kind)
    if not asset_def:
        return None, None, "missing_opencpn_asset_definition"
    bitmap = asset_def.get("bitmap")
    vector = asset_def.get("vector")
    if bitmap and bitmap["width"] > 0 and bitmap["height"] > 0:
        return opencpn_reference_render._crop(sheets[palette], bitmap), asset_def, "bitmap_crop"
    if vector and vector.get("hpgl"):
        image = opencpn_reference_render._render_hpgl(vector, asset_def.get("color_ref") or "", colors)
        if image:
            return image, asset_def, "hpgl_vector"
        return None, asset_def, "vector_render_failed"
    return None, asset_def, "missing_bitmap_or_vector"


def _draw_text(canvas: Image.Image, text_refs: list[dict[str, Any]], color_refs: list[str], colors: dict[str, tuple[int, int, int, int]]) -> None:
    if not text_refs:
        return
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    color = _palette_color(color_refs, colors)
    labels = []
    for ref in text_refs[:2]:
        template = str(ref.get("template") or ref.get("attribute") or "TXT")
        attribute = str(ref.get("attribute") or "TXT")
        if "%s" in template:
            labels.append(template.replace("%s", attribute))
        elif "%" in template:
            labels.append(template.replace("%4.1lf", "1.2"))
        else:
            labels.append(attribute if template == attribute else template)
    for idx, label in enumerate(labels):
        draw.text((12, 8 + idx * 13), label[:18], fill=color, font=font)


def _metadata(image: Image.Image, path: Path) -> dict[str, Any]:
    alpha_bbox = image.getchannel("A").getbbox()
    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "sha256": _sha256(path),
        "width": image.width,
        "height": image.height,
        "nonblank": alpha_bbox is not None,
        "alpha_bbox": list(alpha_bbox) if alpha_bbox else None,
    }


def _render_fixture_palette(
    fixture: dict[str, Any],
    palette: str,
    registry: dict[tuple[str, str], list[dict[str, Any]]],
    sheets: dict[str, Image.Image],
    palettes: dict[str, dict[str, tuple[int, int, int, int]]],
    out_dir: Path,
) -> tuple[dict[str, Any] | None, list[str], list[str], list[str]]:
    evidence = fixture["s52"]["instruction_evidence"]
    colors = palettes[palette]
    symbol_refs = evidence.get("symbol_refs") or []
    pattern_refs = evidence.get("pattern_refs") or []
    line_refs = evidence.get("line_style_refs") or []
    text_refs = evidence.get("text_refs") or []
    conditional_refs = evidence.get("conditional_refs") or []
    color_refs = evidence.get("color_refs") or []
    refs_used: list[str] = []
    render_sources: list[str] = []
    reasons: list[str] = []
    canvas = _blank_canvas()

    if pattern_refs or fixture["row_taxonomy"] == "area_fill":
        refs_used.extend(_draw_pattern_or_area(canvas, pattern_refs, color_refs, palette, colors, registry, sheets))

    if line_refs:
        _draw_line(canvas, line_refs, color_refs, colors)
        refs_used.extend(line_refs)
        render_sources.append("s52_instruction_line_sample")

    for symbol in symbol_refs[:2]:
        image, asset_def, source = _asset_image(symbol, "symbol", palette, registry, sheets, colors)
        if image:
            _paste_center(canvas, image)
            refs_used.append(symbol)
            render_sources.append(source or "asset_render")
        else:
            reasons.append(f"symbol_ref:{symbol}:{source or 'unrenderable'}")
            if asset_def:
                refs_used.append(symbol)

    if not symbol_refs and conditional_refs:
        for conditional in conditional_refs[:1]:
            image, asset_def, source = _asset_image(conditional, "conditional-procedure", palette, registry, sheets, colors)
            if image:
                _paste_center(canvas, image)
                refs_used.append(conditional)
                render_sources.append(source or "conditional_asset_render")
            elif asset_def:
                refs_used.append(conditional)
            else:
                reasons.append(f"conditional_ref:{conditional}:no_direct_asset")

    if text_refs:
        _draw_text(canvas, text_refs, color_refs, colors)
        render_sources.append("s52_text_sample")

    if canvas.getchannel("A").getbbox() is None:
        if not reasons:
            reasons.append("opencpn_reference_render:blank_or_no_renderable_instruction")
        return None, refs_used, render_sources, reasons

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{fixture['chart1_row_id']}__{_safe(fixture['row_key'])}__{palette}.png"
    out_path = out_dir / filename
    canvas.save(out_path)
    metadata = _metadata(canvas, out_path)
    metadata["palette"] = palette
    return metadata, refs_used, render_sources, reasons


def _render_fixture(
    fixture: dict[str, Any],
    registry: dict[tuple[str, str], list[dict[str, Any]]],
    sheets: dict[str, Image.Image],
    palettes: dict[str, dict[str, tuple[int, int, int, int]]],
    out_dir: Path,
    source: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    palette_outputs: dict[str, Any] = {}
    refs_used: set[str] = set()
    render_sources: set[str] = set()
    reasons: set[str] = set()
    for palette in opencpn_reference_render.PALETTE_SHEETS:
        metadata, refs, sources, palette_reasons = _render_fixture_palette(
            fixture,
            palette,
            registry,
            sheets,
            palettes,
            out_dir,
        )
        refs_used.update(refs)
        render_sources.update(source for source in sources if source)
        reasons.update(palette_reasons)
        if metadata:
            palette_outputs[palette] = metadata

    evidence = fixture["s52"]["instruction_evidence"]
    if set(palette_outputs) != set(opencpn_reference_render.PALETTE_SHEETS):
        reasons.add("opencpn_reference_render:missing_palette_output")
    if not palette_outputs:
        return None, _hard_pile_row(fixture, sorted(reasons))

    row = {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": "rendered" if not reasons else "rendered_with_warnings",
        "reason_codes": sorted(reasons),
        "palette_outputs": palette_outputs,
        "nonblank_validation": {
            "all_palette_outputs_nonblank": all(item["nonblank"] for item in palette_outputs.values()),
            "palette_count": len(palette_outputs),
        },
        "s57": fixture["s57"],
        "s52": {
            "instruction": fixture["s52"]["instruction"],
            "command_sequence": evidence.get("command_sequence") or [],
            "symbol_refs": evidence.get("symbol_refs") or [],
            "pattern_refs": evidence.get("pattern_refs") or [],
            "line_style_refs": evidence.get("line_style_refs") or [],
            "conditional_refs": evidence.get("conditional_refs") or [],
            "text_refs": evidence.get("text_refs") or [],
            "color_refs": evidence.get("color_refs") or [],
        },
        "reference_trace": {
            "render_sources": sorted(render_sources),
            "opencpn_refs_used": sorted(refs_used),
            "palette_context": list(opencpn_reference_render.PALETTE_SHEETS),
            "chartsymbols_xml_sha256": source["chartsymbols_xml_sha256"],
            "raster_sheet_sha256": {
                palette: source["raster_sheets"][palette]["sha256"]
                for palette in palette_outputs
            },
            "source_boundary": "comparison_evidence_only_not_helm_canonical_art",
        },
        "runtime_gate": fixture["runtime_gate"],
    }
    return row, None


def _hard_pile_row(fixture: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": "reference_unrenderable",
        "reason_codes": reasons or ["opencpn_reference_render:unrenderable"],
        "s57": fixture["s57"],
        "s52": fixture["s52"],
        "s101": fixture["s101"],
        "runtime_gate": fixture["runtime_gate"],
    }


def build_reference(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    fixture_payload = _load_fixtures(fixtures_path)
    if fixture_payload["schema"] != "helm.forge.electronic_chart1_fixtures.v1":
        raise ValueError(f"unexpected fixture schema: {fixture_payload['schema']}")
    registry = opencpn_reference_render._asset_registry()
    sheets = opencpn_reference_render._load_sheets()
    palettes = opencpn_reference_render._palette_colors()
    source = _palette_source()

    fixtures = fixture_payload["fixtures"][:limit]
    rendered: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []
    for fixture in fixtures:
        row, hard = _render_fixture(fixture, registry, sheets, palettes, out_dir, source)
        if row:
            rendered.append(row)
        if hard:
            hard_pile.append(hard)

    inherited_hard_pile = fixture_payload["hard_pile"] if limit is None else []
    rendered_status_counts = Counter(row["status"] for row in rendered)
    hard_reasons: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])

    produced_pngs = sum(len(row["palette_outputs"]) for row in rendered)
    status = "reference_ready" if len(rendered) + len(hard_pile) == len(fixtures) else "reference_blocked"
    return {
        "schema": SCHEMA,
        "status": status,
        "policy": {
            "source": "FORGE-40 electronic_chart1_fixtures",
            "reference_only": True,
            "canonical_helm_artwork": False,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
            "clean_room_boundary": "OpenCPN/S-52 renders are comparison evidence only and are not packaged as Helm canonical art.",
        },
        "source": {
            "fixture_schema": fixture_payload["schema"],
            "fixture_status": fixture_payload["status"],
            "fixture_source_rows": fixture_payload["summary"]["source_rows"],
            "fixture_rows": len(fixtures),
            "source_hard_pile_rows": len(inherited_hard_pile),
            "opencpn_s52": source,
        },
        "summary": {
            "fixture_rows": len(fixtures),
            "rendered_rows": len(rendered),
            "render_hard_pile_rows": len(hard_pile),
            "source_hard_pile_rows": len(inherited_hard_pile),
            "produced_reference_pngs": produced_pngs,
            "expected_reference_pngs_if_all_rendered": len(fixtures) * len(opencpn_reference_render.PALETTE_SHEETS),
            "palettes": list(opencpn_reference_render.PALETTE_SHEETS),
            "rendered_status_counts": dict(sorted(rendered_status_counts.items())),
            "hard_pile_reason_counts": dict(hard_reasons.most_common(30)),
            "row_taxonomy_counts": dict(sorted(Counter(row["row_taxonomy"] for row in rendered).items())),
        },
        "rows": rendered,
        "hard_pile": hard_pile,
        "source_hard_pile": inherited_hard_pile,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 OpenCPN/S-52 Reference Harness",
        "",
        "FORGE-41 fixture-oriented reference renders from local OpenCPN/S-52 presentation resources.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- fixture_rows: `{summary['fixture_rows']}`",
        f"- rendered_rows: `{summary['rendered_rows']}`",
        f"- render_hard_pile_rows: `{summary['render_hard_pile_rows']}`",
        f"- source_hard_pile_rows: `{summary['source_hard_pile_rows']}`",
        f"- produced_reference_pngs: `{summary['produced_reference_pngs']}`",
        "",
        "## Policy",
        "",
        "- OpenCPN/S-52 output is comparison evidence only.",
        "- These PNGs are not Helm canonical artwork and must not be packaged as owned SVG source.",
        "- Browser/UI consumers may display this backend-generated report but must not infer missing renders.",
        "- Unrenderable fixture rows remain explicit hard-pile entries with reason codes.",
        "",
        "## Rendered Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["rendered_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines.extend([
        "",
        "## Row Taxonomy Counts",
        "",
        "| Taxonomy | Count |",
        "| --- | ---: |",
    ])
    for taxonomy, count in summary["row_taxonomy_counts"].items():
        lines.append(f"| `{taxonomy}` | {count} |")
    lines.extend([
        "",
        "## Top Hard Pile Reasons",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ])
    for reason, count in summary["hard_pile_reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    return "\n".join(lines) + "\n"


def write_reference(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    json_path: Path = REFERENCE_JSON,
    markdown_path: Path = REFERENCE_MD,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    payload = build_reference(fixtures_path=fixtures_path, out_dir=out_dir, limit=limit)
    _write_json(json_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(payload))
    return {
        "status": payload["status"],
        "summary": payload["summary"],
        "json": str(json_path),
        "markdown": str(markdown_path),
        "out_dir": str(out_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_JSON)
    parser.add_argument("--json", type=Path, default=REFERENCE_JSON)
    parser.add_argument("--markdown", type=Path, default=REFERENCE_MD)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_reference(
            fixtures_path=args.fixtures,
            json_path=args.json,
            markdown_path=args.markdown,
            out_dir=args.out_dir,
            limit=args.limit,
        ),
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
