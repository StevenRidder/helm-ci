"""Smoke the multi-source draft SVG pack.

Run:  python -m forge.tests.test_multisource_svg_pack
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .. import multisource_svg_pack


ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    output = multisource_svg_pack.build()
    summary = output["summary"]
    rows = output["symbols"]

    assert summary["master_rows"] == 824
    assert summary["generated_symbol_svgs"] == 740
    assert summary["manifest_only_rows"] == 84
    assert summary["visual_approvals"] == 0
    assert summary["kind_counts"] == {
        "conditional-procedure": 23,
        "line-style": 38,
        "pattern": 24,
        "symbol": 739,
    }
    assert summary["source_counts"]["opencpn_asset_defs"] > 700
    assert summary["source_counts"]["opencpn_lookup_refs"] == 824
    assert summary["source_counts"]["chart1_mappings_refs"] == 372
    assert summary["example_source_counts"]["chart1_mappings_symbol_reference"] > 1400
    assert summary["source_counts"]["s101_exact"] == 244
    assert summary["palette_targets_per_generated_svg"] == 3
    assert summary["palette_target_count"] == 2220
    assert summary["example_source_counts"]["helm_generated_draft_svg"] == 740
    assert summary["example_source_counts"]["opencpn_s52_reference_render"] == 824
    assert summary["example_source_counts"]["s101_portrayal_catalogue_svg"] == 244
    assert summary["example_source_counts"]["wikimedia_commons_svg"] >= 34
    assert sum(count for bucket, count in summary["example_count_buckets"].items() if int(bucket) >= 3) > 300

    by_asset = {row["asset"]: row for row in rows}
    for asset, shape in {
        "BOYCON60": "conical_buoy",
        "BOYCAN60": "can_buoy",
        "BOYSPH60": "spherical_buoy",
        "BOYPIL60": "pillar_buoy",
        "BOYSPR60": "spar_buoy",
        "BOYBAR60": "barrel_buoy",
        "BOYCAR01": "cardinal_mark",
        "TOPMA114": "topmark",
        "WRECKS04": "wreck",
    }.items():
        row = by_asset[asset]
        assert row["asset_file"]
        assert row["geometry"]["shape"] == shape
        assert row["source_refs"]["opencpn_s52"]["asset_definition"]["name"] == asset
        assert row["source_refs"]["opencpn_s52"]["role"] == "reference_oracle_not_canonical_artwork"
        assert row["qa"]["visual_parity"] == "pending"
        assert row["qa"]["final_approved"] is False
        assert row["provenance"]["origin"] == "generated-owned-artwork"
        assert len(row["palette_targets"]) == 3
        assert {target["palette"] for target in row["palette_targets"]} == {"day", "dusk", "night"}
        assert all(target["render_status"] == "pending_render" for target in row["palette_targets"])
        assert row["examples"][0]["source"] == "helm_generated_draft_svg"
        assert any(example["source"] == "opencpn_s52_reference_render" for example in row["examples"])
        svg_path = ROOT / row["asset_file"]
        assert svg_path.exists()
        svg = svg_path.read_text()
        assert f'data-s52-asset="{asset}"' in svg
        assert 'data-reference-oracle="opencpn-s52"' in svg
        assert "var(--" in svg
        assert "rastersymbol" not in svg.lower()
        ET.fromstring(svg)

    achare51 = by_asset["ACHARE51"]
    assert achare51["asset_file"]
    assert achare51["source_refs"]["s101"]["coverage"] == "exact_symbol_match"
    assert achare51["source_refs"]["commons"]["pd_candidate_count"] == 4
    assert any(example["source"] == "s101_portrayal_catalogue_svg" for example in achare51["examples"])
    assert any(example["source"] == "wikimedia_commons_svg" for example in achare51["examples"])

    line_style = next(row for row in rows if row["kind"] == "line-style")
    assert line_style["asset_file"] is None
    assert not line_style["palette_targets"]
    assert any(example["source"] == "opencpn_s52_reference_render" for example in line_style["examples"])
    assert line_style["qa"]["review_status"] == "renderer_not_yet_implemented"
    assert line_style["provenance"]["origin"] == "not_generated_yet"

    assert (ROOT / "catalog" / "multisource_svg_draft_pack.json").exists()
    assert (ROOT / "catalog" / "multisource_svg_draft_pack.yaml").exists()
    assert (ROOT / "catalog" / "multisource_svg_draft_pack.md").exists()
    topmar01 = by_asset["TOPMAR01"]
    assert topmar01["asset_file"]
    assert topmar01["geometry"]["shape"] == "topmark"
    assert len(topmar01["palette_targets"]) == 3

    assert len(list((ROOT / "assets" / "svg" / "multisource_draft").glob("*.svg"))) == 740
    print("multi-source SVG draft pack: OK")


if __name__ == "__main__":
    main()
