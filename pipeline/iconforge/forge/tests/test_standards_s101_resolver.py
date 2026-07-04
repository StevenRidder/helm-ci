"""Smoke the full-catalog S-101 resolver ledger.

Run:  python -m forge.tests.test_standards_s101_resolver
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import standards_s101_resolver


def _row(result: dict, asset: str) -> dict:
    for row in result["rows"]:
        if row["s52_symbol_id"] == asset:
            return row
    raise AssertionError(f"missing asset {asset}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "standards_s101_resolver.json"
        md = Path(tmp) / "standards_s101_resolver.md"
        result = standards_s101_resolver.build()

        assert result["schema"] == "helm.forge.standards-s101-resolver.v1"
        assert result["status"] == "provisional_s101_resolver_ready"
        assert result["coverage"]["rows"] == 824
        assert result["coverage"]["s101_mapping_type_counts"]["direct_asset_match"] == 244
        assert result["coverage"]["s101_mapping_type_counts"]["rule_derived_equivalent"] == 215
        assert result["coverage"]["s101_mapping_type_counts"]["acceptable_deviation"] == 108
        assert result["coverage"]["s101_mapping_type_counts"]["unresolved"] == 257
        assert result["coverage"]["resolver_status_counts"]["resolved_direct"] == 244
        assert result["coverage"]["resolver_status_counts"]["resolved_rule"] == 215
        assert result["coverage"]["resolver_status_counts"]["resolved_rule_catalogue"] == 90
        assert result["coverage"]["resolver_status_counts"]["resolved_with_deviation"] == 108
        assert result["coverage"]["resolver_status_counts"]["classified_non_s101_runtime"] == 44
        assert result["coverage"]["resolver_status_counts"]["classified_extension_requires_profile"] == 123
        assert "unresolved" not in result["coverage"]["resolver_status_counts"]
        assert result["coverage"]["false_filename_gap_count"] == 323
        assert result["clean_room_boundary"]["bundled_iho_catalog_files"] is False
        assert result["clean_room_boundary"]["bundled_opencpn_artwork"] is False

        achare02 = _row(result, "ACHARE02")
        assert achare02["resolver_status"] == "resolved_direct"
        assert achare02["exact_filename_match"] is True
        assert achare02["portrayal_evidence"]["direct_symbol"]["symbol_id"] == "ACHARE02"

        boycan60 = _row(result, "BOYCAN60")
        assert boycan60["resolver_status"] == "resolved_rule"
        assert boycan60["s101_mapping_type"] == "rule_derived_equivalent"
        assert boycan60["exact_filename_match"] is False
        assert boycan60["false_filename_gap"] is True
        assert boycan60["portrayal_evidence"]["feature_type"] == "SpecialPurposeGeneralBuoy"
        assert boycan60["portrayal_evidence"]["attributes"]["buoyShape"] == "can"
        assert boycan60["portrayal_evidence"]["attributes"]["colour"] == ["red"]
        assert boycan60["display_profile"]["profile"] == "paper-chart-full-symbol"

        topmar01 = _row(result, "TOPMAR01")
        assert topmar01["resolver_status"] == "resolved_rule_catalogue"
        assert topmar01["s101_crosswalk_classification"]["basis"] == "s101_catalogue_rule_reference"

        aisdef01 = _row(result, "AISDEF01")
        assert aisdef01["resolver_status"] == "classified_non_s101_runtime"
        assert aisdef01["s101_crosswalk_classification"]["runtime_scope"] == "renderer_overlay_or_ui"

        arcsln01 = _row(result, "ARCSLN01")
        assert arcsln01["resolver_status"] == "resolved_with_deviation"
        assert arcsln01["portrayal_evidence"]["feature_type"] == "ArchipelagicSeaLaneArea"
        assert arcsln01["portrayal_evidence"]["feature_rule_file"] == "PortrayalCatalog/Rules/ArchipelagicSeaLaneArea.lua"
        assert arcsln01["s101_crosswalk_classification"]["basis"] == "s52_s101_portrayal_difference"

        for asset in ("DWLDEF01", "DWRTCL05", "DWRTCL06", "DWRTCL07", "DWRTCL08"):
            row = _row(result, asset)
            assert row["resolver_status"] == "resolved_with_deviation"
            assert row["portrayal_evidence"]["feature_type"] == "DeepWaterRouteCentreline"
            assert row["portrayal_evidence"]["feature_rule_file"] == "PortrayalCatalog/Rules/DeepWaterRouteCentreline.lua"

        for asset in ("LOWACC41", "TIDINF51"):
            row = _row(result, asset)
            assert row["resolver_status"] == "classified_non_s101_runtime"
            assert row["s101_crosswalk_classification"]["class"] == "non_s101_runtime_construct"
            assert row["portrayal_evidence"]["feature_type"] is None
            assert row["portrayal_evidence"]["feature_rule_file"] is None

        standards_s101_resolver._write(out, result)
        md.write_text(standards_s101_resolver._md(result))
        disk = json.loads(out.read_text())
        assert disk["coverage"]["rows"] == 824
        assert "Standards S-101 Resolver" in md.read_text()

    print("standards S-101 resolver: OK")


if __name__ == "__main__":
    main()
