"""Build FORGE-42 Helm S-57/S-52 renders for electronic Chart 1 fixtures.

This harness consumes the FORGE-40 electronic Chart 1 fixtures and renders them
through Helm-owned assets plus backend DB style/colour authority. It is a proof
artifact only: rows remain fail-closed for runtime export until later promotion
gates pass.

Run:
  python3 -m forge.electronic_chart1_helm_s57_render
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import render, style_contract, symbol_recipe_contract


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent
CATALOG = ROOT / "catalog"
FIXTURES_JSON = CATALOG / "electronic_chart1_fixtures.json"
RECIPE_JSON = CATALOG / "helm_symbol_recipe_contract.json"
HELM_S57_JSON = CATALOG / "electronic_chart1_helm_s57_render.json"
HELM_S57_MD = CATALOG / "electronic_chart1_helm_s57_render.md"
OUT_DIR = ROOT / "out" / "electronic_chart1_helm_s57_render"
SCHEMA = "helm.forge.electronic_chart1_helm_s57_render.v1"
CANVAS_SIZE = 128

S52_TO_HELM_COLOR = {
    **symbol_recipe_contract.COLOUR_TOKEN_ALIASES,
    "ADINF": "yellow",
    "APLRT": "red",
    "CURSR": "orange",
    "DEPIT": "blue",
    "DNGHL": "red",
    "NINFO": "yellow",
    "TRFCF": "magenta",
}


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


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def _safe(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value).strip("_")
    return safe or "unnamed"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _recipe_index(path: Path = RECIPE_JSON) -> dict[str, list[dict[str, Any]]]:
    payload = _load_json(path)
    index: dict[str, list[dict[str, Any]]] = {}
    for row in payload["rows"]:
        symbol_id = row.get("symbol_id")
        if symbol_id:
            index.setdefault(symbol_id, []).append(row)
    return index


def _select_recipe(fixture: dict[str, Any], recipes: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    refs = _renderable_refs(fixture)
    for ref in refs:
        rows = recipes.get(ref) or []
        if not rows:
            continue
        ready = [row for row in rows if row.get("helm_symbol_recipe_status") == "recipe_ready"]
        return (ready or rows)[0]
    return None


def _renderable_refs(fixture: dict[str, Any]) -> list[str]:
    evidence = fixture["s52"]["instruction_evidence"]
    refs: list[str] = []
    refs.extend(evidence.get("symbol_refs") or [])
    refs.extend(evidence.get("pattern_refs") or [])
    # Conditional procedure ids are only direct render refs when Helm has a
    # canonical art path for the fixture; otherwise they must stay hard-pile.
    if fixture.get("helm", {}).get("art_path"):
        refs.extend(evidence.get("conditional_refs") or [])
    return list(dict.fromkeys(refs))


def _palette(name: str) -> dict[str, str]:
    base = dict(style_contract.OPENBRIDGE_NAV_PALETTES[name])
    base.setdefault("foreground", base["black"])
    base.setdefault("background", base["white"])
    return base


def _token_for_color_ref(color_ref: str) -> str | None:
    raw = str(color_ref or "").strip().strip("'")
    return S52_TO_HELM_COLOR.get(raw) or S52_TO_HELM_COLOR.get(raw.upper()) or S52_TO_HELM_COLOR.get(raw.lower())


def _tokens_for_refs(color_refs: list[str]) -> tuple[list[str], list[str]]:
    tokens: list[str] = []
    failures: list[str] = []
    supported = set(style_contract.OPENBRIDGE_NAV_PALETTES["day"])
    for color_ref in color_refs:
        token = _token_for_color_ref(color_ref)
        if not token:
            failures.append(f"s52_colour_ref:{color_ref}:unmapped")
            continue
        if token not in supported:
            failures.append(f"s52_colour_ref:{color_ref}:unsupported_token:{token}")
            continue
        tokens.append(token)
    return tokens, failures


def _primary_token(fixture: dict[str, Any], recipe: dict[str, Any] | None) -> tuple[str | None, list[str], str]:
    evidence = fixture["s52"]["instruction_evidence"]
    tokens, failures = _tokens_for_refs(evidence.get("color_refs") or [])
    if tokens:
        # Last S-52 colour ref often belongs to the line sample; use it first
        # for strokes, but report the whole token sequence in the trace.
        return tokens[-1], failures, "s52_instruction_color_refs"
    recipe_tokens = []
    if recipe:
        recipe_tokens = recipe.get("helm_symbol_recipe", {}).get("color_tokens") or []
    if recipe_tokens:
        return recipe_tokens[0], failures, "helm_symbol_recipe.color_tokens"
    authority = fixture.get("helm", {}).get("expected_authority", {}).get("colour", {}).get("helm_colour_authority", {})
    authority_tokens = authority.get("colour_sequence") or []
    if authority_tokens:
        return authority_tokens[0], failures, "fixture.helm_colour_authority"
    return None, failures, "missing"


def _blank_canvas() -> Image.Image:
    return Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 0))


def _png_to_image(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _fit(image: Image.Image, max_size: int = 86) -> Image.Image:
    if image.width <= max_size and image.height <= max_size:
        return image
    copy = image.copy()
    copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return copy


def _paste_center(canvas: Image.Image, image: Image.Image) -> None:
    image = _fit(image)
    canvas.alpha_composite(image, ((canvas.width - image.width) // 2, (canvas.height - image.height) // 2))


def _draw_area(
    canvas: Image.Image,
    palette: dict[str, str],
    token: str | None,
    pattern_refs: list[str],
    pattern_image: Image.Image | None = None,
) -> bool:
    if not token and not pattern_refs and pattern_image is None:
        return False
    draw = ImageDraw.Draw(canvas)
    fill = palette[token or "white"]
    area = (22, 24, 106, 104)
    draw.rectangle(area, fill=fill, outline=palette["black"], width=2)
    if pattern_image is not None:
        tile = _fit(pattern_image, max_size=28)
        for y in range(area[1] + 8, area[3] - 8, 28):
            for x in range(area[0] + 8, area[2] - 8, 28):
                canvas.alpha_composite(tile, (x, y))
    elif pattern_refs:
        # Explicit Helm synthetic pattern sample when no canonical tile can be
        # rasterized; still area-shaped, not a point-icon placeholder.
        for x in range(area[0] + 8, area[2], 16):
            draw.line([(x, area[1] + 4), (x - 16, area[3] - 4)], fill=palette["black"], width=2)
    return True


def _draw_line(canvas: Image.Image, palette: dict[str, str], token: str | None, line_refs: list[str]) -> bool:
    if not line_refs:
        return False
    if not token:
        return False
    draw = ImageDraw.Draw(canvas)
    color = palette[token]
    points = [(18, 84), (48, 48), (78, 76), (110, 38)]
    joined = " ".join(line_refs).upper()
    if "DASH" not in joined and "DOTT" not in joined:
        draw.line(points, fill=color, width=4, joint="curve")
        return True
    if "DOTT" in joined:
        for x, y in points:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
        return True
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy
        steps = max(abs(dx), abs(dy), 1)
        cursor = 0
        while cursor < steps:
            seg = min(10, steps - cursor)
            p0 = (sx + dx * cursor / steps, sy + dy * cursor / steps)
            p1 = (sx + dx * (cursor + seg) / steps, sy + dy * (cursor + seg) / steps)
            draw.line([p0, p1], fill=color, width=4)
            cursor += seg + 7
    return True


def _draw_text(canvas: Image.Image, palette: dict[str, str], token: str | None, text_refs: list[dict[str, Any]]) -> bool:
    if not text_refs:
        return False
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    color = palette[token or "black"]
    for idx, ref in enumerate(text_refs[:2]):
        template = str(ref.get("template") or ref.get("attribute") or "TXT")
        attribute = str(ref.get("attribute") or "TXT")
        if "%s" in template:
            label = template.replace("%s", attribute)
        elif "%4.1lf" in template:
            label = template.replace("%4.1lf", "1.2")
        else:
            label = attribute if template == attribute else template
        draw.text((12, 8 + idx * 13), label[:18], fill=color, font=font)
    return True


def _render_svg_asset(fixture: dict[str, Any], palette: dict[str, str]) -> tuple[Image.Image | None, list[str]]:
    art_path = fixture.get("helm", {}).get("art_path")
    if not art_path:
        return None, ["helm_art_path:missing"]
    path = ROOT / art_path
    if not path.exists():
        return None, [f"helm_art_path:not_found:{art_path}"]
    try:
        svg = path.read_text()
        png = render.rasterize(svg, palette, size=CANVAS_SIZE)
        return _png_to_image(png), []
    except Exception as exc:  # noqa: BLE001 - report exact row failure.
        return None, [f"helm_svg_render_failed:{type(exc).__name__}:{exc}"]


def _metadata(image: Image.Image, path: Path) -> dict[str, Any]:
    bbox = image.getchannel("A").getbbox()
    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "sha256": _sha256(path),
        "width": image.width,
        "height": image.height,
        "nonblank": bbox is not None,
        "alpha_bbox": list(bbox) if bbox else None,
    }


def _render_fixture_palette(
    fixture: dict[str, Any],
    recipe: dict[str, Any] | None,
    palette_name: str,
    out_dir: Path,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    palette = _palette(palette_name)
    evidence = fixture["s52"]["instruction_evidence"]
    line_refs = evidence.get("line_style_refs") or []
    if not line_refs:
        line_refs = fixture.get("helm", {}).get("expected_authority", {}).get("pattern", {}).get("s52_line_style_refs") or []
    pattern_refs = evidence.get("pattern_refs") or []
    text_refs = evidence.get("text_refs") or []
    symbol_refs = evidence.get("symbol_refs") or []
    command_sequence = evidence.get("command_sequence") or []
    token, color_failures, color_source = _primary_token(fixture, recipe)
    reasons = list(color_failures)
    render_sources: list[str] = []
    canvas = _blank_canvas()
    asset_image = None
    asset_reasons: list[str] = []
    if fixture.get("helm", {}).get("art_path"):
        asset_image, asset_reasons = _render_svg_asset(fixture, palette)

    if "AC" in command_sequence or pattern_refs or fixture["row_taxonomy"] == "area_fill":
        pattern_image = asset_image if pattern_refs else None
        if pattern_refs:
            reasons.extend(asset_reasons)
        if _draw_area(canvas, palette, token, pattern_refs, pattern_image=pattern_image):
            render_sources.append("helm_s57_area_sample")
            if pattern_image is not None:
                render_sources.append("helm_canonical_svg_pattern_tile")
        elif fixture["row_taxonomy"] == "area_fill":
            reasons.append("helm_area_sample:missing_colour_or_pattern_authority")

    if line_refs:
        if _draw_line(canvas, palette, token, line_refs):
            render_sources.append("helm_s57_line_sample")
        else:
            reasons.append("helm_line_sample:missing_colour_authority")

    if text_refs:
        if _draw_text(canvas, palette, token, text_refs):
            render_sources.append("helm_s57_text_sample")
        else:
            reasons.append("helm_text_sample:render_failed")

    if symbol_refs or (fixture["row_taxonomy"] == "point_symbol" and fixture.get("helm", {}).get("art_path")):
        reasons.extend(asset_reasons)
        if asset_image:
            _paste_center(canvas, asset_image)
            render_sources.append("helm_canonical_svg")

    if canvas.getchannel("A").getbbox() is None:
        if not reasons:
            reasons.append("helm_s57_render:blank_or_no_renderable_instruction")
        return None, reasons, render_sources

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{fixture['chart1_row_id']}__{_safe(fixture['row_key'])}__{palette_name}.png"
    out_path = out_dir / filename
    canvas.save(out_path)
    metadata = _metadata(canvas, out_path)
    metadata["palette"] = palette_name
    metadata["color_source"] = color_source
    metadata["primary_color_token"] = token
    return metadata, reasons, render_sources


def _hard_pile_row(fixture: dict[str, Any], recipe: dict[str, Any] | None, reasons: list[str]) -> dict[str, Any]:
    return {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": "helm_s57_unrenderable",
        "reason_codes": sorted(set(reasons or ["helm_s57_render:unrenderable"])),
        "s57": fixture["s57"],
        "s52": fixture["s52"],
        "s101": fixture["s101"],
        "helm": fixture["helm"],
        "recipe_trace": _recipe_trace(recipe),
        "runtime_gate": fixture["runtime_gate"],
    }


def _recipe_trace(recipe: dict[str, Any] | None) -> dict[str, Any]:
    if not recipe:
        return {
            "status": "missing",
            "symbol_id": None,
            "helm_catalog_id": None,
            "shape_family": None,
            "color_tokens": [],
            "pattern_token": None,
            "reason_codes": ["helm_symbol_recipe:missing"],
        }
    body = recipe.get("helm_symbol_recipe") or {}
    return {
        "status": recipe.get("helm_symbol_recipe_status"),
        "symbol_id": recipe.get("symbol_id"),
        "helm_catalog_id": recipe.get("helm_catalog_id"),
        "shape_family": body.get("shape_family"),
        "color_tokens": body.get("color_tokens") or [],
        "pattern_token": body.get("pattern_token"),
        "reason_codes": body.get("reason_codes") or [],
        "style_contract_id": body.get("style_contract_id"),
    }


def _render_fixture(
    fixture: dict[str, Any],
    recipe: dict[str, Any] | None,
    out_dir: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    palette_outputs: dict[str, Any] = {}
    reasons: set[str] = set()
    render_sources: set[str] = set()
    for palette_name in style_contract.OPENBRIDGE_NAV_PALETTES:
        metadata, palette_reasons, sources = _render_fixture_palette(fixture, recipe, palette_name, out_dir)
        reasons.update(palette_reasons)
        render_sources.update(sources)
        if metadata:
            palette_outputs[palette_name] = metadata

    if set(palette_outputs) != set(style_contract.OPENBRIDGE_NAV_PALETTES):
        reasons.add("helm_s57_render:missing_palette_output")
    if not palette_outputs:
        return None, _hard_pile_row(fixture, recipe, sorted(reasons))

    status = "rendered" if not reasons else "rendered_with_warnings"
    row = {
        "fixture_id": fixture["fixture_id"],
        "s52_lookup_id": fixture["s52_lookup_id"],
        "row_key": fixture["row_key"],
        "chart1_row_id": fixture["chart1_row_id"],
        "row_taxonomy": fixture["row_taxonomy"],
        "status": status,
        "reason_codes": sorted(reasons),
        "palette_outputs": palette_outputs,
        "nonblank_validation": {
            "all_palette_outputs_nonblank": all(item["nonblank"] for item in palette_outputs.values()),
            "palette_count": len(palette_outputs),
        },
        "s57": fixture["s57"],
        "s52": {
            "instruction": fixture["s52"]["instruction"],
            "instruction_evidence": fixture["s52"]["instruction_evidence"],
        },
        "helm_trace": {
            "art_path": fixture.get("helm", {}).get("art_path"),
            "art_status": fixture.get("helm", {}).get("art_status"),
            "render_sources": sorted(render_sources),
            "recipe": _recipe_trace(recipe),
            "expected_authority": fixture.get("helm", {}).get("expected_authority") or {},
            "style_contract": style_contract.OPENBRIDGE_STYLE_ID,
            "palette_version": "helm_palette_v1",
            "source_boundary": "helm_owned_candidate_render_not_runtime_promotion",
        },
        "runtime_gate": fixture["runtime_gate"],
    }
    return row, None


def build_render(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    recipe_path: Path = RECIPE_JSON,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    fixture_payload = _load_json(fixtures_path)
    if fixture_payload["schema"] != "helm.forge.electronic_chart1_fixtures.v1":
        raise ValueError(f"unexpected fixture schema: {fixture_payload['schema']}")
    recipes = _recipe_index(recipe_path)
    fixtures = fixture_payload["fixtures"][:limit]
    rendered: list[dict[str, Any]] = []
    hard_pile: list[dict[str, Any]] = []
    for fixture in fixtures:
        recipe = _select_recipe(fixture, recipes)
        row, hard = _render_fixture(fixture, recipe, out_dir)
        if row:
            rendered.append(row)
        if hard:
            hard_pile.append(hard)

    hard_reasons: Counter[str] = Counter()
    for row in hard_pile:
        hard_reasons.update(row["reason_codes"])
    rendered_status_counts = Counter(row["status"] for row in rendered)
    produced_pngs = sum(len(row["palette_outputs"]) for row in rendered)
    inherited_hard_pile = fixture_payload["hard_pile"] if limit is None else []
    return {
        "schema": SCHEMA,
        "status": "helm_s57_render_ready" if len(rendered) + len(hard_pile) == len(fixtures) else "helm_s57_render_blocked",
        "policy": {
            "source": "FORGE-40 electronic_chart1_fixtures + Helm-owned canonical SVG/art authority",
            "backend_generated": True,
            "canonical_helm_artwork_only": True,
            "browser_business_logic_allowed": False,
            "static_json_fallback_allowed": False,
            "runtime_promotion_allowed": False,
            "clean_room_boundary": "Helm-owned candidate renders only; no OpenCPN/IHO artwork is used as Helm art.",
        },
        "source": {
            "fixture_schema": fixture_payload["schema"],
            "fixture_status": fixture_payload["status"],
            "fixture_rows": len(fixtures),
            "fixture_source_rows": fixture_payload["summary"]["source_rows"],
            "source_hard_pile_rows": len(inherited_hard_pile),
            "recipe_contract": _display_path(recipe_path),
            "recipe_contract_sha256": _sha256(recipe_path),
            "palette_contract": "forge.style_contract.OPENBRIDGE_NAV_PALETTES",
        },
        "summary": {
            "fixture_rows": len(fixtures),
            "rendered_rows": len(rendered),
            "render_hard_pile_rows": len(hard_pile),
            "source_hard_pile_rows": len(inherited_hard_pile),
            "produced_candidate_pngs": produced_pngs,
            "expected_candidate_pngs_if_all_rendered": len(fixtures) * len(style_contract.OPENBRIDGE_NAV_PALETTES),
            "palettes": list(style_contract.OPENBRIDGE_NAV_PALETTES),
            "rendered_status_counts": dict(sorted(rendered_status_counts.items())),
            "hard_pile_reason_counts": dict(hard_reasons.most_common(30)),
            "row_taxonomy_counts": dict(sorted(Counter(row["row_taxonomy"] for row in rendered).items())),
            "recipe_status_counts": dict(sorted(Counter(row["helm_trace"]["recipe"]["status"] for row in rendered).items())),
        },
        "rows": rendered,
        "hard_pile": hard_pile,
        "source_hard_pile": inherited_hard_pile,
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Electronic Chart 1 Helm S-57 Render Harness",
        "",
        "FORGE-42 Helm-owned candidate renders from electronic Chart 1 fixture rows.",
        "",
        f"- schema: `{payload['schema']}`",
        f"- status: `{payload['status']}`",
        f"- fixture_rows: `{summary['fixture_rows']}`",
        f"- rendered_rows: `{summary['rendered_rows']}`",
        f"- render_hard_pile_rows: `{summary['render_hard_pile_rows']}`",
        f"- source_hard_pile_rows: `{summary['source_hard_pile_rows']}`",
        f"- produced_candidate_pngs: `{summary['produced_candidate_pngs']}`",
        "",
        "## Policy",
        "",
        "- Candidate renders are generated from backend fixture rows and Helm-owned canonical art/style authority.",
        "- Browser/UI consumers may display this report but must not infer missing render behavior.",
        "- Rows remain fail-closed and are not runtime-promoted by this task.",
        "- Missing art or invalid colour authority remains explicit in hard-pile or warning reason codes.",
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
        "## Recipe Status Counts",
        "",
        "| Recipe Status | Count |",
        "| --- | ---: |",
    ])
    for status, count in summary["recipe_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
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


def write_render(
    *,
    fixtures_path: Path = FIXTURES_JSON,
    recipe_path: Path = RECIPE_JSON,
    json_path: Path = HELM_S57_JSON,
    markdown_path: Path = HELM_S57_MD,
    out_dir: Path = OUT_DIR,
    limit: int | None = None,
) -> dict[str, Any]:
    payload = build_render(fixtures_path=fixtures_path, recipe_path=recipe_path, out_dir=out_dir, limit=limit)
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
    parser.add_argument("--recipes", type=Path, default=RECIPE_JSON)
    parser.add_argument("--json", type=Path, default=HELM_S57_JSON)
    parser.add_argument("--markdown", type=Path, default=HELM_S57_MD)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    print(json.dumps(
        write_render(
            fixtures_path=args.fixtures,
            recipe_path=args.recipes,
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
