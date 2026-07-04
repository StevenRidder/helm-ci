"""Smoke the full-catalog three-way proof artifact.

Run:  python -m forge.tests.test_standards_three_way_proof
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .. import standards_three_way_proof


def _row(result: dict, asset: str) -> dict:
    for row in result["rows"]:
        if row["asset"] == asset:
            return row
    raise AssertionError(f"missing asset {asset}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out = tmp_dir / "standards_three_way_proof.json"
        md = tmp_dir / "standards_three_way_proof.md"
        html = tmp_dir / "standards_three_way_proof.html"
        result = standards_three_way_proof.build()

        assert result["schema"] == "helm.forge.three-way-proof.v1"
        assert result["status"] == "provisional_three_way_proof_ready"
        assert result["coverage"]["rows"] == 824
        assert result["coverage"]["gate_status"] == "review_required"
        assert result["coverage"]["review_state_counts"]["review_required"] == 824
        assert result["coverage"]["resolver_status_counts"]["resolved_direct"] == 244
        assert result["coverage"]["resolver_status_counts"]["resolved_rule"] == 215
        assert result["coverage"]["resolver_status_counts"]["resolved_rule_catalogue"] == 90
        assert result["coverage"]["resolver_status_counts"]["resolved_with_deviation"] == 108
        assert result["coverage"]["s101_crosswalk_class_counts"]["s101_feature_equivalent"] == 549
        assert result["coverage"]["s101_crosswalk_class_counts"]["non_s101_runtime_construct"] == 44
        assert result["coverage"]["false_filename_gap_count"] == 323

        achare02 = _row(result, "ACHARE02")
        assert achare02["s101_evidence"]["resolver_status"] == "resolved_direct"
        assert achare02["s52_opencpn_expected"]["comparison_reference"]["paths"]["day"].endswith("ACHARE02__day.png")
        assert achare02["helm_candidate"]["canonical_svg"].endswith("ACHARE02.svg")

        boycan60 = _row(result, "BOYCAN60")
        assert boycan60["s101_evidence"]["resolver_status"] == "resolved_rule"
        assert boycan60["s101_evidence"]["false_filename_gap"] is True
        assert boycan60["s101_evidence"]["portrayal_evidence"]["feature_type"] == "SpecialPurposeGeneralBuoy"
        assert boycan60["helm_candidate"]["origin"] == "generated-owned-artwork"
        assert boycan60["review_state"] == "review_required"

        topmar01 = _row(result, "TOPMAR01")
        assert topmar01["s101_evidence"]["resolver_status"] == "resolved_rule_catalogue"
        assert topmar01["s101_evidence"]["s101_crosswalk_classification"]["basis"] == "s101_catalogue_rule_reference"

        arcsln01 = _row(result, "ARCSLN01")
        assert arcsln01["s101_evidence"]["resolver_status"] == "resolved_with_deviation"
        assert arcsln01["s101_evidence"]["portrayal_evidence"]["feature_type"] == "ArchipelagicSeaLaneArea"
        assert arcsln01["s101_evidence"]["s101_crosswalk_classification"]["class"] == "s101_feature_equivalent_with_documented_deviation"

        lowacc41 = _row(result, "LOWACC41")
        assert lowacc41["s101_evidence"]["resolver_status"] == "classified_non_s101_runtime"
        assert lowacc41["s101_evidence"]["s101_crosswalk_classification"]["class"] == "non_s101_runtime_construct"

        standards_three_way_proof._write(out, result)
        md.write_text(standards_three_way_proof._md(result))
        html.write_text(standards_three_way_proof._html(result))
        disk = json.loads(out.read_text())
        assert disk["coverage"]["rows"] == 824
        assert "Standards Three-Way Proof" in md.read_text()
        assert "BOYCAN60" in html.read_text()
        assert "review_required" in html.read_text()

    print("standards three-way proof: OK")


if __name__ == "__main__":
    main()
