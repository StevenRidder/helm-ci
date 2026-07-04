"""Render the multi-source draft SVG pack into palette PNGs.

This is the first FORGE-15 input matrix: every generated-owned draft SVG gets
materialized as day/dusk/night PNGs so the visual judge can compare pixels
against exact Chart No.1 crops and local reference-oracle renders.

Run:  python -m forge.multisource_svg_render
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from . import multisource_svg_pack
from . import render


ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "catalog" / "multisource_svg_draft_pack.json"
OUT_DIR = ROOT / "out" / "multisource_svg_draft" / "renders"
REPORT = ROOT / "out" / "multisource_svg_draft" / "render_report.json"
README = ROOT / "out" / "multisource_svg_draft" / "README.md"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _ensure_pack() -> dict:
    if not PACK.exists():
        return multisource_svg_pack.build()
    return _read_json(PACK)


def _selected_symbols(symbols: list[dict], limit: int | None, assets: set[str] | None) -> list[dict]:
    generated = [row for row in symbols if row.get("asset_file")]
    if assets:
        generated = [row for row in generated if row["asset"] in assets]
    generated = sorted(generated, key=lambda row: row["asset"])
    return generated[:limit] if limit else generated


def _render_row(row: dict, size: int) -> tuple[list[dict], list[dict]]:
    svg_path = ROOT / row["asset_file"]
    outputs: list[dict] = []
    failures: list[dict] = []
    try:
        svg = svg_path.read_text()
    except OSError as exc:
        return [], [{
            "asset": row["asset"],
            "palette": None,
            "status": "missing_svg",
            "reason": str(exc),
            "source_svg": row["asset_file"],
        }]

    tokens = sorted(render.referenced_tokens(svg))
    for target in row["palette_targets"]:
        palette = target["palette"]
        out_path = ROOT / target["planned_render"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            png = render.rasterize(svg, target["css_variables"], size=size)
            out_path.write_bytes(png)
            outputs.append({
                "asset": row["asset"],
                "palette": palette,
                "status": "rendered",
                "source_svg": row["asset_file"],
                "render": str(out_path.relative_to(ROOT)),
                "bytes": len(png),
                "size_px": size,
                "css_tokens": tokens,
            })
        except Exception as exc:  # noqa: BLE001 - fail-loud report keeps the bad row auditable.
            failures.append({
                "asset": row["asset"],
                "palette": palette,
                "status": "render_failed",
                "source_svg": row["asset_file"],
                "planned_render": target["planned_render"],
                "reason": f"{type(exc).__name__}: {exc}",
                "css_tokens": tokens,
            })
    return outputs, failures


def build(limit: int | None = None, assets: set[str] | None = None, size: int = 128) -> dict:
    pack = _ensure_pack()
    selected = _selected_symbols(pack["symbols"], limit=limit, assets=assets)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    hard_pile: list[dict] = []
    for symbol in selected:
        outputs, failures = _render_row(symbol, size=size)
        rows.extend(outputs)
        hard_pile.extend(failures)

    palette_counts = Counter(row["palette"] for row in rows)
    asset_failures = Counter(row["asset"] for row in hard_pile)
    status = "pass" if not hard_pile else "review_required"
    if limit or assets:
        status = f"{status}_explicit_subset"

    result = {
        "schema_version": 1,
        "generator": "iconforge-multisource-svg-render",
        "status": status,
        "source_pack": "catalog/multisource_svg_draft_pack.json",
        "summary": {
            "pack_symbols": len(pack["symbols"]),
            "generated_symbol_svgs": pack["summary"]["generated_symbol_svgs"],
            "selected_symbols": len(selected),
            "rendered_pngs": len(rows),
            "expected_pngs": len(selected) * len(multisource_svg_pack.PALETTES),
            "hard_pile_entries": len(hard_pile),
            "palettes": list(multisource_svg_pack.PALETTES),
            "palette_counts": dict(sorted(palette_counts.items())),
            "failed_assets": dict(sorted(asset_failures.items())),
            "size_px": size,
            "limits": [
                "Rendered PNGs are generated from Helm-owned draft SVGs, not external artwork.",
                "A subset status is only produced when explicitly requested by limit/assets.",
                "Visual approval remains pending until a deterministic verifier and visual judge pass.",
            ],
        },
        "rows": rows,
        "hard_pile": hard_pile,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_md(result)
    return result


def _write_md(result: dict) -> None:
    summary = result["summary"]
    lines = [
        "# Multi-Source SVG Render Matrix",
        "",
        "Palette PNG renders generated from the Helm-owned draft SVG pack.",
        "",
        "## Summary",
        "",
        f"- Status: `{result['status']}`",
        f"- Selected symbols: {summary['selected_symbols']}",
        f"- Rendered PNGs: {summary['rendered_pngs']}",
        f"- Expected PNGs: {summary['expected_pngs']}",
        f"- Hard-pile entries: {summary['hard_pile_entries']}",
        f"- Size: {summary['size_px']} px",
        "",
        "## Palette Counts",
        "",
    ]
    for palette, count in summary["palette_counts"].items():
        lines.append(f"- `{palette}`: {count}")
    lines.extend([
        "",
        "These renders are repair inputs only; they are not visual approvals.",
        "",
    ])
    README.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="explicit render subset for smoke runs")
    parser.add_argument("--asset", action="append", default=None, help="asset id to render; repeatable")
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args(argv)
    result = build(limit=args.limit, assets=set(args.asset) if args.asset else None, size=args.size)
    summary = result["summary"]
    print(f"multisource render: {result['status']}")
    print(f"selected symbols: {summary['selected_symbols']}")
    print(f"rendered PNGs: {summary['rendered_pngs']}/{summary['expected_pngs']}")
    print(f"hard pile: {summary['hard_pile_entries']}")
    print(f"report: {REPORT}")
    return 0 if summary["hard_pile_entries"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
