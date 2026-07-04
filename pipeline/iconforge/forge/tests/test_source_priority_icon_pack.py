"""Smoke the full-catalog source-priority icon pack.

Run:  python -m forge.tests.test_source_priority_icon_pack
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .. import source_priority_icon_pack


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    output = source_priority_icon_pack.build()
    summary = output["summary"]
    rows = output["symbols"]
    by_asset = {row["asset"]: row for row in rows}

    assert summary["master_rows"] == 824
    assert summary["usable_svg_rows"] == 747
    assert summary["coverage_percent"] == 90.66
    assert summary["selected_s101_exact_svgs"] == 244
    assert summary["selected_helm_draft_svgs"] == 503
    assert summary["hard_pile_rows"] == 77
    assert summary["origin_counts"] == {
        "generated-owned-artwork": 503,
        "license_pending_reference_art": 244,
        "not_generated_yet": 77,
    }

    for asset in ["WRECKS04", "MORFAC03", "MORFAC04", "ACHARE02", "SMCFAC02"]:
        row = by_asset[asset]
        assert row["source_priority"]["selected_basis"] == "s101_exact_svg"
        assert row["provenance"]["origin"] == "license_pending_reference_art"
        assert row["qa"]["visual_parity"] == "reference_exact_pending_license"
        assert row["source_priority"]["fallback_generated_asset_file"]
        svg_path = ROOT / row["asset_file"]
        assert svg_path.exists()
        svg = svg_path.read_text()
        assert f'data-s52-asset="{asset}"' in svg
        assert 'data-origin="license-pending-s101-reference-art"' in svg
        assert "<?xml-stylesheet" not in svg
        assert ".sCHBLK" in svg
        ET.fromstring(svg)

    draft = by_asset["ACHPNT01"]
    assert draft["source_priority"]["selected_basis"] == "helm_multisource_draft_svg"
    assert draft["provenance"]["origin"] == "generated-owned-artwork"
    assert draft["qa"]["visual_parity"] == "pending_repair"
    assert (ROOT / draft["asset_file"]).exists()
    assert len(draft["palette_targets"]) == 3

    hard_pile = by_asset["ARCSLN01"]
    assert hard_pile["source_priority"]["selected_basis"] == "no_svg_renderer_yet"
    assert hard_pile["asset_file"] is None
    assert hard_pile["provenance"]["origin"] == "not_generated_yet"

    assert (ROOT / "catalog" / "source_priority_icon_pack.json").exists()
    assert (ROOT / "catalog" / "source_priority_icon_pack.yaml").exists()
    assert (ROOT / "catalog" / "source_priority_icon_pack.md").exists()
    assert len(list((ROOT / "assets" / "svg" / "source_priority" / "s101_exact").glob("*.svg"))) == 244
    print("source-priority icon pack: OK")


if __name__ == "__main__":
    main()
