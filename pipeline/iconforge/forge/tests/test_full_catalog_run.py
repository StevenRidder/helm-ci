"""Smoke the controlled full-library catalog run.

Run:  python -m forge.tests.test_full_catalog_run
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .. import full_catalog_run


ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "out" / "full_catalog"


def main():
    rc = full_catalog_run.main()
    assert rc == 0, "full catalog controlled run failed"

    catalog = json.loads((ROOT / "pilots" / "full_catalog.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    semantic = json.loads((OUT / "semantic_report.json").read_text())
    atlas = json.loads((OUT / "atlas" / "helm_s52_atlas_full_catalog.json").read_text())
    provenance = json.loads((OUT / "provenance" / "full_catalog_provenance.json").read_text())

    assert catalog["candidate_rows"] >= catalog["selected_assets"] > 800
    assert catalog["selected_assets"] == summary["selected_assets"] == 824
    assert summary["styles"] == 2
    assert summary["palettes"] == 3
    assert summary["svg_outputs"] == 1648
    assert summary["png_outputs"] == 4944
    assert summary["structural_pass"] == summary["structural_total"] == 1648
    assert summary["semantic_valid_accepts"] == summary["semantic_valid_total"] == 1648
    assert summary["semantic_broken_rejects"] == summary["semantic_broken_total"] == 1648
    assert summary["packable_assets"] == summary["selected_assets"] == 824
    assert summary["atlas_count"] == 6
    assert summary["atlas_entries"] == 4944
    assert summary["structural_hard_pile_entries"] == 0
    assert semantic["status"] == "pass"
    assert provenance["status"] == "pass"
    assert provenance["summary"] == summary

    assert atlas["styles"] == ["open-bridge", "us-paper"]
    assert atlas["palettes"] == ["day", "dusk", "night"]
    assert len(atlas["atlases"]) == 6
    assert len(atlas["entries"]) == 4944
    for image in atlas["atlases"]:
        path = OUT / "atlas" / image["image"]
        assert path.exists(), f"missing atlas image {path}"
        assert Image.open(path).size == (image["width"], image["height"])
        assert image["entry_count"] == 824

    for style in atlas["styles"]:
        style_manifest = json.loads((OUT / "atlas" / f"helm_s52_atlas_full_catalog_{style}.json").read_text())
        assert style_manifest["styles"] == [style]
        assert len(style_manifest["atlases"]) == 3
        assert len(style_manifest["entries"]) == 2472
        loader_keys = {
            (entry["name"], entry["kind"], entry["palette"])
            for entry in style_manifest["entries"]
        }
        assert len(loader_keys) == 2472

    assert any("rastersymbols" in s for s in provenance["clean_ip"]["forbidden_sources"])
    assert any("Chart No.1" in s for s in provenance["clean_ip"]["allowed_sources"])
    print("full catalog run: OK")


if __name__ == "__main__":
    main()
