#!/usr/bin/env python3
"""Attach public comparison thumbnails to the static symbol catalog.

The public catalog is intentionally static: the browser reads only
pipeline/iconforge/public/proof/site-index.json.  This script makes the
comparison images explicit in that index and copies only files that exist in the
local source tree into the public bundle.

OpenCPN render paths are recorded as comparison evidence, but this branch does
not ship the generated OpenCPN PNGs.  Missing paths are therefore recorded as
missing instead of guessed or silently replaced.
"""
from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ICONFORGE = ROOT / "pipeline" / "iconforge"
PUBLIC = ICONFORGE / "public"
SITE_INDEX = PUBLIC / "proof" / "site-index.json"
SOURCE_PRIORITY = ICONFORGE / "catalog" / "source_priority_icon_pack.json"
COMPARISON_DIR = PUBLIC / "assets" / "comparison"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def _copy_public(src: Path, dest_rel: str) -> str:
    if not src.exists():
        raise FileNotFoundError(src)
    dest = PUBLIC / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or src.read_bytes() != dest.read_bytes():
        shutil.copyfile(src, dest)
    return dest_rel


def _compact_write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n")


def _find_s101_exact(row: dict[str, Any]) -> Path | None:
    for example in row.get("examples") or []:
        if example.get("source") == "s101_exact_svg" and example.get("path"):
            path = ICONFORGE / example["path"]
            if path.exists():
                return path
    asset_file = row.get("asset_file")
    if asset_file and "/s101_exact/" in asset_file:
        path = ICONFORGE / asset_file
        if path.exists():
            return path
    return None


def _find_opencpn_day(row: dict[str, Any]) -> tuple[Path | None, dict[str, str]]:
    declared: dict[str, str] = {}
    for example in row.get("examples") or []:
        if example.get("source") != "opencpn_s52_reference_render":
            continue
        declared = dict(example.get("paths") or {})
        day = declared.get("day")
        if day:
            path = ICONFORGE / day
            if path.exists():
                return path, declared
    return None, declared


def build() -> dict[str, Any]:
    site = _load_json(SITE_INDEX)
    source = _load_json(SOURCE_PRIORITY)
    source_by_asset = {row.get("asset"): row for row in source.get("symbols", [])}

    counts: Counter[str] = Counter()
    for symbol in site.get("symbols", []):
        sid = symbol.get("id")
        source_row = source_by_asset.get(sid) or {}
        comparison: dict[str, Any] = {}

        s101 = _find_s101_exact(source_row)
        if s101:
            public_path = _copy_public(s101, f"assets/comparison/s101/{sid}.svg")
            comparison["s101"] = {
                "image": public_path,
                "role": "visual_witness_only",
                "source": "s101_exact_svg",
                "status": "available",
                "note": "S-101 visual witness; not Helm canonical artwork.",
            }
            counts["s101_available"] += 1
        else:
            counts["s101_missing"] += 1

        opencpn, declared = _find_opencpn_day(source_row)
        if opencpn:
            public_path = _copy_public(opencpn, f"assets/comparison/opencpn/{sid}__day{opencpn.suffix}")
            comparison["opencpn"] = {
                "image": public_path,
                "role": "comparison_target_only",
                "source": "opencpn_s52_reference_render",
                "status": "available",
                "note": "OpenCPN render output is comparison evidence only.",
            }
            counts["opencpn_available"] += 1
        elif declared:
            comparison["opencpn"] = {
                "role": "comparison_target_only",
                "source": "opencpn_s52_reference_render",
                "status": "declared_missing",
                "declared_paths": declared,
                "note": "OpenCPN render path is declared, but the PNG is not present in this public export.",
            }
            counts["opencpn_declared_missing"] += 1

        if comparison:
            symbol["comparison"] = comparison
        elif "comparison" in symbol:
            del symbol["comparison"]

    coverage = site.setdefault("coverage", {})
    coverage["comparison_visuals"] = dict(sorted(counts.items()))
    _compact_write(SITE_INDEX, site)

    summary = {
        "schema": "helm.forge.public_comparison_assets.v1",
        "site_index": "proof/site-index.json",
        "comparison_dir": "assets/comparison",
        "counts": dict(sorted(counts.items())),
    }
    _compact_write(PUBLIC / "proof" / "comparison-assets.json", summary)
    return summary


def main() -> None:
    summary = build()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
