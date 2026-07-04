"""Build the S-101 / Aqua Map / OpenCPN candidate pile.

This is the fast broad-coverage lane Steve requested after FORGE-14/15:
map every S-57/S-52 icon row to the three strongest reference sets, materialize
Helm-owned candidate SVGs wherever we already have a renderer/candidate, and
queue each candidate for one-symbol visual judging.

Run:
  python -m forge.triad_reference_candidate_pack --render
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from . import render
from .style_contract import OPENBRIDGE_NAV_PALETTES


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
ASSET_DIR = ROOT / "assets" / "svg" / "triad_generated"
OUT = ROOT / "out" / "triad_reference_candidate_pack"
RENDER_DIR = OUT / "renders"
PACK_JSON = CATALOG / "triad_reference_candidate_pack.json"
TABLE_CSV = CATALOG / "triad_reference_candidate_table.csv"
PACK_MD = CATALOG / "triad_reference_candidate_pack.md"
JUDGE_QUEUE = OUT / "judge_queue.json"

SOURCE_PRIORITY = CATALOG / "source_priority_icon_pack.json"
MASTER = CATALOG / "master_symbol_list.json"
AQUAMAP = ROOT / "reference_sources" / "aquamap_map_symbols" / "manifest.json"

PALETTES = ("day", "dusk", "night")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _safe_filename(asset: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", asset).strip("_") or "unnamed_asset"


def _rel(path: Path | str | None) -> str | None:
    if not path:
        return None
    path = Path(path)
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _local(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    candidate = ROOT / path
    return candidate if candidate.exists() else None


def _examples(row: dict, source: str) -> list[dict]:
    return [example for example in row.get("examples", []) if example.get("source") == source]


def _opencpn_refs(row: dict) -> list[dict]:
    refs = []
    for example in _examples(row, "opencpn_s52_reference_render"):
        paths = example.get("paths") or example.get("palette_paths") or {}
        day_path = paths.get("day")
        if not _local(day_path):
            continue
        status = example.get("status")
        if status == "pending_render":
            status = "rendered_reference"
        refs.append({
            "source": "opencpn_s52_reference_render",
            "status": status,
            "label": example.get("asset_description") or row.get("name"),
            "paths": paths,
            "day": day_path,
            "license_boundary": "GPL/OpenCPN local visual oracle; reference only, do not copy pixels",
        })
    return refs


def _s101_refs(row: dict) -> list[dict]:
    refs = []
    for source in ("s101_exact_svg", "s101_portrayal_catalogue_svg"):
        for example in _examples(row, source):
            refs.append({
                "source": source,
                "status": example.get("status"),
                "label": example.get("symbol_id") or example.get("title") or row.get("asset"),
                "path": example.get("path"),
                "symbol_id": example.get("symbol_id"),
                "license_boundary": "S-101/IHO license-pending reference; redraw, do not import as canonical unless cleared",
            })
    if not refs and row.get("source_refs", {}).get("s101", {}).get("symbol_id"):
        s101 = row["source_refs"]["s101"]
        refs.append({
            "source": "s101_metadata",
            "status": s101.get("coverage") or s101.get("license_status"),
            "label": s101.get("symbol_id"),
            "path": s101.get("symbol_file"),
            "symbol_id": s101.get("symbol_id"),
            "license_boundary": "S-101/IHO metadata/reference only",
        })
    return refs


def _aquamap_refs(asset: str) -> list[dict]:
    icons = _aquamap_matches(asset)
    return [
        {
            "source": "aquamap_map_symbols",
            "status": ref.get("status"),
            "label": ref.get("label"),
            "path": ref.get("path"),
            "url": ref.get("url"),
            "section": ref.get("section"),
            "license_boundary": "Aqua Map copyrighted support-page image; visual reference only, redraw into Helm-owned SVG",
        }
        for ref in icons
    ]


def _aquamap_icons() -> dict[str, dict]:
    if not AQUAMAP.exists():
        return {}
    manifest = _read_json(AQUAMAP)
    base = AQUAMAP.parent
    return {
        entry["id"]: {
            **entry,
            "path": str((base / entry["local_image"]).relative_to(ROOT)),
        }
        for entry in manifest.get("entries", [])
        if entry.get("local_image")
    }


def _aquamap_matches(asset: str) -> list[dict]:
    icons = _aquamap_icons()
    explicit = {
        "SMCFAC02": ["Marina1"],
        "MORFAC03": ["Piles1", "Mooring1"],
        "MORFAC04": ["Piles1", "Mooring1"],
        "BOYMOR03": ["Mooring1"],
        "BCNSAW13": ["BCNSAW1", "BOYSAW1"],
        "LIGHTS05": ["LIGHTSM11", "LIGHTSY11", "LIGHTSW11", "LIGHTSR11", "LIGHTSG11"],
        "FOGSIG01": ["BELL1"],
        "RADRFL03": ["RadarReflector1"],
        "RDOCAL03": ["RadioCallinPoint1"],
        "RDOSTA02": ["RadioCallinPoint1"],
        "WRECKS04": ["SubmergedWreck1", "DangerousWreck1", "EmergedWreck1"],
        "UWTROC04": ["SubmergedRock11", "DangerousRock11", "EmergedRock11"],
    }
    ids = list(explicit.get(asset, []))
    family_prefixes = {
        "BOYCAR": "BOYCAR",
        "BCNCAR": "BCNCAR",
        "BOYISD": "BOYISD",
        "BCNISD": "BCNISD",
        "BOYSAW": "BOYSAW",
        "BCNSAW": "BCNSAW",
        "BOYSPP": "BOYSPP",
        "BCNSPP": "BCNSPP",
        "LIGHTS": "LIGHTS",
    }
    for asset_prefix, icon_prefix in family_prefixes.items():
        if asset.startswith(asset_prefix):
            ids.extend(icon_id for icon_id in icons if icon_id.startswith(icon_prefix))
    semantic = []
    if asset.startswith("WRECKS"):
        semantic = ["SubmergedWreck1", "DangerousWreck1", "EmergedWreck1"]
    elif asset.startswith(("UWTROC", "WTROC")):
        semantic = ["SubmergedRock11", "DangerousRock11", "EmergedRock11"]
    elif asset.startswith("OBSTRN"):
        semantic = ["Obstruction1"]
    elif asset.startswith("SMCFAC"):
        semantic = ["Marina1", "BoatRamp1", "WaterTower1"]
    elif asset.startswith(("MORFAC", "BOYMOR")):
        semantic = ["Mooring1", "Piles1"]
    elif asset.startswith("RADRFL"):
        semantic = ["RadarReflector1"]
    elif asset.startswith(("RDOCAL", "RDOSTA")):
        semantic = ["RadioCallinPoint1", "RadarStation1"]
    elif asset.startswith("FOGSIG"):
        semantic = ["BELL1"]
    elif asset.startswith("ACH"):
        semantic = ["AnchoringProhibited1"]
    elif asset.startswith("CHIMNY"):
        semantic = ["Chimney1"]
    elif asset.startswith("CRANES"):
        semantic = ["Crane1"]
    elif asset.startswith("TOWERS"):
        semantic = ["Tower1", "LightedTower1", "WaterTower1"]
    ids.extend(semantic)
    seen = set()
    matches = []
    for icon_id in ids:
        if icon_id in seen or icon_id not in icons:
            continue
        seen.add(icon_id)
        matches.append(icons[icon_id])
    return matches


def _owned_candidates() -> dict[str, dict]:
    candidates: dict[str, dict] = {}
    def batch_number(path: Path) -> int:
        match = re.search(r"owned_repair_batch(\d+)", path.name)
        return int(match.group(1)) if match else -1

    for path in sorted(CATALOG.glob("owned_repair_batch*.json"), key=batch_number):
        data = _read_json(path)
        for row in data.get("symbols", []):
            asset = row.get("asset")
            after_svg = row.get("after_svg")
            if not asset or not after_svg:
                continue
            candidates[asset] = {
                "source": "owned_repair_batch",
                "asset": asset,
                "svg": after_svg,
                "renders": row.get("after_renders") or {},
                "batch": _rel(path),
                "qa": row.get("qa", {}),
                "provenance": row.get("provenance", {}),
                "repair_note": row.get("repair_note"),
            }
    return candidates


def _candidate_source(row: dict, owned: dict[str, dict]) -> dict | None:
    asset = row["asset"]
    if asset in owned:
        return owned[asset]
    basis = row["source_priority"]["selected_basis"]
    fallback = row["source_priority"].get("fallback_generated_asset_file")
    if fallback:
        return {
            "source": "source_priority_fallback_generated",
            "asset": asset,
            "svg": fallback,
            "renders": {},
            "batch": None,
            "qa": row.get("qa", {}),
            "provenance": {"origin": "generated-owned-artwork"},
            "repair_note": "fallback generated-owned SVG selected for triad candidate pile",
        }
    if basis == "helm_multisource_draft_svg" and row.get("asset_file"):
        return {
            "source": "helm_multisource_draft_svg",
            "asset": asset,
            "svg": row["asset_file"],
            "renders": {},
            "batch": None,
            "qa": row.get("qa", {}),
            "provenance": row.get("provenance", {}),
            "repair_note": "draft generated-owned SVG selected for triad candidate pile",
        }
    return None


def _master_by_asset() -> dict[str, dict]:
    if not MASTER.exists():
        return {}
    return {row["asset"]: row for row in _read_json(MASTER)["rows"]}


def _source_priority_rows() -> list[dict]:
    return _read_json(SOURCE_PRIORITY)["symbols"]


def _write_candidate_svg(asset: str, source_svg: str) -> str | None:
    src = _local(source_svg)
    if not src:
        return None
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    dest = ASSET_DIR / f"{_safe_filename(asset)}.svg"
    shutil.copyfile(src, dest)
    return _rel(dest)


def _render_candidate(asset: str, svg_path: str, render_outputs: bool) -> dict[str, str]:
    if not render_outputs:
        return {}
    source = _local(svg_path)
    if not source:
        return {}
    svg = source.read_text()
    renders = {}
    for palette in PALETTES:
        out = RENDER_DIR / f"{_safe_filename(asset)}__{palette}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(render.rasterize(svg, OPENBRIDGE_NAV_PALETTES[palette], size=160))
        renders[palette] = _rel(out)
    return renders


def _row_record(row: dict, master: dict | None, owned: dict[str, dict], render_outputs: bool) -> tuple[dict, dict | None]:
    asset = row["asset"]
    s101 = _s101_refs(row)
    aquamap = _aquamap_refs(asset)
    opencpn = _opencpn_refs(row)
    candidate_source = _candidate_source(row, owned)
    candidate = None
    if candidate_source:
        canonical = _write_candidate_svg(asset, candidate_source["svg"])
        renders = _render_candidate(asset, canonical, render_outputs) if canonical else {}
        candidate = {
            "canonical": canonical,
            "source_svg": candidate_source["svg"],
            "source": candidate_source["source"],
            "source_batch": candidate_source.get("batch"),
            "renders": renders,
            "qa": {
                "semantic_pass": bool(candidate_source.get("qa", {}).get("semantic_pass", row.get("qa", {}).get("semantic_pass", True))),
                "visual_parity": candidate_source.get("qa", {}).get("visual_parity") or "pending_llm_judge",
                "final_approved": False,
            },
            "provenance": {
                "origin": "generated-owned-artwork",
                "allowed_sources": ["S-57/S-52 metadata", "S-101 reference", "Aqua Map visual reference", "OpenCPN visual oracle"],
                "source_art_policy": "redrawn/generated-owned candidate; reference art is not canonical",
            },
        }

    triad = {
        "s101": s101,
        "aquamap": aquamap,
        "opencpn": opencpn,
    }
    covered = any(triad.values())
    record = {
        "id": asset,
        "asset": asset,
        "name": row.get("name"),
        "kind": row.get("kind"),
        "family": row.get("family"),
        "s57": {
            "object_class": (master or {}).get("s57_object_class"),
            "conditions": (master or {}).get("s57_conditions", []),
            "instruction": (master or {}).get("s52_instruction"),
        },
        "s101_symbol_id": (master or {}).get("s101_symbol_id") or (s101[0].get("symbol_id") if s101 else None),
        "triad_refs": triad,
        "triad_coverage": {
            "s101": bool(s101),
            "aquamap": bool(aquamap),
            "opencpn": bool(opencpn),
            "any": covered,
        },
        "asset": {
            "canonical": candidate["canonical"] if candidate else None,
            "renders": candidate["renders"] if candidate else {},
            "source": candidate["source"] if candidate else None,
            "source_batch": candidate["source_batch"] if candidate else None,
            "source_svg": candidate["source_svg"] if candidate else None,
        },
        "qa": candidate["qa"] if candidate else {
            "semantic_pass": bool(row.get("qa", {}).get("semantic_pass", True)),
            "visual_parity": "not_started_no_svg_candidate",
            "final_approved": False,
        },
        "provenance": candidate["provenance"] if candidate else {
            "origin": "not_generated_yet",
            "source_art_policy": "reference coverage exists but Helm SVG renderer/candidate is missing",
        },
    }
    return record, candidate


def _judge_item(record: dict) -> dict:
    refs = []
    for group in ("s101", "aquamap", "opencpn"):
        refs.extend({**ref, "group": group} for ref in record["triad_refs"][group])
    return {
        "status": "queued_for_one_symbol_llm_judge",
        "asset": record["id"],
        "name": record["name"],
        "candidate_svg": record["asset"]["canonical"],
        "candidate_render": record["asset"]["renders"].get("day"),
        "s57": record["s57"],
        "s101_symbol_id": record["s101_symbol_id"],
        "reference_candidates": refs,
        "judge_contract": {
            "compare": "candidate against S-101/Aqua Map/OpenCPN references one symbol at a time",
            "output": ["overall_pass", "judge_comments", "required_change", "reference_used", "confidence"],
            "on_fail": "enqueue renderer repair for this asset only, then rerun judge",
        },
    }


def _write_csv(rows: list[dict]) -> None:
    TABLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "asset", "name", "kind", "family", "s57_object_class", "s57_conditions",
        "s52_instruction", "s101_symbol_id", "has_s101", "has_aquamap", "has_opencpn",
        "canonical_svg", "day_render", "visual_parity",
    ]
    with TABLE_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "asset": row["id"],
                "name": row["name"],
                "kind": row["kind"],
                "family": row["family"],
                "s57_object_class": row["s57"]["object_class"],
                "s57_conditions": ";".join(row["s57"]["conditions"]),
                "s52_instruction": row["s57"]["instruction"],
                "s101_symbol_id": row["s101_symbol_id"],
                "has_s101": row["triad_coverage"]["s101"],
                "has_aquamap": row["triad_coverage"]["aquamap"],
                "has_opencpn": row["triad_coverage"]["opencpn"],
                "canonical_svg": row["asset"]["canonical"],
                "day_render": row["asset"]["renders"].get("day"),
                "visual_parity": row["qa"]["visual_parity"],
            })


def _write_md(result: dict) -> None:
    lines = [
        "# Triad Reference Candidate Pack",
        "",
        "S-57/S-52 icon rows mapped to S-101, Aqua Map, and OpenCPN references.",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Outputs",
        "",
        f"- JSON: `{PACK_JSON.relative_to(ROOT)}`",
        f"- CSV table: `{TABLE_CSV.relative_to(ROOT)}`",
        f"- Judge queue: `{JUDGE_QUEUE.relative_to(ROOT)}`",
        "",
        "## Policy",
        "",
        "- S-101, Aqua Map, and OpenCPN are reference inputs for shape/semantic matching.",
        "- Canonical Helm candidates are generated-owned SVGs under `assets/svg/triad_generated/`.",
        "- No row is visually approved until the one-symbol LLM judge passes it.",
        "- Rows with references but no SVG renderer/candidate stay in the hard-pile.",
    ])
    PACK_MD.write_text("\n".join(lines) + "\n")


def build(*, render_outputs: bool = False) -> dict:
    rows = _source_priority_rows()
    master = _master_by_asset()
    owned = _owned_candidates()
    records = []
    judge_queue = []
    hard_pile = []
    for row in rows:
        record, candidate = _row_record(row, master.get(row["asset"]), owned, render_outputs)
        records.append(record)
        if candidate and record["triad_coverage"]["any"]:
            judge_queue.append(_judge_item(record))
        elif not candidate:
            hard_pile.append({
                "asset": record["id"],
                "name": record["name"],
                "reason": "triad_reference_exists_but_no_helm_svg_candidate_or_renderer"
                if record["triad_coverage"]["any"]
                else "no_provider_reference_and_no_helm_svg_candidate",
                "kind": record["kind"],
                "family": record["family"],
                "triad_coverage": record["triad_coverage"],
            })

    coverage_counts = Counter()
    for record in records:
        for key in ("s101", "aquamap", "opencpn"):
            if record["triad_coverage"][key]:
                coverage_counts[key] += 1

    canonical_count = sum(1 for record in records if record["asset"]["canonical"])
    result = {
        "schema_version": 1,
        "generator": "iconforge-triad-reference-candidate-pack",
        "status": "candidate_pile_pending_llm_judge",
        "summary": {
            "triad_rows": len(records),
            "generated_candidate_svgs": canonical_count,
            "reference_backed_judge_queue_rows": len(judge_queue),
            "hard_pile_no_svg_candidate": len(hard_pile),
            "s101_rows": coverage_counts["s101"],
            "aquamap_rows": coverage_counts["aquamap"],
            "opencpn_rows": coverage_counts["opencpn"],
            "reference_gap_candidate_rows": sum(
                1 for record in records if record["asset"]["canonical"] and not record["triad_coverage"]["any"]
            ),
            "rendered_candidate_pngs": sum(len(item["asset"]["renders"]) for item in records),
        },
        "rows": records,
        "judge_queue": judge_queue,
        "hard_pile": hard_pile,
        "outputs": {
            "json": str(PACK_JSON.relative_to(ROOT)),
            "csv": str(TABLE_CSV.relative_to(ROOT)),
            "markdown": str(PACK_MD.relative_to(ROOT)),
            "judge_queue": str(JUDGE_QUEUE.relative_to(ROOT)),
            "candidate_svg_dir": str(ASSET_DIR.relative_to(ROOT)),
            "render_dir": str(RENDER_DIR.relative_to(ROOT)) if render_outputs else None,
        },
    }
    PACK_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_csv(records)
    _write_md(result)
    OUT.mkdir(parents=True, exist_ok=True)
    JUDGE_QUEUE.write_text(json.dumps({
        "schema_version": 1,
        "status": "queued_for_llm_visual_judge",
        "summary": result["summary"],
        "items": judge_queue,
    }, indent=2, sort_keys=True) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="render day/dusk/night PNGs for each generated candidate")
    args = parser.parse_args(argv)
    result = build(render_outputs=args.render)
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "outputs": result["outputs"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
