"""Run the controlled full-library Icon Forge catalog pass.

FORGE-11 scales the proven scale125 pipeline to every unique presentation asset
referenced by local chartsymbols.xml. This is a controlled run: it reports
coverage and hard-pile counts, keeps provenance hashes, and does not claim final
publish readiness.

Run:  python -m forge.full_catalog_run
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from PIL import Image

from . import contact, render, scale125_generate, scale125_select, scale125_verify, verify


ROOT = Path(__file__).resolve().parent.parent
CATALOG_OUT = ROOT / "pilots" / "full_catalog.json"
OUT = ROOT / "out" / "full_catalog"
SVG_OUT = ROOT / "generated" / "full_catalog" / "compose"
ATLAS_OUT = OUT / "atlas"
PROVENANCE_OUT = OUT / "provenance"
PALETTES = ["day", "dusk", "night"]
CELL = 96
COLS = 8


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_hashes(paths: list[Path]) -> dict[str, str]:
    return {_rel(path): _sha256(path) for path in paths if path.exists()}


def _styles() -> dict[str, scale125_generate.StylePack]:
    return scale125_generate._styles()


def _select_catalog() -> dict:
    root = scale125_select.ET.parse(scale125_select.S52).getroot()
    candidates = scale125_select._candidates(root)
    by_asset = {}
    for candidate in sorted(candidates, key=scale125_select._score):
        by_asset.setdefault(candidate.asset.upper(), candidate)
    entries = [asdict(c) for c in sorted(by_asset.values(), key=lambda c: c.asset)]

    family_counts = {}
    kind_counts = {}
    for entry in entries:
        family_counts[entry["family"]] = family_counts.get(entry["family"], 0) + 1
        kind_counts[entry["asset_kind"]] = kind_counts.get(entry["asset_kind"], 0) + 1

    catalog = {
        "id": "full_catalog",
        "title": "Full available Icon Forge presentation asset catalog",
        "source": str(scale125_select.S52),
        "candidate_rows": len(candidates),
        "selected_assets": len(entries),
        "family_counts": family_counts,
        "asset_kind_counts": kind_counts,
        "selection_rules": [
            "Select every unique presentation asset referenced by chartsymbols.xml lookup rows.",
            "Deduplicate by asset name; keep the highest-scoring provenance row per asset.",
            "Carry lookup provenance, conditions, instruction, description, family, and stress reasons.",
            "This is a controlled run; ambiguous outputs remain reviewable and are not final publish claims.",
        ],
        "expected_outputs": {
            "styles": len(_styles()),
            "palettes": len(PALETTES),
            "svg_outputs": len(entries) * len(_styles()),
            "png_outputs": len(entries) * len(_styles()) * len(PALETTES),
        },
        "entries": entries,
    }
    CATALOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_OUT.write_text(json.dumps(catalog, indent=2))
    return catalog


def _generate(catalog: dict) -> tuple[list[dict], list[dict]]:
    styles = _styles()
    rows, report, hard_pile = [], [], []
    (OUT / "renders").mkdir(parents=True, exist_ok=True)
    for entry in catalog["entries"]:
        spec = scale125_generate._spec(entry)
        for style in styles.values():
            svg = scale125_generate.compose(entry, style)
            svg_dir = SVG_OUT / style.id
            svg_dir.mkdir(parents=True, exist_ok=True)
            svg_path = svg_dir / f"{scale125_generate._slug(entry['asset'])}.svg"
            svg_path.write_text(svg)

            criteria = verify.structural(svg, spec, style, style.palettes["day"])
            ok = all(c.passed for c in criteria)
            if not ok:
                hard_pile.append({
                    "asset": entry["asset"],
                    "style": style.id,
                    "case": "structural",
                    "reason_codes": [c.name for c in criteria if not c.passed],
                    "criteria": [c.__dict__ for c in criteria],
                })

            pngs = {}
            for palette in PALETTES:
                png = render.rasterize(svg, style.palettes[palette], size=128)
                png_path = OUT / "renders" / f"{scale125_generate._slug(entry['asset'])}_{style.id}_{palette}.png"
                png_path.write_bytes(png)
                pngs[palette] = str(png_path)

            rows.append({"label": entry["asset"], "style": style.id, "pngs": pngs, "ok": ok})
            report.append({
                "asset": entry["asset"],
                "style": style.id,
                "asset_kind": entry["asset_kind"],
                "family": entry["family"],
                "svg": str(svg_path),
                "structural_pass": ok,
                "criteria": [c.__dict__ for c in criteria],
                "s52": {
                    "object_class": entry["object_class"],
                    "lookup_id": entry["lookup_id"],
                    "rcid": entry["rcid"],
                    "conditions": entry["conditions"],
                    "instruction": entry["instruction"],
                },
            })

    contact.build_contact(rows, PALETTES, cell=72, out_path=OUT / "contact_sheet.png")
    structural = {
        "status": "pass" if not hard_pile else "fail",
        "assets": catalog["selected_assets"],
        "styles": len(styles),
        "svg_outputs": len(report),
        "png_outputs": len(report) * len(PALETTES),
        "structural_pass": len(report) - len(hard_pile),
        "structural_total": len(report),
        "hard_pile_entries": len(hard_pile),
        "rows": report,
    }
    (OUT / "report.json").write_text(json.dumps(structural, indent=2))
    (OUT / "hard_pile.json").write_text(json.dumps(hard_pile, indent=2))
    return report, hard_pile


def _semantic(catalog: dict) -> tuple[dict, list[dict]]:
    styles = _styles()
    rows = []
    hard_pile = []
    for entry in catalog["entries"]:
        for style in styles.values():
            svg_path = SVG_OUT / style.id / f"{scale125_generate._slug(entry['asset'])}.svg"
            svg = svg_path.read_text()
            valid = scale125_verify._evaluate(entry, style, svg, "valid", "accept")
            rows.append(valid)
            if valid.observed == "reject":
                hard_pile.append(asdict(valid))

            case, bad_svg = scale125_verify._broken_svg(entry, svg)
            broken = scale125_verify._evaluate(entry, style, bad_svg, case, "reject")
            rows.append(broken)
            if broken.observed == "reject":
                hard_pile.append(asdict(broken))

    valid_rows = [r for r in rows if r.case == "valid"]
    broken_rows = [r for r in rows if r.case.startswith("broken:")]
    family_coverage = {}
    for family in sorted({e["family"] for e in catalog["entries"]}):
        family_coverage[family] = {
            "valid_cases": sum(1 for r in valid_rows if r.family == family),
            "broken_cases": sum(1 for r in broken_rows if r.family == family),
            "valid_accepts": sum(1 for r in valid_rows if r.family == family and r.observed == "accept"),
            "broken_rejects": sum(1 for r in broken_rows if r.family == family and r.observed == "reject"),
        }

    report = {
        "status": "pass" if all(r.passed for r in rows) else "review_required",
        "assets": catalog["selected_assets"],
        "styles": len(styles),
        "fixture_valid_cases": len(valid_rows),
        "valid_accepts": sum(1 for r in valid_rows if r.observed == "accept"),
        "valid_total": len(valid_rows),
        "broken_rejects": sum(1 for r in broken_rows if r.observed == "reject"),
        "broken_total": len(broken_rows),
        "family_coverage": family_coverage,
        "hard_pile_entries": len(hard_pile),
        "rows": [asdict(r) for r in rows],
    }
    (OUT / "semantic_report.json").write_text(json.dumps(report, indent=2))
    (OUT / "semantic_hard_pile.json").write_text(json.dumps(hard_pile, indent=2))
    return report, hard_pile


def _manifest_kind(asset_kind: str) -> str:
    if asset_kind == "line-style":
        return "line"
    if asset_kind == "pattern":
        return "pattern"
    return "symbol"


def _dash(entry: dict) -> list[int]:
    asset = entry["asset"].upper()
    if entry["asset_kind"] != "line-style":
        return []
    if "DOTT" in asset:
        return [1, 5]
    if "DASH" in asset:
        return [5, 4]
    return []


def _uv(rect: list[int], width: int, height: int) -> list[float]:
    x, y, w, h = rect
    return [
        round(x / width, 6),
        round(y / height, 6),
        round((x + w) / width, 6),
        round((y + h) / height, 6),
    ]


def _dump_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, separators=(",", ":")) + "\n")


def _accepted_valid_rows() -> dict[tuple[str, str], dict]:
    report = json.loads((OUT / "semantic_report.json").read_text())
    rows = {}
    for row in report["rows"]:
        if row["case"] == "valid" and row["observed"] == "accept" and row["passed"]:
            rows[(row["asset"], row["style"])] = row
    return rows


def _build_atlas(catalog: dict) -> tuple[dict, list[dict]]:
    styles = sorted(_styles())
    accepted = _accepted_valid_rows()
    packable = [entry for entry in catalog["entries"]
                if all((entry["asset"], style) in accepted for style in styles)]
    ATLAS_OUT.mkdir(parents=True, exist_ok=True)
    atlases, manifest_entries = [], []
    for style in styles:
        for palette in PALETTES:
            rows = (len(packable) + COLS - 1) // COLS
            width, height = COLS * CELL, max(1, rows) * CELL
            sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            image_name = f"s52_full_catalog_{style}_{palette}.png"
            sheet_entries = []
            for i, entry in enumerate(packable):
                x, y = (i % COLS) * CELL, (i // COLS) * CELL
                png_path = OUT / "renders" / f"{scale125_generate._slug(entry['asset'])}_{style}_{palette}.png"
                img = Image.open(png_path).convert("RGBA").resize((CELL, CELL))
                sheet.paste(img, (x, y), img)
                anchor = scale125_generate._spec(entry).invariants.anchor
                rect = [x, y, CELL, CELL]
                row = accepted[(entry["asset"], style)]
                manifest_entry = {
                    "name": entry["asset"],
                    "kind": _manifest_kind(entry["asset_kind"]),
                    "palette": palette,
                    "style": style,
                    "atlas": image_name,
                    "pixel_rect": rect,
                    "uv": _uv(rect, width, height),
                    "anchor": [round(anchor[0] * CELL), round(anchor[1] * CELL)],
                    "repeat": [0, 0],
                    "dash": _dash(entry),
                    "color": [0, 0, 0],
                    "anchor_unit": {"x": anchor[0], "y": anchor[1]},
                    "provenance": {
                        "source": "iconforge-full-catalog",
                        "catalog": "pilots/full_catalog.json",
                        "object_class": entry["object_class"],
                        "lookup_id": entry["lookup_id"],
                        "rcid": entry["rcid"],
                        "conditions": entry["conditions"],
                        "qa": {
                            "structural_pass": True,
                            "semantic_passed": row["passed"],
                            "semantic_observed": row["observed"],
                            "reason_codes": row["reason_codes"],
                        },
                    },
                }
                manifest_entries.append(manifest_entry)
                sheet_entries.append(manifest_entry)
            sheet.save(ATLAS_OUT / image_name)
            atlas = {
                "kind": "presentation",
                "style": style,
                "palette": palette,
                "image": image_name,
                "format": "png",
                "width": width,
                "height": height,
                "cell": CELL,
                "entry_count": len(packable),
            }
            atlases.append(atlas)
            _dump_manifest(ATLAS_OUT / f"manifest_full_catalog_{style}_{palette}.json", {
                "schema_version": 1,
                "generator": "iconforge-full-catalog-atlas",
                "style": style,
                "palette": palette,
                "atlas": atlas,
                "entries": sheet_entries,
            })

    manifest = {
        "schema_version": 1,
        "generator": "iconforge-full-catalog-atlas",
        "source": {
            "catalog": "pilots/full_catalog.json",
            "semantic_report": "out/full_catalog/semantic_report.json",
            "structural_report": "out/full_catalog/report.json",
        },
        "styles": styles,
        "palettes": PALETTES,
        "cell": CELL,
        "atlases": atlases,
        "entries": manifest_entries,
    }
    _dump_manifest(ATLAS_OUT / "helm_s52_atlas_full_catalog.json", manifest)
    for style in styles:
        style_manifest = dict(manifest)
        style_manifest["styles"] = [style]
        style_manifest["atlases"] = [a for a in atlases if a["style"] == style]
        style_manifest["entries"] = [e for e in manifest_entries if e["style"] == style]
        _dump_manifest(ATLAS_OUT / f"helm_s52_atlas_full_catalog_{style}.json", style_manifest)
    return manifest, packable


def _provenance(catalog: dict, summary: dict) -> dict:
    PROVENANCE_OUT.mkdir(parents=True, exist_ok=True)
    inputs = [
        CATALOG_OUT,
        ROOT / "stylepacks" / "open-bridge.json",
        ROOT / "stylepacks" / "us-paper.json",
        ROOT / "forge" / "scale125_generate.py",
        ROOT / "forge" / "scale125_verify.py",
        ROOT / "forge" / "full_catalog_run.py",
    ]
    atlas_images = sorted(ATLAS_OUT.glob("s52_full_catalog_*.png"))
    outputs = [
        OUT / "report.json",
        OUT / "semantic_report.json",
        OUT / "semantic_hard_pile.json",
        ATLAS_OUT / "helm_s52_atlas_full_catalog.json",
        ATLAS_OUT / "helm_s52_atlas_full_catalog_open-bridge.json",
        ATLAS_OUT / "helm_s52_atlas_full_catalog_us-paper.json",
    ] + atlas_images
    input_hashes = _file_hashes(inputs)
    output_hashes = _file_hashes(outputs)
    signature = hashlib.sha256(
        json.dumps(input_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "generator": "iconforge-full-catalog-provenance",
        "status": "pass" if summary["packable_assets"] == summary["selected_assets"] else "review_required",
        "input_signature": signature,
        "inputs": input_hashes,
        "outputs": output_hashes,
        "summary": summary,
        "clean_ip": {
            "allowed_sources": [
                "public-domain U.S. Chart No.1 references",
                "local chartsymbols.xml / S-52 lookup metadata",
                "Helm-authored generator primitives and stylepacks",
                "fresh generated SVG artwork produced by Icon Forge",
            ],
            "forbidden_sources": [
                "OpenCPN GPL rastersymbols-*.png extraction",
                "copied IHO proprietary chart-publication artwork",
                "private ENC/S-63/oeSENC data or generated caches",
            ],
            "distribution_gate": "Counsel review required before treating the generated pack as redistributable owned artwork.",
        },
    }
    (PROVENANCE_OUT / "full_catalog_provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> int:
    catalog = _select_catalog()
    structural_rows, structural_hard_pile = _generate(catalog)
    semantic_report, semantic_hard_pile = _semantic(catalog)
    atlas_manifest, packable = _build_atlas(catalog)

    summary = {
        "source": str(scale125_select.S52),
        "candidate_rows": catalog["candidate_rows"],
        "selected_assets": catalog["selected_assets"],
        "styles": len(_styles()),
        "palettes": len(PALETTES),
        "svg_outputs": len(structural_rows),
        "png_outputs": len(structural_rows) * len(PALETTES),
        "structural_pass": sum(1 for row in structural_rows if row["structural_pass"]),
        "structural_total": len(structural_rows),
        "semantic_valid_accepts": semantic_report["valid_accepts"],
        "semantic_valid_total": semantic_report["valid_total"],
        "semantic_broken_rejects": semantic_report["broken_rejects"],
        "semantic_broken_total": semantic_report["broken_total"],
        "packable_assets": len(packable),
        "atlas_count": len(atlas_manifest["atlases"]),
        "atlas_entries": len(atlas_manifest["entries"]),
        "structural_hard_pile_entries": len(structural_hard_pile),
        "semantic_hard_pile_entries": len(semantic_hard_pile),
        "family_counts": catalog["family_counts"],
        "asset_kind_counts": catalog["asset_kind_counts"],
        "non_go_conditions": [
            "Do not publish as final navigation-ready artwork until human/counsel approval.",
            "Do not weaken verifier or hide hard-pile entries to increase apparent coverage.",
            "Do not include assets with source-provenance ambiguity in a redistributable owned pack.",
        ],
    }
    provenance = _provenance(catalog, summary)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print("full catalog run:", provenance["status"].upper())
    print(f"candidate rows: {summary['candidate_rows']}")
    print(f"selected assets: {summary['selected_assets']}")
    print(f"valid accepts: {summary['semantic_valid_accepts']}/{summary['semantic_valid_total']}")
    print(f"broken rejects: {summary['semantic_broken_rejects']}/{summary['semantic_broken_total']}")
    print(f"packable assets: {summary['packable_assets']}/{summary['selected_assets']}")
    print(f"atlas entries: {summary['atlas_entries']}")
    print(f"provenance: {PROVENANCE_OUT / 'full_catalog_provenance.json'}")
    return 0 if provenance["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
