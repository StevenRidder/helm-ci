"""Smoke the exact-crop canonical SVG manifest.

Run:  python -m forge.tests.test_exact_symbol_assets
"""
from __future__ import annotations

from pathlib import Path

from .. import exact_symbol_assets


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    result = exact_symbol_assets.build()
    assert result["status"] == "pass"
    assert result["selected_exact_symbol_crops"] == 139
    assert len(result["entries"]) == 139

    manifest = ROOT / "symbols.yaml"
    assert manifest.exists()
    text = manifest.read_text()
    assert text.startswith("symbols:\n")
    assert text.count("\n  - id: N") == 139
    assert "kind: chart-symbol" in text
    assert "tier: chart-artifact" in text
    assert "origin: generated-owned-artwork" in text
    assert "public-domain Chart No.1 reference" in text
    assert "local metadata lookup" in text
    assert "visual_parity: pending" in text
    assert text.count("chart1:\n        status: exact_symbol_crop") == 139
    assert text.count("s52:\n        object_class:") == 139
    assert text.count("s101:\n        repository: https://github.com/iho-ohi/S-101_Portrayal-Catalogue") == 139
    assert text.count("esri:\n        repository: https://github.com/Esri/nautical-chart-symbols") == 139
    assert text.count("wikimedia:\n        category: https://commons.wikimedia.org/wiki/Category:SVG_Nautical_Chart_icons") == 139
    assert text.count("chart1_mappings:\n        url: \"file:///Users/steveridder/Downloads/Chart%201%20Mappings.pdf\"") == 139
    assert text.count("license_status: per-file-license-review-required") == 139
    assert text.count("permission_required_before_artwork_use") == 139
    assert text.count("source_license_checked: false") == 139
    assert "forbidden_sources:\n        - OpenCPN GPL rastersymbol sprites" in text
    assert "Chart 1 Mappings cropped/extracted artwork without permission" in text
    assert "allowed_use:\n          - name_mapping\n          - s57_object_crosswalk" in text
    assert "forbidden_use:\n          - crop_extract_svg\n          - direct_artwork_derivation" in text
    assert "crop_sha256:" in text
    assert "mapping_status: pending_crosswalk" in text
    assert "mapping_status: pending_per_file_match" in text

    for entry in result["entries"]:
        svg = ROOT / entry["svg"]
        assert svg.exists(), f"missing canonical SVG {svg}"
        body = svg.read_text()
        assert 'data-forge-source="chart1-exact-crop"' in body
        assert f'data-chart1-crop="{entry["chart1_crop"]}"' in body
        assert f'data-s52-asset="{entry["asset"]}"' in body
        assert "M32 32 L32 9" not in body, "star/light flare ray leaked into canonical asset"
        assert 'circle cx="32" cy="32" r="8"' not in body, "light flare center leaked into canonical asset"
        assert "<svg" in body and "</svg>" in body

    first = (ROOT / "assets" / "svg" / "canonical" / "N0001.svg").read_text()
    assert "topmark_cone_down" in first
    assert "TOPMA100" in first
    print("exact symbol assets: OK")


if __name__ == "__main__":
    main()
